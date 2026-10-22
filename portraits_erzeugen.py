# -*- coding: utf-8 -*-
"""Erzeugt die freigestellten Spielerportraits aus dem Mannschaftsfoto.

Einmaliges Werkzeug - das Dashboard selbst braucht weder rembg noch scipy.
Benoetigt: pip install "rembg[cpu]" scipy

Neuen Spieler ergaenzen: Kopfmitte in KOEPFE eintragen (Koordinaten im
Originalfoto) und den Namen in ZUORDNUNG setzen, dann das Skript laufen lassen.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage

sys.stdout.reconfigure(encoding="utf-8")

MANNSCHAFTSFOTO = "C:/Users/rapha/OneDrive/Desktop/DSC_8490-Kopie.jpg"
ZIELORDNER = "bilder"

# Kopfmitte im Originalfoto (3881x2074), nummeriert wie der Kontaktbogen
KOEPFE = {
    1: (453, 517), 2: (893, 556), 3: (1268, 530), 4: (1656, 530), 5: (2005, 466),
    6: (2342, 543), 7: (2704, 582), 8: (3066, 556), 9: (3441, 582),
    10: (1107, 828), 11: (1475, 854), 12: (1837, 841), 13: (2245, 862),
    14: (2548, 866), 15: (2938, 862),
}

# Nummer aus dem Kontaktbogen -> Name wie in den Spieler-CSVs
ZUORDNUNG = {
    2: "M.Nyffenegger", 4: "L.Leuenberger", 5: "C.Mühle", 6: "R.Moser",
    7: "R.Schüpbach", 8: "N.Nyffenegger", 10: "B.Lüthi", 12: "B.Jordi",
    13: "C.Loosli", 14: "D.Geissbühler", 15: "M.Geissbühler",
}

AUSSCHNITT = 300      # Kantenlaenge im Originalfoto
KOPF_OBEN = 0.42      # Kopfmitte sitzt auf dieser Hoehe des Ausschnitts
AUSGABE = 320         # Kantenlaenge der fertigen PNG
RANDANTEIL = 0.06


def ohne_trikotgelb(bild):
    """Schulterstuecke der Hinterleute entfernen.

    Das Trikotgelb ist mit Saettigung ~225 klar von blondem Haar (<=160)
    unterscheidbar, deshalb wird nur im oberen Bildteil danach gesucht.
    """
    a = np.array(bild)
    hsv = np.array(Image.fromarray(a[:, :, :3], "RGB").convert("HSV"))
    hoehe = a.shape[0]
    oben = np.zeros(a.shape[:2], bool)
    oben[: int(hoehe * 0.45), :] = True
    gelb = oben & (hsv[:, :, 0] > 20) & (hsv[:, :, 0] < 65) & (hsv[:, :, 1] > 180)
    a[:, :, 3] = np.where(gelb, 0, a[:, :, 3])
    return Image.fromarray(a)


def nur_kopfteil(bild):
    """Nur die zusammenhaengende Flaeche behalten, die den Kopf enthaelt."""
    a = np.array(bild)
    maske = a[:, :, 3] > 128
    teile, anzahl = ndimage.label(maske)
    if anzahl <= 1:
        return bild
    h, w = maske.shape
    fenster = teile[int(h * 0.10):int(h * 0.60), int(w * 0.38):int(w * 0.62)]
    ids, zaehler = np.unique(fenster[fenster > 0], return_counts=True)
    if len(ids) == 0:
        return bild
    ziel = int(ids[np.argmax(zaehler)])
    a[:, :, 3] = np.where(teile == ziel, a[:, :, 3], 0)
    return Image.fromarray(a)


def loecher_schliessen(bild):
    """Innenliegende Luecken fuellen und die Farbe vom naechsten Nachbarn holen."""
    a = np.array(bild)
    maske = a[:, :, 3] > 128
    gefuellt = ndimage.binary_fill_holes(maske)
    neu = gefuellt & ~maske
    if not neu.any():
        return bild
    # Farbe der naechstgelegenen gueltigen Pixel uebernehmen, sonst entsteht
    # aus dem Loch ein schwarzer Fleck
    _, idx = ndimage.distance_transform_edt(~maske, return_indices=True)
    for kanal in range(3):
        a[:, :, kanal] = np.where(neu, a[:, :, kanal][idx[0], idx[1]], a[:, :, kanal])
    a[:, :, 3] = np.where(gefuellt, 255, a[:, :, 3])
    return Image.fromarray(a)


def zentrieren(bild):
    """Auf den sichtbaren Inhalt beschneiden und mittig auf Zielgroesse setzen."""
    kasten = bild.split()[3].point(lambda v: 255 if v > 128 else 0).getbbox()
    if kasten is None:
        return bild
    inhalt = bild.crop(kasten)
    platz = int(AUSGABE * (1 - 2 * RANDANTEIL))
    faktor = min(platz / inhalt.width, platz / inhalt.height)
    inhalt = inhalt.resize((max(1, int(inhalt.width * faktor)),
                            max(1, int(inhalt.height * faktor))), Image.LANCZOS)
    leinwand = Image.new("RGBA", (AUSGABE, AUSGABE), (0, 0, 0, 0))
    leinwand.alpha_composite(inhalt, ((AUSGABE - inhalt.width) // 2,
                                      (AUSGABE - inhalt.height) // 2))
    return leinwand


def main():
    from rembg import new_session, remove

    foto = ImageOps.exif_transpose(Image.open(MANNSCHAFTSFOTO))
    sitzung = new_session("u2net_human_seg")
    os.makedirs(ZIELORDNER, exist_ok=True)

    for nummer, name in sorted(ZUORDNUNG.items()):
        cx, cy = KOEPFE[nummer]
        halb = AUSSCHNITT // 2
        links = max(0, min(cx - halb, foto.width - AUSSCHNITT))
        oben = max(0, min(int(cy - AUSSCHNITT * KOPF_OBEN), foto.height - AUSSCHNITT))
        teil = foto.crop((links, oben, links + AUSSCHNITT, oben + AUSSCHNITT))

        bild = remove(teil, session=sitzung, post_process_mask=True).convert("RGBA")
        bild = ohne_trikotgelb(bild)
        bild = nur_kopfteil(bild)
        bild = loecher_schliessen(bild)
        bild = zentrieren(bild)

        pfad = os.path.join(ZIELORDNER, f"{name}.png")
        bild.save(pfad)
        sichtbar = (np.array(bild)[:, :, 3] > 128).mean() * 100
        print(f"   {name:18} -> {pfad}  ({sichtbar:.0f}% sichtbar)")

    print(f"{len(ZUORDNUNG)} Portraits erzeugt")


if __name__ == "__main__":
    main()
