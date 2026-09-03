const protocol = new pmtiles.Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);

const map = new maplibregl.Map({
    container: "map",

    center: MAP_SETTINGS.map.center,
    zoom: MAP_SETTINGS.map.zoom,

    style: {
        version: 8,

        glyphs: MAP_SETTINGS.map.glyphsUrl,

        sources: {
            basemap: {
                type: "vector",
                url: MAP_SETTINGS.map.basemapUrl
            }
        },

        layers: []
    }
});

map.on("load", async () => {
    addBaseMapLayers(map);
    const germanyPostalCodes = await addGermanyPlzLayers(map);
    const luxembourgPostalCodes = await addLuxembourgLayers(map);
    const postalCodeData = [germanyPostalCodes, luxembourgPostalCodes];
    initializeCompanySearch(map, postalCodeData);
    initializeAreaSearch(map, postalCodeData);
});

map.on("zoom", () => {
    console.log("Zoom:", map.getZoom());
});
