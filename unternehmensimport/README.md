# Unternehmen per CSV ergänzen

Dieser Import ist bewusst vom vollständigen JSON-Datenumzug der Oberfläche
getrennt. Er **ergänzt** Unternehmen in einer bereits befüllten Datenbank und
ändert oder löscht keine vorhandenen Datensätze.

## Vorbereitung

1. Die Anwendung während eines Imports in die lokale SQLite-Datenbank beenden.
2. `unternehmen.csv.example` nach `unternehmen.csv` kopieren.
3. Die Datei in Excel, LibreOffice oder einem Texteditor bearbeiten und als
   UTF-8-CSV mit Semikolon als Trennzeichen speichern.

Die Spalten bedeuten:

| Spalte | Pflicht | Inhalt |
| --- | --- | --- |
| `name` | ja | Name des Unternehmens |
| `pps_number` | ja | Neue, eindeutige PPS-Nummer |
| `trade` | ja | Exakter Name eines bereits vorhandenen Gewerks |
| `primary_postal_codes` | bedingt | Zweistellige PLZ-Gebiete oder `LUX`, mit Komma getrennt |
| `alternative_postal_codes` | bedingt | Weitere Gebiete, mit Komma getrennt |
| `address`, `phone`, `contact`, `other` | nein | Zusatzinformationen; mehrere Werte mit `|` trennen |
| `status` | nein | `active` (Standard) oder `inactive` |

Mindestens eines der beiden Gebietsfelder muss befüllt sein. Pro Gewerk und
Gebiet darf es systemweit nur einen Eintrag mit der Rolle `primary` geben.

## Prüfen und importieren

Aus dem Stammverzeichnis des Projekts:

```sh
# Erst nur prüfen; die Datenbank bleibt unverändert.
python unternehmensimport/import_companies.py --check

# Danach alle Zeilen gemeinsam importieren.
python unternehmensimport/import_companies.py
```

Ohne weitere Angaben liest das Programm
`unternehmensimport/unternehmen.csv` und verwendet dieselbe lokale Datenbank
wie die Desktopanwendung. Ein anderer Dateipfad kann als Argument angegeben
werden:

```sh
python unternehmensimport/import_companies.py pfad/meine-unternehmen.csv
```

Für den Serverbetrieb wird wie bei der Anwendung `DATABASE_URL` verwendet.
Alternativ lässt sich die Zieladresse ausdrücklich übergeben:

```sh
python unternehmensimport/import_companies.py --database-url \
  'postgresql+psycopg://USER:PASSWORT@HOST/DATENBANK'
```

Vor dem Schreiben werden **alle** CSV-Zeilen und Konflikte mit dem Bestand
geprüft. Bei einem Fehler wird nichts importiert. Auch das anschließende
Schreiben läuft in einer einzigen Transaktion, sodass kein Teilimport entsteht.
Bereits vorhandene Unternehmen werden niemals aktualisiert oder ersetzt;
doppelte PPS-Nummern führen stattdessen zu einer Fehlermeldung.
