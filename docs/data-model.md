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

Für die derzeitige Oberfläche darf die API zusätzlich den Namen des Gewerks als
eingebettetes Feld `trade` liefern. `tradeId` bleibt trotzdem die maßgebliche
Beziehung. Die vorhandenen Beispieldaten werden bei der Migration über den
Gewerknamen den angelegten Gewerken zugeordnet.

### Eindeutigkeit und Normalisierung

- Die Datenbank erzwingt die globale Eindeutigkeit der PPS-Nummer mit einem
  Unique Constraint. Der Import und die API prüfen dies zusätzlich, der
  Constraint bleibt aber die letzte Instanz bei parallelen Anfragen.
- Äußere Leerzeichen in Name und PPS-Nummer werden entfernt.
- PLZ-Werte müssen dem regulären Ausdruck `^\d{2}$` entsprechen. `08` und `82`
  sind deshalb gültig, `8`, `082` und numerische Werte dagegen nicht.
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

## Noch offene Erweiterungen

Adressfelder und weitere Such- oder Importfelder gehören noch nicht zum
verbindlichen Modell. Sie werden erst ergänzt, wenn fachlich geklärt ist,
welche Angaben benötigt werden. API und Import dürfen unbekannte Felder nicht
stillschweigend speichern; Änderungen am Modell erfolgen versioniert über eine
Datenbankmigration und eine Aktualisierung dieser Spezifikation.
