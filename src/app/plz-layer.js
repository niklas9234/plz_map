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
            "fill-color": "#4caf50",
            "fill-opacity": 0.25
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
            "line-color": "#146b37",
            "line-width": 2
        }
    });


    // ---------------------------------------------------------
    // PLZ-Beschriftungen
    // ---------------------------------------------------------

    map.addLayer({
        id: "plz-de-labels",
        type: "symbol",
        source: "plz-de",
        
        minzoom: 6,

        layout: {
            "text-field": ["get", "plz"],

            "text-font": [
                "Noto Sans Regular"
            ],

            "text-size": [
                "interpolate",
                ["linear"],
                ["zoom"],

                5, 8,
                7, 12,
                9, 16
            ],

            "text-allow-overlap": true,
            "text-ignore-placement": true
        },

        paint: {
            "text-color": "#111111",
            "text-halo-width": 2
        }
    });

}