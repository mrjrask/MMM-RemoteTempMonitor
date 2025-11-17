/**
 * Node Helper for MMM-RemoteTempMonitor
 * Listens for UDP temperature broadcasts from remote devices
 */

const NodeHelper = require("node_helper");
const dgram = require("dgram");

module.exports = NodeHelper.create({
    start: function() {
        this.started = false;
        this.devices = {};
        this.server = null;
        this.config = null;
        console.log("Starting node_helper for: " + this.name);
    },

    socketNotificationReceived: function(notification, payload) {
        if (notification === "CONFIG") {
            this.config = payload;
            if (!this.started) {
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

        } catch (err) {
            console.error(`[MMM-RemoteTempMonitor] Failed to start UDP listener: ${err}`);
        }
    },

    handleMessage: function(msg, rinfo) {
        try {
            const data = JSON.parse(msg.toString());

            // Validate message format
            if (data.type === "temperature" && data.hostname && data.temperature) {
                const deviceId = data.hostname;

                // Update device information
                this.devices[deviceId] = {
                    hostname: data.hostname,
                    celsius: data.temperature.celsius,
                    fahrenheit: data.temperature.fahrenheit,
                    pi_model: data.pi_model || null,
                    pi_ram: data.pi_ram || null,
                    lastSeen: Date.now(),
                    ip: rinfo.address
                };

                // Send update to frontend
                this.sendSocketNotification("TEMPERATURE_UPDATE", this.getDeviceList());

                console.log(`[MMM-RemoteTempMonitor] Received from ${data.hostname}: ${data.temperature.celsius}°C`);
            }
        } catch (err) {
            console.error(`[MMM-RemoteTempMonitor] Error parsing message: ${err.message}`);
        }
    },

    getDeviceList: function() {
        // Convert devices object to array
        return Object.keys(this.devices).map(id => this.devices[id]);
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
        if (this.server) {
            this.server.close();
            console.log("[MMM-RemoteTempMonitor] UDP listener stopped");
        }
    }
});
