# Karteneinstellungen

Die Darstellung der Webkarte wird zentral in `src/app/settings.js` konfiguriert.
Dort lassen sich unter anderem Farben, Linienbreiten, Kartenposition sowie
Schriftart und dynamische Schriftgrößen ändern. Die Einstellungen unter
`postalCodes` werden gemeinsam für die deutschen und luxemburgischen
Postleitzahl-Layer verwendet; dadurch haben beide immer dieselbe Füllung,
Umrandung, Mindest-Zoomstufe und Schriftgrößen-Skalierung.

Mit `postalCodes.label.minAreaSquareKilometers` wird in Quadratkilometern
festgelegt, ab welcher Größe eine zusammenhängende Fläche ihre Beschriftung
erhält. Der Wert `0` beschriftet auch kleinste Teilflächen. Ein höherer Wert
unterdrückt beispielsweise Beschriftungen auf kleinen Inseln, ohne diese aus
der Flächen- oder Grenzdarstellung zu entfernen. Auch eine spätere, von der
Postleitzahl abhängige Einfärbung erfasst weiterhin alle Teilflächen.

Eine `.env`-Datei ist dafür nicht erforderlich, weil diese Werte öffentlich im
Browser verwendet werden und die Anwendung keinen Build-Schritt benötigt.
Änderungen an `settings.js` werden nach einem Neuladen der Seite sichtbar.
