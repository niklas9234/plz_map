# API-Vertrag für Stammdaten

Alle Endpunkte liegen unter `/api`. JSON-Feldnamen entsprechen dem fachlichen
Datenmodell in [`data-model.md`](data-model.md). Schreibende Endpunkte müssen
später serverseitig authentifiziert und autorisiert werden.

## Unternehmen

| Methode und Pfad | Verhalten |
| --- | --- |
| `GET /api/companies` | Unternehmen auflisten; Filter: `query`, `tradeId`, `status` und `postalCode`. Ohne `status` liefert die öffentliche Kartensuche nur aktive Einträge. |
| `GET /api/companies/{id}` | Ein Unternehmen laden. |
| `POST /api/companies` | Unternehmen anlegen. |
| `PATCH /api/companies/{id}` | Felder eines Unternehmens ändern. |
| `POST /api/companies/{id}/deactivate` | Unternehmen reversibel deaktivieren. |
| `POST /api/companies/{id}/activate` | Unternehmen reaktivieren. |
| `DELETE /api/companies/{id}` | Unternehmen nach expliziter Bestätigung endgültig löschen. |

Beispiel einer Antwort:

```json
{
  "id": "7bccfe83-a7ef-43fd-b121-3e1fc091ec25",
  "name": "Beispiel GmbH",
  "ppsNumber": "PPS-1001",
  "tradeId": "9603b68f-f93e-433f-91cb-a8a76194452d",
  "trade": "Elektro",
  "territories": [
    { "postalCode": "08", "role": "primary" },
    { "postalCode": "82", "role": "alternative" }
  ],
  "status": "active",
  "createdAt": "2026-09-01T10:00:00Z",
  "updatedAt": "2026-09-01T10:00:00Z"
}
```

## Gewerke

| Methode und Pfad | Verhalten |
| --- | --- |
| `GET /api/trades` | Gewerke auflisten; optional nach `status` filtern. |
| `POST /api/trades` | Ein auswählbares Gewerk anlegen. |
| `PATCH /api/trades/{id}` | Name oder Status ändern. |
| `POST /api/trades/{id}/deactivate` | Gewerk deaktivieren. |
| `POST /api/trades/{id}/activate` | Gewerk reaktivieren. |
| `DELETE /api/trades/{id}` | Nur ein unbenutztes Gewerk endgültig löschen. |

## Fehler und Nebenläufigkeit

Fehlerantworten besitzen mindestens `code`, `message` und optional `fields`.

| Status | Verwendung |
| --- | --- |
| `400 Bad Request` | Ungültiges JSON oder unbekannte Felder. |
| `401 Unauthorized` | Keine gültige Anmeldung. |
| `403 Forbidden` | Keine Berechtigung für die Operation. |
| `404 Not Found` | Ressource existiert nicht. |
| `409 Conflict` | PPS-Nummer oder Gewerkname bereits vorhanden, beziehungsweise Gewerk wird noch verwendet. |
| `422 Unprocessable Content` | Fachliche Feldvalidierung fehlgeschlagen. |

Eindeutigkeitskonflikte werden unabhängig von vorherigen Anwendungsprüfungen aus
den Datenbank-Constraints in `409 Conflict` übersetzt. Listenendpunkte müssen
vor dem Import großer Datenmengen um Pagination ergänzt werden; das konkrete
Verfahren wird mit der Backend-Technologie festgelegt.
