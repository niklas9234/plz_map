const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

class Element {
    constructor() {
        this.listeners = {}; this.hidden = false; this.disabled = false; this.textContent = '';
        this.value = ''; this.files = []; this.children = []; this.attributes = {};
        this.classList = { toggle: () => {} };
    }
    addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
    async emit(name, extra = {}) { for (const callback of this.listeners[name] || []) await callback({ preventDefault() {}, ...extra }); }
    click() { this.clicked = true; }
    showModal() { this.open = true; }
    close() { this.open = false; }
    setAttribute(name, value) { this.attributes[name] = value; }
    replaceChildren() { this.children = []; }
    append(child) { this.children.push(child); }
}

function harness(importData) {
    const ids = ['import-master-data', 'import-master-data-file', 'export-master-data',
        'import-master-data-confirmation', 'import-master-data-status', 'import-master-data-errors',
        'import-master-data-warning', 'confirm-master-data-import', 'cancel-master-data-import'];
    const elements = Object.fromEntries(ids.map((id) => [id, new Element()]));
    elements['confirm-master-data-import'].hidden = true;
    const dispatched = [];
    const document = {
        getElementById: (id) => elements[id],
        createElement: () => new Element(),
        addEventListener: (name, callback) => { if (name === 'DOMContentLoaded') document.ready = callback; },
        dispatchEvent: (event) => dispatched.push(event.type)
    };
    const context = { document, companyStore: { importData }, CustomEvent: class { constructor(type) { this.type = type; } } };
    vm.runInNewContext(readFileSync(`${__dirname}/import-management.js`, 'utf8'), context);
    document.ready();
    return { elements, dispatched };
}

test('CompanyStore sendet Dokument und Modus an den Import-Endpunkt', async () => {
    const requests = [];
    const context = {
        fetch: async (url, options) => {
            requests.push({ url, options });
            return { ok: true, status: 200, json: async () => ({ written: false }) };
        },
        window: { dispatchEvent() {} },
        CustomEvent: class {}
    };
    const source = `${readFileSync(`${__dirname}/company-store.js`, 'utf8')}\nthis.store = companyStore;`;
    vm.runInNewContext(source, context);
    await context.store.importData({ schemaVersion: 1 }, 'validate');
    assert.equal(requests[0].url, '/api/admin/import?mode=validate');
    assert.equal(requests[0].options.method, 'POST');
    assert.equal(requests[0].options.headers['Content-Type'], 'application/json');
    assert.equal(requests[0].options.body, '{"schemaVersion":1}');
});

test('CompanyStore löst nach erfolgreichem Ersatz alle Änderungsereignisse aus', async () => {
    const events = [];
    const context = {
        fetch: async () => ({ ok: true, status: 200, json: async () => ({ written: true }) }),
        window: { dispatchEvent: (event) => events.push(event.type) },
        CustomEvent: class { constructor(type) { this.type = type; } }
    };
    const source = `${readFileSync(`${__dirname}/company-store.js`, 'utf8')}\nthis.store = companyStore;`;
    vm.runInNewContext(source, context);

    await context.store.importData({}, 'replace');

    assert.deepEqual(events, ['companies:changed', 'trades:changed', 'site-managers:changed']);
});

test('Dateiauswahl validiert zuerst und importiert erst nach Bestätigung', async () => {
    const calls = [];
    const ui = harness(async (document, mode) => {
        calls.push([document, mode]);
        return { trades: 2, companies: 3, siteManagers: 4, written: mode === 'replace' };
    });
    ui.elements['import-master-data-file'].files = [{ text: async () => '{"schemaVersion":1}' }];
    await ui.elements['import-master-data-file'].emit('change');
    assert.deepEqual(calls.map((call) => call[1]), ['validate']);
    assert.match(ui.elements['import-master-data-status'].textContent, /2 Gewerke, 3 Unternehmen und 4 Bauleiter/);
    assert.equal(ui.elements['confirm-master-data-import'].hidden, false);
    await ui.elements['confirm-master-data-import'].emit('click');
    assert.deepEqual(calls.map((call) => call[1]), ['validate', 'replace']);
    assert.deepEqual(ui.dispatched, ['site-manager-management:open', 'trade-management:open']);
});

test('ungültiges JSON wird ohne API-Aufruf getrennt angezeigt', async () => {
    let called = false;
    const ui = harness(async () => { called = true; });
    ui.elements['import-master-data-file'].files = [{ text: async () => '{kaputt' }];
    await ui.elements['import-master-data-file'].emit('change');
    assert.equal(called, false);
    assert.match(ui.elements['import-master-data-status'].textContent, /kein gültiges JSON/);
});

test('schemaVersion und sämtliche Validierungsfelder werden angezeigt', async () => {
    const error = Object.assign(new Error('abgelehnt'), {
        code: 'invalid_import', fields: ['schemaVersion: inkompatibel', 'companies[2].name: fehlt']
    });
    const ui = harness(async () => { throw error; });
    ui.elements['import-master-data-file'].files = [{ text: async () => '{}' }];
    await ui.elements['import-master-data-file'].emit('change');
    assert.match(ui.elements['import-master-data-status'].textContent, /schemaVersion/);
    assert.deepEqual(ui.elements['import-master-data-errors'].children.map((item) => item.textContent), error.fields);
});

test('Netzwerkfehler wird lesbar angezeigt und sperrt die Bestätigung', async () => {
    const error = Object.assign(new Error('Der Importdienst ist nicht erreichbar.'), { code: 'network_error' });
    const ui = harness(async () => { throw error; });
    ui.elements['import-master-data-file'].files = [{ text: async () => '{}' }];
    await ui.elements['import-master-data-file'].emit('change');
    assert.match(ui.elements['import-master-data-status'].textContent, /nicht erreichbar/);
    assert.equal(ui.elements['confirm-master-data-import'].hidden, true);
});
