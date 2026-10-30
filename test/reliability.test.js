const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { EventEmitter } = require('node:events');
const NodeModule = require('node:module');
const protocol = require('../lib/protocol');
const cli = require('../bin/remote-temp-monitor-cli');

function helper() {
    const filename = require.resolve('../node_helper');
    delete require.cache[filename];
    const load = NodeModule._load;
    NodeModule._load = function(request, ...args) {
        return request === 'node_helper' ? { create: definition => definition } : load.call(this, request, ...args);
    };
    let result;
    try { result = require(filename); } finally { NodeModule._load = load; }
    result.start();
    result.config = {};
    result.sendSocketNotification = () => {};
    return result;
}
const packet = (extra = {}) => ({ type: 'temperature', hostname: 'pi', temperature: { celsius: 40, fahrenheit: 104 }, ...extra });
const sign = data => ({ ...data, hmac: crypto.createHmac('sha256', 'secret').update(JSON.stringify(data)).digest('hex') });

test('all Python broadcasters produce signatures JavaScript accepts for whole/decimal temperatures and Unicode', () => {
    const code = `
import importlib.util, json, sys, types
from pathlib import Path
sys.modules['wmi'] = types.ModuleType('wmi')
root = Path('remote-service')
for file in ['Pi/temp_broadcaster.py', 'Mac/temp_broadcaster_mac.py', 'Windows/temp_broadcaster_windows.py']:
    spec = importlib.util.spec_from_file_location('broadcast_test', root / file)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    b = mod.TemperatureBroadcaster.__new__(mod.TemperatureBroadcaster)
    b.hostname = 'pi-é'; b.shared_secret = 'secret'; b.pi_model = '4'; b.pi_ram = '4GB'; b.cpu_arch = 'arm64'
    for value in [40.0, 42.5, -10.0, 0.0]: print(b.create_message(value))
`;
    const result = spawnSync(process.env.PYTHON || 'python3', ['-c', code], { cwd: path.join(__dirname, '..'), encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    const messages = result.stdout.trim().split('\n');
    assert.equal(messages.length, 12);
    for (const message of messages) assert.equal(protocol.validateTemperatureMessage(JSON.parse(message), 'secret').valid, true, message);
});

test('invalid identities, coerced numbers, and inconsistent units are rejected', () => {
    for (const data of [null, [], packet({ hostname: 2 }), packet({ hostname: '\x1b[2J' }), packet({ device_id: '__proto__' }), packet({ pi_model: {} }), packet({ temperature: { celsius: null, fahrenheit: 32 } }), packet({ temperature: { celsius: '40', fahrenheit: 104 } }), packet({ temperature: { celsius: 40, fahrenheit: 0 } })]) {
        assert.equal(protocol.validateTemperatureMessage(data).valid, false);
    }
});

test('signed packets must be fresh and cannot refresh lastSeen twice', () => {
    const devices = Object.create(null);
    const config = { ...cli.DEFAULTS, sharedSecret: 'secret' };
    const msg = Buffer.from(JSON.stringify(sign(packet({ timestamp: Math.floor(Date.now()/1000) }))));
    assert.equal(cli.handleMessage(msg, { address: '10.0.0.5' }, devices, config), true);
    const lastSeen = devices['10.0.0.5:pi'].lastSeen;
    assert.equal(cli.handleMessage(msg, { address: '10.0.0.5' }, devices, config), false);
    assert.equal(devices['10.0.0.5:pi'].lastSeen, lastSeen);
    assert.equal(protocol.validateTemperatureMessage(sign(packet({ timestamp: Math.floor(Date.now()/1000)-300 })), 'secret').valid, false);
});

test('CLI prunes stale identities and refuses new ones at its cap', () => {
    const devices = { stale: { lastSeen: 0 } };
    const config = { ...cli.DEFAULTS, sharedSecret: '', maxDevices: 1 };
    assert.equal(cli.handleMessage(Buffer.from(JSON.stringify(packet())), { address: '10.0.0.5' }, devices, config), true);
    assert.equal(Object.keys(devices).length, 1);
    assert.equal(cli.handleMessage(Buffer.from(JSON.stringify(packet({ hostname: 'second' }))), { address: '10.0.0.5' }, devices, config), false);
});

test('helper batches bursts and caps both temperature and status tables', t => {
    t.mock.timers.enable({ apis: ['setTimeout'] });
    const h = helper(); h.config.maxDevices = 2;
    const sent = []; h.sendSocketNotification = kind => sent.push(kind);
    for (let i=0;i<20;i++) {
        h.handleMessage(Buffer.from(JSON.stringify(packet({ hostname: `pi-${i}` }))), { address: '10.0.0.5' });
        h.handleMessage(Buffer.from(JSON.stringify({ type: 'status', hostname: `pi-${i}`, statusUpdateAvailable: true, statusClientUpdate: false })), { address: '10.0.0.5' });
    }
    assert.equal(Object.keys(h.devices).length, 2);
    assert.equal(Object.keys(h.statusDevices).length, 2);
    assert.equal(sent.length, 0);
    t.mock.timers.tick(250);
    assert.deepEqual(sent.sort(), ['STATUS_UPDATE', 'TEMPERATURE_UPDATE']);
    h.stop();
});

test('helper retries socket failures without duplicating timers and cancels retry on stop', t => {
    t.mock.timers.enable({ apis: ['setTimeout'] });
    const dgram = require('node:dgram');
    const original = dgram.createSocket;
    const sockets = [];
    dgram.createSocket = () => {
        const socket = new EventEmitter(); socket.bind = () => {}; socket.close = () => {};
        sockets.push(socket); return socket;
    };
    t.after(() => { dgram.createSocket = original; });
    const h = helper();
    let cleanups = 0; h.startCleanupTimer = () => { cleanups++; h.cleanupTimer = 1; };
    h.startListening();
    sockets[0].emit('error', new Error('bind failed'));
    t.mock.timers.tick(5000);
    assert.equal(sockets.length, 2);
    assert.equal(cleanups, 1);
    sockets[1].emit('error', new Error('network error'));
    h.stop();
    t.mock.timers.tick(5000);
    assert.equal(sockets.length, 2);
});

test('conflicting module configuration never overwrites active helper settings', () => {
    const h = helper(); h.config = { port: 9876 }; h.started = true;
    const sent = []; h.sendSocketNotification = kind => sent.push(kind);
    h.socketNotificationReceived('CONFIG', { port: 9999 });
    assert.equal(h.config.port, 9876);
    assert.deepEqual(sent, ['CONFIG_ERROR']); h.stop();
});

test('status DOM appends its header and visible classes match CSS selectors', () => {
    let definition;
    const element = tag => ({ tag, children: [], style: {}, appendChild(child) { this.children.push(child); } });
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../MMM-RemoteTempStatusMonitor/MMM-RemoteTempStatusMonitor.js'), 'utf8'), {
        Module: { register: (_, value) => { definition = value; } }, document: { createElement: element }
    });
    definition.config = definition.defaults;
    definition.devices = [{ hostname: 'pi', statusUpdateAvailable: true, statusClientUpdate: false }];
    const table = definition.getDom();
    assert.equal(table.children[0].tag, 'thead');
    const content = table.children[1].children[0].children[0].children[0];
    const dots = content.children[0];
    assert.equal(dots.children[0].className, 'status-update-dot visible');
    assert.equal(dots.children[1].className, 'status-client-dot');
    const css = fs.readFileSync(path.join(__dirname, '../MMM-RemoteTempStatusMonitor/MMM-RemoteTempStatusMonitor.css'), 'utf8');
    assert.match(css, /\.status-update-dot\.visible \.status-dot/);
    assert.match(css, /\.status-client-dot\.visible \.status-dot/);
});
