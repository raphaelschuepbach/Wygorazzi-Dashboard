# -*- coding: utf-8 -*-
"""Rechenteil des digitalen Match-Blatts - ohne Streamlit, damit pruefbar.

Die Oberflaeche steht in Erfassung_Wygo.py. Das Blatt hat genau die Spalten
des Papierblatts; hier wird daraus die CSV-Zeile gebaut und gegengeprueft.
"""
import glob
import json
import os

import pandas as pd

PROJEKT = os.path.dirname(os.path.abspath(__file__))
WYGO_CSV = os.path.join(PROJEKT, "Statistik_Wygo.csv")
LAUFEND = os.path.join(PROJEKT, "erfassung_laufend")

# ---------------------------------------------------------------------------
# Kader. Neue Spieler kommen NUR hier dazu, nicht ueber die Oberflaeche.
# Rolle: "1"/"2"/"3" = Linie, "T" = Torhueter, "Ersatz" = war da, spielte aber
# nicht (Zeile mit Gespielt = Nein), "Spielt nicht" = gar nicht anwesend und
# kommt deshalb ueberhaupt nicht in die CSV.
# Die Rolle laesst sich im Blatt pro Spiel umstellen; die Zeile rutscht dann
# an ihren Platz.
# ---------------------------------------------------------------------------
KADER_VORGABE = [
    ("L.Leuenberger", "1"),
    ("M.Geissbühler", "1"),
    ("C.Mühle", "1"),
    ("D.Geissbühler", "2"),
    ("R.Moser", "2"),
    ("M.Nyffenegger", "2"),
    ("R.Schüpbach", "3"),
    ("B.Lüthi", "3"),
    ("N.Nyffenegger", "3"),
    ("B.Jordi", "T"),
    ("C.Loosli", "Ersatz"),
]

ERSATZ = "Ersatz"
NICHT = "Spielt nicht"
ROLLEN = ["1", "2", "3", "T", ERSATZ, NICHT]
ROLLEN_KURZ = {"1": "1", "2": "2", "3": "3", "T": "T", "Ersatz": "Ers.", NICHT: "nicht"}
# Reihenfolge der Zeilen im Blatt
RANG = {"1": 0, "2": 1, "3": 2, "T": 3, "Ersatz": 4, NICHT: 5}

# Spalten des Blatts in der Reihenfolge des Papiers:
# (Name in der CSV, Beschriftung im Blatt)
BLATT_SPALTEN = [
    ("T", "T"),
    ("A", "A"),
    ("Plus", "+"),
    ("Minus", "−"),
    ("Bully-Plus", "Bully +"),
    ("Bully-Minus", "Bully −"),
    ("Strafen", "Strafen"),
    ("Block", "Block"),
    ("Schüsse", "Schuss"),
    ("Schüsse aufs Tor", "Schuss a.T."),
    ("Balleroberung", "Baller."),
    ("Powerplay-Plus", "PP +"),
    ("Powerplay-Minus", "PP −"),
    ("Boxplay-Plus", "BP +"),
    ("Boxplay-Minus", "BP −"),
]

# Kopfzeile von Statistik_Wygo.csv - die fuehrenden Leerzeichen gehoeren dazu
WYGO_SPALTEN = ["Saison", "Format", "Team", "Gegner", "Tore Wygorazzi", "Tore Gegner",
                "Sieg", " Niederlage", " Unentschieden", " Liga Wygorazzi", "Liga Gegner",
                " Match_Id", " Datum", "Powerplay-Plus", "Powerplay-Minus",
                "Boxplay-Plus", "Boxplay-Minus"]

SPIELER_SPALTEN = ["Match_Id", "Gespielt", "Name", "T", "A", "Plus", "Minus", "Strafen",
                   "Bully-Plus", "Bully-Minus", "Linie", "Boxplay-Plus", "Boxplay-Minus",
                   "Powerplay-Plus", "Powerplay-Minus", "Linie-Plus", "Linie-Minus",
                   "Block", "Schüsse", "Balleroberung", "Schüsse aufs Tor"]


def saison_datei(saison):
    """Spieler_Statistik_25_26.csv aus der Saison '25/26'."""
    return os.path.join(PROJEKT, f"Spieler_Statistik_{saison.replace('/', '_')}.csv")


def neue_zeile(rolle="Ersatz"):
    """Eine leere Blattzeile - alle Zellen auf null."""
    return {"rolle": rolle, **{sp: 0 for sp, _ in BLATT_SPALTEN}}


def leeres_blatt():
    """Alle Zellen auf null, Rollen aus der Vorgabe."""
    return {name: neue_zeile(rolle) for name, rolle in KADER_VORGABE}


def bekannte_spieler():
    """Alle Namen, die in einer Spieler-Statistik schon vorkommen.

    Damit laesst sich jemand ins Blatt holen, der frueher schon gespielt hat,
    ohne ihn neu zu tippen - der feste Kader bleibt KADER_VORGABE.
    """
    namen = set()
    for pfad in glob.glob(os.path.join(PROJEKT, "Spieler_Statistik_*.csv")):
        try:
            sp = pd.read_csv(pfad, usecols=["Name"])
        except (ValueError, OSError, pd.errors.ParserError):
            continue
        namen.update(str(n).strip() for n in sp["Name"].dropna() if str(n).strip())
    return sorted(namen)


def linie_von(rolle):
    return int(rolle) if rolle in ("1", "2", "3") else 0


def spielt(rolle):
    """Nur wer auf dem Feld stand, bekommt Zahlen."""
    return rolle not in (ERSATZ, NICHT)


def anwesend(rolle):
    """Ersatz war da und bekommt eine Zeile mit Gespielt = Nein; wer gar nicht
    anwesend war, taucht in der CSV nicht auf."""
    return rolle != NICHT


def reihenfolge(blatt):
    """Die Namen in Blattreihenfolge: Linie 1, 2, 3, dann Torhueter, dann
    Ersatz, zuunterst wer nicht spielt. Innerhalb einer Gruppe bleibt die
    bisherige Folge stehen."""
    namen = list(blatt)
    return sorted(namen, key=lambda n: (RANG.get(blatt[n]["rolle"], 9), namen.index(n)))


# ------------------------------------------------- Zwischenstand auf Platte
AKTUELL = os.path.join(LAUFEND, "aktuell.json")


def zustand_sichern(kopf, blatt):
    """Nach jeder Aenderung auf die Platte - ueberlebt Neuladen und Neustart."""
    os.makedirs(LAUFEND, exist_ok=True)
    with open(AKTUELL, "w", encoding="utf-8") as f:
        json.dump({"kopf": kopf, "blatt": blatt}, f, ensure_ascii=False, indent=1)


def zustand_lesen():
    """Der gesicherte Stand, oder None. Aeltere Entwuerfe werden mitgenommen."""
    pfad = AKTUELL
    if not os.path.exists(pfad):
        alte = glob.glob(os.path.join(LAUFEND, "*.json"))
        if not alte:
            return None
        pfad = max(alte, key=os.path.getmtime)
    try:
        with open(pfad, encoding="utf-8") as f:
            stand = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(stand, dict) or "kopf" not in stand or "blatt" not in stand:
        return None
    for z in stand["blatt"].values():       # fehlende Spalten ergaenzen
        for sp, _ in BLATT_SPALTEN:
            z.setdefault(sp, 0)
        if z.get("rolle") not in ROLLEN:
            z["rolle"] = NICHT
    return stand


def zustand_loeschen():
    for pfad in glob.glob(os.path.join(LAUFEND, "*.json")):
        try:
            os.remove(pfad)
        except OSError:
            pass


def resultat(blatt):
    """Tore und Gegentore aus dem Blatt: die Summe der T bzw. das Minus des Torhüters."""
    eigene = sum(z["T"] for z in blatt.values() if spielt(z["rolle"]))
    feld = [z for z in blatt.values() if z["rolle"] in ("1", "2", "3")]
    gegen = sum(z["Minus"] for z in feld) // 3 if feld else 0
    return eigene, gegen


def _gemeinsamer_wert(werte):
    """Der Wert, den die Linie gemeinsam hat.

    Die Einzelwerte einer Linie koennen abweichen, wenn jemand bei einem Tor
    durch einen Spieler einer anderen Linie ersetzt war. Massgebend ist dann
    der haeufigste Wert - bei Spiel 108 hatte Linie 1 die Plus 4/4/3 und
    gehoerten ihr vier Tore, nicht drei. Das Maximum waere falsch: Linie 2
    hatte 0/0/1 und kein einziges Tor.
    """
    if not werte:
        return 0
    haeufigkeit = {w: werte.count(w) for w in werte}
    spitze = max(haeufigkeit.values())
    kandidaten = sorted(w for w, n in haeufigkeit.items() if n == spitze)
    if len(kandidaten) == 1:
        return kandidaten[0]
    # kein eindeutiger Spitzenwert (alle verschieden) - dann die Mitte nehmen
    return sorted(werte)[len(werte) // 2]


def linien_pm(blatt):
    """Linie-Plus/Minus je Linie ableiten - steht nicht auf dem Blatt."""
    raus = {}
    for lin in (1, 2, 3):
        leute = [z for z in blatt.values() if linie_von(z["rolle"]) == lin
                 and z["rolle"] != "Ersatz"]
        raus[lin] = (_gemeinsamer_wert([z["Plus"] for z in leute]),
                     _gemeinsamer_wert([z["Minus"] for z in leute]))
    return raus


def auswertung(blatt, match_id, linien=None):
    """Eine Zeile je Kaderspieler, fertig fuer Spieler_Statistik_<saison>.csv."""
    linien = linien or linien_pm(blatt)
    zeilen = []
    for name in reihenfolge(blatt):
        z = blatt[name]
        if not anwesend(z["rolle"]):      # gar nicht dabei - keine Zeile
            continue
        lin = linie_von(z["rolle"])
        gespielt = spielt(z["rolle"])
        werte = {sp: (z[sp] if gespielt else 0) for sp, _ in BLATT_SPALTEN}
        werte["Linie"] = lin
        werte["Linie-Plus"], werte["Linie-Minus"] = linien.get(lin, (0, 0)) if gespielt else (0, 0)
        if not gespielt:
            # Ersatz: war da, hat aber nicht gespielt - Plus/Minus als Strich
            werte["Plus"] = werte["Minus"] = "-"
        zeilen.append([match_id, "Ja" if gespielt else "Nein", name]
                      + [werte[sp] for sp in SPIELER_SPALTEN[3:]])
    return pd.DataFrame(zeilen, columns=SPIELER_SPALTEN)


def wygo_zeile(kopf, blatt, datum_text):
    """Die eine Zeile fuer Statistik_Wygo.csv."""
    eigene, gegen = resultat(blatt)
    return [kopf["saison"], kopf["format"], "Wygorazzi", kopf["gegner"], eigene, gegen,
            "Ja" if eigene > gegen else "Nein",
            "Ja" if eigene < gegen else "Nein",
            "Ja" if eigene == gegen else "Nein",
            kopf["liga_wygo"], kopf["liga_gegner"], kopf["match_id"], datum_text,
            kopf["pp_plus"], kopf["pp_minus"], kopf["bp_plus"], kopf["bp_minus"]]


def kontrollen(kopf, blatt, tabelle):
    """Die Querproben vom Papierblatt - jetzt vor dem Schreiben."""
    eigene, gegen = resultat(blatt)
    raus = []

    def pruefe(text, ok, hinweis=""):
        raus.append((bool(ok), text if ok else f"{text} — {hinweis}"))

    feld = [z for z in blatt.values() if z["rolle"] in ("1", "2", "3")]
    hueter = [z for z in blatt.values() if z["rolle"] == "T"]

    pruefe("Genau ein Torhüter im Spiel", len(hueter) == 1, f"gefunden: {len(hueter)}")
    summe_plus = sum(z["Plus"] for z in feld)
    summe_minus = sum(z["Minus"] for z in feld)
    pruefe(f"Summe Plus der Feldspieler = 3 × {eigene} Tore", summe_plus == 3 * eigene,
           f"ist {summe_plus}, erwartet {3 * eigene}")
    pruefe(f"Summe Minus der Feldspieler durch 3 teilbar", summe_minus % 3 == 0,
           f"ist {summe_minus}")

    lin = linien_pm(blatt)
    pruefe(f"Summe Linie-Plus = {eigene} Tore",
           sum(p for p, _ in lin.values()) == eigene,
           f"ist {sum(p for p, _ in lin.values())}")
    pruefe(f"Summe Linie-Minus = {gegen} Gegentore",
           sum(m for _, m in lin.values()) == gegen,
           f"ist {sum(m for _, m in lin.values())}")

    if hueter:
        h = hueter[0]
        pruefe("Plus/Minus des Torhüters passt zum Resultat",
               h["Plus"] <= eigene and h["Minus"] <= gegen,
               f"{h['Plus']}/{h['Minus']} bei {eigene}:{gegen} — "
               "tiefer ist in Ordnung, höher nicht")

    verletzt = [n for n, z in blatt.items() if spielt(z["rolle"])
                and not (z["T"] <= z["Schüsse aufs Tor"] <= z["Schüsse"])]
    pruefe("Tore ≤ Schüsse aufs Tor ≤ Schüsse", not verletzt, ", ".join(verletzt))

    w = pd.read_csv(WYGO_CSV)
    w.columns = w.columns.str.strip()
    vergeben = set(pd.to_numeric(w["Match_Id"], errors="coerce").dropna().astype(int))
    pruefe(f"Match-Id {kopf['match_id']} ist noch frei", kopf["match_id"] not in vergeben,
           "diese Id steht schon in Statistik_Wygo.csv")
    pruefe("Gegner eingetragen", bool(str(kopf["gegner"]).strip()))
    return raus


def zeilenende(pfad):
    """CRLF oder LF - so, wie die Datei es bisher haelt."""
    with open(pfad, "rb") as f:
        return "\r\n" if b"\r\n" in f.read() else "\n"


def anhaengen(pfad, zeilen, spalten):
    """Zeilen an eine CSV anhaengen, ohne den bestehenden Inhalt anzufassen."""
    ende = zeilenende(pfad) if os.path.exists(pfad) else "\r\n"
    neu = "".join(",".join(str(v) for v in z) + ende for z in zeilen)
    if os.path.exists(pfad):
        with open(pfad, encoding="utf-8", newline="") as f:
            alt = f.read()
        kopf = alt.split(ende)[0].split(",")
        if kopf != spalten:
            raise ValueError(f"Kopfzeile von {os.path.basename(pfad)} passt nicht:\n{kopf}")
        inhalt = alt.rstrip("\r\n") + ende + neu
    else:
        inhalt = ",".join(spalten) + ende + neu
    with open(pfad, "w", encoding="utf-8", newline="") as f:
        f.write(inhalt)


def schreiben(kopf, blatt, datum_text, linien=None):
    """Beide CSVs ergaenzen. Wirft, wenn eine Kopfzeile nicht passt."""
    tabelle = auswertung(blatt, kopf["match_id"], linien)
    anhaengen(saison_datei(kopf["saison"]), tabelle.values.tolist(), SPIELER_SPALTEN)
    anhaengen(WYGO_CSV, [wygo_zeile(kopf, blatt, datum_text)], WYGO_SPALTEN)
    return tabelle
