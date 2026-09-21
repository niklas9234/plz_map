# Lokale PMTiles-Basiskarte

## Erzeugung

Das unbereinigte Archiv wurde mit PMTiles CLI 1.31.2 aus dem regionalen
Quellarchiv extrahiert. Der ursprüngliche Aufruf (die Bounding Box umfasst
Deutschland und Luxemburg) lautet:

```bash
pmtiles extract germany.pmtiles \
  germany-luxembourg-full.pmtiles \
  --bbox=2.5,47.2,15.1,55.1
```

Anschließend wird es mit Version 1.0.0 des repository-eigenen Werkzeugs
bereinigt. Eingabe und Ausgabe haben absichtlich unterschiedliche Namen, damit
beide Archive vor dem Austausch visuell verglichen werden können:

```bash
python3 tools/basemap/filter_pmtiles.py \
  germany-luxembourg-full.pmtiles \
  germany-luxembourg-reduced.pmtiles \
  --pmtiles ./pmtiles
```

Der Filter erwartet **PMTiles CLI 1.31.2** für die abschließende Konvertierung.
Er erhält Bounds, minimale und maximale Zoomstufe aus dem Ausgangsarchiv. In den
MVT-Kacheln bleiben genau die vier Source-Layer `earth`, `water`, `roads` und
`places`. `water` enthält nur noch Features mit `kind=ocean`; `places` behält
das für die Beschriftung benötigte Attribut `name`. Das Attribut `kind` bleibt
bei `water` für den defensiven MapLibre-Filter erhalten. `earth` und `roads`
enthalten keine Feature-Attribute. Details, Invarianten und Tests sind unter
[`tools/basemap/README.md`](../../../../tools/basemap/README.md) beschrieben.

Vor dem Ersetzen des produktiven Archivs werden beide Dateien in der Anwendung
bei mehreren Zoomstufen verglichen. Die Prüfpunkte sind Nord- und Ostseeküste,
Inseln, Autobahnen und kleinere Straßen, kleine und große Städte sowie alle vier
Ränder der Bounding Box. Seen, Flüsse und andere Binnengewässer dürfen im
reduzierten Archiv nicht mehr vorhanden sein.

## Installation

Lege die nicht in Git versionierte Datei unter folgendem Namen hier ab:

```text
src/app/data/pmtiles/germany-luxembourg.pmtiles
```

Bei einem lokalen Start mit `src/app` als Dokumentenwurzel ist sie anschließend
unter `/data/pmtiles/germany-luxembourg.pmtiles` erreichbar. Für ein späteres
Deployment muss der Webserver HTTP-Range-Requests für diese Datei unterstützen.
