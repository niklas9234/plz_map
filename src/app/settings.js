/**
 * Zentrale Einstellungen der Karte.
 */
const MAP_SETTINGS = {
    map: {
        center: [10.5, 51.1],
        zoom: 5.5,
        // Das große, nicht versionierte Archiv liegt zusammen mit den übrigen
        // Kartendaten im statischen Frontend-Verzeichnis.
        basemapUrl: `pmtiles://${new URL("./data/pmtiles/germany-luxembourg.pmtiles", window.location.href).href}`,
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
            minZoom: 8,
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
            minZoom: 4,
            font: ["Noto Sans Regular"],
            // Abwechselnd Zoomstufe und Schriftgröße in Pixeln.
            sizes: [5, 18, 7, 20, 9, 18],
            color: "#111111",
            haloWidth: 2
        }
    }
};
