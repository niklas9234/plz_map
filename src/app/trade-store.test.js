const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

function harness(responses) {
    const calls = [];
    const events = [];
    const fetch = async (url, options = {}) => {
        calls.push({ url, options });
        const response = responses.shift() ?? [];
        return { ok: true, status: 200, json: async () => response };
    };
    const context = {
        fetch,
        URLSearchParams,
        CustomEvent: class { constructor(type) { this.type = type; } },
        window: { dispatchEvent: (event) => events.push(event.type) }
    };
    const source = `${readFileSync(`${__dirname}/trade-store.js`, 'utf8')}\nthis.store = tradeStore;`;
    vm.runInNewContext(source, context);
    return { store: context.store, calls, events };
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
