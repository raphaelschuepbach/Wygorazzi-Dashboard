import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from io import BytesIO

# ---------------------------
# Page config & CSS
# ---------------------------
st.set_page_config(page_title="Spielerstatistik UHC Wygorazzi", layout="centered")

st.markdown(
    """
    <style>
    .big-title {font-size:28px; font-weight:700; color:#073763; margin-bottom:0.2rem;}
    .subtle {color: #6b7280; font-size:13px;}
    .result-box {background:linear-gradient(90deg, rgba(7,55,99,0.04), rgba(255,255,255,0.0)); padding:14px; border-radius:12px;}
    
    .player-name {font-size:14px; margin:4px 0;}
    .small-metric {font-size:13px; color:#374151;}
    .header-row {display:flex; justify-content:space-between; align-items:center;}
    
    .line-card {
        background-color: #f0f0f0;  /* hellgrauer Hintergrund */
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 8px;
    }
    .line-card strong {
        color: #333333;  /* dunkle Überschrift */
        font-size: 16px;
    }
    .player-name {
        color: #f0f0f0;  /* dunkler Text für Spieler */
        margin-left: 10px;
    }
    .subtle {
        color: #666666;  /* grauer Text für "Keine Spieler" */
        font-style: italic;
        margin-left: 10px;
    }   

    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# Read CSVs
# ---------------------------
df = pd.read_csv("Spieler_Statistik_25_26.csv")
wygo = pd.read_csv("Statistik_Wygo.csv", sep=",")

# ---------------------------
# Clean column names (trim spaces) and normalize
# ---------------------------
df.columns = df.columns.str.strip()
wygo.columns = wygo.columns.str.strip()

# Config: Match ID column name (user said it's 'Match_Id')
MATCH_COL = "Match_Id"

# ---------------------------
# Parse Datum in wygo and build dropdown labels
# ---------------------------
# Ensure 'Datum' exists as you confirmed
if "Datum" in wygo.columns:
    wygo["Datum_parsed"] = pd.to_datetime(wygo["Datum"], errors="coerce")
    # Only keep rows with a valid date for dropdown
    wygo_valid_date = wygo[~wygo["Datum_parsed"].isna()].copy()
    # Readable date label
    wygo_valid_date["Datum_label"] = wygo_valid_date["Datum_parsed"].dt.strftime("%Y-%m-%d")
else:
    wygo["Datum_parsed"] = pd.NaT
    wygo_valid_date = wygo.iloc[0:0].copy()
    wygo_valid_date["Datum_label"] = ""

# Ensure Gegner and score columns exist exactly as you said
if "Gegner" not in wygo.columns:
    wygo["Gegner"] = "Gegner unbekannt"
if "Tore Gegner" not in wygo.columns:
    wygo["Tore Gegner"] = 0
if "Tore Wygorazzi" not in wygo.columns:
    wygo["Tore Wygorazzi"] = 0

# Build dropdown label and sort by date desc (only valid-dated matches)
wygo_valid_date["Dropdown_Label"] = wygo_valid_date.apply(
    lambda r: f"{r['Datum_label']} — vs {r['Gegner']} ", axis=1
)
wygo_valid_date = wygo_valid_date.sort_values("Datum_parsed", ascending=False).reset_index(drop=True)

# ---------------------------
# Top header + dropdown
# ---------------------------
st.markdown('<div class="header-row"><div><h1 class="big-title">Spielerstatistik UHC Wygorazzi</h1>'
            '<div class="subtle">Saison 25/26 — </div></div></div>',
            unsafe_allow_html=True)
st.markdown("---")

options = ["Alle Spiele"] + wygo_valid_date["Dropdown_Label"].tolist()
selection = st.selectbox("Wähle ein Spiel:", options, index=0)

# Extract selected Match_Id (None for All)
selected_match_id = None
if selection != "Alle Spiele":
    # We created labels without IDs in this variant; try to find match by date+opponent
    # Attempt to parse date and opponent from label
    try:
        parts = selection.split("—")
        date_part = parts[0].strip()
        opponent_part = parts[1].strip().replace("vs ", "")
        found = wygo_valid_date[
            (wygo_valid_date["Datum_label"] == date_part) &
            (wygo_valid_date["Gegner"].astype(str) == opponent_part)
        ]
        if not found.empty:
            selected_match_id = found.iloc[0].get(MATCH_COL, None)
    except Exception:
        selected_match_id = None

# Helper: safely convert Match_Id columns in df/wygo to comparable type
def normalize_match_col(df_obj):
    if MATCH_COL in df_obj.columns:
        try:
            df_obj[MATCH_COL] = pd.to_numeric(df_obj[MATCH_COL], errors="ignore")
        except:
            pass

normalize_match_col(df)
normalize_match_col(wygo)

# Decide which df to use for plots: full or filtered by selected match
if selected_match_id is None:
    df_for_plots = df.copy()
else:
    # filter by match id
    df_for_plots = df[df[MATCH_COL] == selected_match_id].copy()

# ---------------------------
# Ensure numeric preprocessing for df_for_plots (fixes PlusMinus, Punkte, etc.)
# ---------------------------
def preprocess_player_stats(df_in):
    # Coerce columns to numeric where needed, fillna with 0
    for col in ["Plus", "Minus", "T", "A", "Bully-Plus", "Bully-Minus", "Linie-Plus", "Linie-Minus", "Strafen"]:
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

# Also preprocess main df used for "Alle Spiele" view when needed later
df = preprocess_player_stats(df)

# ---------------------------
# Function: generic top-bar plots using df_for_plots
# ---------------------------
def plot_top(df_in, column, title):
    if column not in df_in.columns:
        df_in[column] = 0
    
    # Spezialbehandlung für PlusMinus: durch Anzahl gespielte Spiele teilen
    if column == "PlusMinus":
        # Zähle gespielte Spiele pro Spieler (nur "Ja")
        gespielt_count = df_in[df_in.get("Gespielt", "Nein") == "Ja"].groupby("Name").size()
        # Summiere PlusMinus pro Spieler
        plusminus_sum = df_in.groupby("Name")[column].sum()
        # Berechne Durchschnitt
        top = (plusminus_sum / gespielt_count).fillna(0).sort_values(ascending=False).head(13).reset_index()
        top.columns = ["Name", column]
        fig = px.bar(top, x="Name", y=column, title=title, text=column)
        fig.update_traces(texttemplate='%{text:.2f}', textposition='inside', showlegend=False)
    else:
        top = df_in.groupby("Name")[column].sum().sort_values(ascending=False).head(13).reset_index()
        fig = px.bar(top, x="Name", y=column, title=title, text=column)
        fig.update_traces(texttemplate='%{text}', textposition='inside', showlegend=False)
    
    fig.update_layout(
        yaxis_title=None, 
        xaxis_title=None, 
        title_x=0.02, 
        margin=dict(t=40,b=100),
        height=500,
        xaxis=dict(tickangle=-90)
    )
    fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"])
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
    top = bully.sort_values("Bully-Gewinn %", ascending=False).head(13)
    fig = px.bar(top, x="Name", y="Bully-Gewinn %", title="Bully-Gewinnquote", text="Bully-Gewinn %")
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='inside', showlegend=False)
    fig.update_layout(
        yaxis_title=None, 
        xaxis_title=None, 
        title_x=0.02, 
        margin=dict(t=40,b=100),
        height=500,
        xaxis=dict(tickangle=-90)
    )
    fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"])
    return fig

def plot_top_single_match(df_in, column, title):
    """Spezielle Version für Einzelspiel-Ansicht ohne Division durch gespielte Spiele"""
    if column not in df_in.columns:
        df_in[column] = 0
    top = df_in.groupby("Name")[column].sum().sort_values(ascending=False).head(13).reset_index()
    fig = px.bar(top, x="Name", y=column, title=title, text=column)
    fig.update_traces(texttemplate='%{text}', textposition='inside', showlegend=False)
    fig.update_layout(
        yaxis_title=None, 
        xaxis_title=None, 
        title_x=0.02, 
        margin=dict(t=40,b=100),
        height=500,
        xaxis=dict(tickangle=-90)
    )
    fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"])
    return fig

def plot_gespielt(df_in):
    if "Gespielt" not in df_in.columns:
        df_in["Gespielt"] = "Nein"
    # Zähle nur "Ja" Werte pro Spieler
    gespielt = df_in[df_in["Gespielt"] == "Ja"].groupby("Name").size().reset_index(name="Anzahl Spiele")
    top = gespielt.sort_values("Anzahl Spiele", ascending=False).head(13)
    fig = px.bar(top, x="Name", y="Anzahl Spiele", title="Anzahl gespielte Spiele", text="Anzahl Spiele")
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='inside', showlegend=False)
    fig.update_layout(
        yaxis_title=None, 
        xaxis_title=None, 
        title_x=0.02, 
        margin=dict(t=40,b=100),
        height=500,
        xaxis=dict(tickangle=-90)
    )
    fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"])
    return fig

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
    datum_label = ""
    if meta is not None and "Datum" in meta and pd.notna(meta["Datum"]):
        try:
            datum_label = pd.to_datetime(meta["Datum"]).strftime("%Y-%m-%d")
        except:
            datum_label = str(meta["Datum"])

    # Header
    st.markdown("<div class='result-box'>", unsafe_allow_html=True)
    colL, colC, colR = st.columns([3, 2, 3])
    with colL:
        st.markdown(f"**Wygorazzi**")
        st.markdown(f"<div class='small-metric'>Heimteam</div>", unsafe_allow_html=True)
    with colC:
        st.markdown(f"<h2 style='text-align:center; margin:0;'>{tore_w} : {tore_g}</h2>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:center;' class='subtle'>{datum_label}</div>", unsafe_allow_html=True)
    with colR:
        st.markdown(f"**{opponent}**")
        st.markdown(f"<div class='small-metric'>Gast</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### Aufstellung nach Linien")
    line_cols = st.columns(3)
    for i, linie in enumerate(["1", "2", "3"]):
        with line_cols[i]:
            st.markdown(f"<div class='line-card'><strong>Linie {linie}</strong><hr style='margin:6px 0;'>", unsafe_allow_html=True)
            players = df[(df[MATCH_COL] == selected_match_id) & (df["Linie"].astype(str) == str(linie))]["Name"].tolist()
            if players:
                for p in players:
                    st.markdown(f"<div class='player-name'>• {p}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='subtle'>Keine Spieler</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

   

 

    st.markdown("---")
    st.markdown("### Spieler-Statistikplots für dieses Match")
    st.plotly_chart(plot_top(df_for_plots, "T", "Tore"), use_container_width=True, config={'staticPlot': True})
    st.plotly_chart(plot_top(df_for_plots, "A", "Assists"), use_container_width=True, config={'staticPlot': True})
    st.plotly_chart(plot_top(df_for_plots, "Punkte", "Punkte (T+A)"), use_container_width=True, config={'staticPlot': True})
    st.plotly_chart(plot_top_single_match(df_for_plots, "PlusMinus", "Plus-Minus"), use_container_width=True, config={'staticPlot': True})
    st.plotly_chart(plot_top(df_for_plots, "Strafen", "Strafen"), use_container_width=True, config={'staticPlot': True})
    st.plotly_chart(plot_bully(df_for_plots), use_container_width=True, config={'staticPlot': True})

# ---------------------------
# If "Alle Spiele" selected: show full dashboard (as before) plus wygo season stats fixed
# ---------------------------
if selection == "Alle Spiele":
    # df already preprocessed above

    # Plots
    st.markdown("## Gesamt- und Saisonstatistiken")
    st.plotly_chart(plot_top(df, "T", "Tore"), use_container_width=True, config={'staticPlot': True})
    st.plotly_chart(plot_top(df, "A", "Assists"), use_container_width=True, config={'staticPlot': True})
    st.plotly_chart(plot_top(df, "Punkte", "Punkte (T+A)"), use_container_width=True, config={'staticPlot': True})
    st.plotly_chart(plot_top(df, "PlusMinus", "Plus-Minus (Durchschnitt)"), use_container_width=True, config={'staticPlot': True})
    st.plotly_chart(plot_top(df, "Strafen", "Strafen"), use_container_width=True, config={'staticPlot': True})
    st.plotly_chart(plot_bully(df), use_container_width=True, config={'staticPlot': True})
    st.plotly_chart(plot_gespielt(df), use_container_width=True, config={'staticPlot': True})

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

    saisons = {"Gesamt": wygo}
    if "Saison" in wygo.columns:
        unique_saisons = wygo["Saison"].dropna().unique().tolist()
        for s in unique_saisons:
            saisons[s] = wygo[wygo["Saison"] == s]

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


    