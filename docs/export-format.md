# Datenbankunabhängiges Exportformat

Das JSON-Format ist die stabile Übergabegrenze zwischen Installationen und
Datenbankprodukten. Es bildet fachliche Daten ab, nicht SQLite-Tabellen.

## Version 1

```json
{
  "format": "plz-map-data-export",
  "schemaVersion": 1,
  "exportedAt": "2026-09-03T12:34:56Z",
  "applicationVersion": "1.0.0",
  "trades": [],
  "companies": []
}
```

`format` identifiziert den Dokumenttyp; `schemaVersion` versioniert nur diesen
Vertrag. `exportedAt`, `createdAt` und `updatedAt` sind RFC-3339-Zeitpunkte mit
Zeitzone.

Ein Gewerk enthält `id` (UUID), `name`, `status` (`active`/`inactive`), die
optionale Farbe `color`, `createdAt` und `updatedAt`. Ein Unternehmen enthält
`id` (UUID), `name`, `ppsNumber`, `tradeId` (UUID), `status`, Zeitpunkte,
`territories` und `information`. `tradeId` verweist auf ein Gewerk desselben
Dokuments. Eine Gebietszuordnung besitzt `postalCode` und `role`
(`primary`/`alternative`). Deutsche Gebiete sind zweistellige Strings, etwa
`"08"`; `"LUX"` ist die Sonderkennung für Luxemburg. Zusatzinformationen sind
geordnete Objekte mit `category` und `value`.

Unbekannte oder fehlende Felder werden abgelehnt. Geprüft werden UUIDs,
eindeutige PPS-Nummern und Gewerknamen, Gewerkverweise, Status und Rollen,
mindestens ein Gebiet je Unternehmen, doppelte Gebiete sowie höchstens ein
Vorzugsdienstleister je Gewerk und Gebiet.

## Importgarantien und Modi

Der Import prüft zuerst `format` und `schemaVersion`, danach das gesamte
Dokument und alle Beziehungen. Erst nach erfolgreicher Gesamtprüfung beginnt
die Schreibtransaktion. Jeder Schreibfehler führt zum Rollback.

* `validate`: prüft alles und verändert die Datenbank nicht.
* `empty`: prüft in der Transaktion, dass keine fachlichen Daten vorhanden
  sind, und übernimmt dann den vollständigen Bestand.

Ein Erfolg meldet die Anzahlen und `written`. Validierungsfehler liefern HTTP
422 mit konkreten Feldfehlern.
