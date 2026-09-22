# Unternehmen per CSV ergänzen

Dieser Import ist bewusst vom vollständigen JSON-Datenumzug der Oberfläche
getrennt. Er **ergänzt** Unternehmen in einer bereits befüllten Datenbank und
ändert oder löscht keine vorhandenen Datensätze.

## Schnellstart für die lokale Anwendung

Die Befehle werden im Stammverzeichnis des Projekts ausgeführt:

```sh
# Einmalig, falls die Backend-Abhängigkeiten noch nicht installiert sind
python -m pip install -r server/requirements.txt

# Vorlage kopieren (Linux/macOS)
cp tools/unternehmensimport/unternehmen.csv.example tools/unternehmensimport/unternehmen.csv
```

Unter Windows kann die Vorlage im Explorer kopiert oder in PowerShell mit
folgendem Befehl angelegt werden:

```powershell
Copy-Item tools/unternehmensimport/unternehmen.csv.example tools/unternehmensimport/unternehmen.csv
```

Danach `tools/unternehmensimport/unternehmen.csv` bearbeiten. Vor dem Prüfen und
Importieren muss die lokale Anwendung beendet werden, damit sie nicht
gleichzeitig auf die SQLite-Datei schreibt.

```sh
# Erst nur prüfen; die Datenbank bleibt unverändert.
python tools/unternehmensimport/import_companies.py --check

# Nur nach erfolgreicher Prüfung tatsächlich importieren.
python tools/unternehmensimport/import_companies.py
```

Eine erfolgreiche Ausführung endet zum Beispiel mit
`Import erfolgreich: 2 Unternehmen.`. Bereits vorhandene Unternehmen bleiben
dabei erhalten.

## Vorgeschriebene Kopfzeile

Ja, die CSV benötigt diese **exakte Kopfzeile** in dieser Reihenfolge:

```csv
name;trade;primary_postal_codes;alternative_postal_code
```

Die Datei muss als UTF-8-CSV mit Semikolon als Trennzeichen gespeichert sein.
Die Datei `unternehmen.csv.example` ist eine direkt kopierbare Vorlage. Enthält
ein Wert selbst ein Semikolon, muss das CSV-Programm diesen Wert in doppelte
Anführungszeichen setzen.

## Bedeutung der Spalten

Die Spalten bedeuten:

| Spalte | Pflicht | Inhalt |
| --- | --- | --- |
| `name` | ja | Name des Unternehmens |
| `trade` | ja | Exakter Name eines bereits vorhandenen Gewerks |
| `primary_postal_codes` | bedingt | Zweistellige PLZ-Gebiete oder `LUX`, mit Komma getrennt |
| `alternative_postal_code` | bedingt | Weitere Gebiete, mit Komma getrennt |

Mindestens eines der beiden Gebietsfelder muss befüllt sein. Pro Gewerk und
Gebiet darf es systemweit nur einen Eintrag mit der Rolle `primary` geben.

Der Import setzt jedes neue Unternehmen automatisch auf `active`. Weil die
Datenbank bereits beim Anlegen eine je Gewerk eindeutige PPS-Nummer verlangt, erzeugt das
Programm zunächst einen eindeutig erkennbaren Platzhalter in der Form
`IMPORT-<UUID>`. Dieser kann anschließend in der Unternehmensverwaltung durch
die endgültige PPS-Nummer ersetzt werden. Weitere Unternehmensinformationen
werden bei diesem vereinfachten Import nicht angelegt.

## Eine andere CSV-Datei verwenden

Ohne weitere Angaben liest das Programm
`tools/unternehmensimport/unternehmen.csv` und verwendet dieselbe lokale Datenbank
wie die Desktopanwendung. Ein anderer Dateipfad kann als Argument angegeben
werden:

```sh
python tools/unternehmensimport/import_companies.py pfad/meine-unternehmen.csv
```

Für den Serverbetrieb wird wie bei der Anwendung `DATABASE_URL` verwendet.
Alternativ lässt sich die Zieladresse ausdrücklich übergeben:

```sh
python tools/unternehmensimport/import_companies.py --database-url \
  'postgresql+psycopg://USER:PASSWORT@HOST/DATENBANK'
```

Vor dem Schreiben werden **alle** CSV-Zeilen und Konflikte mit dem Bestand
geprüft. Bei einem Fehler wird nichts importiert. Auch das anschließende
Schreiben läuft in einer einzigen Transaktion, sodass kein Teilimport entsteht.
Bereits vorhandene Unternehmen werden niemals aktualisiert oder ersetzt.
