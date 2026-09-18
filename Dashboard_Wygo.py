import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os
import re
from io import BytesIO

# ---------------------------
# Page config & CSS
# ---------------------------
st.set_page_config(page_title="Spielerstatistik UHC Wygorazzi", layout="centered")

st.markdown(
    """
    <style>
    .big-title {font-size:28px; font-weight:700; color:#073763; margin-bottom:0.2rem;}
    .subtle {color:#6b7280; font-size:13px;}
    .small-metric {font-size:13px; color:#374151;}
    .header-row {display:flex; justify-content:space-between; align-items:center;}
    .result-box {
        background:linear-gradient(90deg, rgba(7,55,99,0.04), rgba(255,255,255,0.0));
        padding:14px; border-radius:12px;
    }

    /* Resultat bleibt auch auf schmalen Bildschirmen einzeilig */
    .scoreboard {display:flex; align-items:center; justify-content:space-between; gap:10px;}
    .scoreboard .team {flex:1 1 0; min-width:0;}
    .scoreboard .team-right {text-align:right;}
    .scoreboard .team-name {font-weight:700; font-size:15px; overflow-wrap:anywhere;}
    .scoreboard .score {flex:0 0 auto; text-align:center;}
    .scoreboard .score-value {font-size:26px; font-weight:700; line-height:1.15;}

    .line-card {background-color:#f0f0f0; padding:10px; border-radius:8px; margin-bottom:8px;}
    .line-card strong {color:#333333; font-size:16px;}
    .player-name {color:#333333; font-size:14px; margin:4px 0 4px 10px;}
    .line-card .subtle {color:#666666; font-style:italic; margin-left:10px;}

    /* Handy */
    @media (max-width: 640px) {
        .block-container, [data-testid="stMainBlockContainer"] {
            padding-left:0.7rem; padding-right:0.7rem; padding-top:1.2rem;
        }
        .big-title {font-size:20px;}
        .result-box {padding:10px;}
        .scoreboard .score-value {font-size:22px;}
        .scoreboard .team-name {font-size:13px;}
        .small-metric, .subtle {font-size:12px;}
        h2 {font-size:20px !important;}
        h3 {font-size:17px !important;}
    }
    </style>
    """,
    unsafe_allow_html=True
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
st.markdown('<div class="header-row"><div><h1 class="big-title">Spielerstatistik UHC Wygorazzi</h1></div></div>',
            unsafe_allow_html=True)
st.markdown("---")

col_saison, col_spiel = st.columns([1, 2])

# Default = aktuellste Saison (erster Eintrag der absteigend sortierten Liste)
with col_saison:
    selected_saison = st.selectbox("Saison:", saison_options, index=0)

# Spiele der gewaehlten Saison, neueste zuerst
wygo_saison = wygo[wygo[SEASON_COL] == selected_saison].copy()
wygo_saison = wygo_saison.sort_values(
    ["Datum_parsed", MATCH_COL], ascending=[False, False], na_position="last"
).reset_index(drop=True)

# Label -> Match_Id (kein Zurueckparsen des Labels noetig)
match_lookup = {}
match_options = ["Alle Spiele"]
for _, r in wygo_saison.iterrows():
    label = f"{r['Datum_label']} - vs {r['Gegner']}"
    if label in match_lookup:
        label = f"{label} (#{r[MATCH_COL]})"
    match_lookup[label] = r[MATCH_COL]
    match_options.append(label)

with col_spiel:
    selection = st.selectbox("Wähle ein Spiel:", match_options, index=0,
                             key=f"spiel_{selected_saison}")

st.markdown(f"<div class='subtle'>Saison {selected_saison} — {len(wygo_saison)} Spiele</div>",
            unsafe_allow_html=True)

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
    df_for_plots = df_saison[df_saison[MATCH_COL] == selected_match_id].copy()

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
    # Ensure Linie as str
    if "Linie" in df_in.columns:
        df_in["Linie"] = df_in["Linie"].astype(str)
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
    if column not in df_in.columns:
        df_in[column] = 0
    
    top = df_in.groupby("Name")[column].sum().sort_values(ascending=False).head(13).reset_index()
    fig = px.bar(top, x="Name", y=column, title=title, text=column)
    fig.update_traces(texttemplate='%{text:.0f}', textposition='inside', textangle=0, showlegend=False)

    return _style_plot(fig)

def plot_bully(df_in):
    if "Bully-Plus" not in df_in.columns:
        df_in["Bully-Plus"] = 0
    if "Bully-Minus" not in df_in.columns:
        df_in["Bully-Minus"] = 0
    bully = df_in.groupby("Name")[["Bully-Plus", "Bully-Minus"]].sum().reset_index()
    denom = (bully["Bully-Plus"] + bully["Bully-Minus"]).replace({0: np.nan})
    bully["Bully-Gewinn %"] = 100 * bully["Bully-Plus"] / denom
    bully["Bully-Gewinn %"] = bully["Bully-Gewinn %"].fillna(0)
    top = bully.sort_values("Bully-Gewinn %", ascending=False).head(13).copy()
    # unter der Quote die gewonnenen (grün) und verlorenen (rot) Bullys nebeneinander
    top["Label"] = [
        f'{q:.1f}%<br><span style="color:#0B6E2E">{g:.0f}</span>'
        f'\u00a0\u00a0<span style="color:#FF5252">{v:.0f}</span>'
        for q, g, v in zip(top["Bully-Gewinn %"], top["Bully-Plus"], top["Bully-Minus"])
    ]
    fig = px.bar(top, x="Name", y="Bully-Gewinn %", title="Bully-Gewinnquote", text="Label")
    fig.update_traces(textposition='inside', textangle=0, showlegend=False)
    return _style_plot(fig)

def plot_gespielt(df_in):
    if "Gespielt" not in df_in.columns:
        df_in["Gespielt"] = "Nein"
    # Zähle nur "Ja" Werte pro Spieler
    gespielt = df_in[df_in["Gespielt"] == "Ja"].groupby("Name").size().reset_index(name="Anzahl Spiele")
    top = gespielt.sort_values("Anzahl Spiele", ascending=False).head(13)
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


def _style_plot(fig, tickangle=-90):
    """Einheitliche Formatierung - kompakt genug fuer Handy-Bildschirme."""
    fig.update_layout(
        yaxis_title=None,
        xaxis_title=None,
        title_x=0.02,
        title_font_size=16,
        font=dict(size=11),
        margin=dict(t=45, b=90, l=8, r=8),
        height=430,
        xaxis=dict(tickangle=tickangle, automargin=True),
        yaxis=dict(automargin=True),
        # Legende unter den Plot, damit sie auf dem Handy keine Breite frisst
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0),
    )
    fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"])
    return fig


def plot_summe(df_in, column, title, ohne_torhueter=True):
    """Einfacher Summen-Balken pro Spieler."""
    d = nur_feldspieler(df_in) if ohne_torhueter else df_in
    if column not in d.columns or d.empty:
        return None
    top = d.groupby("Name")[column].sum().sort_values(ascending=False).head(13).reset_index()
    if top[column].sum() == 0:
        return None
    fig = px.bar(top, x="Name", y=column, title=title, text=column)
    fig.update_traces(texttemplate='%{text:.0f}', textposition='inside', textangle=0, showlegend=False)
    return _style_plot(fig)


def plot_quote(df_in, zaehler, nenner, title, ohne_torhueter=True):
    """Prozentquote zaehler/nenner pro Spieler. Spieler ohne Nenner fallen raus."""
    d = nur_feldspieler(df_in) if ohne_torhueter else df_in
    if zaehler not in d.columns or nenner not in d.columns or d.empty:
        return None
    agg = d.groupby("Name")[[zaehler, nenner]].sum()
    agg = agg[agg[nenner] > 0]
    if agg.empty:
        return None
    agg["Quote"] = 100 * agg[zaehler] / agg[nenner]
    # nach der Quote sortiert, im Balken steht Absolutwert und Prozent
    top = agg.sort_values("Quote", ascending=False).head(13).reset_index()
    top["Label"] = [f"{z:.0f}<br>{q:.1f}%" for z, q in zip(top[zaehler], top["Quote"])]
    fig = px.bar(top, x="Name", y="Quote", title=title, text="Label")
    fig.update_traces(textposition='inside', textangle=0, showlegend=False)
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
    fig = px.bar(top, x="Name", y="Fangquote", title="Torhüter-Fangquote", text="Fangquote")
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='inside', textangle=0, showlegend=False)
    return _style_plot(fig)


def _zeige(fig):
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})


def plot_torschuss_anteile(df_in, gegentore=None):
    """Team: wie sich die gegnerischen Torschüsse auf Block / Parade / Gegentor verteilen."""
    if SPALTE_BLOCK not in df_in.columns:
        return None, None

    feld = nur_feldspieler(df_in)
    tw = nur_torhueter(df_in)

    geblockt = float(feld[SPALTE_BLOCK].sum())
    gehalten = float(tw[SPALTE_BLOCK].sum()) if not tw.empty else 0.0
    if gegentore is None:
        # Rueckfall: Minus des eingesetzten Torhueters
        gegentore = float(tw["Minus"].sum()) if not tw.empty else 0.0
    gegentore = float(gegentore)

    gesamt = geblockt + gehalten + gegentore
    if gesamt <= 0:
        return None, None

    daten = pd.DataFrame({
        "Torschüsse": ["Torschüsse gegen Wygorazzi"] * 3,
        "Kategorie": ["Geblockt", "Vom Torhüter gehalten", "Gegentore"],
        "Anzahl": [geblockt, gehalten, gegentore],
    })
    daten["Label"] = [f"{a:.0f} ({100 * a / gesamt:.1f}%)" for a in daten["Anzahl"]]

    # ein grosser Balken = alle Torschuesse gegen Wygorazzi, anteilig aufgeteilt
    fig = px.bar(daten, x="Torschüsse", y="Anzahl", color="Kategorie",
                 title="Anteil von uns geblockten Torschüssen auf unser Tor", text="Label",
                 color_discrete_sequence=["#00FFAA", "#4C9BE8", "#E86A6A"])
    fig.update_traces(textposition='inside', textangle=0)
    fig.update_layout(legend_title_text="")
    return _style_plot(fig, tickangle=0), None


def plot_abschlussquote(df_in):
    """Team: Schüsse -> davon aufs Tor -> davon im Tor."""
    if SPALTE_SCHUESSE not in df_in.columns or SPALTE_SAT not in df_in.columns:
        return None, None

    feld = nur_feldspieler(df_in)
    schuesse = float(feld[SPALTE_SCHUESSE].sum())
    sat = float(feld[SPALTE_SAT].sum())
    tore = float(feld["T"].sum())
    if schuesse <= 0:
        return None, None

    neben = max(schuesse - sat, 0.0)
    gehalten = max(sat - tore, 0.0)

    # Balken 1 = alle Schüsse (100%), Balken 2 = Torschüsse (100%)
    daten = pd.DataFrame({
        "Balken": ["Schüsse", "Schüsse", "Torschüsse", "Torschüsse"],
        "Kategorie": ["Neben das Tor", "Aufs Tor", "Gehalten", "Tor"],
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
                                  "Kategorie": ["Neben das Tor", "Aufs Tor", "Gehalten", "Tor"]},
                 color_discrete_map={
                     "Neben das Tor": "#E86A6A",
                     "Aufs Tor": "#4C9BE8",
                     "Gehalten": "#7F8FA6",
                     "Tor": "#00FFAA",
                 })
    fig.update_traces(textposition='inside', textangle=0)
    fig.update_layout(legend_title_text="")
    return _style_plot(fig, tickangle=0), None


def _zeige_mit_hinweis(fig, hinweis):
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})
        if hinweis:
            st.caption(hinweis)


def render_erweiterte_plots(df_in, gegentore=None):
    """Blocks, Fangquote, Balleroberungen und Schussquoten - Team und pro Spieler."""
    if not hat_erweiterte_daten(df_in):
        return

    st.markdown("---")

    _zeige(plot_summe(df_in, SPALTE_BLOCK, "Geblockte Schüsse"))
    _zeige(plot_fangquote(df_in))
    _zeige(plot_summe(df_in, SPALTE_BALLEROBERUNG, "Balleroberungen"))
    _zeige(plot_summe(df_in, SPALTE_SCHUESSE, "Schüsse pro Spieler"))
    _zeige(plot_quote(df_in, SPALTE_SAT, SPALTE_SCHUESSE, "Schüsse aufs Tor"))
    _zeige(plot_quote(df_in, "T", SPALTE_SAT, "Torquote aus den Torschüssen"))

    # Team-Auswertungen zuunterst
    st.markdown("### Teamstatistik")
    _zeige_mit_hinweis(*plot_torschuss_anteile(df_in, gegentore))
    _zeige_mit_hinweis(*plot_abschlussquote(df_in))


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

    # Try to extract scores (robustly)
    try:
        tore_w = int(meta["Tore Wygorazzi"]) if (meta is not None and "Tore Wygorazzi" in meta and pd.notna(meta["Tore Wygorazzi"])) else 0
    except:
        tore_w = 0
    try:
        tore_g = int(meta["Tore Gegner"]) if (meta is not None and "Tore Gegner" in meta and pd.notna(meta["Tore Gegner"])) else 0
    except:
        tore_g = 0

    opponent = meta["Gegner"] if (meta is not None and "Gegner" in meta) else "Gegner unbekannt"
    # Datum_label wurde oben bereits korrekt (tagesbasiert) geparst
    datum_label = ""
    if meta is not None and "Datum_label" in meta and pd.notna(meta["Datum_label"]):
        datum_label = str(meta["Datum_label"])

    # Header
    # Als ein HTML-Block statt st.columns: bleibt auf dem Handy nebeneinander
    st.markdown(
        f"""
        <div class='result-box scoreboard'>
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
            players = df_saison[(df_saison[MATCH_COL] == selected_match_id) & (df_saison["Linie"].astype(str) == str(linie))]["Name"].tolist()
            if players:
                for p in players:
                    st.markdown(f"<div class='player-name'>• {p}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='subtle'>Keine Spieler</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

   

 

    st.markdown("---")
    st.markdown("### Spieler-Statistikplots für dieses Match")
    if df_for_plots.empty:
        st.info("Für dieses Spiel sind keine Spielerdaten erfasst.")
    else:
        st.plotly_chart(plot_top(df_for_plots, "T", "Tore"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_top(df_for_plots, "A", "Assists"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_top(df_for_plots, "Punkte", "Punkte (T+A)"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_top(df_for_plots, "PlusMinus", "Plus-Minus"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_top(df_for_plots, "Strafen", "Strafen"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_bully(df_for_plots), use_container_width=True, config={'staticPlot': True})
        render_erweiterte_plots(df_for_plots, gegentore=tore_g)

# ---------------------------
# If "Alle Spiele" selected: show full dashboard (as before) plus wygo season stats fixed
# ---------------------------
if selection == "Alle Spiele":
    # df_saison ist bereits aufbereitet

    # Plots
    st.markdown(f"## Spielerstatistik Saison {selected_saison}")
    if df_saison.empty:
        st.info(f"Für die Saison {selected_saison} sind noch keine Spielerdaten erfasst.")
    else:
        st.plotly_chart(plot_top(df_saison, "T", "Tore"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_top(df_saison, "A", "Assists"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_top(df_saison, "Punkte", "Punkte (T+A)"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_top(df_saison, "PlusMinus", "Plus-Minus"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_top(df_saison, "Strafen", "Strafen"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_bully(df_saison), use_container_width=True, config={'staticPlot': True})

        # Gegentore nur aus den Spielen zaehlen, fuer die auch Spielerdaten existieren
        _ids_mit_daten = df_saison[MATCH_COL].dropna().unique()
        _gegentore = pd.to_numeric(
            wygo_saison[wygo_saison[MATCH_COL].isin(_ids_mit_daten)]["Tore Gegner"],
            errors="coerce",
        ).fillna(0).sum()
        render_erweiterte_plots(df_saison, gegentore=_gegentore)

        st.plotly_chart(plot_gespielt(df_saison), use_container_width=True, config={'staticPlot': True})

    st.markdown("---")
    # Wygo aggregate stats per season (fix counts for Sieg/Niederlage/Unentschieden)
    st.subheader("Wygo - Gesamt- und Saisonkennzahlen")

    # Ensure the flag columns are numeric 0/1
    for flag in ["Sieg", "Niederlage", "Unentschieden"]:
        if flag in wygo.columns:
            # Konvertiere "Ja" zu 1, alles andere zu 0
            wygo[flag] = wygo[flag].apply(lambda x: 1 if str(x).strip().lower() == "ja" else 0)
        else:
            wygo[flag] = 0

    saisons = {
        selected_saison: wygo[wygo[SEASON_COL] == selected_saison],
        "Gesamt": wygo,
    }

    def zeige_statistik(df_s, titel):
        # Safe numeric sums
        tore_wygo_sum = int(pd.to_numeric(df_s.get('Tore Wygorazzi', 0), errors='coerce').fillna(0).sum())
        tore_gegner_sum = int(pd.to_numeric(df_s.get('Tore Gegner', 0), errors='coerce').fillna(0).sum())
        siege_sum = int(df_s['Sieg'].sum())
        niederlagen_sum = int(df_s['Niederlage'].sum())
        unentschieden_sum = int(df_s['Unentschieden'].sum())
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

    for saison_name, df_saison in saisons.items():
        zeige_statistik(df_saison, saison_name)


    