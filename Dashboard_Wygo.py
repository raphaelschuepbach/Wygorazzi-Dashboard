import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import numpy as np
import glob
import os
import re

# ---------------------------
# Farbsystem - einzige Quelle fuer CSS und Plots
# ---------------------------
# Die App laeuft auf dunklem Grund (.streamlit/config.toml). Balken sind deshalb
# hell und der Text darin dunkel - das ergibt auf beiden Seiten genug Kontrast.
FARBEN = {
    "bg": "#0E1117",
    "flaeche": "#171B24",
    "flaeche_hell": "#1E232E",
    "rand": "#2B313D",
    "text": "#E8EAED",
    "gedaempft": "#9AA4B2",
    "akzent": "#00FFAA",
    # Balkenfuellungen (hell, damit sie sich vom Hintergrund abheben)
    "balken": "#9CC9FF",
    "gut": "#6EE7B7",
    "schlecht": "#FCA5A5",
    "neutral": "#CBD5E1",
    "warn": "#FCD34D",
    # Beschriftung in den Balken (dunkel) bzw. ausserhalb (hell)
    "label_innen": "#111827",
    "label_aussen": "#E8EAED",
    "label_gut": "#14532D",
    "label_schlecht": "#7F1D1D",
}

LINIEN_FARBEN = {
    "Linie 1": FARBEN["balken"],
    "Linie 2": FARBEN["gut"],
    "Linie 3": FARBEN["warn"],
}

# ---------------------------
# Page config & CSS
# ---------------------------
st.set_page_config(page_title="UHC Wygorazzi — Statistik", page_icon="🏑",
                   layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {{
      --bg: {FARBEN["bg"]};
      --flaeche: {FARBEN["flaeche"]};
      --flaeche-hell: {FARBEN["flaeche_hell"]};
      --rand: {FARBEN["rand"]};
      --text: {FARBEN["text"]};
      --gedaempft: {FARBEN["gedaempft"]};
      --akzent: {FARBEN["akzent"]};
      --gut: {FARBEN["gut"]};
      --schlecht: {FARBEN["schlecht"]};
      --neutral: {FARBEN["neutral"]};
    }}

    /* Streamlit-Eigenwerbung und Werkzeugleiste ausblenden */
    [data-testid="stHeader"], [data-testid="stToolbar"],
    [data-testid="stDecoration"], #MainMenu, footer {{display:none !important;}}

    html, body, .stApp, [class*="st-"], button, input, select, textarea {{
      font-family:'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }}
    .stApp {{background:var(--bg);}}

    /* Inhalt mittig halten, trotz wide layout */
    .block-container, [data-testid="stMainBlockContainer"] {{
      max-width:1180px; padding-top:1.6rem; padding-bottom:3rem;
    }}

    /* Formularfelder an die dunkle Oberflaeche angleichen */
    [data-baseweb="select"] > div {{
      background:var(--flaeche) !important; border-color:var(--rand) !important;
      border-radius:10px !important;
    }}
    label[data-testid="stWidgetLabel"] p {{
      font-size:11px !important; font-weight:600 !important;
      letter-spacing:0.09em; text-transform:uppercase; color:var(--gedaempft) !important;
    }}

    .big-title {{
      font-size:26px; font-weight:700; color:var(--text);
      letter-spacing:-0.01em; margin:0 0 2px 0;
    }}
    .kicker {{
      font-size:12px; font-weight:600; letter-spacing:0.14em;
      text-transform:uppercase; color:var(--akzent); margin-bottom:2px;
    }}
    .subtle {{color:var(--gedaempft); font-size:13px;}}
    .small-metric {{font-size:12px; color:var(--gedaempft);}}

    /* Diagrammkarten (st.container(border=True)) */
    [data-testid="stVerticalBlockBorderWrapper"]:has(.chart-titel) {{
      background:var(--flaeche); border:1px solid var(--rand) !important;
      border-radius:14px; padding:12px 12px 2px 12px; margin-bottom:12px;
    }}
    /* kein negativer Abstand - der schob das Diagramm ueber die Ueberschrift */
    .chart-titel {{
      font-size:15px; font-weight:600; color:var(--text) !important;
      line-height:1.3; margin:0 0 8px 0;
    }}
    .chart-leer {{
      font-size:12px; color:var(--gedaempft); padding:14px 4px 20px 4px;
    }}

    .karte {{
      background:var(--flaeche); border:1px solid var(--rand);
      border-radius:14px; padding:16px;
    }}

    /* Saisonbilanz */
    .kpi-reihe {{display:flex; flex-wrap:wrap; gap:10px; margin-top:12px;}}
    .kpi {{
      flex:1 1 90px; min-width:90px; background:var(--flaeche-hell);
      border:1px solid var(--rand); border-radius:10px; padding:10px 12px;
    }}
    .kpi .wert {{font-size:21px; font-weight:700; color:var(--text); line-height:1.1;}}
    .kpi .bez {{
      font-size:10px; letter-spacing:0.08em; text-transform:uppercase;
      color:var(--gedaempft); margin-top:3px;
    }}
    .kpi .wert .gut {{color:var(--gut);}}
    .kpi .wert .schlecht {{color:var(--schlecht);}}
    .kpi .wert .neutral {{color:var(--neutral);}}

    .chips {{display:flex; flex-wrap:wrap; gap:5px; margin-top:12px;}}
    a.chip {{
      display:inline-block; font-size:11px; font-weight:600; padding:3px 8px;
      border-radius:6px; border:1px solid transparent; text-decoration:none;
      color:{FARBEN["label_innen"]}; cursor:pointer; transition:transform .08s ease;
    }}
    a.chip:hover {{transform:translateY(-1px); border-color:var(--text);}}
    .chip.sieg {{background:var(--gut);}}
    .chip.remis {{background:var(--neutral);}}
    .chip.nieder {{background:var(--schlecht);}}

    /* Torliste */
    .tor-zeile {{
      display:flex; align-items:center; gap:12px; padding:10px 12px;
      background:var(--flaeche); border:1px solid var(--rand);
      border-left:3px solid var(--gut); border-radius:10px; margin-bottom:8px;
    }}
    .tor-zeile.gegentor {{border-left-color:var(--schlecht);}}
    .tor-nr {{font-size:11px; color:var(--gedaempft); min-width:20px;}}
    .tor-zeit {{font-size:13px; color:var(--gedaempft); min-width:96px;}}
    .tor-wer {{
      font-size:14px; font-weight:600; color:var(--text);
      flex:0 1 auto; min-width:0; overflow:hidden; text-overflow:ellipsis;
      white-space:nowrap;
    }}
    a.tor-link {{
      font-size:12px; font-weight:600; text-decoration:none; white-space:nowrap;
      padding:5px 11px; border-radius:8px;
      background:var(--akzent); color:{FARBEN["label_innen"]};
    }}
    a.tor-link:hover {{filter:brightness(1.12);}}
    .tor-ohne {{font-size:12px; color:var(--gedaempft); white-space:nowrap;}}
    /* Knopf in der Torzeile schlank halten */
    .tor-knopf [data-testid="stBaseButton-secondary"] {{
      padding:6px 10px; min-height:0; border-radius:8px;
      border:1px solid var(--rand); background:var(--flaeche-hell);
    }}
    .tor-gruppe {{
      font-size:14px; font-weight:700; color:var(--text);
      margin:16px 0 8px 0; padding:8px 10px;
      border-bottom:1px solid var(--rand);
      /* bleibt beim Scrollen oben stehen, bis die naechste Gruppe kommt */
      position:sticky; top:0; z-index:5;
      background:var(--bg); border-radius:8px 8px 0 0;
    }}
    .tor-gruppe span {{font-weight:500; color:var(--gedaempft); font-size:12px;}}
    /* sticky bricht, sobald ein Vorfahr den Ueberlauf abschneidet */
    [data-testid="stVerticalBlock"], [data-testid="stElementContainer"],
    [data-testid="stHorizontalBlock"], [data-testid="stColumn"],
    [data-baseweb="tab-panel"], .stTabs, .stTabs > div {{overflow:visible !important;}}
    .tor-spiel {{
      font-size:13px; color:var(--gedaempft); flex:1 1 0; min-width:0;
      overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
    }}
    .tor-linie {{
      font-size:12px; color:var(--gedaempft); min-width:58px;
    }}
    .tor-stand {{
      font-size:13px; font-weight:700; color:var(--text);
      min-width:46px; text-align:right;
    }}

    /* Resultat eines einzelnen Spiels - bleibt auch schmal einzeilig */
    .scoreboard {{display:flex; align-items:center; justify-content:space-between; gap:10px;}}
    .scoreboard .team {{flex:1 1 0; min-width:0;}}
    .scoreboard .team-right {{text-align:right;}}
    .scoreboard .team-name {{
      font-weight:700; font-size:15px; color:var(--text); overflow-wrap:anywhere;
    }}
    .scoreboard .score {{flex:0 0 auto; text-align:center;}}
    .scoreboard .score-value {{
      font-size:28px; font-weight:700; color:var(--text); line-height:1.15;
    }}

    /* Aufstellung nach Linien */
    .line-card {{
      background:var(--flaeche); border:1px solid var(--rand);
      border-radius:12px; padding:12px; margin-bottom:8px;
    }}
    .line-card strong {{
      color:var(--akzent); font-size:11px; letter-spacing:0.1em; text-transform:uppercase;
    }}
    .line-card hr {{border:0; border-top:1px solid var(--rand); margin:8px 0;}}
    .player-name {{color:var(--text); font-size:14px; margin:5px 0;}}
    .line-card .subtle {{color:var(--gedaempft); font-style:italic;}}

    /* Tabs: deutlich Luft zwischen den Reitern */
    .stTabs [data-baseweb="tab-list"] {{gap:32px; border-bottom:1px solid var(--rand);}}
    .stTabs [data-baseweb="tab"] {{
      font-size:15px; font-weight:600; padding-left:2px; padding-right:2px;
    }}

    /* Handy */
    @media (max-width: 640px) {{
        .block-container, [data-testid="stMainBlockContainer"] {{
            padding-left:0.7rem; padding-right:0.7rem; padding-top:1.2rem;
        }}
        .big-title {{font-size:20px;}}
        .karte {{padding:12px;}}
        .kpi {{flex:1 1 72px; min-width:72px; padding:8px 10px;}}
        .kpi .wert {{font-size:17px;}}
        .scoreboard .score-value {{font-size:22px;}}
        .scoreboard .team-name {{font-size:13px;}}
        /* Torzeile und Abspielknopf nebeneinander halten - Streamlit wuerde
           die Spalten sonst untereinander stapeln. Nur hier, nicht bei den
           Diagrammen und Linienkarten, die sollen stapeln. */
        [data-testid="stHorizontalBlock"]:has(.tor-zeile) {{
          flex-wrap:nowrap !important; gap:6px !important;
        }}
        [data-testid="stHorizontalBlock"]:has(.tor-zeile) [data-testid="stColumn"] {{
          min-width:0 !important; width:auto !important;
        }}
        [data-testid="stHorizontalBlock"]:has(.tor-zeile)
          [data-testid="stColumn"]:first-child {{flex:1 1 auto !important;}}
        [data-testid="stHorizontalBlock"]:has(.tor-zeile)
          [data-testid="stColumn"]:last-child {{flex:0 0 auto !important;}}

        /* innerhalb der Zeile enger, damit alles nebeneinander Platz hat */
        .tor-zeile {{gap:8px; padding:9px 10px;}}
        .tor-zeit {{min-width:0; font-size:12px; white-space:nowrap;}}
        .tor-linie {{min-width:0; font-size:11px; white-space:nowrap;}}
        .tor-stand {{min-width:0; font-size:12px;}}

        /* auf schmalen Bildschirmen weniger Abstand, damit alle Reiter passen */
        .stTabs [data-baseweb="tab-list"] {{gap:16px;}}
        .stTabs [data-baseweb="tab"] {{font-size:13px;}}
        h2 {{font-size:20px !important;}}
        h3 {{font-size:17px !important;}}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------
# Read CSVs
# ---------------------------
# Pro Saison eine eigene Spielerdatei. Neuere Dateien haben zusaetzliche Spalten
# (Block, Schuesse, Balleroberung, Schuesse aufs Tor) - fehlende werden zu NaN.
SPIELER_DATEIEN = [
    "Spieler_Statistik_25_26.csv",
    "Spieler_Statistik_26_27.csv",
]

_teile = []
for _datei in SPIELER_DATEIEN:
    if os.path.exists(_datei):
        _teil = pd.read_csv(_datei, on_bad_lines='skip')
        _teil.columns = _teil.columns.str.strip()
        _teile.append(_teil)

if _teile:
    df = pd.concat(_teile, ignore_index=True, sort=False)
else:
    st.error("Keine Spieler-Statistikdatei gefunden.")
    st.stop()

wygo = pd.read_csv("Statistik_Wygo.csv", sep=",")

# Eine Zeile pro Tor, mit Zeitpunkt und Videolink (optional)
TORE_DATEI = "Tore.csv"
if os.path.exists(TORE_DATEI):
    tore = pd.read_csv(TORE_DATEI)
    tore.columns = tore.columns.str.strip()
else:
    tore = pd.DataFrame(columns=["Match_Id", "Nr", "Halbzeit", "Zeit", "Sekunde",
                                 "Art", "Spieler", "Datei", "Video"])

# ---------------------------
# Clean column names (trim spaces) and normalize
# ---------------------------
wygo.columns = wygo.columns.str.strip()

# Config: Spalten-Namen
MATCH_COL = "Match_Id"
SEASON_COL = "Saison"

# ---------------------------
# Match_Id in beiden Tabellen auf den gleichen Typ bringen
# ---------------------------
def normalize_match_col(df_obj):
    if MATCH_COL in df_obj.columns:
        converted = pd.to_numeric(df_obj[MATCH_COL], errors="coerce")
        # nur uebernehmen, wenn dadurch keine Werte verloren gehen
        if converted.notna().sum() == df_obj[MATCH_COL].notna().sum():
            df_obj[MATCH_COL] = converted

normalize_match_col(df)
normalize_match_col(wygo)
normalize_match_col(tore)


def _mit_spielstand(tore_df):
    """Spalte 'Stand' ergaenzen: Spielstand unmittelbar nach diesem Tor."""
    if tore_df.empty:
        tore_df["Stand"] = []
        return tore_df
    staende = {}
    for _, gruppe in tore_df.groupby(MATCH_COL, sort=False):
        wygo_tore = gegner_tore = 0
        for idx, r in gruppe.sort_values("Nr").iterrows():
            if str(r.get("Art", "")).strip() == "Tor":
                wygo_tore += 1
            else:
                gegner_tore += 1
            staende[idx] = f"{wygo_tore}:{gegner_tore}"
    tore_df["Stand"] = tore_df.index.map(staende)
    return tore_df


tore = _mit_spielstand(tore)

# ---------------------------
# Datum in wygo parsen (Format im CSV ist Tag.Monat.Jahr)
# ---------------------------
if "Datum" in wygo.columns:
    wygo["Datum_parsed"] = pd.to_datetime(wygo["Datum"], errors="coerce", dayfirst=True)
else:
    wygo["Datum_parsed"] = pd.NaT
wygo["Datum_label"] = wygo["Datum_parsed"].dt.strftime("%d.%m.%Y").fillna("ohne Datum")

# Fehlende Spalten absichern
if "Gegner" not in wygo.columns:
    wygo["Gegner"] = "Gegner unbekannt"
if "Tore Gegner" not in wygo.columns:
    wygo["Tore Gegner"] = 0
if "Tore Wygorazzi" not in wygo.columns:
    wygo["Tore Wygorazzi"] = 0

# ---------------------------
# Saisons ermitteln (neueste zuerst)
# ---------------------------
def saison_sort_key(s):
    """'25/26' -> 2025, damit Saisons chronologisch sortiert werden."""
    m = re.match(r"\s*(\d{2,4})\s*/", str(s))
    if not m:
        return -1
    jahr = int(m.group(1))
    return jahr + 2000 if jahr < 100 else jahr

if SEASON_COL in wygo.columns:
    wygo[SEASON_COL] = wygo[SEASON_COL].astype(str).str.strip()
else:
    wygo[SEASON_COL] = "Unbekannt"

saison_options = sorted(
    [s for s in wygo[SEASON_COL].unique() if s and s.lower() != "nan"],
    key=saison_sort_key,
    reverse=True,
)
if not saison_options:
    saison_options = ["Unbekannt"]

# ---------------------------
# Top header + Dropdowns
# ---------------------------
st.markdown(
    '<div class="kicker">UHC Wygorazzi</div>'
    '<div class="big-title">Spielerstatistik</div>',
    unsafe_allow_html=True,
)

# ---------------------------
# Klick auf ein Resultat im Kopfbereich: ?match=<id> waehlt das Spiel aus
# ---------------------------
_param = st.query_params.get("match")
if _param is not None:
    # einmal merken und die URL wieder aufraeumen, sonst klebt die Auswahl fest
    st.session_state["_ziel_match"] = _param
    st.query_params.clear()
_ziel_match = st.session_state.pop("_ziel_match", None)

col_saison, col_spiel = st.columns([1, 2])

# Default = aktuellste Saison (erster Eintrag der absteigend sortierten Liste)
with col_saison:
    selected_saison = st.selectbox("Saison:", saison_options, index=0)

# Spiele der gewaehlten Saison, neueste zuerst. Cupspiele bleiben oben
# draussen - Kopfzeile, Auswahl und alle Auswertungen zeigen nur die
# Meisterschaft. Bei "Wygo - Gesamt- und Saisonkennzahlen" ganz unten
# zaehlen sie weiterhin mit.
wygo_saison = wygo[wygo[SEASON_COL] == selected_saison].copy()
if "Format" in wygo_saison.columns:
    wygo_saison = wygo_saison[~wygo_saison["Format"].astype(str).str.strip()
                              .str.lower().eq("cup")]
wygo_saison = wygo_saison.sort_values(
    ["Datum_parsed", MATCH_COL], ascending=[False, False], na_position="last"
).reset_index(drop=True)

# In der Auswahl stehen auch die Cupspiele, erkennbar an der Marke "(Cup)".
# Die Kopfzeile und die Saisonauswertungen bleiben ohne sie.
wygo_auswahl = wygo[wygo[SEASON_COL] == selected_saison].sort_values(
    ["Datum_parsed", MATCH_COL], ascending=[False, False], na_position="last")

# Label -> Match_Id (kein Zurueckparsen des Labels noetig)
match_lookup = {}
match_options = ["Alle Spiele"]
for _, r in wygo_auswahl.iterrows():
    label = f"{r['Datum_label']} - vs {r['Gegner']}"
    if str(r.get("Format", "")).strip().lower() == "cup":
        label += " (Cup)"
    if label in match_lookup:
        label = f"{label} (#{r[MATCH_COL]})"
    match_lookup[label] = r[MATCH_COL]
    match_options.append(label)

# Kam ein Spiel ueber die URL, dessen Label in die Auswahl schreiben.
# Direkt in den session_state, weil `index` bei bestehendem Key ignoriert wird.
_spiel_key = f"spiel_{selected_saison}"
if _ziel_match is not None:
    for _label, _mid in match_lookup.items():
        if str(_mid) == str(_ziel_match) or str(int(float(_mid))) == str(_ziel_match):
            st.session_state[_spiel_key] = _label
            break

with col_spiel:
    selection = st.selectbox("Wähle ein Spiel:", match_options, index=0, key=_spiel_key)



def _ja(spalte, zeilen):
    if spalte not in zeilen.columns:
        return pd.Series(False, index=zeilen.index)
    return zeilen[spalte].astype(str).str.strip().str.lower().eq("ja")


def render_saison_kopf(zeilen, saison):
    """Bilanz der Saison auf einen Blick: Kennzahlen und Resultate als Chips."""
    if zeilen.empty:
        st.markdown(f"<div class='subtle'>Saison {saison} — keine Spiele erfasst</div>",
                    unsafe_allow_html=True)
        return

    tore = pd.to_numeric(zeilen["Tore Wygorazzi"], errors="coerce").fillna(0)
    gegen = pd.to_numeric(zeilen["Tore Gegner"], errors="coerce").fillna(0)
    siege, remis, nieder = int(_ja("Sieg", zeilen).sum()), \
        int(_ja("Unentschieden", zeilen).sum()), int(_ja("Niederlage", zeilen).sum())
    diff = int(tore.sum() - gegen.sum())
    diff_klasse = "gut" if diff > 0 else ("schlecht" if diff < 0 else "neutral")

    kpis = [
        (f"{len(zeilen)}", "Spiele"),
        (f"<span class='gut'>{siege}</span>-{remis}-<span class='schlecht'>{nieder}</span>",
         "S-U-N"),
        (f"{int(tore.sum())}:{int(gegen.sum())}", "Tore"),
        (f"<span class='{diff_klasse}'>{diff:+d}</span>", "Differenz"),
    ]
    kpi_html = "".join(
        f"<div class='kpi'><div class='wert'>{w}</div><div class='bez'>{b}</div></div>"
        for w, b in kpis
    )

    # Resultate chronologisch, aktuellstes zuletzt
    chrono = zeilen.sort_values(["Datum_parsed", MATCH_COL], na_position="first")
    chips = []
    for _, r in chrono.iterrows():
        t, g = int(pd.to_numeric(r["Tore Wygorazzi"], errors="coerce") or 0), \
            int(pd.to_numeric(r["Tore Gegner"], errors="coerce") or 0)
        if str(r.get("Sieg", "")).strip().lower() == "ja":
            klasse = "sieg"
        elif str(r.get("Unentschieden", "")).strip().lower() == "ja":
            klasse = "remis"
        else:
            klasse = "nieder"
        titel = f"{r.get('Datum_label', '')} vs {r.get('Gegner', '')}"
        mid = r.get(MATCH_COL)
        ziel = "" if pd.isna(mid) else str(int(mid))
        chips.append(
            f"<a class='chip {klasse}' href='?match={ziel}' target='_self' "
            f"title='{titel}'>{t}:{g}</a>"
        )

    st.markdown(
        f"<div class='karte'>"
        f"<div class='subtle'>Saison {saison}</div>"
        f"<div class='kpi-reihe'>{kpi_html}</div>"
        f"<div class='chips'>{''.join(chips)}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


render_saison_kopf(wygo_saison, selected_saison)

selected_match_id = match_lookup.get(selection)

# ---------------------------
# Spielerdaten auf die gewaehlte Saison einschraenken
# ---------------------------
saison_match_ids = wygo_saison[MATCH_COL].dropna().tolist()
if MATCH_COL in df.columns:
    df_saison = df[df[MATCH_COL].isin(saison_match_ids)].copy()
else:
    df_saison = df.iloc[0:0].copy()

# Welcher Datensatz wird geplottet: ganze Saison oder ein einzelnes Spiel
if selected_match_id is None:
    df_for_plots = df_saison.copy()
else:
    # auch ein Cupspiel soll seine Zahlen zeigen, falls welche erfasst sind
    df_for_plots = df[df[MATCH_COL] == selected_match_id].copy()

# ---------------------------
# Ensure numeric preprocessing for df_for_plots (fixes PlusMinus, Punkte, etc.)
# ---------------------------
def preprocess_player_stats(df_in):
    # Coerce columns to numeric where needed, fillna with 0
    for col in ["Plus", "Minus", "T", "A", "Bully-Plus", "Bully-Minus", "Linie-Plus", "Linie-Minus",
                "Strafen", "Block", "Schüsse", "Balleroberung", "Schüsse aufs Tor"]:
        if col in df_in.columns:
            df_in[col] = pd.to_numeric(df_in[col].replace("-", np.nan), errors="coerce").fillna(0)
    # Compute PlusMinus
    if ("Plus" in df_in.columns) and ("Minus" in df_in.columns):
        df_in["PlusMinus"] = df_in["Plus"] - df_in["Minus"]
    else:
        df_in["PlusMinus"] = pd.to_numeric(df_in.get("PlusMinus", 0), errors="coerce").fillna(0)
    # Punkte
    if "T" in df_in.columns and "A" in df_in.columns:
        df_in["Punkte"] = df_in["T"].fillna(0) + df_in["A"].fillna(0)
    else:
        df_in["Punkte"] = pd.to_numeric(df_in.get("Punkte", 0), errors="coerce").fillna(0)
    # Linie PlusMinus
    if "Linie-Plus" in df_in.columns and "Linie-Minus" in df_in.columns:
        df_in["PlusMinus_L"] = df_in["Linie-Plus"] - df_in["Linie-Minus"]
    else:
        # fallback aggregate by Linie if PlusMinus exists
        if "PlusMinus" in df_in.columns and "Linie" in df_in.columns:
            # compute on-the-fly if needed (not stored per-player)
            df_in["PlusMinus_L"] = df_in.get("PlusMinus_L", 0)
        else:
            df_in["PlusMinus_L"] = df_in.get("PlusMinus_L", 0)
    # Hilfsspalten fuer die Quoten (jeweils Plus + Minus = Anzahl Situationen)
    for basis in ["Bully", "Powerplay", "Boxplay"]:
        pl, mi = f"{basis}-Plus", f"{basis}-Minus"
        if pl in df_in.columns and mi in df_in.columns:
            df_in[f"{basis}-Gesamt"] = df_in[pl] + df_in[mi]
        else:
            df_in[f"{basis}-Gesamt"] = 0
    # Linie als saubere Ziffer: aus 1.0 oder " 1 " wird "1", aus leer wird "0".
    # Sonst vergleichen nur_linien() und nur_feldspieler() gegen "1.0" ins Leere.
    if "Linie" in df_in.columns:
        df_in["Linie"] = (pd.to_numeric(df_in["Linie"], errors="coerce")
                          .fillna(0).astype(int).astype(str))
    else:
        df_in["Linie"] = "0"
    return df_in

# Preprocess the df_for_plots (so single-match and all-plots use same cleaned data)
df_for_plots = preprocess_player_stats(df_for_plots)

# Auch den Saison-Datensatz fuer die "Alle Spiele"-Ansicht aufbereiten
df_saison = preprocess_player_stats(df_saison)

# ---------------------------
# Function: generic top-bar plots using df_for_plots
# ---------------------------
def plot_top(df_in, column, title):
    # ohne Kopie wuerde eine fehlende Spalte im DataFrame des Aufrufers landen
    d = df_in if column in df_in.columns else df_in.assign(**{column: 0})
    top = d.groupby("Name")[column].sum().sort_values(ascending=False).reset_index()
    fig = px.bar(top, x="Name", y=column, title=title, text=column)
    fig.update_traces(texttemplate='%{text:.0f}', textposition='inside', textangle=0, showlegend=False)

    return _style_plot(fig)

def plot_plusminus(df_in, titel="Plus-Minus"):
    """Plus-Minus je Spieler: gruen ueber null, rot darunter.

    Ueber der Bilanz stehen die beiden Einzelwerte - wie viele Plus und wie
    viele Minus daraus entstanden sind. Die Achse bekommt ganzzahlige
    Schritte, damit ein +1 oder -1 ueberhaupt sichtbar ist, und die Zahlen
    rutschen aus dem Balken heraus, sobald er zu flach dafuer ist.
    """
    if "PlusMinus" not in df_in.columns or df_in.empty:
        return None
    d = df_in.copy()
    for spalte in ("Plus", "Minus"):
        d[spalte] = pd.to_numeric(d.get(spalte, 0), errors="coerce").fillna(0)
    top = (d.groupby("Name")[["PlusMinus", "Plus", "Minus"]].sum()
           .sort_values("PlusMinus", ascending=False).reset_index())
    if top.empty:
        return None

    groesster = max(abs(float(v)) for v in top["PlusMinus"]) or 1
    # Balken unter gut einem Fuenftel des groessten haben innen keinen Platz
    schwelle = groesster * 0.3
    stellen = ["inside" if abs(float(v)) >= schwelle else "outside"
               for v in top["PlusMinus"]]

    def _label(pm, plus, minus, aussen):
        # aussen steht der Text auf dunklem Grund, innen auf hellem Balken -
        # die beiden Einzelwerte brauchen darum je eigene Farben
        gut = FARBEN["gut"] if aussen else FARBEN["label_gut"]
        schlecht = FARBEN["schlecht"] if aussen else FARBEN["label_schlecht"]
        bilanz = f"{pm:+.0f}" if pm else "0"
        return (f'<span style="color:{gut}">{plus:.0f}</span>  '
                f'<span style="color:{schlecht}">{minus:.0f}</span><br>'
                f'<b>{bilanz}</b>')

    top["Farbe"] = [FARBEN["gut"] if v > 0 else FARBEN["schlecht"] if v < 0
                    else FARBEN["neutral"] for v in top["PlusMinus"]]
    top["Label"] = [_label(pm, p, m, stelle == "outside")
                    for pm, p, m, stelle in zip(top["PlusMinus"], top["Plus"],
                                                top["Minus"], stellen)]

    fig = px.bar(top, x="Name", y="PlusMinus", title=titel, text="Label")
    fig.update_traces(marker_color=list(top["Farbe"]), textposition=stellen,
                      textangle=0, cliponaxis=False, showlegend=False)

    # ganzzahlige Achsenschritte und Luft fuer die zweizeiligen Zahlen aussen
    schritt = 1 if groesster <= 8 else 2 if groesster <= 20 else 5 if groesster <= 50 else 10
    luft = max(2 * schritt, groesster * 0.3)
    unten = min(0.0, float(top["PlusMinus"].min()) - luft)
    oben = max(0.0, float(top["PlusMinus"].max()) + luft)
    fig = _style_plot(fig, textfix=False)
    fig.update_yaxes(dtick=schritt, range=[unten, oben], zeroline=True,
                     zerolinewidth=2, zerolinecolor=FARBEN["gedaempft"])
    return fig


def plot_zuspiele(tore_zeilen,
                  titel="Tore je Paar — einer legt auf, der andere trifft "
                        "(T = selbst getroffen, A = Assist gegeben)"):
    """Welches Paar zusammen am meisten trifft - aus der Spalte Assist.

    Gezaehlt wird in beide Richtungen: legt A dem B auf oder B dem A, gehoert
    das Tor demselben Paar. Ueber dem Balken steht je Spieler, wie viele der
    gemeinsamen Tore er selbst erzielt und wie viele er aufgelegt hat. Die
    Farben sind bei jedem Paar dieselben wie sonst im Dashboard: der
    erstgenannte Name gruen, der zweite rot.
    """
    if tore_zeilen is None or tore_zeilen.empty or "Assist" not in tore_zeilen.columns:
        return None
    eigene = tore_zeilen[tore_zeilen["Art"].astype(str).str.strip() == "Tor"]
    richtung = {}
    for _, r in eigene.iterrows():
        geber = str(r.get("Assist") or "").strip()
        nehmer = str(r.get("Spieler") or "").strip()
        if not geber or geber.lower() == "nan" or not nehmer or nehmer.lower() == "nan":
            continue
        if geber == nehmer:        # sich selbst auflegen geht nicht - Tippfehler
            continue
        richtung[(geber, nehmer)] = richtung.get((geber, nehmer), 0) + 1
    if not richtung:
        return None

    paare = {}
    for (geber, nehmer), n in richtung.items():
        paare.setdefault(tuple(sorted((geber, nehmer))), {})[geber] = n

    zeilen = []
    for (a_name, b_name), teile in paare.items():
        # der haeufigere Vorbereiter steht vorn
        erst, zweit = ((a_name, b_name) if teile.get(a_name, 0) >= teile.get(b_name, 0)
                       else (b_name, a_name))
        auf_erst, auf_zweit = teile.get(erst, 0), teile.get(zweit, 0)
        f_erst, f_zweit = FARBEN["gut"], FARBEN["schlecht"]
        zeilen.append({
            "Paar": f"{erst} + {zweit}",
            "Tore": auf_erst + auf_zweit,
            # wer auflegt, bringt den anderen zum Tor: Tore = Zuspiele des Partners
            "Label": (f'<b>{auf_erst + auf_zweit}</b><br>'
                      f'<span style="color:{f_erst};font-size:11px">'
                      f'{auf_zweit} T / {auf_erst} A</span><br>'
                      f'<span style="color:{f_zweit};font-size:11px">'
                      f'{auf_erst} T / {auf_zweit} A</span>'),
            "Achse": (f'<span style="color:{f_erst}">{erst}</span>'
                      f' + <span style="color:{f_zweit}">{zweit}</span>'),
        })
    daten = pd.DataFrame(zeilen).sort_values("Tore", ascending=False)

    fig = px.bar(daten, x="Paar", y="Tore", title=titel, text="Label")
    fig.update_traces(textposition="outside", textangle=0, marker_color=FARBEN["balken"],
                      cliponaxis=False, showlegend=False)
    fig = _style_plot(fig, textfix=False)
    # Namen auf der Achse in denselben Farben wie die Zahlen darueber
    fig.update_xaxes(tickmode="array", tickvals=list(daten["Paar"]),
                     ticktext=list(daten["Achse"]))
    # Luft nach oben, sonst steht die Zahl des hoechsten Balkens ausserhalb
    hoechster = float(daten["Tore"].max())
    fig.update_yaxes(dtick=1 if hoechster <= 12 else 2,
                     range=[0, hoechster + max(3.0, hoechster * 0.55)])
    return fig


def plot_bully(df_in):
    if "Bully-Plus" not in df_in.columns:
        df_in["Bully-Plus"] = 0
    if "Bully-Minus" not in df_in.columns:
        df_in["Bully-Minus"] = 0
    bully = df_in.groupby("Name")[["Bully-Plus", "Bully-Minus"]].sum().reset_index()
    denom = (bully["Bully-Plus"] + bully["Bully-Minus"]).replace({0: np.nan})
    bully["Bully-Gewinn %"] = 100 * bully["Bully-Plus"] / denom
    bully["Bully-Gewinn %"] = bully["Bully-Gewinn %"].fillna(0)
    top = bully.sort_values("Bully-Gewinn %", ascending=False).copy()
    # unter der Quote die gewonnenen (grün) und verlorenen (rot) Bullys nebeneinander
    top["Label"] = [
        _quote_label(q, g, v)
        for q, g, v in zip(top["Bully-Gewinn %"], top["Bully-Plus"], top["Bully-Minus"])
    ]
    fig = px.bar(top, x="Name", y="Bully-Gewinn %", title="Bully-Gewinnquote", text="Label")
    fig.update_traces(textposition='auto', textangle=0, showlegend=False)
    return _style_plot(fig)

def plot_gespielt(df_in):
    if "Gespielt" not in df_in.columns:
        df_in["Gespielt"] = "Nein"
    # Zähle nur "Ja" Werte pro Spieler
    gespielt = df_in[df_in["Gespielt"] == "Ja"].groupby("Name").size().reset_index(name="Anzahl Spiele")
    top = gespielt.sort_values("Anzahl Spiele", ascending=False)
    fig = px.bar(top, x="Name", y="Anzahl Spiele", title="Anzahl gespielte Spiele", text="Anzahl Spiele")
    fig.update_traces(texttemplate='%{text:.0f}', textposition='inside', textangle=0, showlegend=False)
    return _style_plot(fig)

# ---------------------------
# Erweiterte Statistiken (nur fuer Saisons, in denen die neuen Spalten erfasst sind)
# ---------------------------
SPALTE_BLOCK = "Block"
SPALTE_SCHUESSE = "Schüsse"
SPALTE_BALLEROBERUNG = "Balleroberung"
SPALTE_SAT = "Schüsse aufs Tor"
ERWEITERTE_SPALTEN = [SPALTE_BLOCK, SPALTE_SCHUESSE, SPALTE_BALLEROBERUNG, SPALTE_SAT]


def hat_erweiterte_daten(df_in):
    """True, wenn die neuen Spalten vorhanden und nicht durchgehend 0 sind."""
    if df_in.empty:
        return False
    vorhanden = [c for c in ERWEITERTE_SPALTEN if c in df_in.columns]
    if not vorhanden:
        return False
    return float(df_in[vorhanden].fillna(0).to_numpy().sum()) > 0


def nur_feldspieler(df_in):
    """Torhueter und Ersatzbank haben Linie 0 - die zaehlen bei Feldwerten nicht mit."""
    return df_in[df_in["Linie"].astype(str) != "0"]


def nur_torhueter(df_in):
    """Eingesetzte Torhueter: Linie 0 und tatsaechlich gespielt."""
    d = df_in[df_in["Linie"].astype(str) == "0"]
    if "Gespielt" in d.columns:
        d = d[d["Gespielt"].astype(str).str.strip() == "Ja"]
    return d


def _zahl(v):
    """Ganze Zahlen ohne Nachkommastelle, sonst eine."""
    return f"{v:.0f}" if abs(v - round(v)) < 1e-9 else f"{v:.1f}"


def _quote_label(quote, gut, schlecht, teiler=1):
    """Prozent gross, darunter Treffer grün und Fehlschläge rot."""
    return (f'{quote:.1f}%<br>'
            f'<span style="color:{FARBEN["label_gut"]}">{_zahl(gut / teiler)}</span>'
            f'\u00a0\u00a0'
            f'<span style="color:{FARBEN["label_schlecht"]}">{_zahl(schlecht / teiler)}</span>')


def _textposition_anpassen(fig):
    """Labels flacher Balken nach aussen setzen.

    Ein Balken mit Wert 0 hat keine Höhe - ein Label 'inside' wäre unsichtbar,
    und genau dort steht die interessante Information (z.B. 0%).
    """
    for tr in fig.data:
        if tr.y is None:
            continue
        # nur echte Nullen nach aussen - sonst steht der Wert immer im Balken
        tr.textposition = [
            "outside" if (y is None or abs(float(y)) < 1e-9) else "inside"
            for y in tr.y
        ]
    return fig


def _style_plot(fig, tickangle=-90, textfix=True):
    """Einheitliche Formatierung - kompakt genug fuer Handy-Bildschirme.

    `textfix=False` für gestapelte Balken: dort kennt Plotly kein 'outside'.
    """
    fig.update_layout(
        yaxis_title=None,
        xaxis_title=None,
        title_x=0.02,
        title_font_size=16,
        font=dict(size=11),
        # gedrehte Spielernamen brauchen unten Platz, waagrechte Labels nicht
        margin=dict(t=45, b=115 if tickangle else 45, l=8, r=8),
        height=430,
        xaxis=dict(tickangle=tickangle, automargin=True),
        yaxis=dict(automargin=True),
        # Legende unter den Plot, damit sie auf dem Handy keine Breite frisst
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0),
    )
    fig.update_layout(
        modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"],
        colorway=[FARBEN["balken"], FARBEN["gut"], FARBEN["warn"], FARBEN["schlecht"]],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=FARBEN["text"],
        title_font_color=FARBEN["text"],
        xaxis=dict(tickangle=tickangle, automargin=True, showgrid=False,
                   linecolor=FARBEN["rand"], tickcolor=FARBEN["rand"]),
        yaxis=dict(automargin=True, gridcolor=FARBEN["rand"], zerolinecolor=FARBEN["rand"]),
    )
    # dunkler Text auf hellen Balken, heller Text ausserhalb
    fig.update_traces(insidetextfont_color=FARBEN["label_innen"],
                      outsidetextfont_color=FARBEN["label_aussen"],
                      selector=dict(type="bar"))
    if textfix:
        _textposition_anpassen(fig)
    return fig


def plot_summe(df_in, column, title, ohne_torhueter=True):
    """Einfacher Summen-Balken pro Spieler."""
    d = nur_feldspieler(df_in) if ohne_torhueter else df_in
    if column not in d.columns or d.empty:
        return None
    # auch bei lauter Nullen anzeigen, sonst fehlt der Plot in einzelnen Spielen
    top = d.groupby("Name")[column].sum().sort_values(ascending=False).reset_index()
    fig = px.bar(top, x="Name", y=column, title=title, text=column)
    fig.update_traces(texttemplate='%{text:.0f}', textposition='inside', textangle=0, showlegend=False)
    return _style_plot(fig)


def plot_quote(df_in, zaehler, nenner, title, ohne_torhueter=True):
    """Prozentquote zaehler/nenner pro Spieler. Spieler ohne Nenner fallen raus.

    Unter der Quote stehen Treffer grün und der Rest (Nenner - Zähler) rot.
    """
    d = nur_feldspieler(df_in) if ohne_torhueter else df_in
    if zaehler not in d.columns or nenner not in d.columns or d.empty:
        return None
    agg = d.groupby("Name")[[zaehler, nenner]].sum()
    agg = agg[agg[nenner] > 0]
    if agg.empty:
        return None
    agg["Quote"] = 100 * agg[zaehler] / agg[nenner]
    # nach der Quote sortiert, im Balken steht Prozent, Treffer und Rest
    top = agg.sort_values("Quote", ascending=False).reset_index()
    top["Label"] = [_quote_label(q, z, n - z) for q, z, n in
                    zip(top["Quote"], top[zaehler], top[nenner])]
    fig = px.bar(top, x="Name", y="Quote", title=title, text="Label")
    fig.update_traces(textangle=0, showlegend=False)
    return _style_plot(fig)


def plot_fangquote(df_in):
    """Torhueter-Fangquote = 100 / (Minus + Block) * Block."""
    tw = nur_torhueter(df_in)
    if tw.empty or SPALTE_BLOCK not in tw.columns:
        return None
    agg = tw.groupby("Name")[[SPALTE_BLOCK, "Minus"]].sum()
    agg["Gesamt"] = agg[SPALTE_BLOCK] + agg["Minus"]
    agg = agg[agg["Gesamt"] > 0]
    if agg.empty:
        return None
    agg["Fangquote"] = 100 * agg[SPALTE_BLOCK] / agg["Gesamt"]
    top = agg.sort_values("Fangquote", ascending=False).reset_index()
    top["Label"] = [_quote_label(q, b, m) for q, b, m in
                    zip(top["Fangquote"], top[SPALTE_BLOCK], top["Minus"])]
    fig = px.bar(top, x="Name", y="Fangquote", title="Torhüter-Fangquote", text="Label")
    fig.update_traces(textangle=0, showlegend=False)
    return _style_plot(fig)


def _eintrag(fig, hinweis=None, breit=False):
    """Plot fuers Kartenraster vorbereiten - der Titel wandert in die Karte.

    breit=True erzwingt die volle Breite, auch wenn der Plot wenige
    Kategorien hat.
    """
    if fig is None:
        return (hinweis or "Keine Daten", None, 0)
    titel = fig.layout.title.text or ""
    # title_text="" statt title=None: None landet im Browser als "undefined"
    fig.update_layout(title_text="",
                      margin=dict(t=4, b=fig.layout.margin.b, l=8,
                                  r=fig.layout.margin.r))
    kategorien = len({str(x) for tr in fig.data
                      for x in (tr.x if tr.x is not None else [])})
    return (titel, fig, 999 if breit else kategorien)


def _karte(titel, fig, hoehe=None):
    with st.container(border=True):
        st.markdown(f"<div class='chart-titel'>{titel}</div>", unsafe_allow_html=True)
        if fig is None:
            st.markdown("<div class='chart-leer'>keine Daten in dieser Auswahl</div>",
                        unsafe_allow_html=True)
            return
        if hoehe:
            fig.update_layout(height=hoehe)
        st.plotly_chart(fig, width="stretch", config={'staticPlot': True})


def raster(*eintraege, schmal_bis=6):
    """Kompakte Diagramme paarweise nebeneinander, breite ueber die volle Breite.

    Streamlit stapelt die Spalten auf schmalen Bildschirmen von selbst.
    """
    wartend = []

    def leeren():
        while wartend:
            paar = wartend[:2]
            del wartend[:2]
            for spalte, (titel, fig, _) in zip(st.columns(len(paar), gap="medium"), paar):
                with spalte:
                    _karte(titel, fig, hoehe=330)

    for eintrag in eintraege:
        if eintrag is None:
            continue
        titel, fig, anzahl = eintrag
        if fig is None or anzahl <= schmal_bis:
            wartend.append(eintrag)
        else:
            leeren()
            _karte(titel, fig)
    leeren()


def plot_torschuss_anteile(df_in, gegentore=None):
    """Team: wie sich die gegnerischen Torschüsse auf Block / Parade / Gegentor verteilen."""
    if SPALTE_BLOCK not in df_in.columns:
        return None

    feld = nur_feldspieler(df_in)
    tw = nur_torhueter(df_in)

    geblockt = float(feld[SPALTE_BLOCK].sum())
    gehalten = float(tw[SPALTE_BLOCK].sum()) if not tw.empty else 0.0
    if gegentore is None:
        # Rueckfall: Minus des eingesetzten Torhueters
        gegentore = float(tw["Minus"].sum()) if not tw.empty else 0.0
    gegentore = float(gegentore)

    gesamt = geblockt + gehalten + gegentore
    # ohne erfasste Blocks/Paraden waere der Balken reine Gegentore - irrefuehrend
    if gesamt <= 0 or (geblockt + gehalten) <= 0:
        return None

    daten = pd.DataFrame({
        "Torschüsse": ["Torschüsse gegen Wygorazzi"] * 3,
        "Kategorie": ["Geblockt", "Vom Torhüter gehalten", "Gegentore"],
        "Anzahl": [geblockt, gehalten, gegentore],
    })
    daten["Label"] = [f"{a:.0f} ({100 * a / gesamt:.1f}%)" for a in daten["Anzahl"]]

    # ein grosser Balken = alle Torschuesse gegen Wygorazzi, anteilig aufgeteilt
    fig = px.bar(daten, x="Torschüsse", y="Anzahl", color="Kategorie",
                 title="Anteil von uns geblockten Torschüssen auf unser Tor", text="Label",
                 color_discrete_sequence=[FARBEN["gut"], FARBEN["balken"], FARBEN["schlecht"]])
    fig.update_traces(textposition='inside', textangle=0)
    fig.update_layout(legend_title_text="")
    return _style_plot(fig, tickangle=0, textfix=False)


def plot_abschlussquote(df_in):
    """Team: Schüsse -> davon aufs Tor -> davon im Tor."""
    if SPALTE_SCHUESSE not in df_in.columns or SPALTE_SAT not in df_in.columns:
        return None

    feld = nur_feldspieler(df_in)
    schuesse = float(feld[SPALTE_SCHUESSE].sum())
    sat = float(feld[SPALTE_SAT].sum())
    tore = float(feld["T"].sum())
    if schuesse <= 0:
        return None

    neben = max(schuesse - sat, 0.0)
    gehalten = max(sat - tore, 0.0)

    # Balken 1 = alle Schüsse (100%), Balken 2 = Torschüsse (100%)
    daten = pd.DataFrame({
        "Balken": ["Schüsse", "Schüsse", "Torschüsse", "Torschüsse"],
        "Kategorie": ["Neben das Tor oder geblockt", "Aufs Tor", "Gehalten", "Tor"],
        "Anzahl": [neben, sat, gehalten, tore],
        "Bezug": [schuesse, schuesse, sat, sat],
    })
    daten["Label"] = [
        f"{a:.0f} ({100 * a / b:.1f}%)" if b > 0 else f"{a:.0f}"
        for a, b in zip(daten["Anzahl"], daten["Bezug"])
    ]

    fig = px.bar(daten, x="Balken", y="Anzahl", color="Kategorie",
                 title="Abschlussquote", text="Label",
                 category_orders={"Balken": ["Schüsse", "Torschüsse"],
                                  "Kategorie": ["Neben das Tor oder geblockt", "Aufs Tor", "Gehalten", "Tor"]},
                 color_discrete_map={
                     "Neben das Tor oder geblockt": FARBEN["schlecht"],
                     "Aufs Tor": FARBEN["balken"],
                     "Gehalten": FARBEN["neutral"],
                     "Tor": FARBEN["gut"],
                 })
    fig.update_traces(textposition='inside', textangle=0)
    fig.update_layout(legend_title_text="")
    return _style_plot(fig, tickangle=0, textfix=False)


# ---------------------------
# Powerplay / Boxplay
# Plus  = Powerplay mit eigenem Tor bzw. Boxplay ohne Gegentor (Erfolg)
# Minus = Powerplay ohne Tor bzw. Boxplay mit Gegentor (Misserfolg)
# ---------------------------
SPEZIAL_SPALTEN = ["Powerplay-Plus", "Powerplay-Minus", "Boxplay-Plus", "Boxplay-Minus"]

SPEZIAL_FARBEN = {
    "Mit Tor": FARBEN["gut"],
    "Ohne Tor": FARBEN["schlecht"],
    "Ohne Gegentor": FARBEN["gut"],
    "Mit Gegentor": FARBEN["schlecht"],
}


def hat_spezial_daten(df_in):
    vorhanden = [c for c in SPEZIAL_SPALTEN if c in df_in.columns]
    if not vorhanden or df_in.empty:
        return False
    return float(df_in[vorhanden].fillna(0).to_numpy().sum()) > 0


SPEZIAL_KONFIG = {
    # Situation: (Plus-Spalte, Minus-Spalte, Label Erfolg, Label Misserfolg, Titel)
    "Powerplay": ("Powerplay-Plus", "Powerplay-Minus",
                  "Mit Tor", "Ohne Tor", "Powerplay-Erfolg"),
    "Boxplay": ("Boxplay-Plus", "Boxplay-Minus",
                "Ohne Gegentor", "Mit Gegentor", "Boxplay-Erfolg"),
}


def plot_spezial_team(situationen, situation):
    """Erfolgsquote einer Spezialsituation als ein Balken.

    `situationen` ist ein Dict {Spaltenname: Anzahl} aus Statistik_Wygo.csv.
    Die Spielerspalten taugen dafür nicht: pro Situation sind mehrere Spieler
    markiert, und zum Teil kommen zwei Linien zum Einsatz.
    """
    if not situationen:
        return None
    plus_sp, minus_sp, lab_gut, lab_schlecht, titel = SPEZIAL_KONFIG[situation]

    gut = float(situationen.get(plus_sp, 0) or 0)
    schlecht = float(situationen.get(minus_sp, 0) or 0)
    gesamt = gut + schlecht
    if gesamt <= 0:
        return None

    daten = pd.DataFrame({
        "Situation": [situation, situation],
        "Ausgang": [lab_gut, lab_schlecht],
        "Anzahl": [gut, schlecht],
    })
    daten["Label"] = [f"{a:.0f} ({100 * a / gesamt:.1f}%)" for a in daten["Anzahl"]]

    fig = px.bar(daten, x="Situation", y="Anzahl", color="Ausgang",
                 title=titel, text="Label",
                 category_orders={"Ausgang": [lab_gut, lab_schlecht]},
                 color_discrete_map=SPEZIAL_FARBEN)
    fig.update_traces(textposition='inside', textangle=0)
    fig.update_layout(legend_title_text="")
    return _style_plot(fig, tickangle=0, textfix=False)


# ---------------------------
# Auswertungen pro Linie (Torhüter und Ersatzbank zählen nicht mit)
# ---------------------------
LINIEN = ["1", "2", "3"]


def nur_linien(df_in):
    d = df_in[df_in["Linie"].astype(str).isin(LINIEN)].copy()
    d["Linie_Label"] = "Linie " + d["Linie"].astype(str)
    return d


def plot_linie_summe(df_in, column, title):
    d = nur_linien(df_in)
    if column not in d.columns or d.empty:
        return None
    agg = d.groupby("Linie_Label")[column].sum().reindex(LINIEN_FARBEN).fillna(0).reset_index()
    fig = px.bar(agg, x="Linie_Label", y=column, title=title, text=column,
                 color="Linie_Label", color_discrete_map=LINIEN_FARBEN)
    fig.update_traces(texttemplate='%{text:.0f}', textposition='inside', textangle=0)
    fig.update_layout(showlegend=False)
    return _style_plot(fig, tickangle=0)


def plot_linie_quote(df_in, zaehler, nenner, title, teiler=1):
    """Quote je Linie, darunter Treffer grün und Rest rot.

    `teiler` rechnet Spielermarkierungen in Situationen um: im Powerplay ist
    jede Situation bei 3 Spielern einer Linie markiert, im Boxplay bei 2.
    Die Quote selbst ändert sich dadurch nicht.
    """
    d = nur_linien(df_in)
    if zaehler not in d.columns or nenner not in d.columns or d.empty:
        return None
    agg = d.groupby("Linie_Label")[[zaehler, nenner]].sum()
    agg = agg[agg[nenner] > 0]
    if agg.empty:
        return None
    agg["Quote"] = 100 * agg[zaehler] / agg[nenner]
    agg = agg.reindex([l for l in LINIEN_FARBEN if l in agg.index]).reset_index()
    agg["Label"] = [_quote_label(q, z, n - z, teiler) for q, z, n in
                    zip(agg["Quote"], agg[zaehler], agg[nenner])]
    fig = px.bar(agg, x="Linie_Label", y="Quote", title=title, text="Label",
                 color="Linie_Label", color_discrete_map=LINIEN_FARBEN)
    fig.update_traces(textangle=0)
    fig.update_layout(showlegend=False)
    return _style_plot(fig, tickangle=0)


def linien_bilanz(tore_zeilen):
    """Tore und Gegentore je Linie aus Tore.csv zaehlen.

    Ein Tor kann mehreren Linien zugeordnet sein ("1+3", gemischte Formation).
    Es zaehlt dann fuer beide - die Summe ueber die Linien kann deshalb
    hoeher sein als die Anzahl Tore im Spiel.
    """
    bilanz = {l: {"Tor": 0, "Gegentor": 0} for l in LINIEN}
    if tore_zeilen is None or tore_zeilen.empty:
        return bilanz
    for _, r in tore_zeilen.iterrows():
        art = "Tor" if str(r.get("Art", "")).strip() == "Tor" else "Gegentor"
        roh = str(r.get("Linie", "") or "")
        for teil in roh.replace(";", "+").split("+"):
            teil = teil.strip().removesuffix(".0")
            if teil in bilanz:
                bilanz[teil][art] += 1
    return bilanz


def plot_linie_plusminus(tore_zeilen):
    """Plus-Minus je Linie, gerechnet aus den einzelnen Toren."""
    bilanz = linien_bilanz(tore_zeilen)
    aktiv = {l: w for l, w in bilanz.items() if w["Tor"] or w["Gegentor"]}
    if not aktiv:
        return None

    daten = pd.DataFrame([
        {"Linie_Label": f"Linie {l}", "Tore": w["Tor"], "Gegentore": w["Gegentor"],
         "PlusMinus": w["Tor"] - w["Gegentor"]}
        for l, w in sorted(aktiv.items())
    ])
    daten["Label"] = [
        f'{pm:+.0f}<br>'
        f'<span style="color:{FARBEN["label_gut"]}">{t:.0f}</span>'
        f'\u00a0\u00a0'
        f'<span style="color:{FARBEN["label_schlecht"]}">{g:.0f}</span>'
        for pm, t, g in zip(daten["PlusMinus"], daten["Tore"], daten["Gegentore"])
    ]
    fig = px.bar(daten, x="Linie_Label", y="PlusMinus", title="Plus-Minus je Linie",
                 text="Label", color="Linie_Label", color_discrete_map=LINIEN_FARBEN)
    fig.update_traces(textangle=0)
    fig.update_layout(showlegend=False)
    return _style_plot(fig, tickangle=0)


# ---------------------------
# Tab-Inhalte
# ---------------------------
TEAM_SPEZIAL_SPALTEN = ["Powerplay-Plus", "Powerplay-Minus", "Boxplay-Plus", "Boxplay-Minus"]


def team_situationen(wygo_zeilen):
    """Powerplay-/Boxplay-Situationen aus Statistik_Wygo.csv aufsummieren."""
    if wygo_zeilen is None or len(wygo_zeilen) == 0:
        return {}
    werte = {}
    for spalte in TEAM_SPEZIAL_SPALTEN:
        if spalte in wygo_zeilen.columns:
            werte[spalte] = float(
                pd.to_numeric(wygo_zeilen[spalte], errors="coerce").fillna(0).sum()
            )
    return werte


def tab_pro_spieler(df_in, zeige_gespielt=False, spiele=None):
    eintraege = [
        _eintrag(plot_top(df_in, "T", "Tore")),
        _eintrag(plot_top(df_in, "A", "Assists")),
        _eintrag(plot_top(df_in, "Punkte", "Punkte (T+A)")),
        _eintrag(plot_plusminus(df_in), "Plus-Minus"),
        _eintrag(plot_top(df_in, "Strafen", "Strafen")),
        _eintrag(plot_bully(df_in), "Bully-Gewinnquote"),
    ]
    if hat_erweiterte_daten(df_in):
        eintraege += [
            _eintrag(plot_summe(df_in, SPALTE_BLOCK, "Geblockte Schüsse"),
                     "Geblockte Schüsse"),
            _eintrag(plot_fangquote(df_in), "Torhüter-Fangquote"),
            _eintrag(plot_summe(df_in, SPALTE_BALLEROBERUNG, "Balleroberungen"),
                     "Balleroberungen"),
            _eintrag(plot_summe(df_in, SPALTE_SCHUESSE, "Schüsse pro Spieler"),
                     "Schüsse pro Spieler"),
            _eintrag(plot_quote(df_in, SPALTE_SAT, SPALTE_SCHUESSE, "Schüsse aufs Tor"),
                     "Schüsse aufs Tor"),
            _eintrag(plot_quote(df_in, "T", SPALTE_SAT, "Torquote aus den Torschüssen"),
                     "Torquote aus den Torschüssen"),
        ]
    if hat_spezial_daten(df_in):
        eintraege += [
            _eintrag(plot_quote(df_in, "Powerplay-Plus", "Powerplay-Gesamt",
                                "Powerplay-Erfolgsquote"), "Powerplay-Erfolgsquote"),
            _eintrag(plot_quote(df_in, "Boxplay-Plus", "Boxplay-Gesamt",
                                "Boxplay-Erfolgsquote"), "Boxplay-Erfolgsquote"),
        ]
    # Die beiden Uebersichten zum Schluss: eine Zahl je Spieler und wer wann
    # geliefert hat. Beide brauchen die volle Breite.
    eintraege += [e for e in (
        _eintrag(plot_game_score(df_in), breit=True),
        _eintrag(plot_punkte_teppich(df_in, spiele), breit=True)
        if spiele is not None else None,
    ) if e is not None and e[1] is not None]
    if zeige_gespielt:
        eintraege.append(_eintrag(plot_gespielt(df_in), "Anzahl gespielte Spiele"))
    raster(*eintraege)


def tab_pro_linie(df_in, tore_zeilen=None):
    eintraege = [
        _eintrag(plot_linie_plusminus(tore_zeilen), "Plus-Minus je Linie"),
        _eintrag(plot_linie_summe(df_in, "Strafen", "Strafen je Linie"),
                 "Strafen je Linie"),
        _eintrag(plot_linie_quote(df_in, "Bully-Plus", "Bully-Gesamt",
                                  "Bully-Gewinnquote je Linie"), "Bully-Gewinnquote je Linie"),
    ]
    if hat_erweiterte_daten(df_in):
        eintraege += [
            _eintrag(plot_linie_summe(df_in, SPALTE_BLOCK, "Geblockte Schüsse je Linie"),
                     "Geblockte Schüsse je Linie"),
            _eintrag(plot_linie_summe(df_in, SPALTE_BALLEROBERUNG, "Balleroberungen je Linie"),
                     "Balleroberungen je Linie"),
            _eintrag(plot_linie_summe(df_in, SPALTE_SCHUESSE, "Schüsse je Linie"),
                     "Schüsse je Linie"),
            _eintrag(plot_linie_quote(df_in, SPALTE_SAT, SPALTE_SCHUESSE,
                                      "Schüsse aufs Tor je Linie"), "Schüsse aufs Tor je Linie"),
            _eintrag(plot_linie_quote(df_in, "T", SPALTE_SAT,
                                      "Torquote aus den Torschüssen je Linie"),
                     "Torquote aus den Torschüssen je Linie"),
        ]
    if hat_spezial_daten(df_in):
        # je Situation sind im Powerplay 3 Spieler markiert, im Boxplay 2
        eintraege += [
            _eintrag(plot_linie_quote(df_in, "Powerplay-Plus", "Powerplay-Gesamt",
                                      "Powerplay-Erfolgsquote je Linie", teiler=3),
                     "Powerplay-Erfolgsquote je Linie"),
            _eintrag(plot_linie_quote(df_in, "Boxplay-Plus", "Boxplay-Gesamt",
                                      "Boxplay-Erfolgsquote je Linie", teiler=2),
                     "Boxplay-Erfolgsquote je Linie"),
        ]
    raster(*eintraege)


# ---------------------------
# Saisonverlauf, Torzeiten und Gegnerbilanz
# ---------------------------
def _spiel_label(zeile):
    """'25.10 Merenschwand' - kurz genug fuer die Achse."""
    tag = str(zeile.get("Datum_label", ""))
    tag = "" if tag.startswith("ohne") else tag[:6].rstrip(".") + " "
    return f"{tag}{str(zeile.get('Gegner', ''))[:14]}"


def _spielfolge(spiele):
    """Die Spiele der Auswahl in zeitlicher Folge: [(Match_Id, Beschriftung), ...]."""
    if spiele is None or spiele.empty:
        return []
    d = spiele.sort_values(["Datum_parsed", MATCH_COL], na_position="first")
    folge, gesehen = [], set()
    for _, r in d.iterrows():
        mid = r.get(MATCH_COL)
        if pd.isna(mid) or mid in gesehen:
            continue
        gesehen.add(mid)
        folge.append((mid, _spiel_label(r)))
    return folge


# Klar unterscheidbare Farben - eine je Spieler, in beiden Verlaufskarten
# dieselbe. Reihenfolge so gewaehlt, dass Nachbarn nie aehnlich sind.
KURVEN_FARBEN = [
    "#00FFAA", "#FF4D6D", "#4D8BFF", "#FFB000", "#B388FF", "#7CFF4D",
    "#FF52F0", "#00E5FF", "#FF7A00", "#FFE94D", "#00C2A8", "#FF9E9E",
    "#9EFF00", "#C0C8D4",
]

try:                                   # der feste Kader des Erfassungsblatts
    from erfassung_logik import KADER_VORGABE
    STAMMKADER = [n for n, _ in KADER_VORGABE]
except Exception:                      # ohne die Datei zaehlen nur die Punkte
    STAMMKADER = []


def plot_punkte_verlauf(df_in, spiele, aufsummiert=True):
    """Punkte (Tore + Assists) je Spieler ueber die Meisterschaftsspiele.

    Zurzeit nicht eingebunden - siehe Hinweis in tab_team.

    Gezeigt werden der feste Kader und zusaetzlich jeder, der Punkte geholt
    hat. Cupspiele bleiben draussen, sonst springt die Kurve zwischen zwei
    Wettbewerben hin und her. `aufsummiert` zeigt den Stand nach jedem Spiel,
    sonst die Punkte des einzelnen Spiels.
    """
    if spiele is None or spiele.empty:
        return None
    if "Format" in spiele.columns:
        spiele = spiele[~spiele["Format"].astype(str).str.strip()
                        .str.lower().eq("cup")]
    folge = _spielfolge(spiele)
    if len(folge) < 2 or df_in.empty or "Punkte" not in df_in.columns:
        return None
    d = df_in.copy()
    if "Gespielt" in d.columns:
        d = d[d["Gespielt"].astype(str).str.strip() == "Ja"]
    d = d[d[MATCH_COL].isin([mid for mid, _ in folge])]
    if d.empty:
        return None

    punkte = d.groupby([MATCH_COL, "Name"])["Punkte"].sum()
    mit_punkten = {n for n in d["Name"].unique()
                   if float(d[d["Name"] == n]["Punkte"].sum()) > 0}
    dabei = {n for n in d["Name"].unique() if n in STAMMKADER} | mit_punkten
    namen = sorted(dabei)
    if not namen:
        return None
    farbe_je_name = {n: KURVEN_FARBEN[i % len(KURVEN_FARBEN)]
                     for i, n in enumerate(namen)}

    zeilen = []
    stand = {n: 0.0 for n in namen}
    for mid, label in folge:
        for n in namen:
            wert = float(punkte.get((mid, n), 0))
            stand[n] += wert
            zeilen.append({"Spiel": label, "Name": n,
                           "Punkte": stand[n] if aufsummiert else wert})
    daten = pd.DataFrame(zeilen)

    titel = ("Punkteverlauf — aufsummiert" if aufsummiert
             else "Punkte je Spiel (T+A)")
    fig = px.line(daten, x="Spiel", y="Punkte", color="Name", title=titel,
                  markers=True, color_discrete_map=farbe_je_name,
                  category_orders={"Spiel": [l for _, l in folge], "Name": namen})
    fig.update_traces(line_width=2.5, marker=dict(size=7))
    fig = _style_plot(fig, textfix=False)
    # Legende rechts neben dem Plot - unten drunter wird sie zum Farbsalat
    fig.update_layout(height=480, legend_title_text="",
                      legend=dict(orientation="v", yanchor="top", y=1,
                                  xanchor="left", x=1.01, font=dict(size=11)),
                      margin=dict(t=45, b=115, l=8, r=150))
    fig.update_yaxes(dtick=1 if not aufsummiert else None, rangemode="tozero")
    return fig


TOR_FENSTER = 5          # Minuten je Saeule
HALBZEIT_MINUTEN = 20    # eine Halbzeit dauert 20 Minuten
SPIEL_MINUTEN = 2 * HALBZEIT_MINUTEN


def _spielminute(halbzeit, sekunde):
    """Absolute Spielminute 0-40 aus Halbzeit und Spieluhr.

    Die Uhr laeuft je Halbzeit bis 20. Steht in der zweiten Halbzeit mehr auf
    der Tafel (Nachspielzeit, nachgefuehrte Uhr), zaehlt das Tor zu den
    letzten Minuten - so hat es der User festgelegt.
    """
    minute = max(0.0, float(sekunde) / 60)
    if int(halbzeit) == 1:
        return min(minute, HALBZEIT_MINUTEN - 0.001)
    return min(HALBZEIT_MINUTEN + minute, SPIEL_MINUTEN - 0.001)


def plot_tore_minuten(tore_zeilen):
    """Wann die Tore fallen - Fuenfminutenfenster ueber die ganzen 40 Minuten."""
    if tore_zeilen is None or tore_zeilen.empty or "Sekunde" not in tore_zeilen.columns:
        return None
    fenster = [f"{start}–{start + TOR_FENSTER}"
               for start in range(0, SPIEL_MINUTEN, TOR_FENSTER)]
    anzahl = {}
    for _, r in tore_zeilen.iterrows():
        sek = pd.to_numeric(r.get("Sekunde"), errors="coerce")
        hz = pd.to_numeric(r.get("Halbzeit"), errors="coerce")
        if pd.isna(sek) or pd.isna(hz) or int(hz) not in (1, 2):
            continue
        minute = _spielminute(hz, sek)
        start = int(minute // TOR_FENSTER) * TOR_FENSTER
        art = "Tore" if str(r.get("Art", "")).strip() == "Tor" else "Gegentore"
        schluessel = (f"{start}–{start + TOR_FENSTER}", art)
        anzahl[schluessel] = anzahl.get(schluessel, 0) + 1
    if not anzahl:
        return None

    daten = pd.DataFrame([{"Fenster": f, "Art": a, "Anzahl": anzahl.get((f, a), 0)}
                          for f in fenster for a in ("Tore", "Gegentore")])
    fig = px.bar(daten, x="Fenster", y="Anzahl", color="Art", barmode="group",
                 title="Spielminute", text="Anzahl",
                 category_orders={"Fenster": fenster, "Art": ["Tore", "Gegentore"]},
                 color_discrete_map={"Tore": FARBEN["gut"],
                                     "Gegentore": FARBEN["schlecht"]})
    fig.update_traces(texttemplate="%{text:.0f}", textposition="outside", textangle=0,
                      cliponaxis=False)
    fig.update_layout(legend_title_text="")
    return _style_plot(fig, tickangle=0, textfix=False)


def _torfolge(tore_zeilen):
    """Je Spiel die Tore in zeitlicher Folge: [(Match_Id, [(Minute, eigen?, HZ), ...])].

    Grundlage fuer alles, was den Spielverlauf betrifft - Reaktion auf Tore,
    Spielstand und Verlaufskurve.
    """
    if tore_zeilen is None or tore_zeilen.empty or "Sekunde" not in tore_zeilen.columns:
        return []
    raus = []
    for mid, g in tore_zeilen.groupby(MATCH_COL):
        folge = []
        for _, r in g.sort_values("Nr").iterrows():
            sek = pd.to_numeric(r.get("Sekunde"), errors="coerce")
            hz = pd.to_numeric(r.get("Halbzeit"), errors="coerce")
            if pd.isna(sek) or pd.isna(hz) or int(hz) not in (1, 2):
                continue
            # hier bewusst ohne _spielminute: fuer Dauern darf die Uhr nicht
            # bei Minute 40 abgeschnitten werden, sonst fallen mehrere Tore
            # auf denselben Zeitpunkt und die letzte Lage dauert 0 Minuten
            minute = max(0.0, float(sek) / 60)
            if int(hz) == 2:
                minute += HALBZEIT_MINUTEN
            folge.append((minute, str(r.get("Art", "")).strip() == "Tor", int(hz)))
        folge.sort(key=lambda w: w[0])
        if folge:
            raus.append((mid, folge))
    return raus


def _spiel_dauer(folge):
    """Wie lange das Spiel laut Uhr gedauert hat - mindestens die volle Zeit.

    In einigen Spielen lief die Uhr in der zweiten Halbzeit ueber 20:00 hinaus
    (bis 23:17). Ein Tor kann nicht nach Schluss fallen, also ist das Spiel
    mindestens so lang wie sein letztes Tor.
    """
    return max(float(SPIEL_MINUTEN), max((m for m, _, _ in folge), default=0.0))


REAKTION_FENSTER = 2        # Minuten


def plot_reaktion(tore_zeilen):
    """Was in den zwei Minuten nach einem Tor passiert.

    Zwei Lagen: nach einem eigenen Tor und nach einem Gegentor. Je Lage wird
    gezaehlt, ob als naechstes ein eigenes Tor oder ein Gegentor faellt - und
    nur, wenn es ins Fenster faellt. Zeigt, ob wir nachlegen oder einbrechen.
    """
    folgen = _torfolge(tore_zeilen)
    if not folgen:
        return None
    zaehler = {("nach eigenem Tor", True): 0, ("nach eigenem Tor", False): 0,
               ("nach Gegentor", True): 0, ("nach Gegentor", False): 0}
    anlaesse = {"nach eigenem Tor": 0, "nach Gegentor": 0}
    for _, folge in folgen:
        for i, (minute, eigen, hz) in enumerate(folge):
            lage = "nach eigenem Tor" if eigen else "nach Gegentor"
            anlaesse[lage] += 1
            if i + 1 >= len(folge):
                continue
            n_minute, n_eigen, n_hz = folge[i + 1]
            # ueber die Pause hinweg zaehlt nichts, dazwischen liegen 10 Minuten
            if n_hz == hz and n_minute - minute <= REAKTION_FENSTER:
                zaehler[(lage, n_eigen)] += 1
    if not any(zaehler.values()):
        return None

    daten = pd.DataFrame([
        {"Lage": lage, "Was folgt": "eigenes Tor" if eigen else "Gegentor", "Anzahl": n,
         "Label": (f"{n}<br><span style='font-size:11px'>"
                   f"{100 * n / max(anlaesse[lage], 1):.0f}%</span>")}
        for (lage, eigen), n in zaehler.items()
    ])
    titel = f"Was folgt in den {REAKTION_FENSTER} Minuten nach einem Tor"
    fig = px.bar(daten, x="Lage", y="Anzahl", color="Was folgt", barmode="group",
                 title=titel, text="Label",
                 category_orders={"Lage": ["nach eigenem Tor", "nach Gegentor"],
                                  "Was folgt": ["eigenes Tor", "Gegentor"]},
                 color_discrete_map={"eigenes Tor": FARBEN["gut"],
                                     "Gegentor": FARBEN["schlecht"]})
    fig.update_traces(textposition="outside", textangle=0, cliponaxis=False)
    fig.update_layout(legend_title_text="")
    fig = _style_plot(fig, tickangle=0, textfix=False)
    hoechster = float(daten["Anzahl"].max())
    fig.update_yaxes(dtick=1 if hoechster <= 12 else 2,
                     range=[0, hoechster + max(2.0, hoechster * 0.4)])
    return fig


def plot_spielverlauf(tore_zeilen, spiele=None,
                      titel="Tordifferenz über die Spielminute"):
    """Je Spiel eine Treppenkurve der Tordifferenz.

    Daran sieht man, wer in Fuehrung ging, wie lange sie hielt und wann ein
    Spiel gekippt ist - der erste Treffer ist nur der Anfang der Geschichte.
    """
    folgen = _torfolge(tore_zeilen)
    if not folgen:
        return None
    namen = dict(_spielfolge(spiele)) if spiele is not None else {}
    zeilen = []
    for mid, folge in folgen:
        label = namen.get(mid, f"Spiel {int(mid)}")
        stand = 0
        zeilen.append({"Minute": 0.0, "Differenz": 0, "Spiel": label})
        for minute, eigen, _ in folge:
            stand += 1 if eigen else -1
            zeilen.append({"Minute": round(minute, 2), "Differenz": stand, "Spiel": label})
        zeilen.append({"Minute": round(_spiel_dauer(folge), 2), "Differenz": stand,
                       "Spiel": label})
    daten = pd.DataFrame(zeilen)
    reihenfolge = list(dict.fromkeys(daten["Spiel"]))
    farben = {n: KURVEN_FARBEN[i % len(KURVEN_FARBEN)] for i, n in enumerate(reihenfolge)}

    fig = px.line(daten, x="Minute", y="Differenz", color="Spiel", title=titel,
                  line_shape="hv", color_discrete_map=farben,
                  category_orders={"Spiel": reihenfolge})
    fig.update_traces(line_width=2.5)
    fig = _style_plot(fig, tickangle=0, textfix=False)
    fig.update_layout(height=470, legend_title_text="",
                      legend=dict(orientation="v", yanchor="top", y=1,
                                  xanchor="left", x=1.01, font=dict(size=11)),
                      margin=dict(t=45, b=60, l=8, r=170))
    fig.update_xaxes(dtick=5, range=[0, max(SPIEL_MINUTEN, daten["Minute"].max())],
                     title_text="Spielminute")
    fig.update_yaxes(dtick=1, zeroline=True, zerolinewidth=2,
                     zerolinecolor=FARBEN["gedaempft"])
    return fig


ZUSTAENDE = ["in Führung", "Unentschieden", "im Rückstand"]


def spielstand_je_spiel(tore_zeilen, spiele=None):
    """Je Spiel die Gesamtzeit in Fuehrung, Unentschiedenund im Rueckstand.

    Zwischen zwei Toren steht fest, in welcher Lage wir sind - so laesst sich
    die Spielzeit auf die drei Lagen aufteilen. Die Summe je Spiel ist immer
    die volle Spielzeit, die Balken sind also direkt vergleichbar.
    """
    folgen = _torfolge(tore_zeilen)
    if not folgen:
        return pd.DataFrame()
    namen = dict(_spielfolge(spiele)) if spiele is not None else {}
    # Das Resultat gehoert an die Achse: ein Spiel kann lange gefuehrt und
    # trotzdem verloren werden (White Horse Lengnau, 28 Minuten vorn, 5:7).
    ergebnis = {}
    if spiele is not None and not spiele.empty:
        for _, r in spiele.iterrows():
            eigen = pd.to_numeric(r.get("Tore Wygorazzi"), errors="coerce")
            gegen = pd.to_numeric(r.get("Tore Gegner"), errors="coerce")
            if not pd.isna(eigen) and not pd.isna(gegen):
                ergebnis[r.get(MATCH_COL)] = (
                    f"<span style='color:{FARBEN['gut']}'>{int(eigen)}</span>"
                    f"<span style='color:{FARBEN['gedaempft']}'>:</span>"
                    f"<span style='color:{FARBEN['schlecht']}'>{int(gegen)}</span>")

    def lage(diff):
        if diff > 0:
            return "in Führung"
        return "im Rückstand" if diff < 0 else "Unentschieden"

    zeilen = []
    for mid, folge in folgen:
        label = namen.get(mid, f"Spiel {int(mid)}")
        if mid in ergebnis:
            label += f"<br>{ergebnis[mid]}"
        minuten = {z: 0.0 for z in ZUSTAENDE}
        stand, vorher = 0, 0.0
        for minute, eigen, _ in folge:
            minuten[lage(stand)] += max(0.0, minute - vorher)
            stand += 1 if eigen else -1
            vorher = minute
        minuten[lage(stand)] += max(0.0, _spiel_dauer(folge) - vorher)
        for z in ZUSTAENDE:
            zeilen.append({"Spiel": label, "Lage": z, "Minuten": minuten[z]})
    return pd.DataFrame(zeilen)


def _mmss(minuten):
    """0.4 -> '0:24'. Dezimalminuten liest am Balken niemand."""
    s = int(round(float(minuten) * 60))
    return f"{s // 60}:{s % 60:02d}"


def plot_spielstand(tore_zeilen, spiele=None, titel="Spielverlauf"):
    """Je Spiel ein Balken aus drei Abschnitten - die Zeit in jeder Lage.

    Jeder Balken ist gleich hoch (die volle Spielzeit), darum laesst sich auf
    einen Blick vergleichen, welche Spiele wir kontrolliert haben. Wann die
    Lagen eintraten, zeigt die Tordifferenz-Kurve daneben.
    """
    daten = spielstand_je_spiel(tore_zeilen, spiele)
    if daten.empty:
        return None
    reihenfolge = list(dict.fromkeys(daten["Spiel"]))
    # Schwelle nur gegen Null-Abschnitte; was zu schmal ist, blendet Plotly
    # ueber uniformtext selber aus
    daten["Label"] = [_mmss(m) if m >= 1.0 else "" for m in daten["Minuten"]]
    fig = px.bar(daten, x="Spiel", y="Minuten", color="Lage", title=titel,
                 text="Label",
                 category_orders={"Spiel": reihenfolge, "Lage": ZUSTAENDE},
                 color_discrete_map={"in Führung": FARBEN["gut"],
                                     "Unentschieden": FARBEN["neutral"],
                                     "im Rückstand": FARBEN["schlecht"]})
    fig.update_traces(textposition="inside", textangle=0, insidetextanchor="middle",
                      insidetextfont=dict(color=FARBEN["label_innen"], size=12))
    fig.update_layout(legend_title_text="", uniformtext_minsize=9,
                      uniformtext_mode="hide")
    # Senkrechte Beschriftung: im Hochformat auf dem Handy waere eine
    # waagrechte nicht mehr lesbar.
    fig = _style_plot(fig, textfix=False)
    # Legende nach oben neben den Titel - unten verdeckt sie die Spielnamen
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.0,
                                  xanchor="right", x=1))
    hoechste = float(daten.groupby("Spiel")["Minuten"].sum().max())
    fig.update_yaxes(dtick=5, range=[0, max(SPIEL_MINUTEN, hoechste)],
                     title_text="Minuten")
    return fig


def _rgb(hexfarbe):
    h = str(hexfarbe).lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _skala_farbe(skala, anteil):
    """Farbe an Position 0..1 einer Plotly-Farbskala [[pos, '#rrggbb'], ...]."""
    anteil = min(max(float(anteil), 0.0), 1.0)
    for (p0, c0), (p1, c1) in zip(skala, skala[1:]):
        if anteil <= p1:
            t = 0.0 if p1 == p0 else (anteil - p0) / (p1 - p0)
            return tuple(a + t * (b - a) for a, b in zip(_rgb(c0), _rgb(c1)))
    return _rgb(skala[-1][1])


def _textfarbe(rgb):
    """Dunkle Schrift auf hellem Grund - sonst verschwindet die Zahl."""
    hell = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    return FARBEN["label_innen"] if hell > 0.5 else FARBEN["text"]


def plot_punkte_teppich(df_in, spiele, titel="Punkteverlauf"):
    """Je Spieler eine Zeile, je Spiel ein Feld: Punkte an diesem Abend.

    Zeigt, wer regelmaessig punktet und wer von einzelnen Spielen lebt - ein
    Durchschnitt verdeckt genau das. Hinter dem Namen stehen die Saisonpunkte
    und der Anteil der Spiele mit mindestens einem Punkt.
    """
    folge = _spielfolge(spiele)
    if len(folge) < 2 or df_in.empty or "Punkte" not in df_in.columns:
        return None
    d = df_in.copy()
    if "Gespielt" in d.columns:
        d = d[d["Gespielt"].astype(str).str.strip() == "Ja"]
    d = d[d[MATCH_COL].isin([mid for mid, _ in folge])]
    if d.empty:
        return None
    punkte = d.groupby([MATCH_COL, "Name"])["Punkte"].sum()
    gesamt = d.groupby("Name")["Punkte"].sum()
    dabei = {n for n in d["Name"].unique() if n in STAMMKADER or gesamt.get(n, 0) > 0}
    namen = sorted(dabei, key=lambda n: (-float(gesamt.get(n, 0)), n))
    if not namen:
        return None

    werte, texte, beschriftung = [], [], []
    for n in namen:
        zeile_w, zeile_t = [], []
        for mid, _ in folge:
            if (mid, n) in punkte.index:
                wert = float(punkte.loc[(mid, n)])
                zeile_w.append(wert)
                zeile_t.append(f"{wert:.0f}" if wert else "·")
            else:
                zeile_w.append(None)
                zeile_t.append("")
        werte.append(zeile_w)
        texte.append(zeile_t)
        mit_punkt = sum(1 for v in zeile_w if v)
        gespielt = sum(1 for v in zeile_w if v is not None)
        anteil = 100 * mit_punkt / gespielt if gespielt else 0
        beschriftung.append(f"{n} — {gesamt.get(n, 0):.0f} P · {anteil:.0f}%")

    spanne = max((v for z in werte for v in z if v), default=1)
    skala = [[0.0, FARBEN["flaeche"]], [0.35, "#1E4D3B"], [1.0, FARBEN["gut"]]]
    fig = px.imshow(werte, x=[l for _, l in folge], y=beschriftung, title=titel,
                    aspect="auto", color_continuous_scale=skala, zmin=0, zmax=spanne)
    fig.update_traces(xgap=2, ygap=2)
    # Je Feld eine eigene Beschriftung: Plotly kann der Heatmap nur eine
    # einzige Schriftfarbe geben, und die hellen Felder brauchen eine dunkle.
    for zi, zeile in enumerate(texte):
        for si, text in enumerate(zeile):
            if not text:
                continue
            wert = werte[zi][si] or 0
            fig.add_annotation(
                x=folge[si][1], y=beschriftung[zi], text=text, showarrow=False,
                font=dict(size=12,
                          color=_textfarbe(_skala_farbe(skala, wert / spanne))))
    fig = _style_plot(fig, textfix=False)
    fig.update_layout(coloraxis_showscale=False, height=max(360, 34 * len(namen) + 150))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return fig


# ---------------------------
# Spielqualitaet: Torschussanteil, PDO und Game Score
# ---------------------------
def spiel_kennzahlen(df_in, spiele):
    """Je Spiel: Torschuesse und Tore auf beiden Seiten.

    Die gegnerischen Torschuesse kennen wir indirekt - was auf unser Tor kam,
    wurde entweder gehalten (Paraden des Torhueters, Spalte Block) oder ging
    rein.
    """
    noetig = {"Linie", "Schüsse aufs Tor", "Block", "T"}
    if (spiele is None or spiele.empty or df_in.empty
            or not noetig.issubset(set(df_in.columns))):
        return pd.DataFrame()
    zeilen = []
    for _, spiel in spiele.iterrows():
        mid = spiel.get(MATCH_COL)
        d = df_in[df_in[MATCH_COL] == mid]
        if d.empty:
            continue
        feld, tw = nur_feldspieler(d), nur_torhueter(d)
        sat = float(feld["Schüsse aufs Tor"].sum())
        paraden = float(tw["Block"].sum())
        tore = pd.to_numeric(spiel.get("Tore Wygorazzi"), errors="coerce")
        gegen = pd.to_numeric(spiel.get("Tore Gegner"), errors="coerce")
        if pd.isna(tore) or pd.isna(gegen):
            continue
        gegner_sat = paraden + float(gegen)
        if sat <= 0 or gegner_sat <= 0:
            continue
        zeilen.append({
            "Spiel": _spiel_label(spiel),
            "Torschüsse": sat, "Tore": float(tore),
            "Gegner-Torschüsse": gegner_sat, "Gegentore": float(gegen),
        })
    return pd.DataFrame(zeilen)


def plot_torschuesse(df_in, spiele, titel="Torschussquote"):
    """Je Spiel zwei Balken nebeneinander: unsere Torschuesse und seine.

    Ersetzt die frueheren Kennzahlen Torschussanteil und PDO - dieselbe Frage
    (wer hatte mehr Druck, wer hat mehr daraus gemacht), nur direkt ablesbar.
    """
    daten = spiel_kennzahlen(df_in, spiele)
    if daten.empty:
        return None

    def zeile(r, seite, schuss_sp, tor_sp):
        return {"Spiel": r["Spiel"], "Seite": seite, "Torschüsse": r[schuss_sp],
                "Label": (f"{r[schuss_sp]:.0f}<br><span style='font-size:11px'>"
                          f"{r[tor_sp]:.0f} Tore</span>")}

    lang = pd.DataFrame(
        [zeile(r, "wir", "Torschüsse", "Tore") for _, r in daten.iterrows()]
        + [zeile(r, "Gegner", "Gegner-Torschüsse", "Gegentore")
           for _, r in daten.iterrows()])
    fig = px.bar(lang, x="Spiel", y="Torschüsse", color="Seite", barmode="group",
                 title=titel, text="Label",
                 category_orders={"Spiel": list(daten["Spiel"]),
                                  "Seite": ["wir", "Gegner"]},
                 color_discrete_map={"wir": FARBEN["gut"],
                                     "Gegner": FARBEN["schlecht"]})
    fig.update_traces(textposition="outside", textangle=0, cliponaxis=False)
    fig.update_layout(legend_title_text="")
    fig = _style_plot(fig, textfix=False)
    # Legende nach oben neben den Titel - unten verdeckt sie die Spielnamen
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.0,
                                  xanchor="right", x=1))
    hoch = float(lang["Torschüsse"].max())
    fig.update_yaxes(range=[0, hoch * 1.4], title_text="Torschüsse")
    return fig


# Gewichte des Game Score. Nach Dom Luszczyszyn (Hockey Graphs 2016), auf unsere Liga umgerechnet.
# Seine Regel: Gewicht = Tor-Gewicht (0.75) mal Wahrscheinlichkeit, dass die
# Aktion zu einem Tor wird. In der NHL ergibt das 0.075 je Schuss (10 %
# Trefferquote) und -0.15 je Strafe (20 % Ueberzahlquote). Unsere Quoten
# (Saison 26/27, 6 Spiele) sind dreimal hoeher, also:
#   Schuss aufs Tor  0.75 * 28.7 %        (35 Tore aus 122 Schuessen)  = 0.21
#   Block            0.75 * 32.1 % * 2/3  (gegnerische Quote: 36 Tore aus
#                    112 Schuessen; die 2/3 sind Doms Verhaeltnis Block zu
#                    Schuss, ein geblockter Versuch waere nicht sicher aufs
#                    Tor gegangen)                                     = 0.16
#   Balleroberung    0.21 / 3   Annahme des Trainers, nicht gemessen:
#                    jede dritte Balleroberung wird zu einem Schuss     = 0.07
# Unveraendert bei Doms Werten, weil dort unsere Zahlen passen: Assist 0.70
# (0.71 Assists je Tor bei uns, 0.67 in der NHL), Plus/Minus +-0.15 (der Term
# wiegt bei uns 61 % des Tor-Terms, in der NHL 74 %) und Strafe -0.15 (unsere
# Boxplay-Quote ist aus 3 Strafen in 6 Spielen nicht zu schaetzen).
# Das Bully (+-0.01 bei Dom) bleibt auf Wunsch des Trainers draussen.
GAME_SCORE_GEWICHTE = {
    "T": 0.75, "A": 0.70, "Schüsse aufs Tor": 0.21, SPALTE_BLOCK: 0.16,
    SPALTE_BALLEROBERUNG: 0.07, "Strafen": -0.15, "Plus": 0.15, "Minus": -0.15,
}


def game_score(df_in):
    """Game Score je Spieler - eine Zahl für alles, was er beigetragen hat.

    Nach Dom Luszczyszyn aus dem Eishockey, mit unseren Quoten nachgerechnet
    (siehe GAME_SCORE_GEWICHTE): jede Aktion zaehlt so viel, wie sie zu einem
    Tor beitraegt. Gerechnet wird nur fuer Feldspieler - beim Torhueter
    bedeutet die Spalte Block Paraden und haette ein ganz anderes Gewicht.
    """
    d = nur_feldspieler(df_in)
    if d.empty:
        return pd.DataFrame()
    punkte = sum(gewicht * pd.to_numeric(d[spalte], errors="coerce").fillna(0)
                 for spalte, gewicht in GAME_SCORE_GEWICHTE.items() if spalte in d.columns)
    d = d.assign(GameScore=punkte)
    tabelle = d.groupby("Name").agg(Spiele=(MATCH_COL, "nunique"),
                                    GameScore=("GameScore", "sum"))
    tabelle["pro Spiel"] = tabelle["GameScore"] / tabelle["Spiele"]
    return tabelle.sort_values("GameScore", ascending=False).reset_index()


def plot_game_score(df_in,
                    titel="Game Score (Tor 0.75 · Assist 0.70 · Torschuss 0.21 · "
                          "Block 0.16 · Balleroberung 0.07 · Plus 0.15 · "
                          "Minus −0.15 · Strafe −0.15)"):
    tabelle = game_score(df_in)
    if tabelle.empty or float(tabelle["GameScore"].abs().max()) == 0:
        return None
    tabelle["Label"] = [
        f"{g:.1f}<br><span style='font-size:11px'>ø {p:.2f}</span>"
        for g, p in zip(tabelle["GameScore"], tabelle["pro Spiel"])
    ]
    fig = px.bar(tabelle, x="Name", y="GameScore", title=titel, text="Label")
    fig.update_traces(textposition="outside", textangle=0, cliponaxis=False,
                      marker_color=FARBEN["balken"], showlegend=False)
    fig = _style_plot(fig, textfix=False)
    hoch = float(tabelle["GameScore"].max())
    tief = min(0.0, float(tabelle["GameScore"].min()))
    fig.update_yaxes(range=[tief - 0.5, hoch + max(2.0, hoch * 0.3)], title_text=None)
    return fig


def bilanz_gegner(alle_spiele):
    """Bilanz gegen jeden Gegner - ueber alle Saisons zusammen."""
    if alle_spiele is None or alle_spiele.empty or "Gegner" not in alle_spiele.columns:
        return pd.DataFrame()
    d = alle_spiele.copy()
    d["_tore"] = pd.to_numeric(d["Tore Wygorazzi"], errors="coerce").fillna(0)
    d["_gegen"] = pd.to_numeric(d["Tore Gegner"], errors="coerce").fillna(0)
    d["_sieg"], d["_remis"] = _ja("Sieg", d), _ja("Unentschieden", d)
    d["_nieder"] = _ja("Niederlage", d)
    zeilen = []
    for gegner, g in d.groupby(d["Gegner"].astype(str).str.strip()):
        tore, gegentore = int(g["_tore"].sum()), int(g["_gegen"].sum())
        zeilen.append({
            "Gegner": gegner,
            "Spiele": len(g),
            "S-U-N": f"{int(g['_sieg'].sum())}-{int(g['_remis'].sum())}-{int(g['_nieder'].sum())}",
            "Tore": f"{tore}:{gegentore}",
            "Differenz": tore - gegentore,
        })
    tabelle = pd.DataFrame(zeilen)
    # die haeufigsten Gegner zuoberst; umsortieren geht im Kopf der Tabelle
    return tabelle.sort_values(["Spiele", "Differenz"], ascending=[False, False])


def zeige_gegnerbilanz(alle_spiele):
    tabelle = bilanz_gegner(alle_spiele)
    if tabelle.empty:
        return
    with st.container(border=True):
        st.markdown("<div class='chart-titel'>Bilanz gegen jeden Gegner</div>",
                    unsafe_allow_html=True)
        st.dataframe(tabelle, hide_index=True, width="stretch",
                     height=min(420, 36 * len(tabelle) + 40))
        st.caption("Alle Saisons zusammengezählt. Ein Klick auf eine Spaltenüberschrift "
                   "sortiert die Tabelle um.")


def tab_team(df_in, gegentore=None, situationen=None, spiele=None, tore_zeilen=None,
             paar_zeilen=None):
    # Zuerst die Kennzahlen-Karten, danach die Verlaufsanalysen.
    eintraege = [
        _eintrag(plot_torschuss_anteile(df_in, gegentore),
                 "Anteil von uns geblockten Torschüssen auf unser Tor"),
        _eintrag(plot_abschlussquote(df_in), "Abschlussquote"),
        _eintrag(plot_spezial_team(situationen, "Powerplay"), "Powerplay-Erfolg"),
        _eintrag(plot_spezial_team(situationen, "Boxplay"), "Boxplay-Erfolg"),
    ]
    # Die Paare lohnen sich erst ueber eine ganze Saison - bei einem einzelnen
    # Spiel waeren es ein paar Balken mit lauter Einsern.
    zuspiele = plot_zuspiele(paar_zeilen)
    if zuspiele is not None:
        eintraege.append(_eintrag(zuspiele))
    torzeiten = plot_tore_minuten(tore_zeilen)
    if torzeiten is not None:
        eintraege.append(_eintrag(torzeiten))
    # Verlauf, Reaktion und Spielstand - alles aus den Torzeiten. Verlauf,
    # Spielstand und Torschussquote gehen auch fuer ein einzelnes Spiel,
    # die Reaktion braucht mehrere.
    # breit=True fuer alles, was wenige Kategorien hat, aber trotzdem die
    # volle Breite braucht - sonst stauchte raster() die Karte auf 330 Pixel
    # und ueberschriebe die eigene Hoehe des Plots.
    # plot_spielverlauf (Tordifferenz-Kurve) ist ausgehaengt (Wunsch vom
    # 2026-10-31); die Funktion bleibt stehen, zum Wiederanzeigen hier
    # (plot_spielverlauf(tore_zeilen, spiele), False) einfuegen.
    for fig, breit in ((plot_spielstand(tore_zeilen, spiele), True),
                       (plot_reaktion(paar_zeilen), True),
                       (plot_torschuesse(df_in, spiele), True)):
        if fig is not None:
            eintraege.append(_eintrag(fig, breit=breit))
    # Die beiden Punkteverlaeufe sind vorerst ausgeblendet (Wunsch vom
    # 2026-10-30). plot_punkte_verlauf bleibt stehen; zum Wiederanzeigen
    # hier die Schleife ueber (True, False) wieder einhaengen.
    raster(*eintraege)


# Die Clips liegen je Saison in einem eigenen Ordner (tore_26-27). Welcher
# gilt, haengt am Spiel - fest verdrahtet waeren die Videos ab der naechsten
# Saison verschwunden.
def _als_id(wert):
    try:
        return int(float(wert))
    except (TypeError, ValueError):
        return None


SAISON_JE_MATCH = {_als_id(r[MATCH_COL]): r[SEASON_COL] for _, r in wygo.iterrows()
                   if _als_id(r[MATCH_COL]) is not None}


def _video_ordner(saison):
    """'26/27' -> 'tore_26-27'."""
    return "tore_" + str(saison).strip().replace("/", "-")


def _clip_pfad(zeile):
    """Pfad zum Clip im Projekt - der schnellste Weg, weil die App ihn selbst ausliefert."""
    d = str(zeile.get("Datei") or "").strip()
    if not d or d.lower() == "nan":
        return ""
    saison = SAISON_JE_MATCH.get(_als_id(zeile.get(MATCH_COL)))
    ordner = [_video_ordner(saison)] if saison else []
    # Rueckfall: in den uebrigen Saisonordnern nachsehen
    ordner += sorted(o for o in glob.glob("tore_*")
                     if os.path.isdir(o) and o not in ordner)
    for o in ordner:
        pfad = os.path.join(o, d)
        if os.path.isfile(pfad):
            return pfad
    return ""


def _video_url(zeile):
    """Eingebettete Adresse - nur noch Rueckfall, wenn die Datei fehlt."""
    v = str(zeile.get("Video") or "").strip()
    return v if v and v.lower() != "nan" else ""


def _hat_video(zeile):
    return bool(_clip_pfad(zeile) or _video_url(zeile))


def _abspielen(zeile):
    """Lokale Datei bevorzugen, sonst einbetten."""
    pfad = _clip_pfad(zeile)
    if pfad:
        st.video(pfad)
        return
    url = _video_url(zeile)
    if url:
        components.iframe(url, height=430, scrolling=False)
    else:
        st.caption("Für dieses Tor ist kein Video hinterlegt.")


def _tor_waehlen(schluessel, nr):
    """Callback: laeuft vor dem Neuzeichnen, der Player sieht die Auswahl sofort.

    Nochmal auf dasselbe Tor klicken schliesst das Video wieder.
    """
    st.session_state[schluessel] = None if st.session_state.get(schluessel) == nr else nr


def _linie_text(zeile):
    """Linie, die beim Tor auf dem Feld stand - nur wo erfasst."""
    roh = str(zeile.get("Linie") or "").strip()
    if not roh or roh.lower() == "nan":
        return ""
    # kann mehrere Linien enthalten, z.B. "1+3" bei gemischter Formation
    teile = [t.strip().removesuffix(".0") for t in roh.replace(";", "+").split("+")]
    teile = [t for t in teile if t]
    return ("Linie " + "+".join(teile)) if teile else ""


def _zeit_text(zeile):
    """HZ und Spieluhr - bei Toren aus einer Videoluecke fehlt die Zeit."""
    zeit = str(zeile.get("Zeit") or "").strip()
    if not zeit or zeit.lower() == "nan":
        zeit = "—"
    return f"HZ{int(zeile['Halbzeit'])} · {zeit}"


def _torschuetze(zeile):
    """Name des Schuetzen - bei Gegentoren ist das Feld leer bzw. NaN."""
    wer = str(zeile.get("Spieler") or "").strip()
    return "Gegentor" if not wer or wer.lower() == "nan" else wer


@st.fragment
def tab_tore(zeilen, spiel_namen=None):
    """Tore des Spiels. Das Video erscheint direkt unter dem angeklickten Tor.

    Als Fragment: ein Klick laedt nur diese Liste neu statt der ganzen Seite.
    """
    if zeilen.empty:
        st.caption("Für dieses Spiel sind keine Tore erfasst.")
        return

    # nach Nr: die ist chronologisch vergeben und auch ohne Zeit vorhanden
    sortiert = zeilen.sort_values("Nr")
    anz_tor = int((sortiert["Art"].astype(str).str.strip() == "Tor").sum())
    st.caption(f"{anz_tor} Tore, {len(sortiert) - anz_tor} Gegentore")

    schluessel = f"tor_{int(sortiert.iloc[0]['Match_Id'])}"
    gewaehlt = st.session_state.get(schluessel)

    for _, r in sortiert.iterrows():
        nr = int(r["Nr"])
        ist_tor = str(r.get("Art", "")).strip() == "Tor"
        links, rechts = st.columns([6, 1], vertical_alignment="center")
        with links:
            st.markdown(
                f"<div class='tor-zeile {'tor' if ist_tor else 'gegentor'}'>"
                f"<span class='tor-nr'>{nr}</span>"
                f"<span class='tor-zeit'>{_zeit_text(r)}</span>"
                f"<span class='tor-wer'>{_torschuetze(r)}</span></div>",
                unsafe_allow_html=True,
            )
        with rechts:
            st.markdown("<div class='tor-knopf'>", unsafe_allow_html=True)
            if _hat_video(r):
                st.button("▼" if gewaehlt == nr else "▶", key=f"{schluessel}_{nr}",
                          help="Video hier abspielen",
                          on_click=_tor_waehlen, args=(schluessel, nr))
            else:
                st.markdown("<span class='tor-ohne'>—</span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        if gewaehlt == nr:
            _abspielen(r)
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


@st.fragment
def tab_tore_saison(zeilen, spiel_namen):
    """Alle Tore der Saison, gruppiert nach Spieler, innerhalb nach Spiel sortiert.

    Das Video erscheint direkt unter dem angeklickten Tor - auf dem Handy
    muesste man sonst nach jedem Klick wieder hochscrollen.
    """
    if zeilen.empty:
        st.caption("Für diese Saison sind keine Tore erfasst.")
        return

    schluessel = "tor_saison"
    gewaehlt = st.session_state.get(schluessel)

    eigene = zeilen[zeilen["Art"].astype(str).str.strip() == "Tor"]
    gegen = zeilen[zeilen["Art"].astype(str).str.strip() != "Tor"]
    reihenfolge = eigene.groupby("Spieler").size().sort_values(ascending=False).index.tolist()

    # Spieler nach Toranzahl, Gegentore als eigene Gruppe zuunterst
    gruppen = [(n, eigene[eigene["Spieler"] == n]) for n in reihenfolge]
    if not gegen.empty:
        gruppen.append(("Gegentore", gegen))

    for name, g in gruppen:
        if name == "Gegentore":
            zusatz = str(len(g))          # "Gegentore 2" statt "Gegentore 2 Gegentore"
        else:
            zusatz = f"{len(g)} {'Tor' if len(g) == 1 else 'Tore'}"

        # Ueberschrift und ihre Zeilen in einen gemeinsamen Container: nur so hat
        # position:sticky ein Elternelement, in dem es wandern kann.
        gruppe_box = st.container()
        gruppe_box.markdown(
            f"<div class='tor-gruppe'>{name} <span>{zusatz}</span></div>",
            unsafe_allow_html=True)

        # Gegentore nach der Linie ordnen, die auf dem Feld stand
        sortier = (["Linie", MATCH_COL, "Nr"] if name == "Gegentore"
                   and "Linie" in g.columns else [MATCH_COL, "Nr"])
        for _, r in g.sort_values(sortier).iterrows():
            mid = r[MATCH_COL]
            kennung = f"{int(r['Nr'])}_{mid}"
            ist_tor = str(r.get("Art", "")).strip() == "Tor"
            links, rechts = gruppe_box.columns([6, 1], vertical_alignment="center")
            with links:
                st.markdown(
                    f"<div class='tor-zeile {'tor' if ist_tor else 'gegentor'}'>"
                    f"<span class='tor-spiel'>{spiel_namen.get(mid, f'Spiel {mid}')}</span>"
                    f"<span class='tor-zeit'>{_zeit_text(r)}</span>"
                    f"<span class='tor-linie'>{_linie_text(r)}</span>"
                    f"<span class='tor-stand'>{r.get('Stand', '')}</span></div>",
                    unsafe_allow_html=True,
                )
            with rechts:
                st.markdown("<div class='tor-knopf'>", unsafe_allow_html=True)
                if _hat_video(r):
                    st.button("▼" if gewaehlt == kennung else "▶",
                              key=f"saison_{kennung}", help="Video hier abspielen",
                              on_click=_tor_waehlen, args=(schluessel, kennung))
                else:
                    st.markdown("<span class='tor-ohne'>—</span>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            if gewaehlt == kennung:
                with gruppe_box:
                    _abspielen(r)
                    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


def render_tabs(df_in, gegentore=None, zeige_gespielt=False, team_extra=None,
                situationen=None, tore_zeilen=None, tore_saison=None, spiel_namen=None,
                spiele=None, alle_spiele=None):
    saison_modus = tore_saison is not None
    quelle = tore_saison if saison_modus else tore_zeilen   # auch fuer die Linienbilanz
    zeige_tore = quelle is not None and not quelle.empty
    if zeige_tore:
        t_spieler, t_team, t_linie, t_tore = st.tabs(
            ["Pro Spieler", "Team", "Pro Linie", "Tore"])
    else:
        t_spieler, t_team, t_linie = st.tabs(["Pro Spieler", "Team", "Pro Linie"])
    with t_spieler:
        tab_pro_spieler(df_in, zeige_gespielt=zeige_gespielt, spiele=spiele)
    with t_team:
        tab_team(df_in, gegentore=gegentore, situationen=situationen,
                 spiele=spiele, tore_zeilen=quelle,
                 paar_zeilen=quelle if saison_modus else None)
        if team_extra is not None:
            team_extra()
        if alle_spiele is not None:
            # ganz unten, nach den Saison- und Gesamtkennzahlen
            zeige_gegnerbilanz(alle_spiele)
    with t_linie:
        tab_pro_linie(df_in, quelle)
    if zeige_tore:
        with t_tore:
            if saison_modus:
                tab_tore_saison(tore_saison, spiel_namen or {})
            else:
                tab_tore(tore_zeilen, spiel_namen)


# ---------------------------
# When a single match is selected: header, lines, player table, metrics, and the same plots but filtered
# ---------------------------
if selected_match_id is not None:
    # get wygo meta row for this match if exists
    meta = wygo[wygo[MATCH_COL] == selected_match_id]
    if not meta.empty:
        meta = meta.iloc[0]
    else:
        meta = None

    def _tore_aus(zeile, spalte):
        """Torzahl aus der Wygo-Zeile, 0 wenn sie fehlt oder keine Zahl ist."""
        if zeile is None or spalte not in zeile:
            return 0
        wert = pd.to_numeric(zeile[spalte], errors="coerce")
        return 0 if pd.isna(wert) else int(wert)

    tore_w = _tore_aus(meta, "Tore Wygorazzi")
    tore_g = _tore_aus(meta, "Tore Gegner")

    opponent = meta["Gegner"] if (meta is not None and "Gegner" in meta) else "Gegner unbekannt"
    # Datum_label wurde oben bereits korrekt (tagesbasiert) geparst
    datum_label = ""
    if meta is not None and "Datum_label" in meta and pd.notna(meta["Datum_label"]):
        datum_label = str(meta["Datum_label"])

    # Header
    # Als ein HTML-Block statt st.columns: bleibt auf dem Handy nebeneinander
    st.markdown(
        f"""
        <div class='karte scoreboard'>
          <div class='team'>
            <div class='team-name'>Wygorazzi</div>
            <div class='small-metric'>Heimteam</div>
          </div>
          <div class='score'>
            <div class='score-value'>{tore_w} : {tore_g}</div>
            <div class='subtle'>{datum_label}</div>
          </div>
          <div class='team team-right'>
            <div class='team-name'>{opponent}</div>
            <div class='small-metric'>Gast</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Aufstellung nach Linien")
    line_cols = st.columns(3)
    for i, linie in enumerate(["1", "2", "3"]):
        with line_cols[i]:
            st.markdown(f"<div class='line-card'><strong>Linie {linie}</strong><hr style='margin:6px 0;'>", unsafe_allow_html=True)
            players = df_for_plots[df_for_plots["Linie"].astype(str) == str(linie)]["Name"].tolist()
            if players:
                for p in players:
                    st.markdown(f"<div class='player-name'>• {p}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='subtle'>Keine Spieler</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

   

 

    st.markdown("### Statistik zu diesem Spiel")
    if df_for_plots.empty:
        st.info("Für dieses Spiel sind keine Spielerdaten erfasst.")
    else:
        _namen_spiel = {
            r[MATCH_COL]: f"{r['Datum_label']} vs {r['Gegner']}"
            for _, r in wygo[wygo[MATCH_COL] == selected_match_id].iterrows()
        }
        render_tabs(df_for_plots, gegentore=tore_g,
                    situationen=team_situationen(wygo[wygo[MATCH_COL] == selected_match_id]),
                    tore_zeilen=tore[tore[MATCH_COL] == selected_match_id],
                    spiele=wygo[wygo[MATCH_COL] == selected_match_id],
                    spiel_namen=_namen_spiel)

# ---------------------------
# If "Alle Spiele" selected: show full dashboard (as before) plus wygo season stats fixed
# ---------------------------
if selection == "Alle Spiele":
    # df_saison ist bereits aufbereitet

    # Die Ja/Nein-Spalten bleiben, wie sie sind - gezaehlt wird mit _ja().
    saisons = {
        selected_saison: wygo[wygo[SEASON_COL] == selected_saison],
        "Gesamt": wygo,
    }

    def zeige_statistik(df_s, titel):
        # Safe numeric sums
        tore_wygo_sum = int(pd.to_numeric(df_s.get('Tore Wygorazzi', 0), errors='coerce').fillna(0).sum())
        tore_gegner_sum = int(pd.to_numeric(df_s.get('Tore Gegner', 0), errors='coerce').fillna(0).sum())
        siege_sum = int(_ja("Sieg", df_s).sum())
        niederlagen_sum = int(_ja("Niederlage", df_s).sum())
        unentschieden_sum = int(_ja("Unentschieden", df_s).sum())
        anz_spiele = len(df_s)
        tordifferenz = tore_wygo_sum - tore_gegner_sum
        avg_tore_wygo = tore_wygo_sum / anz_spiele if anz_spiele > 0 else 0
        avg_tore_gegner = tore_gegner_sum / anz_spiele if anz_spiele > 0 else 0
        liga = df_s['Liga Wygorazzi'].iloc[0] if 'Liga Wygorazzi' in df_s.columns and not df_s.empty else "N/A"

        if titel == "Gesamt":
            st.subheader("Gesamtstatistik")
        else:
            st.subheader(f"Saison {titel} - {liga} . Liga")

        col_full = st.columns(1)[0]
        col_full.metric("Anzahl Spiele", f"{anz_spiele}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tore", f"{tore_wygo_sum}")
            st.markdown(f"<small>Ø {avg_tore_wygo:.2f} pro Spiel</small>", unsafe_allow_html=True)
        with col2:
            st.metric("Gegentore", f"{tore_gegner_sum}")
            st.markdown(f"<small>Ø {avg_tore_gegner:.2f} pro Spiel</small>", unsafe_allow_html=True)
        col3.metric("Tordifferenz", f"{tordifferenz:+d}")

        col4, col5, col6 = st.columns(3)
        col4.metric("Siege", f"{siege_sum}")
        col5.metric("Niederlagen", f"{niederlagen_sum}")
        col6.metric("Unentschieden", f"{unentschieden_sum}")

    def zeige_wygo_kennzahlen():
        st.markdown("---")
        st.subheader("Wygo - Gesamt- und Saisonkennzahlen")
        for saison_name, df_s in saisons.items():
            zeige_statistik(df_s, saison_name)

    if df_saison.empty:
        st.info(f"Für die Saison {selected_saison} sind noch keine Spielerdaten erfasst.")
        zeige_wygo_kennzahlen()
    else:
        # Gegentore nur aus den Spielen zaehlen, fuer die auch Spielerdaten existieren
        _ids_mit_daten = df_saison[MATCH_COL].dropna().unique()
        _gegentore = pd.to_numeric(
            wygo_saison[wygo_saison[MATCH_COL].isin(_ids_mit_daten)]["Tore Gegner"],
            errors="coerce",
        ).fillna(0).sum()
        _spiel_namen = {
            r[MATCH_COL]: f"{r['Datum_label']} vs {r['Gegner']}"
            for _, r in wygo_saison.iterrows()
        }
        render_tabs(df_saison, gegentore=_gegentore, zeige_gespielt=True,
                    team_extra=zeige_wygo_kennzahlen,
                    spiele=wygo_saison, alle_spiele=wygo,
                    situationen=team_situationen(
                        wygo_saison[wygo_saison[MATCH_COL].isin(_ids_mit_daten)]),
                    tore_saison=tore[tore[MATCH_COL].isin(wygo_saison[MATCH_COL])],
                    spiel_namen=_spiel_namen)


    