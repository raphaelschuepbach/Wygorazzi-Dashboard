# -*- coding: utf-8 -*-
"""Spieler verfolgen und Laufdistanz in Metern messen (Match 104).

Die Kamera steht fest, darum genuegt eine einmal bestimmte Umrechnung
Bild -> Feld. Gemessen wird der Fusspunkt, weil nur der auf dem Boden liegt.
"""
import argparse
import os
import sys

import cv2
import numpy as np
import pandas as pd
from ultralytics import YOLO

sys.stdout.reconfigure(encoding="utf-8")

# ACHTUNG: Die Bildpunkte unten gelten nur fuer die Kameraposition von Match 104.
# Steht die Kamera anders, muessen die Ecken auf einem Standbild neu markiert werden.
VIDEO = "C:/Users/rapha/Downloads/Video_2026-09-13_12-52-24.mp4"
BREITE, TIEFE = 14.0, 24.0          # Feldmass in Metern, vom User gemessen

# Bildpunkte der Markierung: 4 Ecken schwarz, 2 Mittellinienenden orange
BILD = np.float32([[682, 87], [1018, 104], [848, 714], [25, 292], [513, 146], [1006, 212]])
FELD = np.float32([[0, TIEFE], [BREITE, TIEFE], [BREITE, 0], [0, 0],
                   [0, TIEFE / 2], [BREITE, TIEFE / 2]])

RAND = 1.0          # m Toleranz, der Fusspunkt streut um die Bande
MAX_TEMPO = 11.0    # m/s - darueber ist es ein Sprung der Verfolgung, keine Laufleistung


def umrechnung():
    H, _ = cv2.findHomography(BILD, FELD, 0)
    return H


def auf_feld(xy):
    """Punkte im Feld? Haelt Bank und Zuschauer draussen."""
    return ((xy[:, 0] > -RAND) & (xy[:, 0] < BREITE + RAND) &
            (xy[:, 1] > -RAND) & (xy[:, 1] < TIEFE + RAND))


def trikotfarbe(bild, kasten):
    """Medianfarbe des Oberkoerpers - trennt die Mannschaften."""
    x1, y1, x2, y2 = [int(v) for v in kasten]
    h = y2 - y1
    y1, y2 = y1 + int(0.15 * h), y1 + int(0.55 * h)      # Kopf und Beine weglassen
    b = (x2 - x1) // 4
    stueck = bild[max(y1, 0):max(y2, y1 + 1), x1 + b:max(x2 - b, x1 + b + 1)]
    if stueck.size == 0:
        return None
    hsv = cv2.cvtColor(stueck, cv2.COLOR_BGR2HSV)
    return np.median(hsv.reshape(-1, 3), axis=0)


def mannschaft(h, sat, v):
    """Wygorazzi spielt in hellem Rot-Orange, der Gegner dunkel - das trennt sauber."""
    if sat > 110 and (h < 25 or h > 160):
        return "Wygorazzi"
    if v < 65:
        return "Gegner"
    return "unklar"


def glaetten(p, fenster=5):
    """Laufender Median gegen das Zittern der Kaesten.

    Ohne das zaehlt jedes Pixelrauschen als Laufweg und die Distanz waechst kuenstlich.
    """
    if len(p) < fenster:
        return p
    s = pd.DataFrame(p).rolling(fenster, center=True, min_periods=1).median()
    return s.to_numpy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="20:00", help="Videozeit mm:ss")
    ap.add_argument("--dauer", type=int, default=180, help="Sekunden")
    ap.add_argument("--schritt", type=int, default=1, help="jedes n-te Bild")
    ap.add_argument("--overlay", default="overlay.mp4")
    ap.add_argument("--tracker", default="bytetrack_halle.yaml")
    ap.add_argument("--video", default=VIDEO, help="nur mit passender Feldmarkierung")
    a = ap.parse_args()

    m, s = a.start.split(":")
    start_s = int(m) * 60 + int(s)

    H = umrechnung()
    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(start_s * fps))
    takt = fps / a.schritt                      # ausgewertete Bilder je Sekunde
    n_bilder = int(a.dauer * takt)

    model = YOLO("yolo11m.pt")
    ecken_bild = BILD[:4].astype(np.int32)

    schreiber = None
    if a.overlay:
        schreiber = cv2.VideoWriter(a.overlay, cv2.VideoWriter_fourcc(*"mp4v"),
                                    takt, (1280, 720))

    spuren = {}         # id -> dict(punkte, zeiten, farben)
    gelesen = 0
    while gelesen < n_bilder:
        for _ in range(a.schritt):
            ok, frame = cap.read()
            if not ok:
                break
        if not ok:
            break
        t = gelesen / takt

        # Ultralytics bringt ByteTrack selbst mit, persist haelt die Nummern ueber Bilder
        r = model.track(frame, classes=[0], conf=0.08, imgsz=1280, persist=True,
                        tracker=a.tracker, verbose=False, device=0)[0]
        ids = None if r.boxes.id is None else r.boxes.id.int().cpu().numpy()

        if ids is not None and len(ids):
            kaesten = r.boxes.xyxy.cpu().numpy()
            fuss = np.stack([(kaesten[:, 0] + kaesten[:, 2]) / 2, kaesten[:, 3]], axis=1)
            feld = cv2.perspectiveTransform(fuss.reshape(-1, 1, 2).astype(np.float32), H).reshape(-1, 2)
            drin = auf_feld(feld)

            for i in np.where(drin)[0]:
                tid = int(ids[i])
                sp = spuren.setdefault(tid, {"p": [], "t": [], "f": []})
                sp["p"].append(feld[i])
                sp["t"].append(t)
                c = trikotfarbe(frame, kaesten[i])
                if c is not None:
                    sp["f"].append(c)

            if schreiber:
                cv2.polylines(frame, [ecken_bild], True, (255, 255, 0), 2)
                for i in range(len(ids)):
                    x1, y1, x2, y2 = [int(v) for v in kaesten[i]]
                    gut = bool(drin[i])
                    farbe = (0, 255, 0) if gut else (90, 90, 90)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), farbe, 2 if gut else 1)
                    if gut:
                        cv2.putText(frame, str(int(ids[i])), (x1, y1 - 5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        if schreiber:
            schreiber.write(frame)
        gelesen += 1
        if gelesen % 100 == 0:
            print(f"   {gelesen}/{n_bilder} Bilder", flush=True)

    cap.release()
    if schreiber:
        schreiber.release()

    # ---- Auswertung je Spur ----
    zeilen = []
    alle_punkte = []
    for tid, sp in spuren.items():
        p = np.array(sp["p"])
        t = np.array(sp["t"])
        if len(p) < int(takt):          # unter einer Sekunde: Fehldetektion
            continue
        pg = glaetten(p)
        d = np.linalg.norm(np.diff(pg, axis=0), axis=1)
        dt = np.diff(t)
        tempo = np.divide(d, dt, out=np.zeros_like(d), where=dt > 0)
        echt = tempo <= MAX_TEMPO        # Spruenge der Verfolgung nicht mitzaehlen
        farbe = np.median(np.array(sp["f"]), axis=0) if sp["f"] else [0, 0, 0]
        zeilen.append({
            "Spur": tid,
            "Sekunden": round(float(t[-1] - t[0]), 1),
            "Messpunkte": len(p),
            "Distanz_m": round(float(d[echt].sum()), 1),
            "Tempo_max_ms": round(float(np.percentile(tempo[echt], 95)) if echt.any() else 0, 1),
            "Team": mannschaft(*farbe),
            "H": round(float(farbe[0]), 0), "S": round(float(farbe[1]), 0), "V": round(float(farbe[2]), 0),
        })
        alle_punkte.append(pg)

    df = pd.DataFrame(zeilen).sort_values("Distanz_m", ascending=False)
    df.to_csv("spuren.csv", index=False)
    print(f"\n{len(df)} Spuren ueber 1 s, {a.dauer}s Video ab {a.start}")
    print(df.head(25).to_string(index=False))
    print("\nSumme je Mannschaft:")
    print(df.groupby("Team").agg(Spuren=("Spur", "count"), Distanz_m=("Distanz_m", "sum"),
                                 Sekunden=("Sekunden", "sum")).to_string())

    # Heatmap: wo auf dem Feld gespielt wurde
    if alle_punkte:
        pts = np.vstack(alle_punkte)
        gitter, _, _ = np.histogram2d(pts[:, 0], pts[:, 1], bins=[28, 48],
                                      range=[[0, BREITE], [0, TIEFE]])
        weich = cv2.GaussianBlur(gitter.T, (0, 0), 1.5)
        bild = cv2.applyColorMap(
            cv2.normalize(weich, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8),
            cv2.COLORMAP_INFERNO)
        bild = cv2.resize(bild, (28 * 14, 48 * 14), interpolation=cv2.INTER_LANCZOS4)
        bild = cv2.flip(bild, 0)              # Tiefe 0 unten, wie man das Feld anschaut
        cv2.imwrite("heatmap.png", bild)
        print("Heatmap: " + os.path.abspath("heatmap.png"))

    if schreiber:
        print(f"\nKontrollvideo: {os.path.abspath(a.overlay)}")


if __name__ == "__main__":
    main()
