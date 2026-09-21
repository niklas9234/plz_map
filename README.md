# go-pmtiles

The single-file utility for creating and working with [PMTiles](https://github.com/protomaps/PMTiles) archives.

## Installation

See [Releases](https://github.com/protomaps/go-pmtiles/releases) for your OS and architecture.

## Docs

See [docs.protomaps.com/pmtiles/cli](https://docs.protomaps.com/pmtiles/cli) for usage.

See [Go package docs](https://pkg.go.dev/github.com/protomaps/go-pmtiles/pmtiles) for API usage.

## Development

Run the program in development:

```sh
go run main.go
```

Run the test suite:

Der Import ergänzt keine bestehende Datenbank: Sobald Stammdaten vorhanden
sind, wird er abgelehnt. Validieren lässt sich die Datei bereits vor der
Bestätigung, ohne Daten zu schreiben.

### Bestehende Unternehmensdaten per CSV erweitern

Für das schrittweise Ergänzen von Unternehmen gibt es unabhängig von der
Oberfläche den Kommandozeilenimport im Verzeichnis
[`unternehmensimport`](unternehmensimport/README.md). Er liest eine einfach
bearbeitbare CSV-Datei, prüft sie zunächst vollständig und fügt ausschließlich
neue Unternehmen hinzu. Bestehende Datensätze werden dabei weder geändert noch
gelöscht.
