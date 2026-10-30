# -*- coding: utf-8 -*-
"""Digitales Match-Blatt - dasselbe Blatt wie auf Papier, nur angeklickt.

Start:  streamlit run Erfassung_Wygo.py

Oben stehen Match-Id, Datum, Gegner, Liga und die Powerplay-/Boxplay-Zahlen
der Mannschaft. Darunter das ganze Blatt: eine Zeile je Spieler, alle fuenfzehn
Spalten des Papierblatts nebeneinander. Jede Zelle ist ein Knopf mit der Zahl
darauf - ein Klick setzt einen Strich dazu. Der Umschalter ueber dem Blatt
stellt auf Korrektur, dann nimmt ein Klick einen Strich weg.

Der Kader steht in erfassung_logik.py (KADER_VORGABE) - neue Spieler werden
dort eingetragen, nicht hier in der Oberflaeche.

Nach jedem Klick wird der Stand nach erfassung_laufend/ gesichert; ein
versehentliches Neuladen im Browser kostet also nichts.
"""
import datetime
import os
import sys

import pandas as pd
import streamlit as st

# damit erfassung_logik auch gefunden wird, wenn Streamlit aus einem
# anderen Ordner heraus gestartet wird
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from erfassung_logik import (BLATT_SPALTEN, KADER_VORGABE, ROLLEN, ROLLEN_KURZ,
                             WYGO_CSV, WYGO_SPALTEN, auswertung, bekannte_spieler,
                             leeres_blatt, linien_pm, neue_zeile, reihenfolge,
                             resultat, saison_datei, schreiben, spielt, wygo_zeile,
                             zustand_lesen, zustand_loeschen, zustand_sichern)

st.set_page_config(page_title="Match-Blatt — UHC Wygorazzi", page_icon="🏑",
                   layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
    <style>
    [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {display:none !important;}
    .block-container {max-width:100%; padding:1.1rem 0.8rem 2rem 0.8rem;}
    .kicker {font-size:12px; font-weight:600; letter-spacing:.14em; text-transform:uppercase;
             color:#00FFAA;}
    .big-title {font-size:24px; font-weight:700; margin:0 0 8px 0;}

    /* Blatt — die Kopfzeile bleibt beim Scrollen oben stehen, damit man immer
       sieht, in welcher Spalte man klickt. */
    [class*="st-key-blattkopf"] {position:sticky; top:0; z-index:6;
                                 background:#0E1117; padding:4px 0 10px 0;
                                 margin-bottom:4px;}
    .kopf-zelle, .kopf-name {font-size:12px; font-weight:700; letter-spacing:.02em;
                 text-transform:uppercase; color:#E8EAED; line-height:1.15;
                 min-height:48px; display:flex; align-items:flex-end;
                 padding:7px 3px 7px 3px; background:#1A1F29;
                 border-bottom:2px solid #39414F; border-radius:4px 4px 0 0;
                 overflow-wrap:anywhere;}
    .kopf-zelle {text-align:center; justify-content:center;}
    .name {font-weight:600; font-size:13px; line-height:1.1; padding-top:7px;
           white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
    .name-ersatz {font-weight:600; font-size:13px; line-height:1.1; padding-top:7px;
                  color:#6B7280;}
    .korrektur {color:#FCA5A5; font-size:12px; font-weight:600; margin:-2px 0 4px 2px;}

    /* Jede Zelle ist ein Knopf - klein genug, dass 15 Spalten nebeneinander
       passen. Streamlit haengt an jedes Element mit key die Klasse
       st-key-<key>, darueber treffen wir nur die Zellen des Blatts. */
    [class*="st-key-z_"] button {
      width:100%; min-height:32px; padding:0 !important; font-size:15px;
      font-weight:700; line-height:1;
    }
    /* Leere Zellen bleiben blass, gefuellte bekommen weiter unten die Farbe
       ihrer Spalte ("primary" dient nur als Haken dafuer). */
    [class*="st-key-z_"] button[kind="secondary"],
    [class*="st-key-z_"] button[data-testid="stBaseButton-secondary"] {
      color:#596273 !important; font-weight:400;
    }
    div[data-testid="stHorizontalBlock"] [data-testid="stColumn"] {gap:0.1rem;}
    [data-testid="stVerticalBlock"] {gap:0.25rem;}
    [data-baseweb="select"] > div {min-height:32px; font-size:12px;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------ Zustand
def vergebene_ids():
    """Welche Spiel-Ids in Statistik_Wygo.csv schon stehen."""
    w = pd.read_csv(WYGO_CSV)
    w.columns = w.columns.str.strip()
    return set(pd.to_numeric(w["Match_Id"], errors="coerce").dropna().astype(int))


def naechste_id():
    return max(vergebene_ids()) + 1


@st.cache_data(show_spinner=False)
def saison_liste():
    w = pd.read_csv(WYGO_CSV)
    w.columns = w.columns.str.strip()
    return sorted(w["Saison"].dropna().unique(), reverse=True)


def neuer_kopf():
    return {"saison": saison_liste()[0], "format": "Meisterschaft", "gegner": "",
            "datum": datetime.date.today().isoformat(), "match_id": naechste_id(),
            "liga_wygo": 2, "liga_gegner": 2,
            "pp_plus": 0, "pp_minus": 0, "bp_plus": 0, "bp_minus": 0}


# Der Stand liegt auf der Platte und wird beim Start zurueckgeholt - ein
# Neuladen im Browser oder ein Neustart des Servers aendert nichts daran.
# Geleert wird erst mit "Neues Blatt".
if "blatt" not in st.session_state or "kopf" not in st.session_state:
    stand = zustand_lesen()
    st.session_state.setdefault("blatt", stand["blatt"] if stand else leeres_blatt())
    st.session_state.setdefault("kopf", stand["kopf"] if stand else neuer_kopf())
blatt, kopf = st.session_state.blatt, st.session_state.kopf


def sichern():
    zustand_sichern(st.session_state.kopf, st.session_state.blatt)


# -------------------------------------------------------------------- Kopf
eigene, gegentore = resultat(blatt)
st.markdown('<div class="kicker">UHC Wygorazzi</div>', unsafe_allow_html=True)
st.markdown(f'<div class="big-title">Match-Blatt &nbsp;·&nbsp; '
            f'{kopf["gegner"] or "Gegner?"} &nbsp;'
            f'<span style="color:#00FFAA">{eigene}:{gegentore}</span></div>',
            unsafe_allow_html=True)

a, b, c, d, e = st.columns([1.1, 1.4, 2.4, 1, 1])
kopf["match_id"] = a.number_input("Spiel-Id", 1, 9999, int(kopf["match_id"]), step=1)
kopf["datum"] = b.date_input(
    "Datum", value=datetime.date.fromisoformat(kopf["datum"])).isoformat()
kopf["gegner"] = c.text_input("Gegner", value=kopf["gegner"], placeholder="z.B. Spreitenbach")
kopf["liga_wygo"] = d.number_input("Liga Wygo", 1, 9, int(kopf["liga_wygo"]))
kopf["liga_gegner"] = e.number_input("Liga Gegner", 1, 9, int(kopf["liga_gegner"]))

a, b, c, d, e, f = st.columns([1.3, 1.3, 1, 1, 1, 1])
saisons = saison_liste()
kopf["saison"] = a.selectbox("Saison", saisons, index=saisons.index(kopf["saison"]))
formate = ["Meisterschaft", "Cup", "Testspiel"]
kopf["format"] = b.selectbox("Format", formate, index=formate.index(kopf["format"]))
kopf["pp_plus"] = c.number_input("Powerplay +", 0, 50, int(kopf["pp_plus"]))
kopf["pp_minus"] = d.number_input("Powerplay −", 0, 50, int(kopf["pp_minus"]))
kopf["bp_plus"] = e.number_input("Boxplay +", 0, 50, int(kopf["bp_plus"]))
kopf["bp_minus"] = f.number_input("Boxplay −", 0, 50, int(kopf["bp_minus"]))

st.divider()

# ------------------------------------------------------------------- Blatt
spalten = [sp for sp, _ in BLATT_SPALTEN]
titel = dict(BLATT_SPALTEN)

# Linie, Name und dann alle fuenfzehn Spalten des Papierblatts
BREITEN = [0.8, 2.0] + [1.0] * len(spalten)

# Farben statt Suchen: jede Zeile traegt die Farbe ihrer Linie, jede
# Spaltengruppe ihre eigene. Eine gefuellte Zelle leuchtet in der Farbe
# ihrer Spalte, eine leere bleibt nur leicht getoent.
LINIEN_FARBE = {"1": "#00FFAA", "2": "#4DA3FF", "3": "#FFB84D",
                "T": "#C084FC", "Ersatz": "#6B7280"}
SPALTEN_GRUPPEN = [
    (["T", "A"], "#00FFAA"),
    (["Plus", "Minus"], "#4DA3FF"),
    (["Bully-Plus", "Bully-Minus"], "#C084FC"),
    (["Strafen", "Block"], "#FF7B7B"),
    (["Schüsse", "Schüsse aufs Tor", "Balleroberung"], "#FFB84D"),
    (["Powerplay-Plus", "Powerplay-Minus"], "#5EEAD4"),
    (["Boxplay-Plus", "Boxplay-Minus"], "#F472B6"),
]
SPALTEN_FARBE = {sp: farbe for namen, farbe in SPALTEN_GRUPPEN for sp in namen}
GRUPPEN_START = {namen[0] for namen, _ in SPALTEN_GRUPPEN}


def _ton(farbe, anteil):
    r, g, b = (int(farbe[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{anteil})"


def blatt_farben(blatt):
    """Die Farbregeln fuers Blatt - aus Spalten und Kader gebaut, damit sie
    nicht auseinanderlaufen, wenn eine Spalte oder ein Spieler dazukommt.

    Angesprochen wird ueber die Klasse st-key-<key>, die Streamlit an jedes
    Element mit key haengt - nicht ueber die Stellung im Raster.
    """
    regeln = []
    for sp, farbe in SPALTEN_FARBE.items():
        sel = f'[class*="st-key-z_{sp}_"]'        # eine ganze Spalte
        rand = f"border-left:2px solid {_ton(farbe, .45)};" if sp in GRUPPEN_START else ""
        regeln += [
            f'{sel} button {{background:{_ton(farbe, .05)} !important;'
            f' border-color:{_ton(farbe, .20)} !important; {rand}}}',
            f'{sel} button[kind="primary"], {sel} button[data-testid="stBaseButton-primary"]'
            f' {{background:{_ton(farbe, .24)} !important; color:{farbe} !important;'
            f' border-color:{_ton(farbe, .60)} !important; {rand}}}',
            f'{sel} button:hover {{border-color:{farbe} !important;'
            f' color:{farbe} !important; background:{_ton(farbe, .18)} !important;}}',
        ]
    for i, name in enumerate(reihenfolge(blatt)):
        farbe = LINIEN_FARBE.get(blatt[name]["rolle"], "#6B7280")
        sel = f'[class*="st-key-zeile_{i:02d}"]'   # eine ganze Zeile
        regeln += [
            f'{sel} {{background:{_ton(farbe, .055)}; border-left:4px solid {farbe};'
            f' border-bottom:1px solid #1C222C; border-radius:0 6px 6px 0;'
            f' padding:3px 2px 3px 6px;}}',
            f'{sel}:hover {{background:{_ton(farbe, .13)};}}',
            f'{sel} .name {{color:{farbe};}}',
        ]
    return "<style>" + "\n".join(regeln) + "</style>"


def kopf_stil(sp):
    """Die Spaltenbeschriftung traegt ihre Farbe direkt im Element."""
    farbe = SPALTEN_FARBE[sp]
    rand = f"border-left:2px solid {_ton(farbe, .45)};" if sp in GRUPPEN_START else ""
    return (f"color:{farbe};border-bottom-color:{farbe};"
            f"background:{_ton(farbe, .14)};{rand}")


def zellen_aendern(name, spalte):
    """Ein Klick auf die Zahl: im Zaehlmodus ein Strich dazu, sonst einer weg."""
    delta = -1 if st.session_state.get("modus", "").startswith("−") else 1
    z = st.session_state.blatt[name]
    z[spalte] = max(0, z[spalte] + delta)
    sichern()


def rolle_aendern(name):
    st.session_state.blatt[name]["rolle"] = st.session_state[f"rolle_{name}"]
    sichern()


LEER = "— auswählen —"


def spieler_dazu():
    """Jemanden ins Blatt holen: entweder aus den alten Statistiken oder neu."""
    gewaehlt = st.session_state.get("neu_bekannt", LEER)
    name = (st.session_state.get("neu_name") or "").strip()
    name = name or ("" if gewaehlt == LEER else gewaehlt)
    if not name:
        st.session_state.spieler_hinweis = "Kein Name angegeben."
        return
    if name in st.session_state.blatt:
        st.session_state.spieler_hinweis = f"{name} steht schon im Blatt."
        return
    st.session_state.blatt[name] = neue_zeile(st.session_state.get("neu_rolle", "Ersatz"))
    st.session_state.spieler_hinweis = f"{name} ist im Blatt."
    st.session_state.neu_name = ""
    st.session_state.neu_bekannt = LEER
    sichern()


def spieler_weg(name):
    st.session_state.blatt.pop(name, None)
    st.session_state.spieler_hinweis = f"{name} wieder entfernt."
    sichern()


schalter, dazu = st.columns([3, 1.4])
with schalter:
    modus = st.radio("Modus", ["＋ zählen", "− korrigieren"], horizontal=True, key="modus",
                     label_visibility="collapsed",
                     help="Im Zählmodus setzt ein Klick auf eine Zahl einen Strich dazu, "
                          "im Korrekturmodus nimmt er einen weg.")
with dazu:
    with st.popover("👤 Spieler erfassen", use_container_width=True):
        st.caption("Gilt nur für dieses Spiel. Der feste Kader steht in "
                   "erfassung_logik.py.")
        offen = [n for n in bekannte_spieler() if n not in blatt]
        links_p, rechts_p = st.columns([2, 1])
        links_p.selectbox("Schon einmal erfasst", [LEER] + offen, key="neu_bekannt")
        rechts_p.selectbox("Linie", ROLLEN, index=ROLLEN.index("Ersatz"), key="neu_rolle")
        st.text_input("Oder neuer Name", key="neu_name", placeholder="z.B. T.Muster")
        st.button("Ins Blatt aufnehmen", on_click=spieler_dazu, type="primary",
                  use_container_width=True)
        if st.session_state.get("spieler_hinweis"):
            st.caption(st.session_state["spieler_hinweis"])
        zusatz = [n for n in blatt if n not in dict(KADER_VORGABE)]
        if zusatz:
            st.divider()
            st.caption("Zusätzlich im Blatt:")
            for n in zusatz:
                a_p, b_p = st.columns([2, 1])
                a_p.markdown(f"**{n}**")
                b_p.button("entfernen", key=f"weg_{n}", on_click=spieler_weg, args=(n,),
                           use_container_width=True)

if modus.startswith("−"):
    st.markdown('<div class="korrektur">Korrekturmodus — jeder Klick zieht ab</div>',
                unsafe_allow_html=True)

st.markdown(blatt_farben(blatt), unsafe_allow_html=True)

with st.container(key="blattgitter"):
    with st.container(key="blattkopf"):
        kopfzeile = st.columns(BREITEN)
        kopfzeile[0].markdown('<div class="kopf-zelle">Linie</div>', unsafe_allow_html=True)
        kopfzeile[1].markdown('<div class="kopf-name">Name</div>', unsafe_allow_html=True)
        for i, sp in enumerate(spalten):
            kopfzeile[2 + i].markdown(
                f'<div class="kopf-zelle" style="{kopf_stil(sp)}">{titel[sp]}</div>',
                unsafe_allow_html=True)

    for nr, name in enumerate(reihenfolge(blatt)):
        z = blatt[name]
        dabei = spielt(z["rolle"])
        with st.container(key=f"zeile_{nr:02d}"):
            reihe = st.columns(BREITEN)
            reihe[0].selectbox("Linie", ROLLEN, index=ROLLEN.index(z["rolle"]),
                               format_func=lambda r: ROLLEN_KURZ[r],
                               key=f"rolle_{name}", on_change=rolle_aendern, args=(name,),
                               label_visibility="collapsed")
            reihe[1].markdown(
                f'<div class="{"name" if dabei else "name-ersatz"}">{name}</div>',
                unsafe_allow_html=True)
            for i, sp in enumerate(spalten):
                # die Zelle ist der Knopf: er traegt die Zahl, ein Klick aendert sie
                reihe[2 + i].button(str(z[sp]) if dabei else "·", key=f"z_{sp}_{name}",
                                    on_click=zellen_aendern, args=(name, sp),
                                    use_container_width=True, disabled=not dabei,
                                    type="primary" if z[sp] and dabei else "secondary")

st.divider()

# ------------------------------------------------------- Linie-Plus/-Minus
linien = linien_pm(blatt)   # steht nicht auf dem Blatt, wird abgeleitet

# --------------------------------------------------------------- Speichern
tabelle = auswertung(blatt, kopf["match_id"], linien)
datum = datetime.date.fromisoformat(kopf["datum"]).strftime("%d.%m.%Y")

links, rechts = st.columns([1.6, 1])
with links:
    st.subheader("Speichern")
    st.caption(f"**Statistik_Wygo.csv** — eine Zeile · "
               f"**{os.path.basename(saison_datei(kopf['saison']))}** — "
               f"{len(tabelle)} Zeilen")
    if st.button("Blatt in die CSVs übernehmen", type="primary",
                 use_container_width=True):
        if not str(kopf["gegner"]).strip():
            # ein Blatt ohne Gegner ist nie ein echtes Spiel
            st.error("Kein Gegner eingetragen — nichts geschrieben.")
        elif kopf["match_id"] in vergebene_ids():
            # das Einzige, was nicht rueckgaengig zu machen waere
            st.error(f"Spiel-Id {kopf['match_id']} steht schon in Statistik_Wygo.csv — "
                     "nichts geschrieben.")
        else:
            try:
                schreiben(kopf, blatt, datum, linien)
                sichern()
                st.cache_data.clear()
                st.success(f"Spiel {kopf['match_id']} geschrieben.")
                st.balloons()
            except Exception as fehler:
                st.error(f"Nichts geschrieben: {fehler}")

with rechts:
    st.subheader(" ")
    if st.button("Neues Blatt", use_container_width=True):
        zustand_loeschen()
        for schluessel in [k for k in st.session_state
                           if k.startswith(("rolle_", "z_", "weg_"))]:
            del st.session_state[schluessel]
        st.session_state.blatt = leeres_blatt()
        st.session_state.kopf = neuer_kopf()
        st.rerun()

sichern()   # auch die Kopffelder, die erst beim Zeichnen gelesen werden

with st.expander("Das wird geschrieben"):
    st.dataframe(pd.DataFrame([wygo_zeile(kopf, blatt, datum)],
                              columns=[c.strip() for c in WYGO_SPALTEN]).astype(str),
                 hide_index=True, use_container_width=True)
    st.dataframe(tabelle.astype(str), hide_index=True, use_container_width=True)
