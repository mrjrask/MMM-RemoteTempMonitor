const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadModule(file) {
  let definition;
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', file), 'utf8'), {
    Module: { register: (_name, value) => { definition = value; } },
    Log: { info: () => {} }
  });
  return definition;
}

test('temperature module forwards status updates to the status display', () => {
  const temperature = loadModule('MMM-RemoteTempMonitor.js');
  const status = loadModule('MMM-RemoteTempStatusMonitor/MMM-RemoteTempStatusMonitor.js');
  const receiver = Object.assign({}, status, { config: status.defaults, updateDom: () => {} });
  receiver.start();
  const sender = Object.assign({}, temperature, {
    sendNotification: (kind, payload) => receiver.notificationReceived(kind, payload)
  });
  const device = { hostname: 'pi', statusUpdateAvailable: true, statusClientUpdate: false };
  sender.socketNotificationReceived('STATUS_UPDATE', { devices: [device] });
  assert.equal(receiver.loaded, true);
  assert.equal(receiver.devices[0].hostname, 'pi');
});
