"""Kleines Hilfswerkzeug: jedem eigenen Tor eine Kategorie geben.

Einmalig gedacht - laeuft neben dem Dashboard und schreibt direkt in die
Spalte "Kategorie" von Tore.csv, dieselbe, die bei den Gegentoren schon
gefuellt ist.

    streamlit run Kategorien_Tore.py

Gespeichert wird sofort bei jedem Klick, einen Knopf dafuer braucht es nicht.
"""

import glob
import os
import shutil
from datetime import datetime

import pandas as pd
import streamlit as st

TORE_CSV = "Tore.csv"
SPIELE_CSV = "Statistik_Wygo.csv"

# Kategorien fuer unsere Tore - eigene Liste, nicht die der Gegentore.
# Weitere traegst du im Werkzeug unter "Kategorie hinzufuegen" nach.
VORSCHLAEGE = [
    "Freistoss",
    "Powerplay",
    "Schuss eigene Hälfte",
    "Schuss gegner Hälfte",
    "Ballgewinn Konter",
    "Gegner Überlaufen gegner Hälfte",
    "Gegner Überlaufen eigene Hälfte",
    "Zuteilungsfehler Gegner",
]


st.set_page_config(page_title="Tore kategorisieren", layout="centered")


def lade_tore():
    """Alles als Text lesen, damit die Datei beim Schreiben gleich bleibt."""
    return pd.read_csv(TORE_CSV, dtype=str, keep_default_na=False, encoding="utf-8")


def lade_spielnamen():
    """Match_Id -> Gegnername, nur fuer die Beschriftung."""
    try:
        s = pd.read_csv(SPIELE_CSV, dtype=str, keep_default_na=False, encoding="utf-8")
    except Exception:
        return {}
    s.columns = [c.strip() for c in s.columns]
    namen = {}
    for _, r in s.iterrows():
        mid = str(r.get("Match_Id", "")).strip()
        if mid:
            namen[mid] = str(r.get("Gegner", "")).strip() or f"Spiel {mid}"
    return namen


def clip_pfad(datei):
    """Dieselbe Suche wie im Dashboard: Clip in einem der tore_*-Ordner."""
    datei = str(datei or "").strip()
    if not datei:
        return ""
    for ordner in sorted(o for o in glob.glob("tore_*") if os.path.isdir(o)):
        pfad = os.path.join(ordner, datei)
        if os.path.isfile(pfad):
            return pfad
    return ""


def sichern_einmal():
    """Eine Kopie je Sitzung, bevor zum ersten Mal geschrieben wird."""
    if st.session_state.get("gesichert"):
        return
    ziel = f"Tore_backup_{datetime.now():%Y%m%d_%H%M%S}.csv"
    shutil.copy2(TORE_CSV, ziel)
    st.session_state["gesichert"] = ziel


def schreibe_kategorie(nr, match_id, wert):
    """Eine Zelle setzen und die Datei neu schreiben. Gibt zurueck, wie
    viele Zeilen getroffen wurden - 1 ist der Normalfall."""
    df = lade_tore()
    # Art mitpruefen: Nr wird je Spiel fuer Tore und Gegentore gemeinsam
    # vergeben, ohne diesen Riegel kann eine Gegentor-Zeile getroffen werden.
    treffer = ((df["Nr"].astype(str).str.strip() == str(nr))
               & (df["Match_Id"].astype(str).str.strip() == str(match_id))
               & (df["Art"].astype(str).str.strip() == "Tor"))
    df.loc[treffer, "Kategorie"] = wert or ""
    df.to_csv(TORE_CSV, index=False, encoding="utf-8", lineterminator="\n")
    return int(treffer.sum())


def speichern(nr, match_id, wert):
    """Callback beim Klick - erst die Sicherung, dann schreiben."""
    sichern_einmal()
    schreibe_kategorie(nr, match_id, wert)


def gewaehlt(nr, match_id):
    """Wert aus dem Pills-Widget holen - der Key traegt Tor- und Spielnummer."""
    return st.session_state.get(f"kat_{match_id}_{nr}")


# ---------------------------------------------------------------- Oberflaeche

tore = lade_tore()
eigene = tore[tore["Art"].str.strip() == "Tor"].copy()
spielnamen = lade_spielnamen()

# Knopfreihe: die Vorschlaege, dazu was bei unseren Toren schon steht und was
# in dieser Sitzung dazugekommen ist. Die Gegentor-Kategorien bleiben draussen.
aus_datei = sorted({k.strip() for k in eigene["Kategorie"] if k.strip()})
st.session_state.setdefault("eigene_kategorien", [])
kategorien = list(dict.fromkeys(VORSCHLAEGE + aus_datei
                                + st.session_state["eigene_kategorien"]))

fertig = int((eigene["Kategorie"].str.strip() != "").sum())
st.title("Tore kategorisieren")
st.progress(fertig / len(eigene) if len(eigene) else 0,
            text=f"{fertig} von {len(eigene)} Toren zugeordnet")

with st.expander("Kategorie hinzufügen", expanded=False):
    neu = st.text_input("Name der neuen Kategorie", key="neue_kat",
                        placeholder="z.B. Konter nach Balleroberung")
    if st.button("hinzufügen", disabled=not neu.strip()):
        name = neu.strip()
        if name not in kategorien:
            st.session_state["eigene_kategorien"].append(name)
        st.rerun()
    st.caption("Kein Komma im Namen verwenden – die Datei ist kommagetrennt.")

offen_nur = st.toggle("nur noch offene Tore zeigen", value=False)
videos = st.toggle("Videos anzeigen", value=True)

zeigen = eigene[eigene["Kategorie"].str.strip() == ""] if offen_nur else eigene
if zeigen.empty:
    st.success("Alle Tore sind zugeordnet.")

for _, r in zeigen.iterrows():
    nr, mid = str(r["Nr"]).strip(), str(r["Match_Id"]).strip()
    kopf = (f"**{nr}** · {spielnamen.get(mid, 'Spiel ' + mid)} · "
            f"HZ{r['Halbzeit']} {r['Zeit']} · {r['Spieler']}"
            + (f" (Assist {r['Assist']})" if str(r["Assist"]).strip() else "")
            + (f" · Linie {r['Linie']}" if str(r["Linie"]).strip() else ""))
    with st.container(border=True):
        st.markdown(kopf)
        pfad = clip_pfad(r["Datei"])
        if videos and pfad:
            st.video(pfad)
        aktuell = str(r["Kategorie"]).strip() or None
        st.pills("Kategorie", kategorien, default=aktuell,
                 selection_mode="single", key=f"kat_{mid}_{nr}",
                 label_visibility="collapsed",
                 on_change=lambda n=nr, m=mid: speichern(n, m, gewaehlt(n, m)))

if st.session_state.get("gesichert"):
    st.caption(f"Sicherungskopie dieser Sitzung: {st.session_state['gesichert']}")
