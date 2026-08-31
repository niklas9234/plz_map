function getRingAreaAndCentroid(ring) {
    let twiceArea = 0;
    let centroidX = 0;
    let centroidY = 0;

    for (let index = 0; index < ring.length - 1; index += 1) {
        const [x1, y1] = ring[index];
        const [x2, y2] = ring[index + 1];
        const crossProduct = x1 * y2 - x2 * y1;

        twiceArea += crossProduct;
        centroidX += (x1 + x2) * crossProduct;
        centroidY += (y1 + y2) * crossProduct;
    }

    if (twiceArea === 0) {
        return { area: 0, centroid: ring[0] };
    }

    return {
        area: Math.abs(twiceArea / 2),
        centroid: [centroidX / (3 * twiceArea), centroidY / (3 * twiceArea)]
    };
}

function getPolygonAreaAndCentroid(polygon) {
    const outerRing = getRingAreaAndCentroid(polygon[0]);
    const holeArea = polygon.slice(1).reduce((total, ring) => {
        return total + getRingAreaAndCentroid(ring).area;
    }, 0);

    return {
        area: Math.max(0, outerRing.area - holeArea),
        centroid: outerRing.centroid
    };
}

function createPlzLabelData(postalCodeData) {
    const largestPolygonByPostalCode = new Map();

    postalCodeData.features.forEach((feature) => {
        const postalCode = feature.properties?.plz;
        const geometry = feature.geometry;

        if (!postalCode || !geometry || !["Polygon", "MultiPolygon"].includes(geometry.type)) {
            return;
        }

        const polygons = geometry.type === "Polygon"
            ? [geometry.coordinates]
            : geometry.coordinates;

        polygons.forEach((polygon) => {
            const candidate = getPolygonAreaAndCentroid(polygon);
            const current = largestPolygonByPostalCode.get(postalCode);

            if (!current || candidate.area > current.area) {
                largestPolygonByPostalCode.set(postalCode, candidate);
            }
        });
    });

    return {
        type: "FeatureCollection",
        features: Array.from(largestPolygonByPostalCode, ([plz, polygon]) => ({
            type: "Feature",
            properties: { plz },
            geometry: {
                type: "Point",
                coordinates: polygon.centroid
            }
        }))
    };
}

async function addGermanyPlzLayers(map) {
    const response = await fetch("./plz-2stellig.geojson");

    if (!response.ok) {
        throw new Error(`PLZ-Daten konnten nicht geladen werden (${response.status}).`);
    }

    const postalCodeData = await response.json();

    // Die getrennte Punktquelle verhindert mehrfache Labels bei MultiPolygonen.
    map.addSource("plz-de", {
        type: "geojson",
        data: postalCodeData
    });

    map.addSource("plz-de-label-points", {
        type: "geojson",
        data: createPlzLabelData(postalCodeData)
    });

    map.addLayer({
        id: "plz-de-fill",
        type: "fill",
        source: "plz-de",
        paint: {
            "fill-color": MAP_SETTINGS.postalCodes.fillColor,
            "fill-opacity": MAP_SETTINGS.postalCodes.fillOpacity
        },
        filter: ["==", ["get", "plz"], ""]
    });

    map.addLayer({
        id: "plz-de-border",
        type: "line",
        source: "plz-de",
        paint: {
            "line-color": MAP_SETTINGS.postalCodes.borderColor,
            "line-width": MAP_SETTINGS.postalCodes.borderWidth
        },
        filter: ["==", ["get", "plz"], ""]
    });

    map.addLayer({
        id: "plz-de-labels",
        type: "symbol",
        source: "plz-de-label-points",
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
        },
        filter: ["==", ["get", "plz"], ""]
    });
}
