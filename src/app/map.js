(function initializeApplication() {
    // API-backed search and administration must be usable even when the two
    // optional map libraries cannot be downloaded (common for installed,
    // firewalled desktop clients). The bridge becomes a real map later.
    let map = null;
    let mapStarted = false;
    let consecutiveBasemapErrors = 0;
    const postalCodeData = [];
    const errorElement = document.getElementById("map-load-error");
    const mapBridge = {
        setFilter(...args) { map?.setFilter(...args); },
        setPaintProperty(...args) { map?.setPaintProperty(...args); },
        fitBounds(...args) { map?.fitBounds(...args); }
    };

    initializeCompanySearch(mapBridge, postalCodeData);
    initializeSiteManagerSearch(mapBridge, postalCodeData);
    initializeAreaSearch(mapBridge, postalCodeData);

    function showMapError(message) {
        if (errorElement) {
            errorElement.hidden = false;
            errorElement.textContent = message;
        }
    }

    function hideMapError() {
        if (errorElement) {
            errorElement.hidden = true;
            errorElement.textContent = "";
        }
    }

    function logMapError(message, error) {
        const detail = error?.message || error?.error?.message || error || "unbekannter Fehler";
        const logMessage = `${message} (${detail})`;
        console.error(logMessage);
        window.plzLog?.error(logMessage);
    }

    function reportMapError(message, error) {
        showMapError(message);
        logMapError(message, error);
    }

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
        map.on("error", (event) => {
            const sourceId = event.sourceId || event.source?.id || event.tile?.source;
            const detail = String(event.error?.message || event.message || "");
            const isBasemapError = sourceId === "basemap" || detail.toLowerCase().includes("pmtiles");
            if (!isBasemapError) return;

            logMapError("Fehler beim Laden der Basemap.", event);
            consecutiveBasemapErrors += 1;

            // A bad archive header/metadata prevents PMTiles from being initialized at
            // all. Individual tile requests, on the other hand, can fail temporarily.
            const isFatalArchiveError = /(?:header|metadata)/i.test(detail);
            if (isFatalArchiveError || consecutiveBasemapErrors >= 2) {
                showMapError("Das Kartenarchiv konnte nicht geladen werden.");
            }
        });
        map.on("sourcedata", (event) => {
            if (event.sourceId === "basemap" && map.isSourceLoaded("basemap")) {
                consecutiveBasemapErrors = 0;
                hideMapError();
            }
        });
        map.on("zoom", () => console.log("Zoom:", map.getZoom()));
    }

    [["maplibre-script", "MapLibre GL JS"], ["pmtiles-script", "PMTiles"]].forEach(([id, name]) => {
        const script = document.getElementById(id);
        script?.addEventListener("load", startMap);
        script?.addEventListener("error", (event) => {
            reportMapError(`${name} konnte nicht geladen werden.`, event);
        });
    });
    startMap();
})();
