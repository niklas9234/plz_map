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
        this.textContent = '';
        this.value = '';
        this.classList = { toggle() {} };
        this.style = {};
    }
    addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; this.textContent = ''; }
    setAttribute(name, value) { this.attributes[name] = value; }
    getAttribute(name) { return this.attributes[name] ?? null; }
    removeAttribute(name) { delete this.attributes[name]; }
    querySelectorAll(selector) {
        return selector === 'button'
            ? this.children.flatMap((child) => child.children.filter((item) => item.tagName === 'button'))
            : [];
    }
    scrollIntoView() {}
    focus() {}
}

function harness(companies) {
    const input = new Element('input');
    const suggestions = new Element('ul');
    suggestions.hidden = true;
    const status = new Element();
    const elements = {
        'company-search-input': input,
        'company-suggestions': suggestions,
        'company-search-status': status
    };
    const visibleSelections = [];
    const document = {
        getElementById: (id) => elements[id],
        createElement: (tagName) => new Element(tagName),
        addEventListener() {}
    };
    const window = { addEventListener() {} };
    const context = {
        document,
        window,
        maplibregl: { LngLatBounds: class { isEmpty() { return true; } } },
        companyStore: { list: async () => companies },
        tradeStore: {
            list: async () => [
                { id: 'trade-1', name: 'Elektro', status: 'active' },
                { id: 'trade-2', name: 'Heizung', status: 'active' }
            ],
            colorFor: async () => '#123456'
        }
    };
    const map = {
        setFilter(id, filter) { visibleSelections.push({ id, filter }); },
        setPaintProperty() {}
    };
    const source = `${readFileSync(`${__dirname}/company-search.js`, 'utf8')}\nthis.initialize = initializeCompanySearch;`;
    vm.runInNewContext(source, context);
    return { initialize: context.initialize, input, suggestions, status, visibleSelections, map };
}

test('gleiche PPS-Nummer zeigt beide Unternehmen und waehlt per ID aus', async () => {
    const companies = [
        { id: 'company-1', name: 'Beispiel GmbH', ppsNumber: 'PPS-1', tradeAssignments: [{ tradeId: 'trade-1', territories: [{ postalCode: '08', role: 'primary' }] }] },
        { id: 'company-2', name: 'Beispiel GmbH', ppsNumber: 'PPS-1', tradeAssignments: [{ tradeId: 'trade-2', territories: [{ postalCode: '10', role: 'primary' }] }] }
    ];
    const ui = harness(companies);
    await ui.initialize(ui.map, []);

    ui.input.value = 'PPS-1';
    ui.input.listeners.input[0]();

    const buttons = ui.suggestions.querySelectorAll('button');
    assert.equal(buttons.length, 2);
    assert.deepEqual(buttons.map((button) => button.dataset.companyId), ['company-1', 'company-2']);

    ui.input.listeners.keydown[0]({ key: 'ArrowDown', preventDefault() {} });
    ui.input.listeners.keydown[0]({ key: 'ArrowDown', preventDefault() {} });
    ui.input.listeners.keydown[0]({ key: 'Enter', preventDefault() {} });

    assert.deepEqual(Array.from(ui.visibleSelections.at(-1).filter[2][1]), ['10']);
});

test('zeigt Unternehmensinformationen beim Ausklappen der Details', async () => {
    const companies = [{
        id: 'company-1',
        name: 'Beispiel GmbH',
        ppsNumber: 'PPS-1',
        tradeAssignments: [{ tradeId: 'trade-1', territories: [{ postalCode: '08', role: 'primary' }] }],
        information: [
            { category: 'phone', value: '0323 123 1231' },
            { category: 'contact', value: 'Max Mustermann' }
        ]
    }];
    const ui = harness(companies);
    await ui.initialize(ui.map, []);

    ui.input.value = 'Beispiel';
    ui.input.listeners.input[0]();
    ui.suggestions.querySelectorAll('button')[0].listeners.click[0]();

    const companyDetails = ui.status.children[0];
    const detailsButton = companyDetails.children[0].children[2];
    const detailsArea = companyDetails.children[1];
    assert.equal(detailsArea.hidden, true);

    detailsButton.listeners.click[0]();

    assert.equal(detailsArea.hidden, false);
    const information = detailsArea.children[1];
    assert.equal(information.className, 'company-search__information');
    assert.equal(detailsArea.children[0].className, 'company-search__postal-codes');
    assert.deepEqual(information.children.map((child) => child.textContent), [
        'Telefon', '0323 123 1231', 'Ansprechpartner', 'Max Mustermann'
    ]);
});
