# Python-Backend

Dieses Verzeichnis ist für die geplante gemeinsame Datenhaltung vorgesehen.
Das bestehende Frontend bleibt davon getrennt unter `src/app`.

## Vorgesehene Verantwortlichkeiten

- `app/api/`: HTTP-Endpunkte, zum Beispiel `/api/companies`
- `app/models/`: persistente Datenbankmodelle
- `app/schemas/`: validierte API-Ein- und Ausgaben
- `migrations/`: versionierte Änderungen am Datenbankschema
- `tests/`: automatisierte Backendtests

Framework, Abhängigkeiten und ausführbarer Anwendungscode werden erst mit der
Backend-Implementierung ergänzt. So enthält das Repository bis dahin kein nur
scheinbar funktionsfähiges Servergerüst.
