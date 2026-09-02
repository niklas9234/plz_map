function addBaseMapLayers(map) {
    const oceanFilter = ["==", ["get", "kind"], "ocean"];

    map.addLayer({
        id: "background",
        type: "background",

        paint: {
            "background-color": MAP_SETTINGS.basemap.backgroundColor
        }
    });


    map.addLayer({
        id: "earth",
        type: "fill",

        source: "basemap",
        "source-layer": "earth",

        paint: {
            "fill-color": MAP_SETTINGS.basemap.earthColor
        }
    });


    map.addLayer({
        id: "water-fill",
        type: "fill",

        source: "basemap",
        "source-layer": "water",
        filter: oceanFilter,

        paint: {
            "fill-color": MAP_SETTINGS.basemap.waterColor
        }
    });


    map.addLayer({
        id: "water-lines",
        type: "line",
        minzoom: MAP_SETTINGS.basemap.minZoomMapObjects,

        source: "basemap",
        "source-layer": "water",
        filter: oceanFilter,

        paint: {
            "line-color": MAP_SETTINGS.basemap.waterLineColor,
            "line-width": MAP_SETTINGS.basemap.waterLineWidth
        }
    });


    map.addLayer({
        id: "roads",
        type: "line",

        source: "basemap",
        "source-layer": "roads",

        paint: {
            "line-color": MAP_SETTINGS.basemap.roadColor,

            "line-width": [
                "interpolate",
                ["linear"],
                ["zoom"],

                ...MAP_SETTINGS.basemap.roadWidths
            ]
        }
    });


    map.addLayer({
        id: "places",
        type: "symbol",
        minzoom: MAP_SETTINGS.basemap.placeLabel.minZoom,

        source: "basemap",
        "source-layer": "places",

        layout: {
            "text-field": ["get", "name"],

            "text-font": MAP_SETTINGS.basemap.placeLabel.font,

            "text-size": [
                "interpolate",
                ["linear"],
                ["zoom"],

                ...MAP_SETTINGS.basemap.placeLabel.sizes
            ]
        },

        paint: {
            "text-color": MAP_SETTINGS.basemap.placeLabel.color,
            "text-halo-color": MAP_SETTINGS.basemap.placeLabel.haloColor,
            "text-halo-width": MAP_SETTINGS.basemap.placeLabel.haloWidth
        }
    });

}
