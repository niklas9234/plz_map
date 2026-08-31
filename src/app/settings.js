/**
 * Zentrale Einstellungen der Karte.
 *
 * Nach einer Änderung genügt es, die Seite neu zu laden. Eine .env-Datei ist
 * hier nicht nötig: Die Karte läuft direkt im Browser und benötigt keine
 * geheimen Zugangsdaten oder einen Build-Schritt.
 */
const MAP_SETTINGS = {
    map: {
        center: [10.5, 51.1],
        zoom: 5.5,
        basemapUrl: "pmtiles://http://localhost:8000/germany.pmtiles",
        glyphsUrl: "https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf"
    },

    basemap: {
        backgroundColor: "#f5f5f5",
        earthColor: "#f3f1ea",
        waterColor: "#cfe8f3",
        waterLineColor: "#7dbbd3",
        waterLineWidth: 1,
        roadColor: "#999999",
        roadWidths: [5, 0.5, 8, 1, 12, 2],
        placeLabel: {
            font: ["Noto Sans Regular"],
            sizes: [5, 10, 8, 13, 12, 16],
            color: "#222222",
            haloColor: "#ffffff",
            haloWidth: 1.5
        }
    },

    // Diese Darstellung gilt gemeinsam für Deutschland und Luxemburg.
    postalCodes: {
        fillColor: "#4caf50",
        fillOpacity: 0.25,
        borderColor: "#146b37",
        borderWidth: 2,
        label: {
            minZoom: 6,
            // Kleine, getrennte Teilflächen (z. B. Inseln) nicht beschriften.
            // Der Wert wird in Quadratkilometern angegeben; 0 zeigt alle Labels.
            minAreaSquareKilometers: 50,
            font: ["Noto Sans Regular"],
            // Abwechselnd Zoomstufe und Schriftgröße in Pixeln.
            sizes: [5, 8, 7, 12, 9, 16],
            color: "#111111",
            haloWidth: 2
        }
    }
};
