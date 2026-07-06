const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const cli = require('../bin/remote-temp-monitor-cli.js');

test('parseArgs handles common options', () => {
  const config = cli.parseArgs(['--port', '9999', '--sort', 'hostname', '--celsius-only', '--shared-secret', 'secret']);
  assert.equal(config.port, 9999);
  assert.equal(config.sortBy, 'hostname');
  assert.equal(config.showCelsius, true);
  assert.equal(config.showFahrenheit, false);
  assert.equal(config.sharedSecret, 'secret');
});

test('getTempLabel maps thresholds', () => {
  assert.equal(cli.getTempLabel(45, cli.DEFAULTS.tempThresholds), 'Normal');
  assert.equal(cli.getTempLabel(60, cli.DEFAULTS.tempThresholds), 'Warm');
  assert.equal(cli.getTempLabel(86, cli.DEFAULTS.tempThresholds), 'Critical');
});

test('sortDevices sorts by temperature and hostname', () => {
  const devices = [{ hostname: 'b', celsius: 30 }, { hostname: 'a', celsius: 70 }];
  assert.deepEqual(cli.sortDevices(devices, 'temperature').map(d => d.hostname), ['a', 'b']);
  assert.deepEqual(cli.sortDevices(devices, 'hostname').map(d => d.hostname), ['a', 'b']);
});

test('handleMessage validates numbers and keys duplicate hostnames by address', () => {
  const devices = {};
  const msg = Buffer.from(JSON.stringify({ type: 'temperature', hostname: 'pi', temperature: { celsius: '42.5', fahrenheit: '108.5' } }));
  assert.equal(cli.handleMessage(msg, { address: '192.0.2.10' }, devices), true);
  assert.equal(cli.handleMessage(msg, { address: '192.0.2.11' }, devices), true);
  assert.deepEqual(Object.keys(devices).sort(), ['192.0.2.10:pi', '192.0.2.11:pi']);
  assert.equal(devices['192.0.2.10:pi'].celsius, 42.5);
});

test('validateTemperatureMessage rejects out-of-range and authenticates token/HMAC', () => {
  const base = { type: 'temperature', hostname: 'pi', temperature: { celsius: 42, fahrenheit: 107.6 } };
  assert.equal(cli.validateTemperatureMessage({ ...base, temperature: { celsius: 200, fahrenheit: 392 } }).valid, false);
  assert.equal(cli.validateTemperatureMessage({ ...base, auth_token: 'secret' }, 'secret').valid, true);
  assert.equal(cli.validateTemperatureMessage({ ...base, auth_token: 'wrong' }, 'secret').valid, false);

  const unsigned = { ...base };
  const hmac = crypto.createHmac('sha256', 'secret').update(JSON.stringify(unsigned)).digest('hex');
  assert.equal(cli.validateTemperatureMessage({ ...unsigned, hmac }, 'secret').valid, true);
});
