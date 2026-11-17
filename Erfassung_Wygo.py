# -*- coding: utf-8 -*-
"""Digitales Match-Blatt - dasselbe Blatt wie auf Papier, nur angeklickt.

Start:  streamlit run Erfassung_Wygo.py

Oben stehen Match-Id, Datum, Gegner, Liga und die Powerplay-/Boxplay-Zahlen
der Mannschaft. Darunter das ganze Blatt: eine Zeile je Spieler, alle fuenfzehn
Spalten des Papierblatts nebeneinander. Jede Zelle ist ein Knopf mit der Zahl
darauf - ein Klick setzt einen Strich dazu. Der Umschalter ueber dem Blatt
stellt auf Korrektur, dann nimmt ein Klick einen Strich weg.

Unter dem Blatt steht, was das Papier nicht hergibt, das Dashboard aber
braucht:

  * **Tore.** Ein Strich in der Spalte T legt den Eintrag gleich an; dazu
    kommen Halbzeit, Zeit, Assist, Linie, Kategorie und der Videoausschnitt.
    Gegentore ueber den Knopf daneben. Das wird Tore.csv - daraus baut das
    Dashboard Spielverlauf, Torkategorien, Assist-Paare und die Clips.
    Ist oben ein Spielvideo hinterlegt, kommt je Tor die Videozeit dazu -
    sekundengenau, denn sie ist die Mitte des Ausschnitts. Die
    Spieluhr bleibt davon unberuehrt: sie steht bei jedem Unterbruch still,
    das Video laeuft weiter, die beiden Zeiten driften auseinander.
  * **Abschluesse des Gegners je Linie**, gehalten und daneben. Das wird
    Gegner_Abschluesse.csv und ergibt zusammen mit den Gegentoren und der
    Spalte Block das Corsi gegen.

Der Kader steht in erfassung_logik.py (KADER_VORGABE) - neue Spieler werden
dort eingetragen, nicht hier in der Oberflaeche.

Nach jedem Klick wird der Stand nach erfassung_laufend/ gesichert; ein
versehentliches Neuladen im Browser kostet also nichts. Geschrieben wird
erst beim Uebernehmen, und zwar in alle vier CSVs auf einmal.
"""
import datetime
import os
import sys

import pandas as pd
import streamlit as st

# damit erfassung_logik auch gefunden wird, wenn Streamlit aus einem
# anderen Ordner heraus gestartet wird
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from erfassung_logik import (ABSCHLUSS_ARTEN, BLATT_SPALTEN, GEGNER_SPALTEN,
                             KADER_VORGABE, KATEGORIEN, MAX_MINUTE, ROLLEN,
                             ROLLEN_KURZ, TORE_SPALTEN, WYGO_CSV, WYGO_SPALTEN,
                             auswertung, bekannte_spieler, clip_ablegen,
                             clip_entfernen, gegner_zeilen, leere_abschluesse,
                             leeres_blatt, linien_pm, neue_zeile, neues_tor,
                             reihenfolge, resultat, saison_datei, schreiben, spielt,
                             tor_kontrollen, tore_geordnet, tore_zeilen,
                             CLIP_DAUER, clip_aus_video, clips_nachschneiden,
                             spielvideos, tore_eines_spiels, VIDEO_SCHRITT,
                             VIDEO_SPALTEN, videozeit_text,
                             wygo_zeile, zustand_lesen, zustand_loeschen,
                             zustand_sichern)

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
            "liga_wygo": 2, "liga_gegner": 2, "video": "",
            "pp_plus": 0, "pp_minus": 0, "bp_plus": 0, "bp_minus": 0}


# Der Stand liegt auf der Platte und wird beim Start zurueckgeholt - ein
# Neuladen im Browser oder ein Neustart des Servers aendert nichts daran.
# Geleert wird erst mit "Neues Blatt".
if "blatt" not in st.session_state or "kopf" not in st.session_state:
    stand = zustand_lesen()
    st.session_state.setdefault("blatt", stand["blatt"] if stand else leeres_blatt())
    st.session_state.setdefault("kopf", stand["kopf"] if stand else neuer_kopf())
    st.session_state.setdefault("tore", stand["tore"] if stand else [])
    st.session_state.setdefault("abschluesse",
                                stand["abschluesse"] if stand else leere_abschluesse())
blatt, kopf = st.session_state.blatt, st.session_state.kopf


def sichern():
    zustand_sichern(st.session_state.kopf, st.session_state.blatt,
                    st.session_state.tore, st.session_state.abschluesse)


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

# Ein Video je Spiel. Es bleibt liegen, wo es liegt - hier steht nur der
# Pfad. Darauf beziehen sich die Videozeiten bei den Toren weiter unten,
# und daraus lassen sich spaeter die Ausschnitte schneiden.
kopf["video"] = st.text_input(
    "Spielvideo (Pfad auf diesem Rechner)", value=kopf.get("video", ""),
    placeholder=r"C:\Users\rapha\Downloads\Video_2026-10-04_07-33-09.mp4",
    help="Rechtsklick auf die Datei → „Als Pfad kopieren\" und hier einfügen. "
         "Die Anführungszeichen, die Windows dabei mitgibt, dürfen stehen bleiben.")
# Windows gibt beim "Als Pfad kopieren" Anfuehrungszeichen mit. Die hier
# wegzunehmen ist bequemer, als sie jedes Mal von Hand zu loeschen.
kopf["video"] = str(kopf["video"]).strip().strip('"').strip("'").strip()
video_pfad = kopf["video"]
video_da = bool(video_pfad) and os.path.isfile(video_pfad)
if video_pfad and not video_da:
    st.warning("Diese Datei finde ich nicht. Die Videozeiten lassen sich "
               "trotzdem eintragen, nur das Nachschauen geht nicht.")
elif video_da:
    with st.expander(f"Spielvideo ansehen — {os.path.basename(video_pfad)}, "
                     f"{os.path.getsize(video_pfad) / 1e9:.1f} GB"):
        st.caption("Zum Tor spulen, die Zeit im Spieler ablesen und unten bei "
                   "diesem Tor eintragen.")
        st.video(video_pfad)

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
    (["Ballverlust"], "#FF7B7B"),
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
    vorher = z[spalte]
    z[spalte] = max(0, z[spalte] + delta)
    # Ein Strich in der Spalte T ist ein Tor - und ein Tor braucht mehr als
    # einen Strich. Der Eintrag entsteht gleich mit, auszufuellen ist er
    # unten am Blatt. So bleiben Blatt und Tore.csv von selbst beieinander.
    if spalte == "T" and z[spalte] != vorher:
        tore = st.session_state.tore
        if delta > 0:
            tore.append(neues_tor("Tor", name, z["rolle"] if z["rolle"] in "123" else ""))
        else:
            fuer_ihn = [t for t in tore if t["art"] == "Tor" and t["spieler"] == name]
            if fuer_ihn:
                letztes = max(fuer_ihn, key=lambda t: (int(t["hz"]), int(t["sek"])))
                clip_entfernen(letztes["datei"])
                tore.remove(letztes)
    sichern()


def gegentor_dazu():
    st.session_state.tore.append(neues_tor("Gegentor"))
    sichern()


def tor_weg(kennung):
    for t in list(st.session_state.tore):
        if t["id"] == kennung:
            clip_entfernen(t["datei"])
            st.session_state.tore.remove(t)
            # den Strich auf dem Blatt gleich mitnehmen, sonst laufen die
            # beiden Zaehlungen auseinander
            z = st.session_state.blatt.get(t["spieler"])
            if t["art"] == "Tor" and z:
                z["T"] = max(0, z["T"] - 1)
    sichern()


def tor_setzen(tor, feld, schluessel):
    tor[feld] = st.session_state[schluessel]
    sichern()


def tor_wahl_setzen(tor, feld, schluessel):
    """Wie tor_setzen, aber der Strich und das Leerfeld heissen beide 'nichts'."""
    wert = st.session_state[schluessel]
    tor[feld] = "" if wert in (None, "—") else wert
    sichern()


def clip_loesen(tor):
    clip_entfernen(tor["datei"])
    tor["datei"] = ""
    sichern()


def tor_zeit_setzen(tor, min_schluessel, sek_schluessel):
    tor["sek"] = (st.session_state[min_schluessel] * 60
                  + st.session_state[sek_schluessel])
    sichern()


def tor_videozeit_setzen(tor, min_schluessel, sek_schluessel):
    """Die Stelle im Spielvideo, sekundengenau. Null heisst
    'noch nicht eingetragen' - ein Tor in der ersten Videosekunde gibt es nicht."""
    sek = st.session_state[min_schluessel] * 60 + st.session_state[sek_schluessel]
    tor["videozeit"] = "" if sek <= 0 else str(sek)
    sichern()


def abschluss_aendern(linie, art, delta):
    werte = st.session_state.abschluesse[linie]
    werte[art] = max(0, werte[art] + delta)
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

# ----------------------------------------------------------------- Tore
# Ein Strich in der Spalte T legt oben schon den Eintrag an. Hier kommt
# dazu, was Tore.csv sonst noch braucht - und was das Dashboard daraus
# baut: Spielverlauf, Torkategorien, Assist-Paare und die Clips.
tore = st.session_state.tore
kader_dabei = [n for n in reihenfolge(blatt) if spielt(blatt[n]["rolle"])]


def tor_schuetze_setzen(tor, schluessel):
    """Schuetze wechseln - der Strich auf dem Blatt wandert mit."""
    neu = st.session_state[schluessel]
    alt = tor["spieler"]
    if neu == alt:
        return
    if alt in st.session_state.blatt:
        st.session_state.blatt[alt]["T"] = max(0, st.session_state.blatt[alt]["T"] - 1)
    if neu in st.session_state.blatt:
        st.session_state.blatt[neu]["T"] += 1
        tor["linie"] = st.session_state.blatt[neu]["rolle"] \
            if st.session_state.blatt[neu]["rolle"] in "123" else tor["linie"]
    tor["spieler"] = neu
    sichern()


eigene, gegentore = resultat(blatt)
kopfzeile_tore, knopf_schnitt, knopf_gegentor = st.columns([2.2, 1.4, 1.4])
kopfzeile_tore.subheader(f"Tore &nbsp;·&nbsp; {eigene}:{gegentore}")

# Alle Ausschnitte auf einen Schlag. Geschnitten wird nur, wo eine Videozeit
# steht und noch kein Clip haengt - zweimal druecken schadet also nichts.
offen_schnitt = [t for t in tore_geordnet(tore)
                 if str(t.get("videozeit", "")).strip() and not t["datei"]]
if knopf_schnitt.button(f"✂ {len(offen_schnitt)} Ausschnitte schneiden",
                        use_container_width=True, disabled=not (video_da and offen_schnitt),
                        help="Je Tor zehn Sekunden aus dem Spielvideo, mittig um "
                             "die eingetragene Videozeit."):
    fehler_beim_schneiden = []
    balken = st.progress(0.0, text="schneide …")
    for nr, t in enumerate(offen_schnitt, 1):
        balken.progress((nr - 1) / len(offen_schnitt),
                        text=f"{nr} von {len(offen_schnitt)} — "
                             f"{t['art']} bei {videozeit_text(t['videozeit'])}")
        try:
            t["datei"] = clip_aus_video(video_pfad, t)
        except Exception as fehler:
            fehler_beim_schneiden.append(f"{t['art']} "
                                         f"{videozeit_text(t['videozeit'])}: {fehler}")
    balken.empty()
    sichern()
    for text in fehler_beim_schneiden:
        st.error(text)
    if not fehler_beim_schneiden:
        st.rerun()

knopf_gegentor.button("＋ Gegentor erfassen", on_click=gegentor_dazu,
                      use_container_width=True,
                      help="Eigene Tore entstehen von selbst, sobald du in der "
                           "Spalte T einen Strich setzt.")

if not tore:
    st.caption("Noch kein Tor erfasst. Ein Strich in der Spalte **T** legt ein "
               "eigenes Tor an, für ein Gegentor der Knopf oben rechts.")

for t in tore_geordnet(tore):
    k = t["id"]
    ist_tor = t["art"] == "Tor"
    with st.container(key=f"tor_{k}", border=True):
        a, b, c, d, e, f = st.columns([2.4, 0.9, 0.9, 0.9, 2.2, 0.7],
                                      vertical_alignment="bottom")
        if ist_tor:
            wahl = kader_dabei if t["spieler"] in kader_dabei \
                else [t["spieler"]] + kader_dabei
            a.selectbox("🟢 Schütze", wahl, index=wahl.index(t["spieler"]),
                        key=f"sch_{k}",
                        on_change=tor_schuetze_setzen, args=(t, f"sch_{k}"))
        else:
            a.markdown("🔴 **Gegentor**")
        b.selectbox("HZ", [1, 2], index=int(t["hz"]) - 1, key=f"hz_{k}",
                    on_change=tor_setzen, args=(t, "hz", f"hz_{k}"))
        c.number_input("Min", 0, MAX_MINUTE, int(t["sek"]) // 60, key=f"min_{k}",
                       on_change=tor_zeit_setzen, args=(t, f"min_{k}", f"sek_{k}"))
        d.number_input("Sek", 0, 59, int(t["sek"]) % 60, key=f"sek_{k}",
                       on_change=tor_zeit_setzen, args=(t, f"min_{k}", f"sek_{k}"))
        if ist_tor:
            assist = ["—"] + [n for n in kader_dabei if n != t["spieler"]]
            e.selectbox("Assist", assist,
                        index=assist.index(t["assist"]) if t["assist"] in assist else 0,
                        key=f"ass_{k}", on_change=tor_wahl_setzen,
                        args=(t, "assist", f"ass_{k}"))
        f.button("🗑", key=f"torweg_{k}", on_click=tor_weg, args=(k,),
                 use_container_width=True, help="Dieses Tor wieder entfernen")

        # Videozeit: wo im Spielvideo das Tor liegt. Die Spieluhr oben bleibt
        # davon unberuehrt - sie steht bei jedem Unterbruch still, das Video
        # laeuft weiter, die beiden Zeiten driften also auseinander.
        vid = int(t.get("videozeit") or 0)
        v1, v2, v3, v4 = st.columns([0.9, 0.9, 1.2, 3], vertical_alignment="bottom")
        v1.number_input("Video Min", 0, 180, vid // 60, key=f"vmin_{k}",
                        on_change=tor_videozeit_setzen,
                        args=(t, f"vmin_{k}", f"vsek_{k}"))
        v2.number_input("Sek", 0, 59, vid % 60, step=VIDEO_SCHRITT,
                        key=f"vsek_{k}", on_change=tor_videozeit_setzen,
                        args=(t, f"vmin_{k}", f"vsek_{k}"))
        v3.markdown(f"<div style='padding-bottom:9px;opacity:.7'>Video "
                    f"{videozeit_text(t.get('videozeit'))}</div>",
                    unsafe_allow_html=True)
        if video_da and t.get("videozeit"):
            with v4.expander("im Video nachsehen"):
                st.video(video_pfad, start_time=int(t["videozeit"]))

        linien_wahl = ["—", "1", "2", "3"]
        g, h = st.columns([1, 5], vertical_alignment="center")
        g.selectbox("Linie", linien_wahl,
                    index=linien_wahl.index(t["linie"]) if t["linie"] in linien_wahl
                    else 0, key=f"lin_{k}", on_change=tor_wahl_setzen,
                    args=(t, "linie", f"lin_{k}"),
                    help="Welche Linie stand auf dem Feld? In Unterzahl leer lassen.")
        with h:
            st.pills("Kategorie", KATEGORIEN[t["art"]],
                     default=t["kategorie"] or None, selection_mode="single",
                     key=f"kat_{k}", on_change=tor_wahl_setzen,
                     args=(t, "kategorie", f"kat_{k}"))

        if t["datei"]:
            i, j = st.columns([5, 1], vertical_alignment="center")
            i.caption(f"Torausschnitt angehängt: `{t['datei']}` — wird beim "
                      f"Übernehmen in den Saisonordner gelegt.")
            j.button("lösen", key=f"clipweg_{k}", use_container_width=True,
                     on_click=clip_loesen, args=(t,))
        else:
            schnittbar = video_da and str(t.get("videozeit", "")).strip()
            i, j, l = st.columns([1.3, 2, 2] if schnittbar else [0.01, 2, 2])
            if schnittbar and i.button("✂ schneiden", key=f"cut_{k}",
                                       use_container_width=True,
                                       help=f"{CLIP_DAUER} Sekunden aus dem "
                                            f"Spielvideo, mittig um "
                                            f"{videozeit_text(t['videozeit'])}"):
                with st.spinner("schneide den Ausschnitt …"):
                    try:
                        t["datei"] = clip_aus_video(video_pfad, t)
                        sichern()
                    except Exception as fehler:
                        st.error(f"Nicht geschnitten: {fehler}")
                    else:
                        st.rerun()
            hoch = j.file_uploader("Torausschnitt", type=["mp4", "mov", "m4v", "webm"],
                                   key=f"up_{k}", label_visibility="collapsed")
            if hoch is not None and st.session_state.get(f"hat_{k}") != hoch.name:
                st.session_state[f"hat_{k}"] = hoch.name
                t["datei"] = clip_ablegen(hoch.name, hoch.getvalue())
                sichern()
                st.rerun()
            l.text_input("Videoadresse", value=t["video"], key=f"url_{k}",
                         placeholder="oder Adresse zum Einbetten",
                         label_visibility="collapsed",
                         on_change=tor_setzen, args=(t, "video", f"url_{k}"))

st.divider()

# ------------------------------------------- Abschluesse des Gegners je Linie
# Was der Gegner abgeschlossen hat, waehrend eine Linie draussen stand.
# Gegentore und von uns geblockte Versuche gehoeren NICHT hierher - die
# stehen schon oben und in der Spalte Block; zusammen ergibt das Corsi gegen.
st.subheader("Abschlüsse des Gegners je Linie")
st.caption("Nur gehaltene Schüsse und solche daneben. Gegentore **nicht** "
           "mitzählen — die stehen oben, die geblockten in der Spalte Block.")

abschluesse = st.session_state.abschluesse
spalten_ab = st.columns(3)
for sp, linie in zip(spalten_ab, ("1", "2", "3")):
    with sp:
        with st.container(border=True):
            st.markdown(f"**Linie {linie}**")
            for art in ABSCHLUSS_ARTEN:
                wert = abschluesse[linie][art]
                st.caption(art)
                weg, zahl, hin = st.columns([1, 1, 1])
                weg.button("−", key=f"ab_{linie}_{art}_minus", use_container_width=True,
                           disabled=wert <= 0, on_click=abschluss_aendern,
                           args=(linie, art, -1))
                zahl.markdown(f"<div style='text-align:center;font-weight:700;"
                              f"font-size:18px'>{wert}</div>", unsafe_allow_html=True)
                hin.button("+", key=f"ab_{linie}_{art}_plus", use_container_width=True,
                           on_click=abschluss_aendern, args=(linie, art, 1))

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
               f"{len(tabelle)} Zeilen · **Tore.csv** — {len(tore)} Zeilen · "
               f"**Gegner_Abschluesse.csv** — bis zu 3 Zeilen"
               + (" · **Spielvideos.csv** — eine Zeile" if video_pfad else ""))
    # Die Querproben vom Papierblatt, jetzt vor dem Schreiben. Sie halten nur
    # auf, wenn etwas wirklich nicht zusammenpasst - geschrieben wird trotzdem,
    # denn manches ist in Unterzahl von Natur aus ungleich.
    proben = tor_kontrollen(blatt, tore, abschluesse, kopf.get("video", ""))
    offen = [text for ok, text in proben if not ok]
    if offen:
        with st.expander(f"⚠ {len(offen)} Querproben gehen nicht auf", expanded=False):
            for text in offen:
                st.markdown(f"- {text}")
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
                schreiben(kopf, blatt, datum, linien, tore, abschluesse)
                sichern()
                st.cache_data.clear()
                st.success(f"Spiel {kopf['match_id']} geschrieben — "
                           f"{len(tabelle)} Spielerzeilen, {len(tore)} Tore.")
                st.balloons()
            except Exception as fehler:
                st.error(f"Nichts geschrieben: {fehler}")

with rechts:
    st.subheader(" ")
    if st.button("Neues Blatt", use_container_width=True):
        zustand_loeschen()
        for schluessel in [k for k in st.session_state
                           if k.startswith(("rolle_", "z_", "weg_", "sch_", "hz_",
                                            "min_", "sek_", "ass_", "lin_", "kat_",
                                            "up_", "hat_", "url_", "clipweg_", "ab_",
                                            "torweg_", "cut_", "vmin_", "vsek_"))]:
            del st.session_state[schluessel]
        st.session_state.blatt = leeres_blatt()
        st.session_state.kopf = neuer_kopf()
        st.session_state.tore = []
        st.session_state.abschluesse = leere_abschluesse()
        st.rerun()

sichern()   # auch die Kopffelder, die erst beim Zeichnen gelesen werden

with st.expander("Das wird geschrieben"):
    st.dataframe(pd.DataFrame([wygo_zeile(kopf, blatt, datum)],
                              columns=[c.strip() for c in WYGO_SPALTEN]).astype(str),
                 hide_index=True, use_container_width=True)
    st.dataframe(tabelle.astype(str), hide_index=True, use_container_width=True)
    if tore:
        st.dataframe(pd.DataFrame(tore_zeilen(kopf["match_id"], tore),
                                  columns=TORE_SPALTEN).astype(str),
                     hide_index=True, use_container_width=True)
    zeilen_gegner = gegner_zeilen(kopf["match_id"], abschluesse)
    if zeilen_gegner:
        st.dataframe(pd.DataFrame(zeilen_gegner, columns=GEGNER_SPALTEN).astype(str),
                     hide_index=True, use_container_width=True)
    if video_pfad:
        st.dataframe(pd.DataFrame([[kopf["match_id"], video_pfad]],
                                  columns=VIDEO_SPALTEN).astype(str),
                     hide_index=True, use_container_width=True)

# -------------------------------- Ausschnitte eines schon erfassten Spiels
# Der uebliche Ablauf: das Blatt wird nach dem Spiel uebernommen, das Video
# kommt spaeter. Dann ist das Blatt oben laengst leer - geschnitten wird
# hier, direkt aus Tore.csv.
with st.expander("Ausschnitte für ein bereits erfasstes Spiel schneiden"):
    videos = spielvideos()
    if not videos:
        st.caption("Noch kein Spiel mit hinterlegtem Video. Der Pfad kommt oben "
                   "ins Feld **Spielvideo** und wird beim Übernehmen festgehalten.")
    else:
        spiele_wahl = sorted(videos, key=lambda m: int(m), reverse=True)
        gewaehlt = st.selectbox("Spiel", spiele_wahl, key="nach_spiel")
        quelle = videos[gewaehlt]
        alle = tore_eines_spiels(gewaehlt)
        mit_zeit = [t for t in alle if t["Videozeit"].strip()]
        mit_clip = [t for t in alle if t["Datei"].strip()]
        offen = [t for t in mit_zeit if not t["Datei"].strip()]
        st.caption(f"{len(alle)} Tore · {len(mit_zeit)} mit Videozeit · "
                   f"{len(mit_clip)} mit Ausschnitt · **{len(offen)} offen**")
        if not os.path.isfile(quelle):
            st.warning(f"Das hinterlegte Video finde ich nicht: `{quelle}`")
        elif not offen:
            st.success("Für dieses Spiel ist nichts mehr zu schneiden."
                       if mit_zeit else
                       "Für dieses Spiel ist keine Videozeit eingetragen.")
        elif st.button(f"✂ {len(offen)} fehlende Ausschnitte schneiden",
                       type="primary", use_container_width=True,
                       key="nach_schneiden"):
            balken = st.progress(0.0, text="schneide …")
            stand = {"i": 0}

            def melden(tor, name, _n=len(offen)):
                stand["i"] += 1
                balken.progress((stand["i"] - 1) / _n,
                                text=f"{stand['i']} von {_n} — {name}")

            try:
                gemacht, fehler = clips_nachschneiden(gewaehlt, melden)
            except Exception as fehlgeschlagen:
                balken.empty()
                st.error(str(fehlgeschlagen))
            else:
                balken.empty()
                st.success(f"{len(gemacht)} Ausschnitte geschnitten und in "
                           f"Tore.csv eingetragen.")
                for text in fehler:
                    st.error(text)
        ohne_zeit = [t for t in alle if not t["Videozeit"].strip()]
        if ohne_zeit:
            st.caption("Ohne Videozeit und darum übersprungen: "
                       + ", ".join(f"Nr {t['Nr']} ({t['Art']} {t['Zeit']})"
                                   for t in ohne_zeit))
