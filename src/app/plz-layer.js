function addGermanyPlzLayers(map) {

    // ---------------------------------------------------------
    // GeoJSON-Quelle laden
    // ---------------------------------------------------------

    map.addSource("plz-de", {
        type: "geojson",
        data: "./plz-2stellig.geojson"
    });


    // ---------------------------------------------------------
    // PLZ-Flächen
    // ---------------------------------------------------------

    map.addLayer({
        id: "plz-de-fill",
        type: "fill",
        source: "plz-de",

        paint: {
            "fill-color": MAP_SETTINGS.postalCodes.fillColor,
            "fill-opacity": MAP_SETTINGS.postalCodes.fillOpacity
        }
    });


    // ---------------------------------------------------------
    // PLZ-Grenzen
    // ---------------------------------------------------------

    map.addLayer({
        id: "plz-de-border",
        type: "line",
        source: "plz-de",

        paint: {
            "line-color": MAP_SETTINGS.postalCodes.borderColor,
            "line-width": MAP_SETTINGS.postalCodes.borderWidth
        }
    });


    // ---------------------------------------------------------
    // PLZ-Beschriftungen
    // ---------------------------------------------------------

    map.addLayer({
        id: "plz-de-labels",
        type: "symbol",
        source: "plz-de",
        
        minzoom: MAP_SETTINGS.postalCodes.label.minZoom,

        layout: {
            "text-field": ["get", "plz"],

            "text-font": MAP_SETTINGS.postalCodes.label.font,

            "text-size": [
                "interpolate",
                ["linear"],
                ["zoom"],

                ...MAP_SETTINGS.postalCodes.label.sizes
            ],

            "text-allow-overlap": true,
            "text-ignore-placement": true
        },

        paint: {
            "text-color": MAP_SETTINGS.postalCodes.label.color,
            "text-halo-width": MAP_SETTINGS.postalCodes.label.haloWidth
        }
    });

}
