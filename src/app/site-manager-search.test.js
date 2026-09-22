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
    const elements = {
        'site-manager-search-input': input,
        'site-manager-suggestions': suggestions,
        'site-manager-search-status': status
    };
    const document = {
        getElementById: (id) => elements[id],
        createElement: (tagName) => new Element(tagName),
        addEventListener() {}
    };
    const window = { addEventListener() {} };
    const context = {
        document,
        window,
        siteManagerStore: { listActive: async () => siteManagers },
        siteManagerPostalCodes: (territories) => territories.map((territory) => territory.postalCode),
        setVisiblePostalCodes() {},
        zoomToPostalCodes() {}
    };
    const source = `${readFileSync(`${__dirname}/site-manager-search.js`, 'utf8')}\nthis.initialize = initializeSiteManagerSearch;`;
    vm.runInNewContext(source, context);
    return { initialize: context.initialize, input, suggestions, status };
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
