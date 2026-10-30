/**
 * Node Helper for MMM-RemoteTempMonitor
 * Listens for UDP temperature broadcasts from remote devices
 */

const NodeHelper = require("node_helper");
const dgram = require("dgram");
const os = require("os");
const fs = require("fs");
const { execFile } = require("child_process");
const protocol = require("./lib/protocol");
const http = require("http");
const path = require("path");

const VERSION_FILE = path.join(__dirname, "remote-service", "VERSION");

function parseVersion(version) {
    const match = String(version || "").trim().match(/^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?/);
    return match ? [match[1], match[2] || 0, match[3] || 0].map(Number) : null;
}

// Returns true when `installed` is missing/unparseable or older than `latest`.
function isServiceOutdated(installed, latest) {
    const latestParts = parseVersion(latest);
    if (!latestParts) {
        return false;
    }
    const installedParts = parseVersion(installed);
    if (!installedParts) {
        return true;
    }
    for (let i = 0; i < 3; i += 1) {
        if (installedParts[i] !== latestParts[i]) {
            return installedParts[i] < latestParts[i];
        }
    }
    return false;
}

module.exports = NodeHelper.create({
    isServiceOutdated,

    start: function() {
        this.started = false;
        this.stopping = false;
        this.retryTimer = null;
        this.publishTimer = null;
        this.pendingUpdates = new Set();
        this.latestServiceVersion = null;
        this.packetWindow = 0;
        this.packetCount = 0;
        this.lastPacketWarning = 0;
        this.devices = Object.create(null);
        this.server = null;
        this.config = null;
        this.localMonitorTimer = null;
        this.cleanupTimer = null;
        this.statusDevices = Object.create(null);
        this.tempsEndpointRegistered = false;
        this.aggregateHttpServer = null;
        this.aggregateHttpEndpointPath = null;
        this.latestUpdateAt = null;
        console.log("Starting node_helper for: " + this.name);
    },

    socketNotificationReceived: function(notification, payload) {
        if (notification === "CONFIG") {
            if (!payload || typeof payload !== "object") return;
            const numericSettings = { port: [1, 65535], updateInterval: [100, 3600000], cleanupInterval: [100, 3600000], maxDevices: [1, 4096], maxPacketAge: [1000, 3600000], maxDeviceAge: [1000, 86400000], statusMaxDeviceAge: [1000, 86400000] };
            for (const [key, [minimum, maximum]] of Object.entries(numericSettings)) {
                if (payload[key] !== undefined && (!Number.isInteger(payload[key]) || payload[key] < minimum || payload[key] > maximum)) {
                    this.sendSocketNotification("CONFIG_ERROR", `Invalid ${key}`);
                    return;
                }
            }
            if (this.config) {
                const keys = ["port", "sharedSecret", "snapshotToken", "aggregatePort", "aggregateHost", "aggregateEndpointPath", "tempsEndpointPath", "monitorLocalHost", "updateInterval", "cleanupInterval", "maxDeviceAge", "statusMaxDeviceAge", "maxDevices", "maxPacketAge", "latestServiceVersion"];
                if (keys.some(key => JSON.stringify(this.config[key]) !== JSON.stringify(payload[key]))) {
                    console.error("[MMM-RemoteTempMonitor] Conflicting helper configuration; all instances must share listener settings");
                    this.sendSocketNotification("CONFIG_ERROR", "All instances must share helper settings");
                    return;
                }
            } else {
                this.config = { ...payload };
                this.latestServiceVersion = this.getLatestServiceVersion();
            }
            if (!this.started) {
                this.registerTempsEndpoint();
                this.startAggregateHttpServer();
                this.startListening();
                this.started = true;
                this.sendSocketNotification("TEMPERATURE_UPDATE", this.getDeviceList());
            } else {
                this.sendSocketNotification("TEMPERATURE_UPDATE", this.getDeviceList());
                this.sendSocketNotification("STATUS_UPDATE", { devices: Object.values(this.statusDevices) });
            }
        }
    },

    startListening: function() {
        if (this.stopping || this.server) return;
        const port = this.config.port || 9876;

        try {
            this.server = dgram.createSocket({ type: 'udp4', reuseAddr: true });

            const server = this.server;
            server.on('error', (err) => {
                console.error(`[MMM-RemoteTempMonitor] Server error: ${err.message}`);
                try { server.close(); } catch (_) { /* Already closed or not bound. */ }
                if (this.server === server) this.server = null;
                this.scheduleListenerRetry();
            });

            this.server.on('message', (msg, rinfo) => {
                this.handleMessage(msg, rinfo);
            });

            this.server.on('listening', () => {
                const address = server.address();
                console.log(`[MMM-RemoteTempMonitor] UDP listener started on port ${address.port}`);

                // Enable broadcast reception
                try {
                    server.setBroadcast(true);
                } catch (e) {
                    console.error(`[MMM-RemoteTempMonitor] Could not set broadcast: ${e}`);
                }
            });

            this.server.bind(port);

            // Set up periodic cleanup of stale devices
            if (!this.cleanupTimer) this.startCleanupTimer();
            if (this.config.monitorLocalHost && !this.localMonitorTimer) {
                this.startLocalMachineMonitor();
            }

        } catch (err) {
            console.error(`[MMM-RemoteTempMonitor] Failed to start UDP listener: ${err}`);
            if (this.server) { try { this.server.close(); } catch (_) {} }
            this.server = null;
            this.scheduleListenerRetry();
        }
    },

    scheduleListenerRetry: function() {
        if (this.stopping || this.retryTimer) return;
        this.retryTimer = setTimeout(() => {
            this.retryTimer = null;
            this.startListening();
        }, 5000);
    },

    warnInvalidPacket: function() {
        if (Date.now() - (this.lastPacketWarning || 0) < 10000) return;
        this.lastPacketWarning = Date.now();
        console.warn("[MMM-RemoteTempMonitor] Ignored invalid packet(s)");
    },

    queueUpdate: function(kind) {
        if (this.stopping) return;
        this.pendingUpdates = this.pendingUpdates || new Set();
        this.pendingUpdates.add(kind);
        if (this.publishTimer) return;
        this.publishTimer = setTimeout(() => {
            this.publishTimer = null;
            const pending = [...this.pendingUpdates];
            this.pendingUpdates.clear();
            for (const notification of pending) {
                this.sendSocketNotification(notification, notification === "STATUS_UPDATE"
                    ? { devices: Object.values(this.statusDevices) } : this.getDeviceList());
            }
        }, 250);
    },

    getLatestServiceVersion: function() {
        if (this.config && this.config.latestServiceVersion) {
            return String(this.config.latestServiceVersion);
        }
        try {
            return fs.readFileSync(VERSION_FILE, "utf8").trim();
        } catch (err) {
            return null;
        }
    },

    handleMessage: function(msg, rinfo) {
        try {
            if (this.stopping || msg.length > 4096) return;
            const window = Math.floor(Date.now() / 1000);
            if (this.packetWindow !== window) { this.packetWindow = window; this.packetCount = 0; }
            if (++this.packetCount > 100) return;
            const rawMessage = msg.toString();
            const data = JSON.parse(rawMessage);
            if (data && data.type === "status") {
                this.handleStatusMessage(data, rawMessage, rinfo);
                return;
            }
            const validated = this.validateTemperatureMessage(data, rawMessage);

            if (!validated.valid) {
                this.warnInvalidPacket();
                return;
            }

            const deviceId = data.device_id || `${rinfo.address}:${data.hostname}`;

            protocol.pruneDevices(this.devices, this.config.maxDeviceAge || 30000);
            if (!protocol.admitDevice(this.devices, deviceId, data, this.config)) return;
            // Update device information
            this.devices[deviceId] = {
                deviceId,
                hostname: data.hostname,
                celsius: validated.celsius,
                fahrenheit: validated.fahrenheit,
                pi_model: data.pi_model || null,
                pi_ram: data.pi_ram || null,
                platform: data.platform || null,
                cpu_arch: data.cpu_arch || null,
                service_version: data.service_version || null,
                serviceUpdateAvailable: isServiceOutdated(data.service_version, this.latestServiceVersion),
                packetTimestamp: data.timestamp,
                lastSeen: Date.now(),
                ip: rinfo.address
            };
            this.latestUpdateAt = Date.now();

            // Send update to frontend
            this.queueUpdate("TEMPERATURE_UPDATE");
        } catch (err) {
            this.warnInvalidPacket();
        }
    },

    handleStatusMessage: function(data, rawMessage, rinfo) {
        if (!protocol.validIdentity(data) ||
            typeof data.statusUpdateAvailable !== "boolean" || typeof data.statusClientUpdate !== "boolean" ||
            !this.isMessageAuthenticated(data, rawMessage)) {
            this.warnInvalidPacket();
            return;
        }
        const deviceId = String(data.device_id || `${rinfo.address}:${data.hostname}`);
        protocol.pruneDevices(this.statusDevices, this.config.statusMaxDeviceAge || 1200000);
        if (!protocol.admitDevice(this.statusDevices, deviceId, data, this.config)) return;
        this.statusDevices[deviceId] = {
            deviceId,
            hostname: data.hostname,
            pi_model: data.pi_model || null,
            pi_ram: data.pi_ram || null,
            statusUpdateAvailable: data.statusUpdateAvailable,
            statusClientUpdate: data.statusClientUpdate,
            packetTimestamp: data.timestamp,
            lastSeen: Date.now()
        };
        this.queueUpdate("STATUS_UPDATE");
    },

    validateTemperatureMessage: function(data) {
        return protocol.validateTemperatureMessage(data, this.config.sharedSecret, Math.min(this.config.maxPacketAge || 120000, this.config.maxDeviceAge || 30000));
    },

    isMessageAuthenticated: function(data) {
        return protocol.isMessageAuthenticated(data, this.config.sharedSecret, this.config.maxPacketAge);
    },

    timingSafeStringEqual: protocol.timingSafeStringEqual,

    getDeviceList: function() {
        // Convert devices object to array
        return Object.keys(this.devices).map(id => this.devices[id]);
    },

    getTemperatureSnapshot: function() {
        const devices = this.getDeviceList().map(device => this.formatDeviceForSnapshot(device));
        return {
            type: "temperature_snapshot",
            count: devices.length,
            updatedAt: this.latestUpdateAt ? new Date(this.latestUpdateAt).toISOString() : null,
            devices,
            temps: devices,
            temperatures: devices
        };
    },

    formatDeviceForSnapshot: function(device) {
        return {
            ...device,
            device_id: device.deviceId,
            id: device.deviceId,
            name: device.hostname,
            temp_c: device.celsius,
            temperature_c: device.celsius,
            temp_f: device.fahrenheit,
            temperature_f: device.fahrenheit,
            temperature: {
                celsius: device.celsius,
                fahrenheit: device.fahrenheit
            }
        };
    },

    sendTemperatureSnapshot: function(res) {
        res.setHeader("Content-Type", "application/json");
        res.end(JSON.stringify(this.getTemperatureSnapshot()));
    },

    registerTempsEndpoint: function() {
        if (this.tempsEndpointRegistered || !this.expressApp) {
            return;
        }

        const endpointPath = this.config.tempsEndpointPath || "/temps";

        this.expressApp.get(endpointPath, (req, res) => {
            if (!this.authorizeSnapshot(req, res)) return;
            res.json(this.getTemperatureSnapshot());
        });

        this.tempsEndpointRegistered = true;
        console.log(`[MMM-RemoteTempMonitor] Temperature data endpoint available at ${endpointPath}`);
    },


    startAggregateHttpServer: function() {
        const aggregatePort = Number(this.config.aggregatePort || this.config.rebroadcastPort || 9877);
        const endpointPath = this.config.aggregateEndpointPath || this.config.tempsEndpointPath || "/temps";

        if (!Number.isInteger(aggregatePort) || aggregatePort <= 0 || aggregatePort > 65535) {
            console.warn(`[MMM-RemoteTempMonitor] Aggregate HTTP server disabled: invalid aggregatePort ${aggregatePort}`);
            return;
        }

        if (this.aggregateHttpServer) {
            return;
        }

        this.aggregateHttpEndpointPath = endpointPath;
        this.aggregateHttpServer = http.createServer((req, res) => {
            const requestUrl = this.parseAggregateRequestUrl(req);

            if (requestUrl && req.method === "GET" && requestUrl.pathname === endpointPath) {
                if (!this.authorizeSnapshot(req, res)) return;
                this.sendTemperatureSnapshot(res);
                return;
            }

            res.statusCode = 404;
            res.setHeader("Content-Type", "application/json");
            res.end(JSON.stringify({ error: "not_found", endpoint: endpointPath }));
        });

        this.aggregateHttpServer.requestTimeout = 5000;
        this.aggregateHttpServer.headersTimeout = 5000;
        this.aggregateHttpServer.maxConnections = 32;
        this.aggregateHttpServer.on("error", (err) => {
            console.error(`[MMM-RemoteTempMonitor] Aggregate HTTP server error on port ${aggregatePort}: ${err.message}`);
        });

        const host = this.config.snapshotToken ? (this.config.aggregateHost || "0.0.0.0") : "127.0.0.1";
        this.aggregateHttpServer.listen(aggregatePort, host, () => {
            console.log(`[MMM-RemoteTempMonitor] Aggregate temperature endpoint available at http://${host}:${aggregatePort}${endpointPath}`);
        });
    },

    authorizeSnapshot: function(req, res) {
        const token = this.config.snapshotToken;
        const remote = req.socket && req.socket.remoteAddress;
        if (token && protocol.timingSafeStringEqual(req.headers.authorization, `Bearer ${token}`)) return true;
        if (!token && (remote === "127.0.0.1" || remote === "::1" || remote === "::ffff:127.0.0.1")) return true;
        res.statusCode = 403;
        res.end("Forbidden");
        return false;
    },

    parseAggregateRequestUrl: function(req) {
        try {
            return new URL(req.url || "/", "http://localhost");
        } catch (err) {
            return null;
        }
    },

    getLocalHostHardwareInfo: function() {
        let modelNumber = null;

        try {
            const modelText = fs.readFileSync("/proc/device-tree/model", "utf8").replace(/\u0000/g, "").trim();
            const modelMatch = modelText.match(/Raspberry Pi\s+(\d+)/i);
            if (modelMatch) {
                modelNumber = modelMatch[1];
            }
        } catch (err) {
            // Ignore: this file won't exist on non-Raspberry Pi hosts.
        }

        const totalMemoryGb = Math.round(os.totalmem() / (1024 ** 3));

        return {
            model: modelNumber,
            ram: `${totalMemoryGb}GB`
        };
    },

    startLocalMachineMonitor: function() {
        const interval = this.config.updateInterval || 5000;

        const hostHardware = this.getLocalHostHardwareInfo();
        let pending = false;
        const publishLocalTemperature = () => {
            if (pending || this.stopping) return;
            pending = true;
            this.readLocalCpuTemp((err, celsius) => {
                pending = false;
                if (this.stopping || err || !Number.isFinite(celsius)) {
                    return;
                }


                this.devices.__local_machine__ = {
                    deviceId: "__local_machine__",
                    hostname: `${os.hostname()} (host)`,
                    celsius,
                    fahrenheit: (celsius * 9 / 5) + 32,
                    pi_model: hostHardware.model,
                    pi_ram: hostHardware.ram,
                    lastSeen: Date.now(),
                    ip: "127.0.0.1"
                };
                this.latestUpdateAt = Date.now();

                this.queueUpdate("TEMPERATURE_UPDATE");
            });
        };

        publishLocalTemperature();
        this.localMonitorTimer = setInterval(publishLocalTemperature, interval);
    },

    readLocalCpuTemp: function(callback) {
        const linuxPath = "/sys/class/thermal/thermal_zone0/temp";

        fs.readFile(linuxPath, "utf8", (err, raw) => {
            if (!err) {
                const millidegrees = parseInt(raw.trim(), 10);
                if (!Number.isNaN(millidegrees)) {
                    callback(null, millidegrees / 1000);
                    return;
                }
            }

            execFile("python3", ["-c", "import psutil; print(psutil.sensors_temperatures())"], { timeout: 1500 }, (pyErr, stdout) => {
                if (pyErr || !stdout) {
                    callback(new Error("Could not read local CPU temperature"));
                    return;
                }

                const match = stdout.match(/current=([0-9]+(?:\.[0-9]+)?)/);
                if (!match) {
                    callback(new Error("Could not parse local CPU temperature"));
                    return;
                }

                callback(null, parseFloat(match[1]));
            });
        });
    },

    startCleanupTimer: function() {
        const cleanupInterval = this.config.cleanupInterval || 10000;
        const maxAge = this.config.maxDeviceAge || 30000; // 30 seconds default
        const statusMaxAge = this.config.statusMaxDeviceAge || 1200000;

        this.cleanupTimer = setInterval(() => {
            const now = Date.now();
            let changed = false;

            Object.keys(this.devices).forEach(deviceId => {
                if (now - this.devices[deviceId].lastSeen > maxAge) {
                    console.log(`[MMM-RemoteTempMonitor] Removing stale device: ${deviceId}`);
                    delete this.devices[deviceId];
                    changed = true;
                }
            });
            let statusChanged = false;
            Object.keys(this.statusDevices).forEach(deviceId => {
                if (now - this.statusDevices[deviceId].lastSeen > statusMaxAge) {
                    delete this.statusDevices[deviceId];
                    statusChanged = true;
                }
            });
            if (statusChanged) this.sendSocketNotification("STATUS_UPDATE", { devices: Object.values(this.statusDevices) });

            if (changed) {
                this.sendSocketNotification("TEMPERATURE_UPDATE", this.getDeviceList());
            }
        }, cleanupInterval);
    },

    stop: function() {
        this.stopping = true;
        clearTimeout(this.retryTimer);
        clearTimeout(this.publishTimer);
        this.retryTimer = this.publishTimer = null;
        if (this.pendingUpdates) this.pendingUpdates.clear();
        if (this.cleanupTimer) {
            clearInterval(this.cleanupTimer);
            this.cleanupTimer = null;
        }
        if (this.localMonitorTimer) {
            clearInterval(this.localMonitorTimer);
            this.localMonitorTimer = null;
        }
        if (this.server) {
            try { this.server.close(); } catch (_) { /* Already closed. */ }
            this.server = null;
            console.log("[MMM-RemoteTempMonitor] UDP listener stopped");
        }
        if (this.aggregateHttpServer) {
            this.aggregateHttpServer.close();
            if (this.aggregateHttpServer.closeAllConnections) this.aggregateHttpServer.closeAllConnections();
            this.aggregateHttpServer = null;
            console.log("[MMM-RemoteTempMonitor] Aggregate HTTP server stopped");
        }
    }
});
