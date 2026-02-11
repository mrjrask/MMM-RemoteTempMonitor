/**
 * MMM-RemoteTempMonitor
 * MagicMirror module to display CPU temperatures from remote devices
 *
 * By mrjrask
 * MIT Licensed
 */

Module.register("MMM-RemoteTempMonitor", {
    defaults: {
        port: 9876,                    // UDP port to listen on
        updateInterval: 5000,          // How often to refresh display (ms)
        maxDeviceAge: 30000,          // Remove devices not seen for this long (ms)
        cleanupInterval: 60000,       // How often to check for stale devices (ms)
        showFahrenheit: true,         // Show Fahrenheit temperature
        showCelsius: true,            // Show Celsius temperature
        sortBy: "temperature",        // Sort by: "hostname" or "temperature"
        devicesPerPage: 6,            // Devices to show per page
        pageTransitionSpeed: 1000,    // Fade transition duration (ms)

        // Temperature thresholds for color coding (in Celsius)
        tempThresholds: {
            normal: 50,      // Below this: green
            warm: 60,        // 50-60: yellow-green
            hot: 70,         // 60-70: orange
            veryHot: 80,     // 70-80: red
            critical: 85     // 80+: purple
        }
    },

    start: function() {
        Log.info("Starting module: " + this.name);
        this.devices = [];
        this.loaded = false;
        this.currentPage = 0;
        this.totalPages = 1;
        this.isTransitioning = false;
        this.pendingFadeIn = false;
        this.wrapperElement = null;
        this.startPageRotation();
        this.sendSocketNotification("CONFIG", this.config);
    },

    getStyles: function() {
        return ["MMM-RemoteTempMonitor.css"];
    },

    socketNotificationReceived: function(notification, payload) {
        if (notification === "TEMPERATURE_UPDATE") {
            this.devices = payload;
            const wasLoaded = this.loaded;
            this.loaded = true;
            const fadeSpeed = wasLoaded ? 0 : this.config.pageTransitionSpeed;
            this.updateDom(fadeSpeed);
        }
    },

    getDom: function() {
        const wrapper = document.createElement("div");
        wrapper.className = "mmm-remote-temp-monitor";
        wrapper.style.setProperty("--page-fade-duration", `${this.config.pageTransitionSpeed}ms`);
        this.wrapperElement = wrapper;

        if (this.pendingFadeIn) {
            wrapper.classList.add("is-fading");
            this.pendingFadeIn = false;
            setTimeout(() => {
                if (this.wrapperElement === wrapper) {
                    wrapper.classList.remove("is-fading");
                }
            }, 0);
        }

        // Show loading message if no data yet
        if (!this.loaded) {
            wrapper.innerHTML = "Loading temperature monitors...";
            wrapper.className += " dimmed light small";
            return wrapper;
        }

        // Show message if no devices found
        if (this.devices.length === 0) {
            wrapper.innerHTML = "No temperature monitors found";
            wrapper.className += " dimmed light small";
            return wrapper;
        }

        // Sort devices
        const sortedDevices = this.sortDevices(this.devices);
        const devicesPerPage = this.getDevicesPerPage();
        const shouldPaginate = sortedDevices.length > 6;
        const totalPages = shouldPaginate
            ? Math.max(1, Math.ceil(sortedDevices.length / devicesPerPage))
            : 1;
        this.totalPages = totalPages;
        if (this.currentPage >= totalPages) {
            this.currentPage = 0;
        }

        const startIndex = this.currentPage * devicesPerPage;
        const pageDevices = sortedDevices.slice(startIndex, startIndex + devicesPerPage);

        // Create table
        const table = document.createElement("table");
        table.className = "small";

        // Create header
        const header = document.createElement("thead");
        const headerRow = document.createElement("tr");

        const hostHeader = document.createElement("th");
        hostHeader.innerHTML = "Device";
        hostHeader.className = "hostname-header";
        headerRow.appendChild(hostHeader);

        if (this.config.showCelsius) {
            const celsiusHeader = document.createElement("th");
            celsiusHeader.innerHTML = "°C";
            celsiusHeader.className = "temp-header";
            headerRow.appendChild(celsiusHeader);
        }

        if (this.config.showFahrenheit) {
            const fahrenheitHeader = document.createElement("th");
            fahrenheitHeader.innerHTML = "°F";
            fahrenheitHeader.className = "temp-header";
            headerRow.appendChild(fahrenheitHeader);
        }

        header.appendChild(headerRow);
        table.appendChild(header);

        // Create body with device rows
        const body = document.createElement("tbody");

        pageDevices.forEach(device => {
            const row = document.createElement("tr");

            // Hostname column
            const hostnameCell = document.createElement("td");
            let displayName = device.hostname;

            // Add Pi model and RAM info if available
            if (device.pi_model && device.pi_ram) {
                displayName += ` (${device.pi_model} | ${device.pi_ram})`;
            } else if (device.pi_model) {
                displayName += ` (${device.pi_model})`;
            } else if (device.pi_ram) {
                displayName += ` (${device.pi_ram})`;
            }

            hostnameCell.innerHTML = displayName;
            hostnameCell.className = "hostname";
            row.appendChild(hostnameCell);

            // Get temperature color class
            const colorClass = this.getTempColorClass(device.celsius);

            // Celsius column
            if (this.config.showCelsius) {
                const celsiusCell = document.createElement("td");
                celsiusCell.innerHTML = device.celsius.toFixed(1);
                celsiusCell.className = "temperature " + colorClass;
                row.appendChild(celsiusCell);
            }

            // Fahrenheit column
            if (this.config.showFahrenheit) {
                const fahrenheitCell = document.createElement("td");
                fahrenheitCell.innerHTML = device.fahrenheit.toFixed(1);
                fahrenheitCell.className = "temperature " + colorClass;
                row.appendChild(fahrenheitCell);
            }

            body.appendChild(row);
        });

        table.appendChild(body);
        wrapper.appendChild(table);

        if (shouldPaginate) {
            wrapper.appendChild(this.buildPaginationDots(totalPages));
        }

        return wrapper;
    },

    getTempColorClass: function(celsius) {
        const thresholds = this.config.tempThresholds;

        if (celsius >= thresholds.critical) {
            return "temp-critical";  // Purple
        } else if (celsius >= thresholds.veryHot) {
            return "temp-very-hot";  // Red
        } else if (celsius >= thresholds.hot) {
            return "temp-hot";       // Orange
        } else if (celsius >= thresholds.warm) {
            return "temp-warm";      // Yellow
        } else {
            return "temp-normal";    // Green
        }
    },

    sortDevices: function(devices) {
        const sorted = [...devices];

        if (this.config.sortBy === "temperature") {
            sorted.sort((a, b) => b.celsius - a.celsius);
        } else {
            // Sort by hostname (default)
            sorted.sort((a, b) => a.hostname.localeCompare(b.hostname));
        }

        return sorted;
    },

    getDevicesPerPage: function() {
        const parsed = parseInt(this.config.devicesPerPage, 10);
        if (Number.isNaN(parsed) || parsed <= 0) {
            return 6;
        }
        return parsed;
    },

    buildPaginationDots: function(totalPages) {
        const dotsWrapper = document.createElement("div");
        dotsWrapper.className = "pagination-dots";

        for (let pageIndex = 0; pageIndex < totalPages; pageIndex += 1) {
            const dot = document.createElement("span");
            dot.className = "pagination-dot";
            if (pageIndex === this.currentPage) {
                dot.className += " is-active";
            }
            dotsWrapper.appendChild(dot);
        }

        return dotsWrapper;
    },

    startPageRotation: function() {
        const interval = this.config.updateInterval || 5000;
        setInterval(() => {
            if (!this.loaded || this.totalPages <= 1) {
                return;
            }
            if (this.isTransitioning) {
                return;
            }
            this.isTransitioning = true;
            const nextPage = (this.currentPage + 1) % this.totalPages;
            const wrapper = this.wrapperElement;
            if (wrapper) {
                wrapper.classList.add("is-fading");
            }
            const fadeDuration = this.config.pageTransitionSpeed;
            setTimeout(() => {
                this.currentPage = nextPage;
                this.pendingFadeIn = true;
                this.updateDom(0);
                this.isTransitioning = false;
            }, fadeDuration);
        }, interval);
    }
});
