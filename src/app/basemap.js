function addBaseMapLayers(map) {

    map.addLayer({
        id: "background",
        type: "background",

        paint: {
            "background-color": "#f5f5f5"
        }
    });


    map.addLayer({
        id: "earth",
        type: "fill",

        source: "basemap",
        "source-layer": "earth",

        paint: {
            "fill-color": "#f3f1ea"
        }
    });


    map.addLayer({
        id: "water-fill",
        type: "fill",

        source: "basemap",
        "source-layer": "water",

        paint: {
            "fill-color": "#cfe8f3"
        }
    });


    map.addLayer({
        id: "water-lines",
        type: "line",

        source: "basemap",
        "source-layer": "water",

        paint: {
            "line-color": "#7dbbd3",
            "line-width": 1
        }
    });


    map.addLayer({
        id: "roads",
        type: "line",

        source: "basemap",
        "source-layer": "roads",

        paint: {
            "line-color": "#999999",

            "line-width": [
                "interpolate",
                ["linear"],
                ["zoom"],

                5, 0.5,
                8, 1,
                12, 2
            ]
        }
    });


    map.addLayer({
        id: "places",
        type: "symbol",

        source: "basemap",
        "source-layer": "places",

        layout: {
            "text-field": ["get", "name"],

            "text-font": [
                "Noto Sans Regular"
            ],

            "text-size": [
                "interpolate",
                ["linear"],
                ["zoom"],

                5, 10,
                8, 13,
                12, 16
            ]
        },

        paint: {
            "text-color": "#222222",
            "text-halo-color": "#ffffff",
            "text-halo-width": 1.5
        }
    });

}