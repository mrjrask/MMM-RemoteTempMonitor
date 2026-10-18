/**
 * MMM-RemoteTempStatusMonitor
 * MagicMirror module to display remote device status indicators
 * Shows yellow dot for apt updates and blue dot for client updates
 *
 * Companion to MMM-RemoteTempMonitor module
 * By mrjrask
 * MIT Licensed
 */

Module.register("MMM-RemoteTempStatusMonitor", {
    defaults: {
        port: 9876,                    // Same UDP port as temperature monitor
        maxDeviceAge: 30000,          // Remove devices not seen for this long (ms)
        cleanupInterval: 60000,       // How often to check for stale devices (ms)
        aggregatePort: 9877,           // HTTP port for status endpoint
        aggregateEndpointPath: "/status", // HTTP path for status endpoint

        // Colors for status indicators
        updateAvailableColor: "#FFFF00",   // Yellow for apt updates
        updateAvailableShadow: "rgba(255, 255, 0, 0.6)",
        clientUpdateColor: "#00FFFF",      // Blue for client updates
        clientUpdateShadow: "rgba(0, 255, 255, 0.6)",

        // Pulse animation settings
        updatePulseDuration: 2000,  // ms for yellow pulse
        clientPulseDuration: 1500,  // ms for blue pulse (different to avoid sync)
    },

    start: function() {
        Log.info("Starting module: " + this.name);
        this.devices = [];
        this.loaded = false;
        this.updateInterval = this.config.cleanupInterval;
        this.startStatusRefresh();
        
        // Send CONFIG to self to initialize
        this.sendSocketNotification("CONFIG", this.config);
    },

    getStyles: function() {
        return ["MMM-RemoteTempStatusMonitor.css"];
    },

    socketNotificationReceived: function(notification, payload) {
        if (notification === "STATUS_UPDATE") {
            this.devices = payload.devices || [];
            this.loaded = true;
            this.updateDom(0);
        } else if (notification === "CONFIG") {
            // Self-initialization for CONFIG notification
            this.sendSocketNotification(notification, payload);
        }
    },

    getDom: function() {
        const wrapper = document.createElement("table");
        wrapper.className = "mmm-remote-temp-status-monitor small";
        this.wrapperElement = wrapper;

        // Create header
        const header = document.createElement("thead");
        const headerRow = document.createElement("tr");

        // Device column header
        const deviceHeader = document.createElement("th");
        deviceHeader.textContent = "Device";
        deviceHeader.className = "status-hostname-header";
        headerRow.appendChild(deviceHeader);

        header.appendChild(headerRow);

        // Status table body
        const body = document.createElement("tbody");

        this.devices.forEach(device => {
            const row = document.createElement("tr");

            // Create device info cell with status dots
            const deviceCell = document.createElement("td");
            deviceCell.className = "status-device-cell";

            // Create container for hostname + dots
            const deviceContent = document.createElement("span");
            deviceContent.className = "status-device-content";

            // Create status dot container (positioned to left of text)
            const dotContainer = document.createElement("span");
            dotContainer.className = "status-dot-indicator";
            deviceContent.appendChild(dotContainer);

            // Device name text
            const nameSpan = document.createElement("span");
            nameSpan.className = "status-device-name";
            nameSpan.textContent = device.hostname;
            deviceContent.appendChild(nameSpan);

            // Add Pi model/RAM if available
            if (device.pi_model && device.pi_ram) {
                const modelSpan = document.createElement("span");
                modelSpan.className = "status-device-meta";
                modelSpan.textContent = ` (${device.pi_model} | ${device.pi_ram})`;
                deviceContent.appendChild(modelSpan);
            } else if (device.pi_model) {
                const modelSpan = document.createElement("span");
                modelSpan.className = "status-device-meta";
                modelSpan.textContent = ` (${device.pi_model})`;
                deviceContent.appendChild(modelSpan);
            } else if (device.pi_ram) {
                const ramSpan = document.createElement("span");
                ramSpan.className = "status-device-meta";
                ramSpan.textContent = ` (${device.pi_ram})`;
                deviceContent.appendChild(ramSpan);
            }

            deviceCell.appendChild(deviceContent);
            row.appendChild(deviceCell);

            // Yellow update available indicator
            const updateDotContainer = document.createElement("span");
            updateDotContainer.className = "status-update-dot" + (device.statusUpdateAvailable ? " visible" : "");
            updateDotContainer.style.animation = `pulseUpdate ${this.config.updatePulseDuration}ms ease-in-out infinite`;
            updateDotContainer.innerHTML = `
                <span class="status-dot" style="background-color: ${this.config.updateAvailableColor}; box-shadow: 0 0 4px ${this.config.updateAvailableShadow};"></span>
            `;
            dotContainer.appendChild(updateDotContainer);

            // Blue client update indicator
            const clientDotContainer = document.createElement("span");
            clientDotContainer.className = "status-client-dot" + (device.statusClientUpdate ? " visible" : "");
            clientDotContainer.style.animation = `pulseClient ${this.config.clientPulseDuration}ms ease-in-out infinite`;
            clientDotContainer.innerHTML = `
                <span class="status-dot" style="background-color: ${this.config.clientUpdateColor}; box-shadow: 0 0 4px ${this.config.clientUpdateShadow};"></span>
            `;
            dotContainer.appendChild(clientDotContainer);

            body.appendChild(row);
        });

        wrapper.appendChild(body);

        return wrapper;
    },

    startStatusRefresh: function() {
        setInterval(() => {
            this.updateDom(this.config.cleanupInterval - 1000);
        }, this.updateInterval);
    }
});