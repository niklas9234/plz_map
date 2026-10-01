function placeRankFilter(minPopulationRank, maxPopulationRank) {
    const filters = [
        ["has", "population_rank"],
        [">=", ["get", "population_rank"], minPopulationRank]
    ];
    if (maxPopulationRank !== undefined) {
        filters.push(["<", ["get", "population_rank"], maxPopulationRank]);
    }
    return ["all", ...filters];
}

function placeLabelLayer(id, minZoom, filter) {
    return {
        id,
        type: "symbol",
        minzoom: minZoom,
        source: "basemap",
        "source-layer": "places",
        filter,
        layout: {
            "text-field": ["get", "name"],
            "text-font": MAP_SETTINGS.basemap.placeLabel.font,
            "text-size": [
                "interpolate", ["linear"], ["zoom"],
                ...MAP_SETTINGS.basemap.placeLabel.sizes
            ]
        },
        paint: {
            "text-color": MAP_SETTINGS.basemap.placeLabel.color,
            "text-halo-color": MAP_SETTINGS.basemap.placeLabel.haloColor,
            "text-halo-width": MAP_SETTINGS.basemap.placeLabel.haloWidth
        }
    };
}

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


    const zoomLevels = MAP_SETTINGS.basemap.placeLabel.zoomLevels;
    zoomLevels.forEach((level, index) => {
        const previousThreshold = index === 0 ? undefined : zoomLevels[index - 1].minPopulationRank;
        map.addLayer(placeLabelLayer(
            `places-ranked-${index}`,
            level.minZoom,
            placeRankFilter(level.minPopulationRank, previousThreshold)
        ));
    });

    map.addLayer(placeLabelLayer(
        "places-unranked",
        MAP_SETTINGS.basemap.placeLabel.unrankedMinZoom,
        ["!", ["has", "population_rank"]]
    ));

}
