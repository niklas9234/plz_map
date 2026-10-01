const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

function loadBasemap() {
    const context = { URL, window: { location: { href: 'http://localhost/' } } };
    vm.createContext(context);
    vm.runInContext(fs.readFileSync(`${__dirname}/settings.js`, 'utf8'), context);
    vm.runInContext(`${fs.readFileSync(`${__dirname}/basemap.js`, 'utf8')}
        this.addBaseMapLayers = addBaseMapLayers;`, context);
    return context;
}

function local(value) {
    return JSON.parse(JSON.stringify(value));
}

test('place labels use separately configurable population-rank zoom levels', () => {
    const layers = [];
    loadBasemap().addBaseMapLayers({ addLayer(layer) { layers.push(layer); } });

    const placeLayers = layers.filter((layer) => layer['source-layer'] === 'places');
    assert.deepEqual(placeLayers.map((layer) => [layer.id, layer.minzoom]), [
        ['places-ranked-0', 5],
        ['places-ranked-1', 6.5],
        ['places-ranked-2', 8],
        ['places-unranked', 5]
    ]);
    assert.deepEqual(local(placeLayers[0].filter), [
        'all', ['has', 'population_rank'], ['>=', ['get', 'population_rank'], 12]
    ]);
    assert.deepEqual(local(placeLayers[1].filter), [
        'all', ['has', 'population_rank'], ['>=', ['get', 'population_rank'], 10],
        ['<', ['get', 'population_rank'], 12]
    ]);
    assert.deepEqual(local(placeLayers[3].filter), ['!', ['has', 'population_rank']]);
});
