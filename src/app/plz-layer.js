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

function getSquaredDistanceToSegment(point, start, end) {
    let x = start[0];
    let y = start[1];
    let deltaX = end[0] - x;
    let deltaY = end[1] - y;

    if (deltaX !== 0 || deltaY !== 0) {
        const position = Math.max(0, Math.min(1,
            ((point[0] - x) * deltaX + (point[1] - y) * deltaY)
            / (deltaX * deltaX + deltaY * deltaY)
        ));
        x += deltaX * position;
        y += deltaY * position;
    }

    deltaX = point[0] - x;
    deltaY = point[1] - y;
    return deltaX * deltaX + deltaY * deltaY;
}

function getDistanceToPolygon(point, polygon) {
    let inside = false;
    let minimumSquaredDistance = Infinity;

    polygon.forEach((ring) => {
        for (let index = 0, previous = ring.length - 1; index < ring.length; previous = index, index += 1) {
            const currentPoint = ring[index];
            const previousPoint = ring[previous];

            if ((currentPoint[1] > point[1]) !== (previousPoint[1] > point[1])
                && point[0] < (previousPoint[0] - currentPoint[0])
                    * (point[1] - currentPoint[1])
                    / (previousPoint[1] - currentPoint[1]) + currentPoint[0]) {
                inside = !inside;
            }

            minimumSquaredDistance = Math.min(
                minimumSquaredDistance,
                getSquaredDistanceToSegment(point, currentPoint, previousPoint)
            );
        }
    });

    const distance = Math.sqrt(minimumSquaredDistance);
    return inside ? distance : -distance;
}

function createLabelCell(x, y, halfSize, polygon) {
    const distance = getDistanceToPolygon([x, y], polygon);
    return {
        x,
        y,
        halfSize,
        distance,
        maximumDistance: distance + halfSize * Math.SQRT2
    };
}

// Sucht den "Pole of Inaccessibility": den Punkt innerhalb der Fläche mit dem
// größtmöglichen Abstand zu jeder Außenkante und zu Löchern. Dadurch sitzen
// Labels auch in konkaven PLZ-Flächen gut lesbar statt nahe an einer Grenze.
function getVisualCenter(polygon, precision = 0.005) {
    const outerRing = polygon[0];
    const latitudes = outerRing.map((coordinate) => coordinate[1]);
    const latitudeScale = Math.cos(
        (latitudes.reduce((sum, latitude) => sum + latitude, 0) / latitudes.length)
        * Math.PI / 180
    );
    const projectedPolygon = polygon.map((ring) => ring.map(([longitude, latitude]) => [
        longitude * latitudeScale,
        latitude
    ]));
    const projectedOuterRing = projectedPolygon[0];
    const xCoordinates = projectedOuterRing.map((coordinate) => coordinate[0]);
    const yCoordinates = projectedOuterRing.map((coordinate) => coordinate[1]);
    const minimumX = Math.min(...xCoordinates);
    const minimumY = Math.min(...yCoordinates);
    const maximumX = Math.max(...xCoordinates);
    const maximumY = Math.max(...yCoordinates);
    const cellSize = Math.min(maximumX - minimumX, maximumY - minimumY);

    if (cellSize === 0) {
        return outerRing[0];
    }

    const cells = [];
    const halfSize = cellSize / 2;
    for (let x = minimumX; x < maximumX; x += cellSize) {
        for (let y = minimumY; y < maximumY; y += cellSize) {
            cells.push(createLabelCell(x + halfSize, y + halfSize, halfSize, projectedPolygon));
        }
    }

    const centroid = getRingAreaAndCentroid(projectedOuterRing).centroid;
    let bestCell = createLabelCell(centroid[0], centroid[1], 0, projectedPolygon);
    const boundingBoxCell = createLabelCell(
        (minimumX + maximumX) / 2,
        (minimumY + maximumY) / 2,
        0,
        projectedPolygon
    );
    if (boundingBoxCell.distance > bestCell.distance) {
        bestCell = boundingBoxCell;
    }

    while (cells.length > 0) {
        cells.sort((first, second) => first.maximumDistance - second.maximumDistance);
        const cell = cells.pop();

        if (cell.distance > bestCell.distance) {
            bestCell = cell;
        }
        if (cell.maximumDistance - bestCell.distance <= precision) {
            continue;
        }

        const nextHalfSize = cell.halfSize / 2;
        cells.push(
            createLabelCell(cell.x - nextHalfSize, cell.y - nextHalfSize, nextHalfSize, projectedPolygon),
            createLabelCell(cell.x + nextHalfSize, cell.y - nextHalfSize, nextHalfSize, projectedPolygon),
            createLabelCell(cell.x - nextHalfSize, cell.y + nextHalfSize, nextHalfSize, projectedPolygon),
            createLabelCell(cell.x + nextHalfSize, cell.y + nextHalfSize, nextHalfSize, projectedPolygon)
        );
    }

    return [bestCell.x / latitudeScale, bestCell.y];
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
            const candidate = {
                ...getPolygonAreaAndCentroid(polygon),
                coordinates: polygon
            };
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
                coordinates: getVisualCenter(polygon.coordinates)
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

    return postalCodeData;
}
