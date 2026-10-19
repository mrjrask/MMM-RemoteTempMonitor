const test = require('node:test');
const assert = require('node:assert/strict');
const Module = require('node:module');

function loadNodeHelper() {
  const helperPath = require.resolve('../node_helper.js');
  delete require.cache[helperPath];

  const originalLoad = Module._load;
  Module._load = function(request, parent, isMain) {
    if (request === 'node_helper') {
      return { create: (definition) => definition };
    }
    return originalLoad.call(this, request, parent, isMain);
  };

  try {
    return require('../node_helper.js');
  } finally {
    Module._load = originalLoad;
  }
}

test('parseAggregateRequestUrl ignores malformed Host headers', () => {
  const helper = loadNodeHelper();
  const parsed = helper.parseAggregateRequestUrl({ url: '/temps', headers: { host: 'bad host' } });

  assert.equal(parsed.pathname, '/temps');
});

test('parseAggregateRequestUrl returns null for malformed request URLs', () => {
  const helper = loadNodeHelper();

  assert.equal(helper.parseAggregateRequestUrl({ url: 'http://[::1', headers: {} }), null);
});


test('getTemperatureSnapshot includes PiNOC-compatible aliases', () => {
  const helper = loadNodeHelper();
  helper.devices = {
    pi: {
      deviceId: '192.168.1.42:pi-test',
      hostname: 'pi-test',
      celsius: 42.5,
      fahrenheit: 108.5,
      lastSeen: 1784808000000,
      ip: '192.168.1.42'
    }
  };
  helper.latestUpdateAt = 1784808000000;

  const snapshot = helper.getTemperatureSnapshot();

  assert.equal(snapshot.count, 1);
  assert.equal(snapshot.temps, snapshot.devices);
  assert.equal(snapshot.temperatures, snapshot.devices);
  assert.equal(snapshot.devices[0].device_id, '192.168.1.42:pi-test');
  assert.equal(snapshot.devices[0].id, '192.168.1.42:pi-test');
  assert.equal(snapshot.devices[0].name, 'pi-test');
  assert.equal(snapshot.devices[0].temp_c, 42.5);
  assert.equal(snapshot.devices[0].temperature_c, 42.5);
  assert.equal(snapshot.devices[0].temperature.celsius, 42.5);
});

test('isServiceOutdated compares versions and treats missing versions as outdated', () => {
  const helper = loadNodeHelper();

  assert.equal(helper.isServiceOutdated('1.0.0', '1.1.0'), true);
  assert.equal(helper.isServiceOutdated('1.1.0', '1.1.0'), false);
  assert.equal(helper.isServiceOutdated('1.10.0', '1.9.0'), false);
  assert.equal(helper.isServiceOutdated(null, '1.1.0'), true);
  assert.equal(helper.isServiceOutdated(null, null), false);
});

test('handleMessage flags devices running an outdated remote-service', () => {
  const helper = loadNodeHelper();
  helper.config = { latestServiceVersion: '1.1.0' };
  helper.devices = {};
  helper.sendSocketNotification = () => {};

  const send = (hostname, extra) => helper.handleMessage(
    Buffer.from(JSON.stringify({ type: 'temperature', hostname, temperature: { celsius: 40, fahrenheit: 104 }, ...extra })),
    { address: '10.0.0.5' }
  );
  send('old', {});
  send('stale', { service_version: '1.0.0' });
  send('current', { service_version: '1.1.0' });

  assert.equal(helper.devices['10.0.0.5:old'].serviceUpdateAvailable, true);
  assert.equal(helper.devices['10.0.0.5:stale'].serviceUpdateAvailable, true);
  assert.equal(helper.devices['10.0.0.5:current'].serviceUpdateAvailable, false);
});
