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
        addGermanyPlzLayers: async () => ({ features: [] }),
        addLuxembourgLayers: async () => ({ features: [] }),
        createPlzLabelData: (data) => data,
        Event: class { constructor(type) { this.type = type; } },
        MAP_SETTINGS: { postalCodes: { label: { minZoom: 4, font: ['Noto Sans Regular'], color: '#111' } }, map: { center: [10, 51], zoom: 5, glyphsUrl: '/glyphs', basemapUrl: 'pmtiles:///map.pmtiles' } },
        window: { dispatchEvent() {}, plzLog: { error: (message) => logMessages.push(message) } },
        console: { log() {}, error: (message) => logMessages.push(message) }
    };
    if (withLibraries) {
        context.pmtiles = { Protocol: class { tile() {} } };
        context.maplibregl = {
            addProtocol() {},
            Map: class {
                constructor(options) { this.options = options; context.map = this; this.listeners = {}; }
                on(name, callback) { this.listeners[name] = callback; }
                addSource(id, source) { (this.sources ||= {})[id] = source; }
                addLayer(layer) { (this.layers ||= []).push(layer); }
                setFilter(...args) { (this.filters ||= []).push(args); }
                setPaintProperty() {}
                setLayoutProperty(...args) { (this.layouts ||= []).push(args); }
                getZoom() { return 5; }
                isSourceLoaded() { return this.sourceLoaded === true; }
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

test('protokolliert einen einzelnen Basemap-Fehler ohne dauerhafte Warnung', () => {
    const { context, elements, logMessages } = runMap({ withLibraries: true });

    context.map.listeners.error({ sourceId: 'basemap', error: new Error('HTTP 500') });

    assert.equal(elements['map-load-error'].hidden, true);
    assert.ok(logMessages.some((message) => message.includes('HTTP 500')));
});

test('zeigt einen fatalen PMTiles-Headerfehler sofort an', () => {
    const { context, elements } = runMap({ withLibraries: true });

    context.map.listeners.error({ sourceId: 'basemap', error: new Error('Invalid PMTiles header') });

    assert.equal(elements['map-load-error'].hidden, false);
    assert.match(elements['map-load-error'].textContent, /Kartenarchiv/);
});

test('zeigt wiederholte Basemap-Abruffehler an', () => {
    const { context, elements } = runMap({ withLibraries: true });

    context.map.listeners.error({ sourceId: 'basemap', error: new Error('HTTP 500') });
    context.map.listeners.error({ sourceId: 'basemap', error: new Error('HTTP 500') });

    assert.equal(elements['map-load-error'].hidden, false);
    assert.match(elements['map-load-error'].textContent, /Kartenarchiv/);
});

test('blendet die Warnung nach erfolgreichem Laden der Basemap wieder aus', () => {
    const { context, elements } = runMap({ withLibraries: true });
    context.map.listeners.error({ sourceId: 'basemap', error: new Error('HTTP 500') });
    context.map.listeners.error({ sourceId: 'basemap', error: new Error('HTTP 500') });

    context.map.sourceLoaded = true;
    context.map.listeners.sourcedata({ sourceId: 'basemap' });

    assert.equal(elements['map-load-error'].hidden, true);
    assert.equal(elements['map-load-error'].textContent, '');
});


test('fruehe Gesamtansicht wartet auf Kartenlayer und ergaenzt separate Namen', async () => {
    const { context, initialized } = runMap({ withLibraries: true });
    const bridge = initialized[1][1];
    bridge.setFilter('site-manager-names', ['in', ['get', 'plz'], ['literal', ['08']]]);
    bridge.setLayoutProperty('site-manager-names', 'text-field', 'Anna');
    assert.equal(context.map.filters, undefined);
    await context.map.listeners.load();
    assert.equal(context.map.filters[0][0], 'site-manager-names');
    assert.equal(context.map.layouts[0][2], 'Anna');
    const names = context.map.layers.find(layer => layer.id === 'site-manager-names');
    assert.equal(names.layout['text-anchor'], 'top');
    assert.equal(names.layout['text-offset'][1], 1.2);
});
