import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from io import BytesIO

# ---------------------------
# Page config & CSS
# ---------------------------
st.set_page_config(page_title="Spielerstatistik UHC Wygorazzi", layout="wide")

st.markdown(
    """
    <style>
    .big-title {font-size:28px; font-weight:700; color:#073763; margin-bottom:0.2rem;}
    .subtle {color: #6b7280; font-size:13px;}
    .result-box {background:linear-gradient(90deg, rgba(7,55,99,0.04), rgba(255,255,255,0.0)); padding:14px; border-radius:12px;}
    .line-card {background:#ffffff; padding:10px; border-radius:8px; box-shadow: 0 1px 6px rgba(0,0,0,0.06); margin-bottom:8px;}
    .player-name {font-size:14px; margin:4px 0;}
    .small-metric {font-size:13px; color:#374151;}
    .header-row {display:flex; justify-content:space-between; align-items:center;}
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
# (User confirmed: "Gegner", "Tore Gegner", "Tore Wygorazzi")
if "Gegner" not in wygo.columns:
    wygo["Gegner"] = "Gegner unbekannt"
if "Tore Gegner" not in wygo.columns:
    wygo["Tore Gegner"] = 0
if "Tore Wygorazzi" not in wygo.columns:
    wygo["Tore Wygorazzi"] = 0

# Build dropdown label and sort by date desc
wygo_valid_date["Dropdown_Label"] = wygo_valid_date.apply(
    lambda r: f"{r['Datum_label']} — vs {r['Gegner']}  (ID {r.get(MATCH_COL)})", axis=1
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
    try:
        raw_id = selection.split("(ID")[-1].replace(")", "").strip()
        try:
            selected_match_id = int(raw_id)
        except:
            selected_match_id = raw_id
    except:
        selected_match_id = None

# Helper: safely convert Match_Id columns in df/wygo to comparable type
# (avoid mismatches due to strings vs ints)
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
    df_for_plots = df[df[MATCH_COL] == selected_match_id].copy()

# ---------------------------
# Function: generic top-bar plots using df_for_plots
# ---------------------------
def plot_top(df_in, column, title):
    # If column missing, create zeros to avoid errors
    if column not in df_in.columns:
        df_in[column] = 0
    top = df_in.groupby("Name")[column].sum().sort_values(ascending=False).head(13).reset_index()
    # handle if column numeric or not
    fig = px.bar(top, x="Name", y=column, title=title, text=column)
    fig.update_traces(texttemplate='%{text}', textposition='inside', showlegend=False)
    fig.update_layout(yaxis_title=None, xaxis_title=None, title_x=0.02, margin=dict(t=40,b=20))
    fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"])
    return fig

def plot_bully(df_in):
    if "Bully-Plus" not in df_in.columns or "Bully-Minus" not in df_in.columns:
        df_in["Bully-Plus"] = df_in.get("Bully-Plus", 0)
        df_in["Bully-Minus"] = df_in.get("Bully-Minus", 0)
    bully = df_in.groupby("Name")[["Bully-Plus", "Bully-Minus"]].sum().reset_index()
    bully["Bully-Gewinn %"] = 100 * bully["Bully-Plus"] / (bully["Bully-Plus"] + bully["Bully-Minus"]).replace({0: np.nan})
    bully["Bully-Gewinn %"] = bully["Bully-Gewinn %"].fillna(0)
    top = bully.sort_values("Bully-Gewinn %", ascending=False).head(13)
    fig = px.bar(top, x="Name", y="Bully-Gewinn %", title="Bully-Gewinnquote", text="Bully-Gewinn %")
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='inside', showlegend=False)
    fig.update_layout(yaxis_title=None, xaxis_title=None, title_x=0.02, margin=dict(t=40,b=20))
    fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"])
    return fig

def plot_linie(df_in):
    # need PlusMinus_L per player aggregated by Linie
    if "Linie" not in df_in.columns:
        df_in["Linie"] = "0"
    if "Linie-Plus" in df_in.columns and "Linie-Minus" in df_in.columns:
        df_in["PlusMinus_L"] = df_in["Linie-Plus"] - df_in["Linie-Minus"]
    else:
        # fallback: aggregate PlusMinus by Linie if exists
        if "PlusMinus" in df_in.columns:
            tmp = df_in.groupby("Linie")["PlusMinus"].sum().reset_index().rename(columns={"PlusMinus":"PlusMinus_L"})
            df_plot = tmp
            fig = px.bar(df_plot, x="Linie", y="PlusMinus_L", title="Plus-Minus nach Linie", text="PlusMinus_L")
            fig.update_traces(texttemplate='%{text}', textposition='inside', showlegend=False)
            fig.update_layout(xaxis=dict(type="category"), yaxis_title=None, xaxis_title=None, title_x=0.02, margin=dict(t=40,b=20))
            fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"])
            return fig
        else:
            df_in["PlusMinus_L"] = 0
    top = df_in.groupby("Linie")["PlusMinus_L"].sum().reset_index()
    fig = px.bar(top, x="Linie", y="PlusMinus_L", title="Plus-Minus nach Linie", text="PlusMinus_L")
    fig.update_traces(texttemplate='%{text}', textposition='inside', showlegend=False)
    fig.update_layout(xaxis=dict(type="category"), yaxis_title=None, xaxis_title=None, title_x=0.02, margin=dict(t=40,b=20))
    fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"])
    return fig

# ---------------------------
# When a single match is selected: show header, lines, player table, metrics, and the same plots but filtered
# ---------------------------
if selected_match_id is not None:
    # get wygo meta row for this match if exists
    meta = wygo[wygo[MATCH_COL] == selected_match_id]
    if not meta.empty:
        meta = meta.iloc[0]
    else:
        meta = None

    # Try to extract scores
    tore_w = int(meta["Tore Wygorazzi"]) if (meta is not None and "Tore Wygorazzi" in meta and pd.notna(meta["Tore Wygorazzi"])) else 0
    tore_g = int(meta["Tore Gegner"]) if (meta is not None and "Tore Gegner" in meta and pd.notna(meta["Tore Gegner"])) else 0
    opponent = meta["Gegner"] if (meta is not None and "Gegner" in meta) else "Gegner unbekannt"
    datum_label = meta["Datum"].strftime("%Y-%m-%d") if (meta is not None and hasattr(meta["Datum"], "strftime")) else (meta["Datum"] if (meta is not None and "Datum" in meta) else "")

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
    # Use df_for_plots (which is filtered to selected match)
    left_col, right_col = st.columns([2, 1])
    with left_col:
        st.plotly_chart(plot_top(df_for_plots, "T", "Tore (Top in Auswahl)"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_top(df_for_plots, "A", "Assists (Top in Auswahl)"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_top(df_for_plots, "Punkte", "Punkte (T+A) (Top in Auswahl)"), use_container_width=True, config={'staticPlot': True})
    with right_col:
        st.plotly_chart(plot_top(df_for_plots, "PlusMinus", "Plus-Minus (Top in Auswahl)"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_bully(df_for_plots), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_linie(df_for_plots), use_container_width=True, config={'staticPlot': True})

# ---------------------------
# If "Alle Spiele" selected: show full dashboard (as before)
# ---------------------------
if selection == "Alle Spiele":
    # Preprocessing similar to your original code
    if "Linie" in df.columns:
        df["Linie"] = df["Linie"].astype(str)
    else:
        df["Linie"] = "0"

    for col in ["Plus", "Minus"]:
        if col in df.columns:
            df[col] = df[col].replace("-", np.nan)
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    if "Bully-Plus" not in df.columns: df["Bully-Plus"] = df.get("Bully-Plus", 0)
    if "Bully-Minus" not in df.columns: df["Bully-Minus"] = df.get("Bully-Minus", 0)

    df["PlusMinus"] = df["Plus"] - df["Minus"] if ("Plus" in df.columns and "Minus" in df.columns) else df.get("PlusMinus", 0)
    if "T" in df.columns and "A" in df.columns:
        df["Punkte"] = df["T"].fillna(0) + df["A"].fillna(0)
    else:
        df["Punkte"] = df.get("Punkte", 0)

    # For Linie plot
    if "Linie-Plus" in df.columns and "Linie-Minus" in df.columns:
        df["PlusMinus_L"] = df["Linie-Plus"] - df["Linie-Minus"]
    else:
        df["PlusMinus_L"] = df.get("PlusMinus_L", 0)

    # Plots
    st.markdown("## Gesamt- und Saisonstatistiken")
    left_col, right_col = st.columns([2, 1])
    with left_col:
        st.plotly_chart(plot_top(df, "T", "Tore (Top 13)"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_top(df, "A", "Assists (Top 13)"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_top(df, "Punkte", "Punkte (T+A) (Top 13)"), use_container_width=True, config={'staticPlot': True})
    with right_col:
        st.plotly_chart(plot_top(df, "PlusMinus", "Plus-Minus (Top 13)"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_bully(df), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_linie(df), use_container_width=True, config={'staticPlot': True})

    st.markdown("---")
    # Wygo aggregate stats (as previously)
    st.subheader("Wygo - Gesamt- und Saisonkennzahlen")
    saisons = {"Gesamt": wygo}
    if "Saison" in wygo.columns:
        unique_saisons = wygo["Saison"].dropna().unique().tolist()
        for s in unique_saisons:
            saisons[s] = wygo[wygo["Saison"] == s]

    def zeige_statistik(df_s, titel):
        try:
            tore_wygo_sum = int(pd.to_numeric(df_s['Tore Wygorazzi'], errors='coerce').fillna(0).sum())
        except:
            tore_wygo_sum = 0
        try:
            tore_gegner_sum = int(pd.to_numeric(df_s['Tore Gegner'], errors='coerce').fillna(0).sum())
        except:
            tore_gegner_sum = 0
        siege_sum = int(pd.to_numeric(df_s['Sieg'], errors='coerce').fillna(0).sum()) if 'Sieg' in df_s.columns else 0
        niederlagen_sum = int(pd.to_numeric(df_s['Niederlage'], errors='coerce').fillna(0).sum()) if 'Niederlage' in df_s.columns else 0
        unentschieden_sum = int(pd.to_numeric(df_s['Unentschieden'], errors='coerce').fillna(0).sum()) if 'Unentschieden' in df_s.columns else 0
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
        col4.metric("Siege", f"{sieg_sum}")
        col5.metric("Niederlagen", f"{niederlagen_sum}")
        col6.metric("Unentschieden", f"{unentschieden_sum}")

    for saison_name, df_saison in saisons.items():
        zeige_statistik(df_saison, saison_name)

st.markdown("---")
st.markdown("<div class='subtle'>Hinweis: Nur Spiele mit einem gültigen Datum erscheinen im Dropdown. Wenn etwas nicht korrekt angezeigt wird, sende mir bitte die exakten Spaltennamen oder ein Beispiel-CSV.</div>", unsafe_allow_html=True)
