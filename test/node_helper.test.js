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
