# -*- coding: utf-8 -*-
"""Rechenteil des digitalen Match-Blatts - ohne Streamlit, damit pruefbar.

Die Oberflaeche steht in Erfassung_Wygo.py. Das Blatt hat genau die Spalten
des Papierblatts; hier wird daraus die CSV-Zeile gebaut und gegengeprueft.
"""
import glob
import json
import os
import shutil
import subprocess
import uuid

import pandas as pd

PROJEKT = os.path.dirname(os.path.abspath(__file__))
WYGO_CSV = os.path.join(PROJEKT, "Statistik_Wygo.csv")
TORE_CSV = os.path.join(PROJEKT, "Tore.csv")
GEGNER_CSV = os.path.join(PROJEKT, "Gegner_Abschluesse.csv")
LAUFEND = os.path.join(PROJEKT, "erfassung_laufend")
# Hochgeladene Torclips warten hier, bis das Blatt uebernommen wird. Erst
# dann ist die Match-Id endgueltig und sie wandern in den Saisonordner.
CLIPS = os.path.join(LAUFEND, "clips")

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
    ("Ballverlust", "Ballverl."),
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
                   "Block", "Schüsse", "Balleroberung", "Schüsse aufs Tor",
                   "Ballverlust"]

# Eine Zeile je Tor und Gegentor - daraus baut das Dashboard den Spielverlauf,
# die Torkategorien, die Assist-Paare und die Clips zum Anschauen.
# "Sekunde" ist die Spieluhr innerhalb der Halbzeit, "Videozeit" die Stelle
# im Spielvideo. Beides wird gebraucht: die Uhr fuer die Statistik, die
# Videozeit zum Schneiden der Ausschnitte.
TORE_SPALTEN = ["Match_Id", "Nr", "Halbzeit", "Zeit", "Sekunde", "Art", "Spieler",
                "Assist", "Linie", "Kategorie", "Datei", "Video", "Videozeit"]

# Ein Video je Spiel, damit sich die Ausschnitte spaeter daraus schneiden
# lassen. Eine eigene kleine Datei, damit die Kopfzeilen der gewachsenen
# Tabellen unangetastet bleiben.
VIDEOS_CSV = os.path.join(PROJEKT, "Spielvideos.csv")
VIDEO_SPALTEN = ["Match_Id", "Datei"]

# Die Videozeit wird sekundengenau angegeben. Sie ist die Mitte des
# Ausschnitts, darum lohnt sich die Genauigkeit: eine Sekunde daneben
# verschiebt das Tor eine Sekunde aus der Mitte.
VIDEO_SCHRITT = 1

# Eine Zeile je Spiel und Linie: was der Gegner abgeschlossen hat, waehrend
# diese Linie auf dem Feld stand. Gegentore und von uns geblockte Versuche
# gehoeren NICHT hier hinein - die stehen in Tore.csv und in der Spalte
# "Block"; zusammen ergibt das Corsi gegen.
ABSCHLUSS_ARTEN = ["Gegner aufs Tor gehalten", "Gegner daneben"]
GEGNER_SPALTEN = ["Match_Id", "Linie"] + ABSCHLUSS_ARTEN

# Zwei getrennte Listen: ein eigenes Tor faellt anders als ein Gegentor.
KATEGORIEN = {
    "Tor": ["Schuss eigene Hälfte", "Schuss gegner Hälfte", "Freistoss", "Powerplay",
            "Ballgewinn Konter", "Zuteilungsfehler Gegner",
            "Gegner Überlaufen eigene Hälfte", "Gegner Überlaufen gegner Hälfte"],
    "Gegentor": ["Nicht geblockt eigene Hälfte", "Nicht geblockt gegnerische Hälfte",
                 "Freistoss", "Boxplay", "Ballverlust Konter", "Zuteilungsfehler",
                 "Überlaufen eigene Hälfte", "Überlaufen gegnerische Hälfte"],
}
HALBZEIT_MINUTEN = 20
MAX_MINUTE = 25        # etwas Luft ueber die regulaere Halbzeit hinaus


def saison_datei(saison):
    """Spieler_Statistik_25_26.csv aus der Saison '25/26'."""
    return os.path.join(PROJEKT, f"Spieler_Statistik_{saison.replace('/', '_')}.csv")


def neue_zeile(rolle="Ersatz"):
    """Eine leere Blattzeile - alle Zellen auf null."""
    return {"rolle": rolle, **{sp: 0 for sp, _ in BLATT_SPALTEN}}


def leeres_blatt():
    """Alle Zellen auf null, Rollen aus der Vorgabe."""
    return {name: neue_zeile(rolle) for name, rolle in KADER_VORGABE}


# ------------------------------------------------------ Tore und Abschluesse

def zeit_text(sekunde):
    return f"{int(sekunde) // 60}:{int(sekunde) % 60:02d}"


def videozeit_text(sekunde):
    """Videos laufen ueber eine Stunde - darum mit Stundenangabe."""
    if sekunde in ("", None):
        return "—"
    s = int(sekunde)
    return (f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600
            else f"{s // 60}:{s % 60:02d}")


def neues_tor(art, spieler="", linie=""):
    """Ein Toreintrag, wie ihn Tore.csv braucht - erst nur mit dem, was der
    Klick aufs Blatt schon weiss. Der Rest wird unten am Blatt nachgetragen.

    Die Kennung bleibt dem Eintrag erhalten, auch ueber ein Neuladen hinweg.
    Daran haengen die Eingabefelder: ohne sie wuerden sie beim Loeschen eines
    Tors auf den Nachbarn rutschen und dessen Werte zeigen.
    """
    return {"id": uuid.uuid4().hex[:8], "art": art, "spieler": spieler,
            "assist": "", "hz": 1, "sek": 0, "linie": str(linie),
            "kategorie": "", "datei": "", "video": "", "videozeit": ""}


def leere_abschluesse():
    return {l: {a: 0 for a in ABSCHLUSS_ARTEN} for l in ("1", "2", "3")}


def tore_geordnet(tore):
    """Chronologisch - so sind sie gefallen, und so nummeriert sie das
    Dashboard, das daraus den Spielverlauf zeichnet."""
    return sorted(tore, key=lambda t: (int(t["hz"]), int(t["sek"])))


def tore_zeilen(match_id, tore):
    """Die Zeilen fuer Tore.csv. Nr laeuft je Spiel ueber Tore und Gegentore
    gemeinsam und in der Reihenfolge der Uhr."""
    zeilen = []
    for nr, t in enumerate(tore_geordnet(tore), 1):
        zeilen.append([match_id, nr, t["hz"], zeit_text(t["sek"]), int(t["sek"]),
                       t["art"], t["spieler"], t["assist"], t["linie"],
                       t["kategorie"], t["datei"], t["video"], t["videozeit"]])
    return zeilen


def gegner_zeilen(match_id, abschluesse):
    """Die Zeilen fuer Gegner_Abschluesse.csv - Linien ohne jeden Abschluss
    bleiben weg, sonst steht die Datei voller Nullen."""
    return [[match_id, linie] + [werte[a] for a in ABSCHLUSS_ARTEN]
            for linie, werte in sorted(abschluesse.items())
            if any(werte[a] for a in ABSCHLUSS_ARTEN)]


def clip_namen(tore):
    """Zu jedem Tor mit Clip der endgueltige Dateiname, in Spielreihenfolge.

    Schema wie bei den bisher von Hand geschnittenen Clips: <Schuetze><k>,
    bei Gegentoren Gegentor<k>, wobei k je Art durchzaehlt. Erst beim
    Uebernehmen vergeben - vorher kann sich die Reihenfolge noch aendern.
    """
    zaehler, raus = {}, []
    for t in tore_geordnet(tore):
        # durchgezaehlt wird ueber alle Tore einer Art, nicht nur ueber die
        # mit Clip - sonst passen die Nummern nicht zu den schon vorhandenen
        zaehler[t["art"]] = zaehler.get(t["art"], 0) + 1
        if not t.get("datei"):
            continue
        stamm = (t["spieler"].strip() if t["art"] == "Tor" and t["spieler"].strip()
                 else "Gegentor")
        stamm = "".join(z for z in stamm if z.isalnum() or z in " .-_") or "Tor"
        endung = os.path.splitext(t["datei"])[1] or ".mp4"
        raus.append((t, f"{stamm}{zaehler[t['art']]}{endung}"))
    return raus


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


def zustand_sichern(kopf, blatt, tore=None, abschluesse=None):
    """Nach jeder Aenderung auf die Platte - ueberlebt Neuladen und Neustart."""
    os.makedirs(LAUFEND, exist_ok=True)
    with open(AKTUELL, "w", encoding="utf-8") as f:
        json.dump({"kopf": kopf, "blatt": blatt, "tore": tore or [],
                   "abschluesse": abschluesse or leere_abschluesse()},
                  f, ensure_ascii=False, indent=1)


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
    # Entwuerfe aus der Zeit vor den Toren sollen weiter aufgehen
    stand["kopf"].setdefault("video", "")
    stand.setdefault("tore", [])
    for t in stand["tore"]:
        for feld, wert in neues_tor("Tor").items():
            t.setdefault(feld, wert)
    stand.setdefault("abschluesse", leere_abschluesse())
    for linie, werte in leere_abschluesse().items():
        stand["abschluesse"].setdefault(linie, werte)
    return stand


def zustand_loeschen():
    for pfad in glob.glob(os.path.join(LAUFEND, "*.json")):
        try:
            os.remove(pfad)
        except OSError:
            pass
    for pfad in glob.glob(os.path.join(CLIPS, "*")):
        try:
            os.remove(pfad)
        except OSError:
            pass


# --------------------------------------------------- Torclips zwischenlagern

def clip_ablegen(name, daten):
    """Einen hochgeladenen Clip zwischenlagern und seinen Namen liefern.

    Noch nicht in den Saisonordner: solange das Blatt nicht uebernommen ist,
    steht die Match-Id nicht fest, und ein verworfenes Blatt soll keine
    verwaisten Dateien hinterlassen.
    """
    os.makedirs(CLIPS, exist_ok=True)
    stamm, endung = os.path.splitext(os.path.basename(name))
    ziel, i = f"{stamm}{endung}", 1
    while os.path.exists(os.path.join(CLIPS, ziel)):
        i += 1
        ziel = f"{stamm}_{i}{endung}"
    with open(os.path.join(CLIPS, ziel), "wb") as f:
        f.write(daten)
    return ziel


def clip_entfernen(name):
    try:
        os.remove(os.path.join(CLIPS, name))
    except OSError:
        pass


# ----------------------------------------------- Ausschnitte selber schneiden

CLIP_DAUER = 10        # Sekunden je Ausschnitt


def ffmpeg_pfad():
    """Das mit imageio-ffmpeg mitgelieferte ffmpeg - es muss nichts
    zusaetzlich installiert sein."""
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def clip_schneiden(video, mitte_s, ziel, dauer=CLIP_DAUER):
    """Einen Ausschnitt um die angegebene Videosekunde herum.

    Die Videozeit am Tor ist die **Mitte**: geschnitten wird fuenf Sekunden
    davor bis fuenf danach. Am Anfang des Videos wird nach vorne geschoben,
    damit der Ausschnitt seine volle Laenge behaelt.

    Neu kodiert statt nur kopiert: ein Kopierschnitt beginnt immer erst beim
    naechsten Schluesselbild und laege dann leicht ein, zwei Sekunden daneben.
    """
    start = max(0.0, float(mitte_s) - dauer / 2)
    ordner = os.path.dirname(ziel)
    if ordner:
        os.makedirs(ordner, exist_ok=True)
    befehl = [ffmpeg_pfad(), "-hide_banner", "-loglevel", "error", "-y",
              "-ss", f"{start:.2f}", "-i", video, "-t", str(dauer),
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
              "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", ziel]
    fertig = subprocess.run(befehl, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if fertig.returncode != 0 or not os.path.exists(ziel):
        raise RuntimeError((fertig.stderr or "").strip()[-400:]
                           or "ffmpeg hat nichts geschrieben")
    return ziel


def spielvideos():
    """Match-Id -> Pfad zum Spielvideo, aus Spielvideos.csv."""
    if not os.path.exists(VIDEOS_CSV):
        return {}
    d = pd.read_csv(VIDEOS_CSV, dtype=str, keep_default_na=False)
    return {str(r["Match_Id"]).strip(): str(r["Datei"]).strip().strip('"').strip()
            for _, r in d.iterrows() if str(r["Datei"]).strip()}


def saison_von(match_id):
    """Die Saison eines erfassten Spiels - sie bestimmt den Videoordner."""
    w = pd.read_csv(WYGO_CSV, dtype=str, keep_default_na=False)
    w.columns = [c.strip() for c in w.columns]
    treffer = w[w["Match_Id"].str.strip() == str(match_id)]
    return str(treffer["Saison"].iat[0]).strip() if len(treffer) else ""


def tore_eines_spiels(match_id):
    """Die Tore eines schon erfassten Spiels, chronologisch, als Liste von
    Zeilen-Woerterbuechern mit der Zeilennummer in Tore.csv."""
    if not os.path.exists(TORE_CSV):
        return []
    d = pd.read_csv(TORE_CSV, dtype=str, keep_default_na=False)
    d.columns = [c.strip() for c in d.columns]
    teil = d[d["Match_Id"].str.strip() == str(match_id)].copy()
    if teil.empty:
        return []
    teil["_nr"] = pd.to_numeric(teil["Nr"], errors="coerce").fillna(0)
    teil = teil.sort_values("_nr")
    return [{"zeile": i, **{s: r[s] for s in TORE_SPALTEN if s in r}}
            for i, r in zip(teil.index, teil.to_dict("records"))]


def tore_datei_setzen(aenderungen):
    """Die Spalte Datei fuer einzelne Zeilen von Tore.csv neu setzen.

    Ueber das csv-Modul gelesen und geschrieben, damit Trennzeichen,
    Anfuehrungszeichen und Zeilenenden so bleiben, wie die Datei sie haelt -
    sonst sieht jede kleine Aenderung aus wie eine neue Datei.
    """
    import csv
    ende = zeilenende(TORE_CSV)
    with open(TORE_CSV, encoding="utf-8", newline="") as f:
        zeilen = list(csv.reader(f))
    kopf = zeilen[0]
    spalte = kopf.index("Datei")
    for nr, wert in aenderungen.items():
        zeilen[nr + 1][spalte] = wert       # +1 wegen der Kopfzeile
    with open(TORE_CSV, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, lineterminator=ende).writerows(zeilen)


def clips_nachschneiden(match_id, melden=None):
    """Fehlende Ausschnitte eines schon erfassten Spiels schneiden.

    Anders als beim laufenden Blatt landen sie gleich im Saisonordner - die
    Match-Id steht ja laengst fest. Geschnitten wird nur, wo eine Videozeit
    steht und noch kein Clip haengt.
    """
    video = spielvideos().get(str(match_id), "")
    if not video or not os.path.isfile(video):
        raise ValueError(f"Für Spiel {match_id} ist kein vorhandenes Video hinterlegt.")
    alle = tore_eines_spiels(match_id)
    if not alle:
        raise ValueError(f"Für Spiel {match_id} stehen keine Tore in Tore.csv.")
    ordner = os.path.join(video_ordner(saison_von(match_id)), str(match_id))
    os.makedirs(ordner, exist_ok=True)

    zaehler, aenderungen, fehler = {}, {}, []
    for t in alle:
        art = t["Art"].strip()
        zaehler[art] = zaehler.get(art, 0) + 1
        if t["Datei"].strip() or not t["Videozeit"].strip():
            continue
        stamm = t["Spieler"].strip() if art == "Tor" and t["Spieler"].strip() \
            else "Gegentor"
        stamm = "".join(z for z in stamm if z.isalnum() or z in " .-_") or "Tor"
        name, i = f"{stamm}{zaehler[art]}.mp4", 1
        while os.path.exists(os.path.join(ordner, name)):
            i += 1
            name = f"{stamm}{zaehler[art]}_{i}.mp4"
        if melden:
            melden(t, name)
        try:
            clip_schneiden(video, int(t["Videozeit"]), os.path.join(ordner, name))
            aenderungen[t["zeile"]] = f"{match_id}/{name}"
        except Exception as fehlgeschlagen:
            fehler.append(f"Nr {t['Nr']} ({art} {t['Zeit']}): {fehlgeschlagen}")
    if aenderungen:
        tore_datei_setzen(aenderungen)
    return aenderungen, fehler


def clip_aus_video(video, tor, dauer=CLIP_DAUER):
    """Den Ausschnitt zu einem Tor ins Zwischenlager schneiden.

    Der Name hier ist vorlaeufig - den endgueltigen bekommt die Datei erst
    beim Uebernehmen, wenn die Reihenfolge der Tore feststeht.
    """
    if not str(tor.get("videozeit", "")).strip():
        raise ValueError("Für dieses Tor ist keine Videozeit eingetragen.")
    os.makedirs(CLIPS, exist_ok=True)
    stamm = f"{tor['art']}_{tor['videozeit']}s"
    ziel, i = f"{stamm}.mp4", 1
    while os.path.exists(os.path.join(CLIPS, ziel)):
        i += 1
        ziel = f"{stamm}_{i}.mp4"
    clip_schneiden(video, int(tor["videozeit"]), os.path.join(CLIPS, ziel), dauer)
    return ziel


def video_ordner(saison):
    """'26/27' -> 'tore_26-27' - derselbe Name, den das Dashboard sucht."""
    return os.path.join(PROJEKT, "tore_" + str(saison).strip().replace("/", "-"))


def clips_uebernehmen(saison, match_id, tore):
    """Die zwischengelagerten Clips an ihren Platz legen.

    Setzt in jedem Toreintrag "datei" auf den Eintrag, den Tore.csv braucht -
    <Match-Id>/<Name>, immer mit Schraegstrich, so sucht ihn das Dashboard.
    """
    ordner = os.path.join(video_ordner(saison), str(match_id))
    for tor, name in clip_namen(tore):
        quelle = os.path.join(CLIPS, tor["datei"])
        if not os.path.exists(quelle):
            continue
        os.makedirs(ordner, exist_ok=True)
        stamm, endung = os.path.splitext(name)
        i = 1
        while os.path.exists(os.path.join(ordner, name)):
            i += 1
            name = f"{stamm}_{i}{endung}"
        shutil.move(quelle, os.path.join(ordner, name))
        tor["datei"] = f"{match_id}/{name}"


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


def tor_kontrollen(blatt, tore, abschluesse, video=""):
    """Querproben fuer Tore.csv und Gegner_Abschluesse.csv.

    Gibt eine Liste (ok, Text) zurueck - dieselbe Form wie kontrollen().
    """
    eigene, gegen = resultat(blatt)
    raus = []

    def pruefe(text, ok, hinweis=""):
        raus.append((bool(ok), text if ok else f"{text} — {hinweis}"))

    erzielt = sum(1 for t in tore if t["art"] == "Tor")
    kassiert = sum(1 for t in tore if t["art"] == "Gegentor")
    pruefe(f"{eigene} Tore erfasst", erzielt == eigene, f"erfasst sind {erzielt}")
    pruefe(f"{gegen} Gegentore erfasst", kassiert == gegen, f"erfasst sind {kassiert}")

    ohne_zeit = [t for t in tore if int(t["sek"]) <= 0]
    pruefe("Jedes Tor hat eine Zeit", not ohne_zeit,
           f"{len(ohne_zeit)} stehen noch auf 0:00")
    doppelt = len(tore) - len({(t["hz"], t["sek"], t["art"]) for t in tore})
    pruefe("Keine zwei Tore zur selben Zeit", doppelt == 0, f"{doppelt} doppelt")
    ohne_kat = [t for t in tore if not t["kategorie"].strip()]
    pruefe("Jedes Tor hat eine Kategorie", not ohne_kat,
           f"{len(ohne_kat)} ohne — das Dashboard zeigt sie dann unter 'ohne Angabe'")

    # Die Videozeit nur einfordern, wenn ueberhaupt ein Spielvideo hinterlegt ist
    if str(video).strip():
        ohne_vid = [t for t in tore if str(t.get("videozeit", "")).strip() == ""]
        pruefe("Jedes Tor hat eine Videozeit", not ohne_vid,
               f"{len(ohne_vid)} ohne — daraus lässt sich später kein Ausschnitt "
               f"schneiden")
        zeiten = sorted(int(t["videozeit"]) for t in tore
                        if str(t.get("videozeit", "")).strip() != "")
        pruefe("Videozeiten laufen in derselben Reihenfolge wie die Uhr",
               zeiten == [int(t["videozeit"]) for t in tore_geordnet(tore)
                          if str(t.get("videozeit", "")).strip() != ""],
               "ein Tor liegt im Video vor einem, das laut Uhr früher fiel")

    # Die Schuetzen muessen zu den Strichen auf dem Blatt passen
    je_spieler = {}
    for t in tore:
        if t["art"] == "Tor":
            je_spieler[t["spieler"]] = je_spieler.get(t["spieler"], 0) + 1
    falsch = [f"{n}: Blatt {z['T']}, erfasst {je_spieler.get(n, 0)}"
              for n, z in blatt.items()
              if spielt(z["rolle"]) and z["T"] != je_spieler.get(n, 0)]
    pruefe("Tore je Schütze passen zum Blatt", not falsch, "; ".join(falsch))

    # Die gehaltenen Schuesse zusammen = Paraden des Torhueters. Faellt die
    # Summe kleiner aus, fehlen Schuesse aus Unterzahl - das ist in Ordnung.
    hueter = [z for z in blatt.values() if z["rolle"] == "T"]
    paraden = hueter[0]["Block"] if hueter else 0
    gehalten = sum(w[ABSCHLUSS_ARTEN[0]] for w in abschluesse.values())
    pruefe(f"Gehaltene Gegnerschüsse ≤ {paraden} Paraden des Torhüters",
           gehalten <= paraden,
           f"erfasst sind {gehalten} — Gegentore gehören nicht in diesen Zähler")
    return raus


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


def _feld(wert):
    """Ein Wert fuer die CSV. Kategorien und Videoadressen duerfen ein Komma
    enthalten - dann gehoert das Feld in Anfuehrungszeichen."""
    text = str(wert)
    if any(z in text for z in ',"\n\r'):
        return '"' + text.replace('"', '""') + '"'
    return text


def anhaengen(pfad, zeilen, spalten):
    """Zeilen an eine CSV anhaengen, ohne den bestehenden Inhalt anzufassen."""
    ende = zeilenende(pfad) if os.path.exists(pfad) else "\r\n"
    neu = "".join(",".join(_feld(v) for v in z) + ende for z in zeilen)
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


def schreiben(kopf, blatt, datum_text, linien=None, tore=None, abschluesse=None):
    """Alle vier CSVs ergaenzen. Wirft, wenn eine Kopfzeile nicht passt.

    Reihenfolge mit Absicht: zuerst die Clips an ihren Platz, denn erst
    dadurch stehen die Dateinamen fuer Tore.csv fest.
    """
    tabelle = auswertung(blatt, kopf["match_id"], linien)
    if tore:
        clips_uebernehmen(kopf["saison"], kopf["match_id"], tore)
    anhaengen(saison_datei(kopf["saison"]), tabelle.values.tolist(), SPIELER_SPALTEN)
    anhaengen(WYGO_CSV, [wygo_zeile(kopf, blatt, datum_text)], WYGO_SPALTEN)
    if tore:
        anhaengen(TORE_CSV, tore_zeilen(kopf["match_id"], tore), TORE_SPALTEN)
    zeilen = gegner_zeilen(kopf["match_id"], abschluesse or {})
    if zeilen:
        anhaengen(GEGNER_CSV, zeilen, GEGNER_SPALTEN)
    if str(kopf.get("video", "")).strip():
        anhaengen(VIDEOS_CSV, [[kopf["match_id"], kopf["video"].strip()]],
                  VIDEO_SPALTEN)
    return tabelle
