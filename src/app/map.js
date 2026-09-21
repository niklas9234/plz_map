(function initializeApplication() {
    // API-backed search and administration must be usable even when the two
    // optional map libraries cannot be downloaded (common for installed,
    // firewalled desktop clients). The bridge becomes a real map later.
    let map = null;
    let mapStarted = false;
    const postalCodeData = [];
    const mapBridge = {
        setFilter(...args) { map?.setFilter(...args); },
        setPaintProperty(...args) { map?.setPaintProperty(...args); },
        fitBounds(...args) { map?.fitBounds(...args); }
    };

    initializeCompanySearch(mapBridge, postalCodeData);
    initializeSiteManagerSearch(mapBridge, postalCodeData);
    initializeAreaSearch(mapBridge, postalCodeData);

    function startMap() {
        if (mapStarted || typeof maplibregl === "undefined" || typeof pmtiles === "undefined") return;
        mapStarted = true;
        const protocol = new pmtiles.Protocol();
        maplibregl.addProtocol("pmtiles", protocol.tile);

        map = new maplibregl.Map({
            container: "map",
            center: MAP_SETTINGS.map.center,
            zoom: MAP_SETTINGS.map.zoom,
            style: {
                version: 8,
                glyphs: MAP_SETTINGS.map.glyphsUrl,
                sources: {
                    basemap: { type: "vector", url: MAP_SETTINGS.map.basemapUrl }
                },
                layers: []
            }
        });

        map.on("load", async () => {
            addBaseMapLayers(map);
            const germanyPostalCodes = await addGermanyPlzLayers(map);
            const luxembourgPostalCodes = await addLuxembourgLayers(map);
            postalCodeData.push(germanyPostalCodes, luxembourgPostalCodes);
        });
        map.on("zoom", () => console.log("Zoom:", map.getZoom()));
    }

    ["maplibre-script", "pmtiles-script"].forEach((id) => {
        document.getElementById(id)?.addEventListener("load", startMap);
    });
    startMap();
})();
