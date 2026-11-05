# Videoanalyse

Aus dem Matchvideo wird gemessen, wo die Mannschaften gespielt haben und wie
weit sie gelaufen sind. Vier Schritte, jeder einzeln aufrufbar.

## 1. Feld markieren

    py -3.12 feld_markieren.py --match 105

Sechs Klicks auf einem Standbild: vier Bandenecken und die beiden Enden der
Mittellinie. Das Feld misst 24 m in der Laenge (quer durchs Bild, von Tor zu
Tor) und 14 m in der Breite. Gemeint ist der **Fuss der Bande**; bei den
runden Ecken der gedachte Schnittpunkt der beiden geraden Bandenstuecke.

Ab vier Punkten zeichnet das Werkzeug ein 2-Meter-Gitter ins Bild - liegt das
auf der Bande, stimmt die Umrechnung. Ergebnis: `feld_<match>.json`.

Auf dem Desktop liegen `Feld markieren 105.bat` und `... 106.bat`.

## 2. Markierung nachziehen (freiwillig)

    py -3.12 feld_feinschliff.py --match 105

Schnappt jede Feldseite an die staerkste Bildkante in ihrer Naehe und setzt
die Ecken neu als Schnittpunkte der vier Geraden. **An der nahen Bande
arbeitet das zuverlaessig, an der fernen nicht** - dort haengen Werbebanner,
und die Kantensuche erwischt mal den Bandenfuss, mal die Bannerkante. Das
Ergebnis also immer am Kontrollbild pruefen und notfalls die Klicks behalten.

Probe ohne Zirkelschluss: die Mittellinie geht nicht in die Rechnung ein und
muss bei 12.0 m herauskommen.

| Spiel | Mittellinie hinten | vorne | Genauigkeit |
|---|--:|--:|--:|
| 105 | 11.61 m | 11.73 m | rund 0.4 m |
| 106 | 11.09 m | 12.96 m | rund 1 m |

## 3. Aus dem Video extrahieren

    py -3.12 spur_extrakt.py --match 105 --start 400 --dauer 2900 --schritt 3

YOLO11m erkennt Personen, ByteTrack verfolgt sie, der Fusspunkt jedes
Kastens wird ins Feld gerechnet. Geschrieben wird eine Zeile je Erkennung
mit Zeit, Spur, Feld- und Bildkoordinate, Kastenhoehe und Trikotfarbe
(`roh_<match>_<start>_<dauer>.csv`).

Das ist der einzige teure Schritt: rund eine Minute Rechenzeit je Minute
Video auf einer RTX 4070, bei jedem dritten Bild und 1600 Pixel
Eingangsgroesse.

## 4. Auswerten

    py -3.12 spur_auswertung.py --roh roh_105_voll.csv

Trennt die Rollen, misst Laufwege, Zonen und zeichnet die Heatmaps. Rechnet
in Sekunden, die Regeln lassen sich also beliebig oft aendern, ohne das
Video noch einmal anzufassen.

### Wie die Rollen getrennt werden

| Rolle | Merkmal |
|---|---|
| Torhueter | Medianposition in den aeusseren 6.5 m, quer in der Mitte, kaum Streuung |
| Schiedsrichter | Saettigung unter 34 bei hoher Helligkeit (mintfarbenes bzw. gestreiftes Trikot) |
| Wygorazzi | Saettigung unter 70 (weiss-schwarz) |
| Gegner | alles darueber (schwarz) |

Zwischen den Mannschaften klafft in der Saettigung eine Luecke von 61 bis 73,
die Trennung ist also nicht knapp. Helligkeit und Saettigung liefern dasselbe
Ergebnis; genommen wird die Saettigung, weil sie weniger an der
Hallenbeleuchtung haengt.

## Was belastbar ist und was nicht

**Belastbar**, weil die Zahl der erkannten Personen je Rolle stimmt
(2 Torhueter, 1 Schiedsrichter, 3 + 3 Feldspieler):

* Aufenthalt je Felddrittel, Heatmap, Feldlage im Spielverlauf
* Laufweg je Mannschaft, umgerechnet auf Meter je Personenminute

**Nicht belastbar**: die Zuordnung zu einzelnen Spielern. Die Verfolgung
zerfaellt in rund 25 Spuren je Minute fuer acht Personen, weil sich die
Spieler gegenseitig verdecken. Trikotnummern sind bei 50 Pixel Koerperhoehe
nicht lesbar, und Wiedererkennung ueber das Aussehen bringt wenig, weil alle
Spieler einer Mannschaft gleich aussehen.

**Systematisch**: die dunkle Mannschaft wird seltener erkannt als die helle
(2.5 statt 3 Spieler je Bild). Summen je Mannschaft darum immer auf
Personenminuten normieren, nie roh vergleichen.

## Weitere Werkzeuge

* `tor_zeiten.py` - legt die Tore aus `Tore.csv` ueber die abgelesene
  Spieluhr auf die Videozeit (auf etwa 15 s genau).
* `tor_kontext.py` - fasst zusammen, was in den Sekunden vor jedem Tor auf
  dem Feld stand: Zahl der Spieler je Mannschaft, Schwerpunkt, Breite.
* `erkennung_test.py` - Messlauf zur Erkennung selbst: Personen je
  Eingangsaufloesung, Ball, Trennbarkeit der Trikotfarben.

## 5. Trikotnummern: vom Namenlosen zum Spieler

Die Verfolgung allein liefert Ketten von im Mittel 20 Sekunden - zu kurz
fuer einen ganzen Einsatz. Die Nummer auf dem Ruecken schliesst die Luecke.
Gemessen an diesem Spiel: 66 % der Ketten enthalten mindestens einen
Ausschnitt ueber 100 Pixel Koerperhoehe, 37 % einen ueber 120 Pixel, und
diese decken 55 % der verfolgten Zeit ab. Von Auge ist auf etwa einem
Drittel dieser Ausschnitte die Nummer zu lesen.

Zwei Dinge machen das machbar, obwohl allgemeines Ziffernlesen bei dieser
Aufloesung scheitert:

* **Geschlossene Menge.** Dreizehn eigene Nummern, eine Handvoll
  gegnerische - eine Klassifikation mit rund zwanzig Klassen.
* **Mehrheitsentscheid je Kette.** Nicht jedes Bild muss stimmen. Bei fuenf
  Ausschnitten derselben Person reicht eine mittelmaessige Trefferquote.

### Ablauf

    py -3.12 nummern_sammeln.py --match 105     # Stichprobe schneiden
    py -3.12 nummern_labeln.py  --match 105     # von Hand beschriften
    py -3.12 nummern_lernen.py  --match 105     # Modell trainieren
    py -3.12 nummern_zuordnen.py --match 105    # auf alle Ketten anwenden

`nummern_sammeln.py` schneidet den oberen Ruecken aus jeder Erkennung ab
110 Pixel Hoehe und streut die Stichprobe ueber die Ketten, damit
moeglichst viele verschiedene Personen darin vorkommen.

`nummern_labeln.py` zeigt jeden Ausschnitt gross und hart vergroessert
nebeneinander; getippt wird die Nummer, Leertaste heisst "keine Nummer
lesbar". Gespeichert wird nach jedem Eintrag, Abbrechen und Weitermachen
ist jederzeit moeglich.

`nummern_lernen.py` trainiert ein vorgelerntes ResNet18. Zwei Punkte, die
das Ergebnis ehrlich halten: die Aufteilung in Training und Pruefung geht
ueber die **Ketten** (zwei Ausschnitte derselben Kette sind fast dasselbe
Bild), und gespiegelt wird nie (eine gespiegelte 17 ist keine 17).
Berichtet wird beides - Trefferquote je Bild und, was wirklich zaehlt,
nach Mehrheitsentscheid je Kette.

`nummern_zuordnen.py` liest das Video einmal durch, laesst das Modell jeden
Ausschnitt lesen, entscheidet je Kette per gewichteter Mehrheit (Sicherheit
mal Ausschnittgroesse) und fasst Ketten derselben Nummer zusammen, solange
sie sich zeitlich nicht ueberlappen.

### Der Kader

| Nr | Spieler | Nr | Spieler |
|--:|---|--:|---|
| 8 | B.Lüthi | 43 | C.Loosli (TH) |
| 13 | M.Geissbühler | 69 | B.Jordi (TH) |
| 17 | R.Schüpbach | 74 | D.Geissbühler |
| 25 | M.Nyffenegger | 77 | R.Moser |
| 32 | N.Nyffenegger | 84 | C.Mühle |
| 33 | G.Thierstein | 88 | L.Leuenberger |
| 42 | F.Baschung | | |
