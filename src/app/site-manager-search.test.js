const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

class Element {
    constructor(tagName = 'div') {
        this.tagName = tagName;
        this.children = [];
        this.listeners = {};
        this.attributes = {};
        this.dataset = {};
        this.hidden = false;
        this.disabled = false;
        this.textContent = '';
        this.value = '';
        this.classList = { toggle() {} };
    }
    addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; this.textContent = ''; }
    setAttribute(name, value) { this.attributes[name] = value; }
    removeAttribute(name) { delete this.attributes[name]; }
    querySelectorAll(selector) {
        return selector === 'button'
            ? this.children.flatMap((child) => child.children.filter((item) => item.tagName === 'button'))
            : [];
    }
    scrollIntoView() {}
    focus() {}
}

function harness(siteManagers) {
    const input = new Element('input');
    const suggestions = new Element('ul');
    suggestions.hidden = true;
    const status = new Element();
    const toggle = new Element('button');
    const calls = [];
    const listeners = {};
    const elements = {
        'site-manager-search-input': input,
        'site-manager-suggestions': suggestions,
        'site-manager-search-status': status,
        'site-manager-show-all': toggle
    };
    const document = {
        getElementById: (id) => elements[id],
        createElement: (tagName) => new Element(tagName),
        addEventListener() {}
    };
    const window = { addEventListener(name, callback) { listeners[name] = callback; } };
    const context = {
        document,
        window,
        siteManagerStore: { listActive: async () => siteManagers },
        siteManagerPostalCodes: (territories) => territories.map((territory) => territory.postalCode),
        tradeStore: { colors: ['#72b788', '#63b5ad', '#68a9c7'] },
        MAP_SETTINGS: { postalCodes: { fillColor: '#4caf50' } },
        postalCodeFilter: (codes) => ['in', ['get', 'plz'], ['literal', codes]],
        setPostalCodeColor(map, color) { calls.push(['color', color]); },
        setVisiblePostalCodes(map, codes) { calls.push(['visible', [...codes]]); },
        zoomToPostalCodes() {}
    };
    const source = `${readFileSync(`${__dirname}/site-manager-search.js`, 'utf8')}\nthis.initialize = initializeSiteManagerSearch;`;
    vm.runInNewContext(source, context);
    return { initialize: () => context.initialize({
        setLayoutProperty(...args) { calls.push(['layout', ...args]); },
        setFilter(...args) { calls.push(['filter', ...args]); }
    }, []), input, suggestions, status, toggle, calls, listeners };
}

function click(element) {
    element.listeners.click.forEach((listener) => listener({ target: element }));
}

test('aktive Bauleiter werden nach dem Laden als Vorschlaege angezeigt', async () => {
    const ui = harness([{ id: 'manager-1', name: 'Ackermann', territories: [{ postalCode: '08' }] }]);

    await ui.initialize({}, []);

    assert.equal(ui.input.disabled, false);
    assert.equal(ui.status.textContent, '');
    assert.equal(ui.suggestions.hidden, false);
    assert.equal(ui.suggestions.children.length, 1);
    assert.equal(ui.suggestions.children[0].children[0].textContent, 'Ackermann');
    assert.equal(ui.input.attributes['aria-expanded'], 'true');
});

test('ausgewaehlter Bauleiter wird wie ein Unternehmen unter dem Suchfeld angezeigt', async () => {
    const ui = harness([{ id: 'manager-1', name: 'Ackermann', territories: [{ postalCode: '08' }] }]);

    await ui.initialize({}, []);
    click(ui.suggestions.children[0].children[0]);

    assert.equal(ui.input.value, '');
    assert.equal(ui.suggestions.hidden, true);
    const details = ui.status.children[0];
    assert.equal(details.className, 'company-search__company-details');
    assert.equal(details.children[0].children[0].textContent, 'Ackermann');
    assert.equal(details.children[1].textContent, 'PLZ-Gebiete: 08');
});

const managers = [
    { id: 'a', name: 'Anna', territories: [{ postalCode: '08' }, { postalCode: '09' }] },
    { id: 'b', name: 'Bert', territories: [{ postalCode: 'LUX' }] }
];

test('Gesamtansicht zeigt zugeordnete Gebiete mit Namen und konsistenten Farben', async () => {
    const ui = harness(managers);
    await ui.initialize();
    click(ui.toggle);
    assert.equal(ui.toggle.attributes['aria-pressed'], 'true');
    assert.deepEqual(ui.calls.find(call => call[0] === 'visible')[1], ['08', '09', 'LUX']);
    const colors = ui.calls.find(call => call[0] === 'color')[1];
    assert.equal(colors[3], colors[5]);
    assert.notEqual(colors[3], colors[7]);
    const names = ui.calls.find(call => call[0] === 'layout')[3];
    assert.equal(names[3], 'Anna');
    assert.equal(names[7], 'Bert');
});

test('Ausschalten stellt die Einzelauswahl wieder her; Suche beendet Gesamtansicht', async () => {
    const ui = harness(managers);
    await ui.initialize();
    click(ui.suggestions.children[0].children[0]);
    click(ui.toggle);
    click(ui.toggle);
    assert.deepEqual(ui.calls.filter(call => call[0] === 'visible').at(-1)[1], ['08', '09']);
    click(ui.toggle);
    ui.input.listeners.focus[0]();
    click(ui.suggestions.children[1].children[0]);
    assert.equal(ui.toggle.attributes['aria-pressed'], 'false');
    assert.deepEqual(ui.calls.filter(call => call[0] === 'visible').at(-1)[1], ['LUX']);
});

test('Gesamtansicht aktualisiert sich nach Datenänderungen und Kartenstart', async () => {
    const data = [...managers];
    const ui = harness(data);
    await ui.initialize();
    click(ui.toggle);
    data.pop();
    await ui.listeners['site-managers:changed']();
    ui.listeners['postal-code-layers:ready']();
    assert.equal(ui.toggle.attributes['aria-pressed'], 'true');
    assert.deepEqual(ui.calls.filter(call => call[0] === 'visible').at(-1)[1], ['08', '09']);
});

test('Leere Gesamtansicht und Ausschalten ohne Einzelauswahl zeigen keine Gebiete', async () => {
    const ui = harness([]);
    await ui.initialize();
    click(ui.toggle);
    assert.equal(ui.status.textContent, 'Keine aktiven Bauleiter verfügbar.');
    click(ui.toggle);
    assert.deepEqual(ui.calls.at(-1), ['visible', []]);
});
