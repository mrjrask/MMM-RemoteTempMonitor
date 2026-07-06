#!/usr/bin/env node
/*
 * CLI monitor for MMM-RemoteTempMonitor UDP temperature broadcasts.
 */

const dgram = require("dgram");
const os = require("os");
const crypto = require("crypto");

const DEFAULTS = {
    port: 9876,
    maxDeviceAge: 30000,
    refreshInterval: 5000,
    showFahrenheit: true,
    showCelsius: true,
    sortBy: "temperature",
    devicesPerPage: 9,
    clearScreen: true,
    sharedSecret: process.env.TEMP_MONITOR_SHARED_SECRET || "",
    tempThresholds: {
        normal: 50,
        warm: 60,
        hot: 70,
        veryHot: 80,
        critical: 85
    }
};

function parseArgs(argv) {
    const config = { ...DEFAULTS, tempThresholds: { ...DEFAULTS.tempThresholds } };

    for (let index = 0; index < argv.length; index += 1) {
        const arg = argv[index];
        const next = argv[index + 1];

        switch (arg) {
            case "--help":
            case "-h":
                printHelp();
                process.exit(0);
                break;
            case "--port":
            case "-p":
                config.port = parsePositiveInteger(next, "port");
                index += 1;
                break;
            case "--max-age":
                config.maxDeviceAge = parsePositiveInteger(next, "max-age");
                index += 1;
                break;
            case "--refresh":
            case "-r":
                config.refreshInterval = parsePositiveInteger(next, "refresh");
                index += 1;
                break;
            case "--sort":
            case "-s":
                if (!["temperature", "hostname"].includes(next)) {
                    throw new Error("--sort must be either 'temperature' or 'hostname'");
                }
                config.sortBy = next;
                index += 1;
                break;
            case "--celsius-only":
                config.showCelsius = true;
                config.showFahrenheit = false;
                break;
            case "--fahrenheit-only":
                config.showCelsius = false;
                config.showFahrenheit = true;
                break;
            case "--no-clear":
                config.clearScreen = false;
                break;
            case "--shared-secret":
                if (!next) {
                    throw new Error("--shared-secret requires a value");
                }
                config.sharedSecret = next;
                index += 1;
                break;
            default:
                throw new Error(`Unknown option: ${arg}`);
        }
    }

    return config;
}

function parsePositiveInteger(value, label) {
    const parsed = parseInt(value, 10);
    if (Number.isNaN(parsed) || parsed <= 0) {
        throw new Error(`--${label} must be a positive integer`);
    }
    return parsed;
}

function printHelp() {
    console.log(`MMM-RemoteTempMonitor CLI

Listen for temperature broadcasts and render the same device table used by the MagicMirror module.

Usage:
  node bin/remote-temp-monitor-cli.js [options]

Options:
  -p, --port <port>        UDP port to listen on (default: ${DEFAULTS.port})
  -r, --refresh <ms>       Screen refresh interval in milliseconds (default: ${DEFAULTS.refreshInterval})
      --max-age <ms>       Drop devices not seen for this long (default: ${DEFAULTS.maxDeviceAge})
  -s, --sort <mode>        Sort by "temperature" or "hostname" (default: ${DEFAULTS.sortBy})
      --celsius-only       Show only Celsius values
      --fahrenheit-only    Show only Fahrenheit values
      --no-clear           Do not clear the terminal between refreshes
      --shared-secret <s>  Require matching auth token/HMAC (or TEMP_MONITOR_SHARED_SECRET)
  -h, --help               Show this help message`);
}

function getTempLabel(celsius, thresholds) {
    if (celsius >= thresholds.critical) {
        return "Critical";
    }
    if (celsius >= thresholds.veryHot) {
        return "Very hot";
    }
    if (celsius >= thresholds.hot) {
        return "Hot";
    }
    if (celsius >= thresholds.warm) {
        return "Warm";
    }
    return "Normal";
}

function getDisplayName(device) {
    let displayName = device.hostname;

    if (device.pi_model && device.pi_ram) {
        displayName += ` (${device.pi_model} | ${device.pi_ram})`;
    } else if (device.pi_model) {
        displayName += ` (${device.pi_model})`;
    } else if (device.pi_ram) {
        displayName += ` (${device.pi_ram})`;
    }

    return displayName;
}

function sortDevices(devices, sortBy) {
    const sorted = [...devices];
    if (sortBy === "temperature") {
        sorted.sort((a, b) => b.celsius - a.celsius);
    } else {
        sorted.sort((a, b) => a.hostname.localeCompare(b.hostname));
    }
    return sorted;
}

function pad(value, width, alignRight = false) {
    const text = String(value);
    if (text.length >= width) {
        return text;
    }
    return alignRight ? text.padStart(width, " ") : text.padEnd(width, " ");
}

function render(devicesById, config, status) {
    const now = Date.now();
    const devices = Object.values(devicesById).filter(device => now - device.lastSeen <= config.maxDeviceAge);
    const sortedDevices = sortDevices(devices, config.sortBy).slice(0, config.devicesPerPage);

    if (config.clearScreen && process.stdout.isTTY) {
        process.stdout.write("\x1Bc");
    }

    console.log("MMM-RemoteTempMonitor");
    console.log(`Listening on UDP port ${config.port} from ${os.hostname()}`);
    console.log(status);
    console.log("");

    if (sortedDevices.length === 0) {
        console.log("No temperature monitors found");
        return;
    }

    const nameWidth = Math.max("Device".length, ...sortedDevices.map(device => getDisplayName(device).length));
    const columns = [pad("Device", nameWidth)];
    if (config.showCelsius) {
        columns.push(pad("°C", 6, true));
    }
    if (config.showFahrenheit) {
        columns.push(pad("°F", 6, true));
    }
    columns.push(pad("Status", 10), pad("Last seen", 10), "IP");

    console.log(columns.join("  "));
    console.log("-".repeat(columns.join("  ").length));

    sortedDevices.forEach(device => {
        const ageSeconds = Math.round((now - device.lastSeen) / 1000);
        const row = [pad(getDisplayName(device), nameWidth)];
        if (config.showCelsius) {
            row.push(pad(device.celsius.toFixed(1), 6, true));
        }
        if (config.showFahrenheit) {
            row.push(pad(device.fahrenheit.toFixed(1), 6, true));
        }
        row.push(
            pad(getTempLabel(device.celsius, config.tempThresholds), 10),
            pad(`${ageSeconds}s ago`, 10),
            device.ip
        );
        console.log(row.join("  "));
    });
}

function timingSafeStringEqual(actual, expected) {
    const actualBuffer = Buffer.from(String(actual));
    const expectedBuffer = Buffer.from(String(expected));
    return actualBuffer.length === expectedBuffer.length && crypto.timingSafeEqual(actualBuffer, expectedBuffer);
}

function isMessageAuthenticated(data, secret) {
    if (!secret) {
        return true;
    }

    if (data.auth_token) {
        return timingSafeStringEqual(data.auth_token, secret);
    }

    if (!data.hmac) {
        return false;
    }

    const unsigned = { ...data };
    delete unsigned.hmac;
    const expected = crypto.createHmac("sha256", secret).update(JSON.stringify(unsigned)).digest("hex");
    return timingSafeStringEqual(data.hmac, expected);
}

function validateTemperatureMessage(data, secret = "") {
    if (data.type !== "temperature" || !data.hostname || !data.temperature) {
        return { valid: false, reason: "missing required temperature fields" };
    }

    if (!isMessageAuthenticated(data, secret)) {
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
}

function handleMessage(msg, rinfo, devicesById, config = DEFAULTS) {
    const data = JSON.parse(msg.toString());
    const validated = validateTemperatureMessage(data, config.sharedSecret || "");

    if (!validated.valid) {
        return false;
    }

    const deviceId = data.device_id || `${rinfo.address}:${data.hostname}`;
    devicesById[deviceId] = {
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

    return true;
}

function main() {
    let config;
    try {
        config = parseArgs(process.argv.slice(2));
    } catch (err) {
        console.error(err.message);
        console.error("Run with --help for usage.");
        process.exit(1);
    }

    const devicesById = {};
    let status = "Waiting for temperature broadcasts...";
    const server = dgram.createSocket({ type: "udp4", reuseAddr: true });

    server.on("error", err => {
        console.error(`[MMM-RemoteTempMonitor CLI] Server error: ${err.stack}`);
        server.close();
        process.exit(1);
    });

    server.on("message", (msg, rinfo) => {
        try {
            if (handleMessage(msg, rinfo, devicesById, config)) {
                status = `Last update received from ${rinfo.address}`;
                render(devicesById, config, status);
            }
        } catch (err) {
            status = `Ignored invalid packet from ${rinfo.address}: ${err.message}`;
        }
    });

    server.on("listening", () => {
        try {
            server.setBroadcast(true);
        } catch (err) {
            status = `Listening, but could not enable broadcast reception: ${err.message}`;
        }
        render(devicesById, config, status);
    });

    server.bind(config.port);

    const refreshTimer = setInterval(() => {
        render(devicesById, config, status);
    }, config.refreshInterval);

    process.on("SIGINT", () => {
        clearInterval(refreshTimer);
        server.close();
        console.log("\nStopped MMM-RemoteTempMonitor CLI.");
        process.exit(0);
    });
}

if (require.main === module) {
    main();
}

module.exports = {
    DEFAULTS,
    parseArgs,
    getTempLabel,
    sortDevices,
    validateTemperatureMessage,
    handleMessage,
    isMessageAuthenticated
};
