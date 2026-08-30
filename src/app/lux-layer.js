function addLuxembourgLayers(map) {

    map.addSource("plz-lux", {
        type: "geojson",
        data: "./luxemburg.json"
    });

    map.addLayer({
        id: "plz-lux-fill",
        type: "fill",
        source: "plz-lux",
        paint: {
            "fill-color": "#4caf50",
            "fill-opacity": 0.25
        }
    });

    map.addLayer({
        id: "plz-lux-border",
        type: "line",
        source: "plz-lux",
        paint: {
            "line-color": "#146b37",
            "line-width": 2
        }
    });

    map.addLayer({
        id: "plz-lux-label",
        type: "symbol",
        source: "plz-lux",

        minzoom: 6,

        layout: {
            "text-field": "LUX",

            "text-font": [
                "Noto Sans Regular"
            ],

            "text-size": [
                "interpolate",
                ["linear"],
                ["zoom"],
                5, 12,
                7, 20,
                9, 22
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