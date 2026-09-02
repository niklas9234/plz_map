# Karteneinstellungen

Die Darstellung der Webkarte wird zentral in `src/app/settings.js` konfiguriert.
Dort lassen sich unter anderem Farben, Linienbreiten, Kartenposition sowie
Schriftart, dynamische Schriftgrößen und die Mindest-Zoomstufe der Städtenamen
ändern. Die Einstellungen unter
`postalCodes` werden gemeinsam für die deutschen und luxemburgischen
Postleitzahl-Layer verwendet; dadurch haben beide immer dieselbe Füllung,
Umrandung, Mindest-Zoomstufe und Schriftgrößen-Skalierung.

Eine `.env`-Datei ist dafür nicht erforderlich, weil diese Werte öffentlich im
Browser verwendet werden und die Anwendung keinen Build-Schritt benötigt.
Änderungen an `settings.js` werden nach einem Neuladen der Seite sichtbar.

## PMTiles-Basiskarte

Die Basiskarte wird aus
`src/app/data/pmtiles/germany-luxembourg.pmtiles` geladen. Sie liefert die in
`src/app/basemap.js` dargestellten Karteninhalte, darunter Städte und Straßen.
Die URL wird relativ zur URL der geöffneten Anwendung aufgelöst und anschließend
mit dem von PMTiles erwarteten `pmtiles://`-Schema versehen. Bei einem Aufruf an
der Domain-Wurzel verweist sie daher auf
`/data/pmtiles/germany-luxembourg.pmtiles`; beim in `README.md` beschriebenen
Aufruf unter `/src/app/` verweist sie auf
`/src/app/data/pmtiles/germany-luxembourg.pmtiles`. Dadurch sind weder Hostname
noch Installationspfad fest konfiguriert. Das große, lokal bereitgestellte Archiv
bleibt durch `.gitignore` von Git ausgeschlossen.

Nach einem frischen Checkout muss die PMTiles-Datei manuell in dieses
Verzeichnis kopiert werden. Weitere Hinweise stehen in
`src/app/data/pmtiles/README.md`.
