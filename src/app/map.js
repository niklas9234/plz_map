const protocol = new pmtiles.Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);

const map = new maplibregl.Map({
    container: "map",

    center: [10.5, 51.1],
    zoom: 5.5,

    style: {
        version: 8,

        glyphs: "https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf",

        sources: {
            basemap: {
                type: "vector",
                url: "pmtiles://http://localhost:8000/germany.pmtiles"
            }
        },

        layers: []
    }
});

map.on("load", () => {
    addBaseMapLayers(map);
    addGermanyPlzLayers(map);
    addLuxembourgLayers(map);
});