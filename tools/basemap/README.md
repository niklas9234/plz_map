# PMTiles-Basiskarte filtern

`filter_pmtiles.py` bearbeitet PMTiles-v3-Archive reproduzierbar. Es kopiert die
MVT-Geometrie, den Feature-Typ, die Feature-ID, den Layer-Extent und die
Layer-Version direkt aus dem Protobuf-Wireformat. Damit findet keine
Geometrie-Dekodierung mit Rundung oder Neuquantisierung statt. Neu aufgebaut
werden nur Feature-Tags sowie die Key-/Value-Tabellen.

Voraussetzungen sind Python 3.11+ (nur Standardbibliothek) und exakt
`pmtiles 1.31.2`. Das Werkzeug prüft die CLI-Version vor dem Start.

```bash
python3 tools/basemap/filter_pmtiles.py \
  germany-luxembourg-full.pmtiles \
  germany-luxembourg-reduced.pmtiles \
  --pmtiles ./pmtiles
```

Das Eingabearchiv bleibt unangetastet. Ein temporäres MBTiles-Archiv wird in
einem temporären Verzeichnis erzeugt und von `pmtiles convert` wieder als
PMTiles geschrieben. Leere Layer und Kacheln werden ausgelassen. Der Prozess
behält nur `earth`, `water`, `roads` und `places`; in `water` nur Features mit
`kind=ocean`. `places` behält `name`, `water` behält `kind`, während `earth`
und `roads` keine Attribute behalten.

Tests:

```bash
python3 -m unittest tools/basemap/test_filter_pmtiles.py
```
