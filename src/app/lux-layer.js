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
            "fill-color": MAP_SETTINGS.postalCodes.fillColor,
            "fill-opacity": MAP_SETTINGS.postalCodes.fillOpacity
        }
    });

    map.addLayer({
        id: "plz-lux-border",
        type: "line",
        source: "plz-lux",
        paint: {
            "line-color": MAP_SETTINGS.postalCodes.borderColor,
            "line-width": MAP_SETTINGS.postalCodes.borderWidth
        }
    });

    map.addLayer({
        id: "plz-lux-label",
        type: "symbol",
        source: "plz-lux",

        minzoom: MAP_SETTINGS.postalCodes.label.minZoom,

        layout: {
            "text-field": "LUX",

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
