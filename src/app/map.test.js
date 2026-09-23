const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

test('lädt die Kartenbibliotheken im Serverbetrieb über das CDN', () => {
    const html = readFileSync(`${__dirname}/index.html`, 'utf8');

    assert.match(html, /https:\/\/unpkg\.com\/maplibre-gl@5\/dist\/maplibre-gl\.js/);
    assert.match(html, /https:\/\/unpkg\.com\/maplibre-gl@5\/dist\/maplibre-gl\.css/);
    assert.match(html, /https:\/\/unpkg\.com\/pmtiles@4\/dist\/pmtiles\.js/);
    assert.doesNotMatch(html, /src="vendor\//);
});

function runMap({ withLibraries = false } = {}) {
    const initialized = [];
    const elements = {
        'map-load-error': { hidden: true, textContent: '' },
        'maplibre-script': createScriptElement(),
        'pmtiles-script': createScriptElement()
    };
    const logMessages = [];
    const context = {
        document: { getElementById: (id) => elements[id] },
        initializeCompanySearch: (map, data) => initialized.push(['company', map, data]),
        initializeSiteManagerSearch: (map, data) => initialized.push(['site-manager', map, data]),
        initializeAreaSearch: (map, data) => initialized.push(['area', map, data]),
        addBaseMapLayers() {},
        addGermanyPlzLayers: async () => [],
        addLuxembourgLayers: async () => [],
        MAP_SETTINGS: { map: { center: [10, 51], zoom: 5, glyphsUrl: '/glyphs', basemapUrl: 'pmtiles:///map.pmtiles' } },
        window: { plzLog: { error: (message) => logMessages.push(message) } },
        console: { log() {}, error: (message) => logMessages.push(message) }
    };
    if (withLibraries) {
        context.pmtiles = { Protocol: class { tile() {} } };
        context.maplibregl = {
            addProtocol() {},
            Map: class {
                constructor(options) { this.options = options; context.map = this; this.listeners = {}; }
                on(name, callback) { this.listeners[name] = callback; }
                getZoom() { return 5; }
            }
        };
    }
    vm.runInNewContext(readFileSync(`${__dirname}/map.js`, 'utf8'), context);
    return { context, elements, initialized, logMessages };
}

function createScriptElement() {
    return {
        listeners: {},
        addEventListener(name, callback) { this.listeners[name] = callback; }
    };
}

test('startet Suche und Karte mit erfolgreich geladenen Bibliotheken', () => {
    const { context, elements, initialized } = runMap({ withLibraries: true });

    assert.deepEqual(initialized.map(([name]) => name), ['company', 'site-manager', 'area']);
    assert.equal(context.map.options.style.sources.basemap.url, 'pmtiles:///map.pmtiles');
    assert.equal(elements['map-load-error'].hidden, true);
});

test('zeigt und protokolliert eine fehlende Kartenbibliothek', () => {
    const { elements, logMessages } = runMap();

    elements['maplibre-script'].listeners.error(new Error('Datei fehlt'));

    assert.equal(elements['map-load-error'].hidden, false);
    assert.match(elements['map-load-error'].textContent, /MapLibre GL JS/);
    assert.ok(logMessages.some((message) => message.includes('Datei fehlt')));
});

test('zeigt und protokolliert einen Ladefehler der PMTiles-Quelle', () => {
    const { context, elements, logMessages } = runMap({ withLibraries: true });

    context.map.listeners.error({ sourceId: 'basemap', error: new Error('HTTP 500') });

    assert.equal(elements['map-load-error'].hidden, false);
    assert.match(elements['map-load-error'].textContent, /Kartenarchiv/);
    assert.ok(logMessages.some((message) => message.includes('HTTP 500')));
});
