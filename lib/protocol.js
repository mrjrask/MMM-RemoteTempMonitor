"use strict";
const crypto = require("crypto");
const FORBIDDEN_IDS = new Set(["__proto__", "constructor", "prototype", "__local_machine__"]);
function validText(value, limit = 128) {
    return typeof value === "string" && value.trim().length > 0 && value.length <= limit && !/[\x00-\x1f\x7f]/.test(value);
}
function validIdentity(data) {
    return data && typeof data === "object" && !Array.isArray(data) && validText(data.hostname) &&
        (data.device_id === undefined || data.device_id === null ||
         (validText(data.device_id) && !FORBIDDEN_IDS.has(data.device_id))) &&
        ["pi_model", "pi_ram", "platform", "cpu_arch", "service_version"].every(key =>
            data[key] == null || validText(data[key]));
}
function timingSafeStringEqual(actual, expected) {
    if (typeof actual !== "string") return false;
    const a = Buffer.from(actual), b = Buffer.from(expected);
    return a.length === b.length && crypto.timingSafeEqual(a, b);
}
function isMessageAuthenticated(data, secret, maxPacketAge = 120000) {
    if (!secret) return true;
    if (!data || typeof data.hmac !== "string" || !/^[a-f0-9]{64}$/.test(data.hmac) ||
        !Number.isSafeInteger(data.timestamp) || Math.abs(Date.now() - data.timestamp * 1000) > maxPacketAge) return false;
    const unsigned = { ...data };
    delete unsigned.hmac;
    const expected = crypto.createHmac("sha256", secret).update(JSON.stringify(unsigned)).digest("hex");
    return timingSafeStringEqual(data.hmac, expected);
}
function validateTemperatureMessage(data, secret = "", maxPacketAge = 120000) {
    if (!validIdentity(data) || data.type !== "temperature" || !data.temperature) {
        return { valid: false, reason: "invalid temperature fields" };
    }
    if (!isMessageAuthenticated(data, secret, maxPacketAge)) return { valid: false, reason: "authentication failed" };
    const { celsius, fahrenheit } = data.temperature;
    if (typeof celsius !== "number" || typeof fahrenheit !== "number" ||
        !Number.isFinite(celsius) || !Number.isFinite(fahrenheit) || celsius < -50 || celsius > 150 ||
        Math.abs(fahrenheit - (celsius * 9 / 5 + 32)) > 0.2) {
        return { valid: false, reason: "invalid or inconsistent temperature values" };
    }
    return { valid: true, celsius, fahrenheit };
}
function pruneDevices(devices, maxAge, now = Date.now()) {
    let changed = false;
    for (const id of Object.keys(devices)) {
        if (now - devices[id].lastSeen > maxAge) { delete devices[id]; changed = true; }
    }
    return changed;
}
function admitDevice(devices, id, data, config) {
    if (config.sharedSecret && devices[id] && data.timestamp <= devices[id].packetTimestamp) return false;
    if (!Object.hasOwn(devices, id) && Object.keys(devices).length >= (config.maxDevices || 256)) return false;
    return true;
}
module.exports = { validIdentity, timingSafeStringEqual, isMessageAuthenticated, validateTemperatureMessage, pruneDevices, admitDevice };
