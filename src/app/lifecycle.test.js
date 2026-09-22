const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

test('pagehide meldet die aktuelle Surface per Beacon ab', async () => {
    const listeners = {};
    const button = {
        hidden: true,
        addEventListener(name, callback) { listeners[`button:${name}`] = callback; },
    };
    const beacons = [];
    const window = {
        addEventListener(name, callback) { listeners[name] = callback; },
        setInterval() { return 42; },
        clearInterval() {},
    };
    const navigator = {
        sendBeacon(url, body) { beacons.push({url, body}); return true; },
    };
    const fetch = async (url) => ({
        ok: true,
        json: async () => ({surfaceId: 'surface-1', token: 'secret', heartbeatInterval: 30}),
        status: 200,
    });
    const context = {
        Blob, fetch, navigator, window,
        document: {getElementById: () => button},
    };

    vm.runInNewContext(readFileSync(`${__dirname}/lifecycle.js`, 'utf8'), context);
    await new Promise((resolve) => setImmediate(resolve));
    listeners.pagehide({persisted: false});

    assert.equal(beacons.length, 1);
    assert.equal(beacons[0].url, '/api/system/session/close');
    assert.deepEqual(
        JSON.parse(await beacons[0].body.text()),
        {surfaceId: 'surface-1', token: 'secret'},
    );
});
