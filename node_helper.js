/**
 * Node Helper for MMM-RemoteTempMonitor
 * Listens for UDP temperature broadcasts from remote devices
 */

const NodeHelper = require("node_helper");
const dgram = require("dgram");
const os = require("os");
const fs = require("fs");
const { execFile } = require("child_process");
const crypto = require("crypto");

module.exports = NodeHelper.create({
    start: function() {
        this.started = false;
        this.devices = {};
        this.server = null;
        this.config = null;
        this.localMonitorTimer = null;
        this.tempsEndpointRegistered = false;
        this.latestUpdateAt = null;
        console.log("Starting node_helper for: " + this.name);
    },

    socketNotificationReceived: function(notification, payload) {
        if (notification === "CONFIG") {
            this.config = payload;
            if (!this.started) {
                this.registerTempsEndpoint();
                this.startListening();
                this.started = true;
            }
        }
    },

    startListening: function() {
        const port = this.config.port || 9876;

        try {
            this.server = dgram.createSocket({ type: 'udp4', reuseAddr: true });

            this.server.on('error', (err) => {
                console.error(`[MMM-RemoteTempMonitor] Server error: ${err.stack}`);
                this.server.close();
            });

            this.server.on('message', (msg, rinfo) => {
                this.handleMessage(msg, rinfo);
            });

            this.server.on('listening', () => {
                const address = this.server.address();
                console.log(`[MMM-RemoteTempMonitor] UDP listener started on port ${address.port}`);

                // Enable broadcast reception
                try {
                    this.server.setBroadcast(true);
                } catch (e) {
                    console.error(`[MMM-RemoteTempMonitor] Could not set broadcast: ${e}`);
                }
            });

            this.server.bind(port);

            // Set up periodic cleanup of stale devices
            this.startCleanupTimer();
            if (this.config.monitorLocalHost) {
                this.startLocalMachineMonitor();
            }

        } catch (err) {
            console.error(`[MMM-RemoteTempMonitor] Failed to start UDP listener: ${err}`);
        }
    },

    handleMessage: function(msg, rinfo) {
        try {
            const rawMessage = msg.toString();
            const data = JSON.parse(rawMessage);
            const validated = this.validateTemperatureMessage(data, rawMessage);

            if (!validated.valid) {
                console.warn(`[MMM-RemoteTempMonitor] Ignored invalid packet from ${rinfo.address}: ${validated.reason}`);
                return;
            }

            const deviceId = data.device_id || `${rinfo.address}:${data.hostname}`;

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
                lastSeen: Date.now(),
                ip: rinfo.address
            };
            this.latestUpdateAt = Date.now();

            // Send update to frontend
            this.sendSocketNotification("TEMPERATURE_UPDATE", this.getDeviceList());

            console.log(`[MMM-RemoteTempMonitor] Received from ${data.hostname} (${rinfo.address}): ${validated.celsius}°C`);
        } catch (err) {
            console.error(`[MMM-RemoteTempMonitor] Error parsing message: ${err.message}`);
        }
    },

    validateTemperatureMessage: function(data, rawMessage) {
        if (data.type !== "temperature" || !data.hostname || !data.temperature) {
            return { valid: false, reason: "missing required temperature fields" };
        }

        if (!this.isMessageAuthenticated(data, rawMessage)) {
            return { valid: false, reason: "authentication failed" };
        }

        const celsius = Number(data.temperature.celsius);
        const fahrenheit = Number(data.temperature.fahrenheit);
        if (!Number.isFinite(celsius) || !Number.isFinite(fahrenheit)) {
            return { valid: false, reason: "temperature values must be finite numbers" };
        }
        if (celsius < -50 || celsius > 150) {
            return { valid: false, reason: "celsius temperature outside expected range" };
        }

        return { valid: true, celsius, fahrenheit };
    },

    isMessageAuthenticated: function(data, rawMessage) {
        const secret = this.config.sharedSecret;
        if (!secret) {
            return true;
        }

        if (!data.hmac) {
            return false;
        }

        const unsigned = { ...data };
        delete unsigned.hmac;
        const expected = crypto.createHmac("sha256", secret).update(JSON.stringify(unsigned)).digest("hex");
        return this.timingSafeStringEqual(data.hmac, expected);
    },

    timingSafeStringEqual: function(actual, expected) {
        const actualBuffer = Buffer.from(String(actual));
        const expectedBuffer = Buffer.from(String(expected));
        return actualBuffer.length === expectedBuffer.length && crypto.timingSafeEqual(actualBuffer, expectedBuffer);
    },

    getDeviceList: function() {
        // Convert devices object to array
        return Object.keys(this.devices).map(id => this.devices[id]);
    },

    registerTempsEndpoint: function() {
        if (this.tempsEndpointRegistered || !this.expressApp) {
            return;
        }

        const endpointPath = this.config.tempsEndpointPath || "/temps";

        this.expressApp.get(endpointPath, (req, res) => {
            const devices = this.getDeviceList();
            res.json({
                type: "temperature_snapshot",
                count: devices.length,
                updatedAt: this.latestUpdateAt ? new Date(this.latestUpdateAt).toISOString() : null,
                devices
            });
        });

        this.tempsEndpointRegistered = true;
        console.log(`[MMM-RemoteTempMonitor] Temperature data endpoint available at ${endpointPath}`);
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

        const publishLocalTemperature = () => {
            this.readLocalCpuTemp((err, celsius) => {
                if (err || Number.isNaN(celsius)) {
                    return;
                }

                const hostHardware = this.getLocalHostHardwareInfo();

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

                this.sendSocketNotification("TEMPERATURE_UPDATE", this.getDeviceList());
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
        const cleanupInterval = this.config.cleanupInterval || 60000; // 1 minute default
        const maxAge = this.config.maxDeviceAge || 30000; // 30 seconds default

        setInterval(() => {
            const now = Date.now();
            let changed = false;

            Object.keys(this.devices).forEach(deviceId => {
                if (now - this.devices[deviceId].lastSeen > maxAge) {
                    console.log(`[MMM-RemoteTempMonitor] Removing stale device: ${deviceId}`);
                    delete this.devices[deviceId];
                    changed = true;
                }
            });

            if (changed) {
                this.sendSocketNotification("TEMPERATURE_UPDATE", this.getDeviceList());
            }
        }, cleanupInterval);
    },

    stop: function() {
        if (this.localMonitorTimer) {
            clearInterval(this.localMonitorTimer);
            this.localMonitorTimer = null;
        }
        if (this.server) {
            this.server.close();
            console.log("[MMM-RemoteTempMonitor] UDP listener stopped");
        }
    }
});
