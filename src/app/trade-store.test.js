const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

function harness(responses) {
    const calls = [];
    const events = [];
    const listeners = {};
    const fetch = async (url, options = {}) => {
        calls.push({ url, options });
        const response = responses.shift() ?? [];
        return { ok: true, status: 200, json: async () => response };
    };
    const context = {
        fetch,
        URLSearchParams,
        CustomEvent: class { constructor(type) { this.type = type; } },
        window: {
            addEventListener: (name, callback) => { (listeners[name] ||= []).push(callback); },
            dispatchEvent: (event) => {
                events.push(event.type);
                (listeners[event.type] || []).forEach((callback) => callback(event));
            }
        }
    };
    const source = `${readFileSync(`${__dirname}/trade-store.js`, 'utf8')}\nthis.store = tradeStore;`;
    vm.runInNewContext(source, context);
    return { store: context.store, calls, events, window: context.window, CustomEvent: context.CustomEvent };
}

test('list teilt parallele und spaetere Lesezugriffe', async () => {
    const ui = harness([[{ id: 'trade-1', name: 'Elektro' }]]);

    const [first, second] = await Promise.all([ui.store.list(), ui.store.list()]);
    const third = await ui.store.list();

    assert.equal(ui.calls.length, 1);
    assert.equal(first, second);
    assert.equal(second, third);
});

test('Aenderungen leeren den Cache und laden aktuelle Gewerke', async () => {
    const ui = harness([
        [{ id: 'trade-1', name: 'Elektro' }],
        { id: 'trade-2', name: 'Heizung' },
        [{ id: 'trade-1', name: 'Elektro' }, { id: 'trade-2', name: 'Heizung' }]
    ]);

    await ui.store.list();
    await ui.store.add('Heizung', '#72b788');
    const current = await ui.store.list();

    assert.equal(ui.calls.length, 3);
    assert.equal(ui.calls[1].options.method, 'POST');
    assert.deepEqual(current.map((trade) => trade.id), ['trade-1', 'trade-2']);
    assert.deepEqual(ui.events, ['trades:changed']);
});

test('externe Gewerk-Aenderungen wie ein Import leeren den Cache', async () => {
    const ui = harness([
        [{ id: 'trade-old', name: 'Alt', color: '#72b788' }],
        [{ id: 'trade-new', name: 'Neu', color: '#63b5ad' }]
    ]);

    await ui.store.list();
    // Use the same browser event emitted after a successful replacement import.
    ui.window.dispatchEvent(new ui.CustomEvent('trades:changed'));
    const current = await ui.store.list();

    assert.equal(ui.calls.length, 2);
    assert.deepEqual(current.map((trade) => trade.id), ['trade-new']);
});
