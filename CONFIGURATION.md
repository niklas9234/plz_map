# Karteneinstellungen

Die Darstellung der Webkarte wird zentral in `src/app/settings.js` konfiguriert.
Dort lassen sich unter anderem Farben, Linienbreiten, Kartenposition sowie
Schriftart und dynamische Schriftgrößen ändern. Die Einstellungen unter
`postalCodes` werden gemeinsam für die deutschen und luxemburgischen
Postleitzahl-Layer verwendet; dadurch haben beide immer dieselbe Füllung,
Umrandung, Mindest-Zoomstufe und Schriftgrößen-Skalierung.

Eine `.env`-Datei ist dafür nicht erforderlich, weil diese Werte öffentlich im
Browser verwendet werden und die Anwendung keinen Build-Schritt benötigt.
Änderungen an `settings.js` werden nach einem Neuladen der Seite sichtbar.

## PMTiles-Basiskarte

Die Basiskarte wird aus `germany-luxembourg.pmtiles` im Wurzelverzeichnis des
Webservers geladen. Sie liefert die in `src/app/basemap.js` dargestellten
Karteninhalte, darunter Städte und Straßen. Der Hostname wird automatisch von
der geöffneten Seite übernommen, sodass dafür keine auf `localhost` begrenzte
URL konfiguriert werden muss. Das große, lokal bereitgestellte Archiv bleibt
durch `.gitignore` von Git ausgeschlossen.

## Testdaten der Unternehmenssuche

Bis zur Anbindung einer Datenbank liest die Suche die fünf Beispielunternehmen
aus `src/app/companies.json`. Jeder Datensatz enthält `name`, `ppsNumber` und
eine Liste zusammenhängender zweistelliger Postleitzahlgebiete unter
`postalCodes`. Der Datenzugriff ist in `loadCompanies()` in
`src/app/company-search.js` gekapselt. Für eine spätere API-Anbindung muss damit
nur diese Ladefunktion ausgetauscht werden; Suche und Kartendarstellung können
unverändert bleiben.
