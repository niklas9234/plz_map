# Fachliches Datenmodell

Dieses Dokument hält die verbindlichen Regeln für die spätere API, Datenbank
und Datenimporte fest. Bis zur Backend-Umstellung bildet das Frontend diese
Regeln lokal ab.

## Unternehmen

| Feld | Typ | Regel |
| --- | --- | --- |
| `id` | UUID | Technischer, unveränderlicher Primärschlüssel. |
| `name` | String | Pflichtfeld, nach dem Entfernen äußerer Leerzeichen nicht leer. |
| `ppsNumber` | String | Pflichtfeld und global eindeutig; Änderungen ändern nicht die `id`. |
| `tradeId` | UUID | Pflichtverweis auf ein vorhandenes Gewerk. Kein Freitext. |
| `territories` | Gebietszuordnungs-Liste | Mindestens ein Eintrag. Jede Zuordnung enthält `postalCode` und die Rolle `primary` oder `alternative`. |
| `information` | Informations-Liste | Geordnete Liste aus `category` und `value`; Details siehe unten. |
| `status` | Enum | `active` oder `inactive`; neue Unternehmen sind `active`. |
| `createdAt` | Zeitpunkt | Vom Server gesetzter Erstellungszeitpunkt. |
| `updatedAt` | Zeitpunkt | Vom Server bei jeder Änderung aktualisiert. |

Ein Unternehmen darf gleichzeitig deutsche und luxemburgische PLZ-Gebiete
besitzen. Die API behandelt Postleitzahlen ausdrücklich als Strings und nie als
Zahlen, damit führende Nullen nicht verloren gehen.

Pro Kombination aus PLZ-Gebiet und Gewerk darf es höchstens einen
Vorzugsdienstleister (`primary`) geben. Beliebig viele Unternehmen können als
Alternativdienstleister (`alternative`) zugeordnet sein; zwischen ihnen besteht
keine weitere Rangfolge. Ein Unternehmen kann in verschiedenen Gebieten
unterschiedliche Rollen haben.

`tradeId` ist die einzige gespeicherte Gewerkbeziehung. Ein Feld `trade` wird
weder gespeichert noch exportiert. Clients lösen die Bezeichnung über
`GET /api/trades` auf; so entspricht die lokale Repräsentation unmittelbar
einem PostgreSQL-Fremdschlüssel.

### Zusätzliche Informationen

`information` ist verbindlich eine (gegebenenfalls leere) geordnete Liste von
Objekten mit genau den Feldern `category` und `value`. `category` ist eines der
stabilen, sprachneutralen Enum-Werte `address`, `phone`, `contact` oder `other`.
`value` ist ein nicht leerer String; äußere Leerzeichen werden entfernt.
Unbekannte Kategorien, leere Werte, zusätzliche Objektfelder und ein anderer
Datentyp werden mit einem Validierungsfehler abgelehnt. Reihenfolge und doppelte
Kategorien bleiben erhalten, weil beispielsweise mehrere Telefonnummern
fachlich zulässig sind.

In PostgreSQL wird jeder Listeneintrag als eigene Zeile mit `company_id`,
`position`, `category` und `value` gespeichert. Der eindeutige Schlüssel
`(company_id, position)` bewahrt die Reihenfolge verlustfrei; `category` erhält
einen Check Constraint auf die vier Werte.

### Eindeutigkeit und Normalisierung

- Die Datenbank erzwingt die globale Eindeutigkeit der PPS-Nummer mit einem
  Unique Constraint. Der Import und die API prüfen dies zusätzlich, der
  Constraint bleibt aber die letzte Instanz bei parallelen Anfragen.
- Äußere Leerzeichen in Name und PPS-Nummer werden entfernt.
- Deutsche PLZ-Gebiete müssen dem regulären Ausdruck `^\d{2}$` entsprechen;
  `LUX` ist die Sonderkennung für Luxemburg. `08`, `82` und `LUX` sind deshalb
  gültig, `8`, `082` und numerische Werte dagegen nicht.
- Doppelte PLZ-Werte werden abgelehnt oder vor dem Speichern eindeutig
  normalisiert; die gewählte Importstrategie muss das Ergebnis protokollieren.

## Gewerke

Gewerke sind eine erweiterbare Stammdatenliste und kein Freitextfeld.

| Feld | Typ | Regel |
| --- | --- | --- |
| `id` | UUID | Technischer, unveränderlicher Primärschlüssel. |
| `name` | String | Pflichtfeld und eindeutig ohne Beachtung der Groß-/Kleinschreibung. |
| `status` | Enum | `active` oder `inactive`. |
| `createdAt` | Zeitpunkt | Vom Server gesetzt. |
| `updatedAt` | Zeitpunkt | Vom Server aktualisiert. |
| `color` | String | Darstellungsfarbe im Format `#rrggbb`, innerhalb der Gewerkeliste eindeutig. |

Eine eigene Verwaltungsansicht ermöglicht das Anlegen und Bearbeiten von
Gewerken. In Unternehmensformularen werden nur aktive Gewerke zur Auswahl
angeboten. Ein bereits verwendetes Gewerk darf nicht endgültig gelöscht werden;
es kann deaktiviert werden und bleibt bei bestehenden Unternehmen sichtbar.

## Deaktivieren und Löschen

Deaktivieren ist eine reversible fachliche Statusänderung. Inaktive Unternehmen
bleiben in der Datenbank und in der Verwaltung auffindbar, erscheinen jedoch
nicht in der regulären Kartensuche. Reaktivieren setzt den Status wieder auf
`active`.

Löschen entfernt einen Datensatz endgültig und erfordert eine gesonderte
Bestätigung. Ob für den Produktivbetrieb zusätzlich ein Audit-Log oder eine
Aufbewahrungsfrist nötig ist, muss vor der Freigabe von Echtdaten entschieden
werden.

Die Aktionsspalte der Unternehmensverwaltung hat diese feste Reihenfolge:

1. Bearbeiten (Bleistift-Symbol)
2. Deaktivieren beziehungsweise Reaktivieren (eindeutiges Status-Symbol)
3. Löschen (Mülleimer-Symbol)

Alle Symbolschaltflächen benötigen einen sichtbaren Tooltip und einen
zugänglichen Namen über `aria-label`.

## Status und Zeitpunkte

`active` ist kein Feld des Modells. Frühere boolesche Werte werden einmalig in
`status` überführt (`false` nach `inactive`, alle anderen beziehungsweise
fehlenden Werte nach `active`) und anschließend nicht mehr exportiert.
`createdAt` und `updatedAt` sind UTC-Zeitpunkte im ISO-8601-Format. Beim Anlegen
sind beide identisch; jede fachliche Änderung aktualisiert `updatedAt`, während
`id` und `createdAt` unverändert bleiben.

## Seed- und Bestandsmigration

Das portable JSON-Format hat `schemaVersion: 2` und enthält die beiden Arrays
`trades` und `companies`. Der Seed-Import erfolgt in einer Transaktion: zuerst
Gewerke, dann Unternehmen, Gebietszuordnungen und Informationseinträge. IDs und
Zeitpunkte werden aus der Datei übernommen, nicht neu erzeugt. Damit kann
dasselbe Dokument lokal importiert und später ohne fachliche Sonderkonvertierung
in PostgreSQL geschrieben werden.

Die Migration aus dem bisherigen lokalen Format erfolgt einmalig wie folgt:

1. Für jedes Gewerk wird eine UUID erzeugt; die mitgelieferten Gewerke besitzen
   bereits feste UUIDv5-Werte. Bei vorhandenen lokalen Gewerken wird die neu
   erzeugte UUID im Speicherformat `v2` dauerhaft festgeschrieben.
2. Der frühere Gewerkname `trade` jedes Unternehmens wird ohne Beachtung der
   Groß-/Kleinschreibung gegen die Gewerkeliste aufgelöst und als `tradeId`
   gespeichert. Nicht auflösbare Namen brechen die Migration sichtbar ab.
3. Informationskategorien werden ohne Inhaltsverlust abgebildet: `Adresse` →
   `address`, `Telefon` → `phone`, `Ansprechpartner` → `contact` und
   `Sonstiges` → `other`.
4. `active` wird nach der oben genannten Regel in `status` überführt. Fehlende
   UUIDs und Zeitpunkte werden beim einmaligen Import erzeugt; vorhandene Werte
   bleiben erhalten. Danach wird ausschließlich das `v2`-Format geschrieben.

## Noch offene Erweiterungen

Weitere strukturierte Adress- oder Suchfelder gehören noch nicht zum
verbindlichen Modell. API und Import dürfen unbekannte Felder nicht
stillschweigend speichern; Änderungen am Modell erfolgen versioniert über eine
Datenbankmigration und eine Aktualisierung dieser Spezifikation.
