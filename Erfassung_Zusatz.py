"""Nacherfassung: Gegner-Abschluesse je Linie und Ballverluste je Spieler.

Zwei Dinge, die auf dem Matchblatt nicht vorgesehen waren:

  1. Wie viele Abschluesse der Gegner hatte, waehrend eine Linie auf dem Feld
     war - vom Torhueter gehalten und daneben. Die Gegentore und die von uns
     geblockten Versuche stehen schon in Tore.csv und in der Spalte "Block";
     zusammen ergibt das Corsi gegen. Die Tore gehoeren deshalb ausdruecklich
     NICHT in den Zaehler "aufs Tor", sonst zaehlen sie doppelt.
  2. Ballverluste und Fehlpaesse je Spieler.

    streamlit run Erfassung_Zusatz.py

Gespeichert wird bei jedem Klick, einen Knopf dafuer braucht es nicht.
"""

import os
import shutil
from datetime import datetime

import pandas as pd
import streamlit as st

SPIELE_CSV = "Statistik_Wygo.csv"
TORE_CSV = "Tore.csv"
GEGNER_CSV = "Gegner_Abschluesse.csv"
LINIEN = ["1", "2", "3"]
ZAEHLER = ["Gegner aufs Tor gehalten", "Gegner daneben"]
GEGNER_SPALTEN = ["Match_Id", "Linie"] + ZAEHLER

st.set_page_config(page_title="Nacherfassung", layout="centered")


# ------------------------------------------------------------------ Dateien

def saison_datei(saison):
    return f"Spieler_Statistik_{saison.replace('/', '_')}.csv"


def lade(pfad):
    return pd.read_csv(pfad, dtype=str, keep_default_na=False, encoding="utf-8")


def spiele():
    """Match_Id -> (Saison, Beschriftung), neustes Spiel zuoberst."""
    s = lade(SPIELE_CSV)
    s.columns = [c.strip() for c in s.columns]
    raus = {}
    for _, r in s.iterrows():
        mid = str(r.get("Match_Id", "")).strip()
        if mid:
            raus[mid] = (str(r.get("Saison", "")).strip(),
                         f"{mid} - {r.get('Datum', '')} - {r.get('Gegner', '')} "
                         f"({r.get('Tore Wygorazzi', '')}:{r.get('Tore Gegner', '')})")
    return dict(reversed(list(raus.items())))


def zeilenende(pfad):
    """Die Datei behaelt ihre Zeilenenden - sonst sieht jede Aenderung riesig aus."""
    with open(pfad, encoding="utf-8", newline="") as f:
        return "\r\n" if "\r\n" in f.read(4096) else "\n"


def schreibe(df, pfad):
    ende = zeilenende(pfad) if os.path.exists(pfad) else "\n"
    df.to_csv(pfad, index=False, encoding="utf-8", lineterminator=ende)


def sichern_einmal(pfad):
    """Eine Kopie je Datei und Sitzung, bevor zum ersten Mal geschrieben wird."""
    merker = st.session_state.setdefault("gesichert", {})
    if pfad in merker or not os.path.exists(pfad):
        return
    name, endung = os.path.splitext(pfad)
    ziel = f"{name}_backup_{datetime.now():%Y%m%d_%H%M%S}{endung}"
    shutil.copy2(pfad, ziel)
    merker[pfad] = ziel


# ------------------------------------------------------- Gegner-Abschluesse

def lade_gegner():
    if not os.path.exists(GEGNER_CSV):
        return pd.DataFrame(columns=GEGNER_SPALTEN)
    d = lade(GEGNER_CSV)
    # Fehlende Spalten ergaenzen: eine aeltere oder von Hand bearbeitete Datei
    # soll die Seite nicht abstuerzen lassen.
    for spalte in GEGNER_SPALTEN:
        if spalte not in d.columns:
            d[spalte] = "0"
    return d


def gegner_wert(d, match_id, linie, spalte):
    if d.empty:
        return 0
    treffer = d[(d["Match_Id"].str.strip() == str(match_id))
                & (d["Linie"].str.strip() == str(linie))]
    if treffer.empty:
        return 0
    return int(pd.to_numeric(treffer[spalte], errors="coerce").fillna(0).iloc[0])


def gegner_setzen(match_id, linie, spalte, wert):
    """Eine Zelle setzen, die Zeile bei Bedarf anlegen. Nie unter null."""
    sichern_einmal(GEGNER_CSV)
    d = lade_gegner()
    wert = max(0, int(wert))
    passt = (pd.Series([False] * len(d)) if d.empty else
             ((d["Match_Id"].str.strip() == str(match_id))
              & (d["Linie"].str.strip() == str(linie))))
    if len(d) and passt.any():
        d.loc[passt.values, spalte] = str(wert)
    else:
        neu = {"Match_Id": str(match_id), "Linie": str(linie),
               **{s: "0" for s in ZAEHLER}}
        neu[spalte] = str(wert)
        d = pd.concat([d, pd.DataFrame([neu])], ignore_index=True)
    d = d[GEGNER_SPALTEN].sort_values(["Match_Id", "Linie"])
    schreibe(d, GEGNER_CSV)


# ----------------------------------------------------------- Ballverluste

def ballverlust_setzen(saison, match_id, name, wert):
    pfad = saison_datei(saison)
    sichern_einmal(pfad)
    d = lade(pfad)
    if "Ballverlust" not in d.columns:
        d["Ballverlust"] = "0"
    treffer = ((d["Match_Id"].str.strip() == str(match_id))
               & (d["Name"].str.strip() == str(name)))
    d.loc[treffer, "Ballverlust"] = str(max(0, int(wert)))
    schreibe(d, pfad)


# ------------------------------------------------------------ Oberflaeche

def zaehler_zeile(beschriftung, wert, schluessel, setzen):
    """Eine Zeile: Text, minus, Zahl, plus. Jeder Klick speichert sofort."""
    links, weg, zahl, hin = st.columns([5, 1, 1, 1], vertical_alignment="center")
    links.markdown(beschriftung, unsafe_allow_html=True)
    weg.button("−", key=f"{schluessel}_minus", width="stretch",
               disabled=wert <= 0, on_click=setzen, args=(wert - 1,))
    zahl.markdown(
        f"<div style='text-align:center; font-weight:700; font-size:18px'>{wert}</div>",
        unsafe_allow_html=True)
    hin.button("+", key=f"{schluessel}_plus", width="stretch",
               on_click=setzen, args=(wert + 1,))


liste = spiele()
if not liste:
    st.error(f"{SPIELE_CSV} enthaelt keine Spiele.")
    st.stop()

st.title("Nacherfassung")
mid = st.selectbox("Spiel", list(liste), format_func=lambda m: liste[m][1])
saison = liste[mid][0]
pfad_spieler = saison_datei(saison)

# ---- Abschnitt 1: Gegner-Abschluesse je Linie
st.header("Gegner-Abschlüsse je Linie")
st.caption("Nur die gehaltenen Schüsse und die daneben. Gegentore **nicht** "
           "mitzählen — die stehen schon in Tore.csv, genauso wie die von uns "
           "geblockten Versuche in der Spalte Block.")

# eigene Zeile fuer gemischte Formationen - welche beiden Linien, waehlst du hier
erste = st.session_state.get("misch_a", "1")
zweite = st.session_state.get("misch_b", "3")
misch = f"{erste}+{zweite}"

gegner = lade_gegner()
for linie in LINIEN:
    with st.container(border=True):
        st.markdown(f"**Linie {linie}**")
        for spalte in ZAEHLER:
            zaehler_zeile(
                spalte, gegner_wert(gegner, mid, linie, spalte),
                f"g_{mid}_{linie}_{spalte}",
                lambda w, l=linie, s=spalte: gegner_setzen(mid, l, s, w))

with st.container(border=True):
    st.markdown("**gemischte Formation**")
    a, b = st.columns(2)
    a.selectbox("erste Linie", LINIEN, key="misch_a")
    b.selectbox("zweite Linie", LINIEN, key="misch_b")
    if erste == zweite:
        st.caption("Zwei verschiedene Linien wählen.")
    else:
        for spalte in ZAEHLER:
            zaehler_zeile(
                spalte, gegner_wert(gegner, mid, misch, spalte),
                f"g_{mid}_{misch}_{spalte}",
                lambda w, l=misch, s=spalte: gegner_setzen(mid, l, s, w))

# Gegenprobe: die gehaltenen Schuesse zusammen = Paraden des Torhueters.
# Die Gegentore kommen aus Tore.csv dazu und stehen hier nur zur Kontrolle.
spieler = lade(pfad_spieler)
dieses = spieler[spieler["Match_Id"].str.strip() == str(mid)]
gespielt = dieses[dieses["Gespielt"].str.strip() == "Ja"]
paraden = int(pd.to_numeric(gespielt.loc[gespielt["Linie"].str.strip() == "0", "Block"],
                            errors="coerce").fillna(0).sum())
tore = lade(TORE_CSV)
gegentore = len(tore[(tore["Match_Id"].str.strip() == str(mid))
                     & (tore["Art"].str.strip() == "Gegentor")])
aktuell = lade_gegner()
ist = sum(gegner_wert(aktuell, mid, l, ZAEHLER[0]) for l in LINIEN + [misch])
rest = paraden - ist
if rest == 0:
    st.success(f"Alle {paraden} Paraden sind einer Linie zugeordnet.")
elif rest > 0:
    # In Unterzahl steht keine Linie als Einheit auf dem Feld. Solche Schuesse
    # bleiben ohne Linie - sie zaehlen trotzdem in die Teamstatistik.
    st.info(f"{ist} von {paraden} Paraden zugeordnet, {rest} offen. "
            f"Das ist in Ordnung, wenn die restlichen Schüsse in Unterzahl "
            f"fielen — die zählen nur fürs Team, nicht für eine Linie.")
else:
    st.warning(f"Zu viele: {ist} erfasst, der Torhüter hatte nur {paraden} "
               f"Paraden. Die {gegentore} Gegentore kommen separat aus "
               f"Tore.csv und gehören nicht in den Zähler.")

# ---- Abschnitt 2: Ballverluste je Spieler
st.header("Ballverluste und Fehlpässe")
# Torhueter (Linie 0) bleibt draussen - fuer ihn wird das nicht gezaehlt
feldspieler = gespielt[gespielt["Linie"].str.strip() != "0"]
if feldspieler.empty:
    st.caption("Für dieses Spiel sind keine Feldspieler erfasst.")
else:
    with st.container(border=True):
        for _, r in feldspieler.sort_values(["Linie", "Name"]).iterrows():
            name = str(r["Name"]).strip()
            wert = int(pd.to_numeric(r.get("Ballverlust", 0), errors="coerce") or 0)
            zaehler_zeile(
                f"{name} <span style='opacity:.55'>Linie {r['Linie'].strip()}</span>",
                wert, f"b_{mid}_{name}",
                lambda w, n=name: ballverlust_setzen(saison, mid, n, w))
    summe = int(pd.to_numeric(feldspieler.get("Ballverlust", 0),
                              errors="coerce").fillna(0).sum())
    st.caption(f"{summe} Ballverluste in diesem Spiel erfasst.")

for pfad, ziel in st.session_state.get("gesichert", {}).items():
    st.caption(f"Sicherungskopie von {pfad}: {ziel}")
