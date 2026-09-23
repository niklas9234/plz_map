const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

test('lädt die Kartenbibliotheken beim lokalen Start weiterhin über das CDN', () => {
    const html = readFileSync(`${__dirname}/index.html`, 'utf8');

    assert.match(html, /https:\/\/unpkg\.com\/maplibre-gl@5\/dist\/maplibre-gl\.js/);
    assert.match(html, /https:\/\/unpkg\.com\/maplibre-gl@5\/dist\/maplibre-gl\.css/);
    assert.match(html, /https:\/\/unpkg\.com\/pmtiles@4\/dist\/pmtiles\.js/);
    assert.doesNotMatch(html, /id="map-load-error"/);
});

test('Suche startet auch ohne geladene Kartenbibliotheken', async () => {
    const initialized = [];
    const scriptListeners = [];
    const context = {
        document: {
            getElementById() {
                return { addEventListener(name, callback) { scriptListeners.push([name, callback]); } };
            }
        },
        initializeCompanySearch: async (map, data) => initialized.push(['company', map, data]),
        initializeSiteManagerSearch: async (map, data) => initialized.push(['site-manager', map, data]),
        initializeAreaSearch: async (map, data) => initialized.push(['area', map, data]),
        console
    };

    vm.runInNewContext(readFileSync(`${__dirname}/map.js`, 'utf8'), context);
    await Promise.resolve();

    assert.deepEqual(initialized.map(([name]) => name), ['company', 'site-manager', 'area']);
    assert.equal(initialized[0][1], initialized[1][1]);
    assert.equal(initialized[0][2], initialized[2][2]);
    assert.equal(scriptListeners.length, 2);
});
