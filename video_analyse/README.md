# Videoanalyse

Verfolgt die Spieler im Matchvideo und rechnet ihre Laufwege in Meter um.

## Feldvermessung

Die Kamera steht fest, darum genuegt eine einmal bestimmte Umrechnung Bild -> Feld.
Grundlage sind sechs auf einem Standbild markierte Punkte: die vier Feldecken und
die beiden Enden der Mittellinie. Das Feld misst 24 m in die Tiefe und 14 m in die Breite.

Kontrolle der Umrechnung an Massen, die nicht zur Berechnung verwendet wurden:

| Probe | gemessen | Soll |
|---|---|---|
| Mittellinie links / rechts | 12.0 m / 11.6 m | 12.0 m |
| fernes Tor, Mitte quer | 7.06 m | 7.00 m |
| fernes Tor, Breite | 1.43 m | 1.60 m |
| nahes Tor, Mitte quer | 7.35 m | 7.00 m |

Mittlere Abweichung der sechs Markierungen: 0.31 m, groesste 0.47 m.

**Die Bildpunkte im Skript gelten nur fuer die Kameraposition von Match 104**
(`Video_2026-09-13_12-52-24.mp4`). Fuer ein anderes Spiel muessen die Ecken neu
markiert werden, sonst sind alle Meterangaben falsch.

## Aufruf

    py -3.12 spieler_tracking.py --start 20:00 --dauer 180 --overlay kontrolle.mp4

Ergebnisse: `spuren.csv` (eine Zeile je Spur), `heatmap.png`, und das Kontrollvideo
mit eingezeichneten Kaesten und Feldgrenze.

## Was belastbar ist und was nicht

Belastbar: Laufdistanz und Zeit **je Mannschaft**, Heatmap, Tempowerte. Die erkannten
Personensekunden entsprechen rund zehn Personen durchgehend auf dem Feld
(8 Spieler + 2 Schiedsrichter), die Spuren schliessen also lueckenlos aneinander an.

Nicht belastbar: die Zuordnung zu einzelnen Spielern. Die Verfolgung zerfaellt in rund
40 Spuren je Minute fuer zehn Personen, weil sich die Spieler gegenseitig verdecken.
Trikotnummern sind bei 13 Pixel Hoehe nicht lesbar, und Wiedererkennung ueber das
Aussehen (BoT-SORT mit ReID, `--tracker botsort_halle.yaml`) bringt praktisch nichts,
weil alle Spieler einer Mannschaft gleich aussehen.
