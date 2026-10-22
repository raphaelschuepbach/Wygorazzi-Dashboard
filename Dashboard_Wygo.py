import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os
import re
from io import BytesIO

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
st.set_page_config(page_title="Spielerstatistik UHC Wygorazzi", layout="centered")

st.markdown(
    f"""
    <style>
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
    .chip {{
      font-size:11px; font-weight:600; padding:3px 8px; border-radius:6px;
      border:1px solid transparent; color:{FARBEN["label_innen"]};
    }}
    .chip.sieg {{background:var(--gut);}}
    .chip.remis {{background:var(--neutral);}}
    .chip.nieder {{background:var(--schlecht);}}

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
st.markdown(
    '<div class="kicker">UHC Wygorazzi</div>'
    '<div class="big-title">Spielerstatistik</div>',
    unsafe_allow_html=True,
)

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
        chips.append(f"<span class='chip {klasse}' title='{titel}'>{t}:{g}</span>")

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
    # Hilfsspalten fuer die Quoten (jeweils Plus + Minus = Anzahl Situationen)
    for basis in ["Bully", "Powerplay", "Boxplay"]:
        pl, mi = f"{basis}-Plus", f"{basis}-Minus"
        if pl in df_in.columns and mi in df_in.columns:
            df_in[f"{basis}-Gesamt"] = df_in[pl] + df_in[mi]
        else:
            df_in[f"{basis}-Gesamt"] = 0
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
        margin=dict(t=45, b=90, l=8, r=8),
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
    top = d.groupby("Name")[column].sum().sort_values(ascending=False).head(13).reset_index()
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
    top = agg.sort_values("Quote", ascending=False).head(13).reset_index()
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


def _zeige(fig):
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})


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


def _zeige_oder(fig, hinweis):
    """Plot anzeigen - oder kurz sagen, warum es ihn hier nicht gibt."""
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})
    else:
        st.caption(hinweis)


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


def plot_linie_plusminus(df_in):
    """Plus-Minus je Linie.

    Linie-Plus/Linie-Minus steht bei allen Spielern einer Linie gleich drin,
    darum pro Spiel und Linie nur einmal nehmen statt zu summieren.
    """
    d = nur_linien(df_in)
    if d.empty or "Linie-Plus" not in d.columns or MATCH_COL not in d.columns:
        return None
    pro_spiel = d.groupby([MATCH_COL, "Linie_Label"])[["Linie-Plus", "Linie-Minus"]].first()
    agg = pro_spiel.groupby("Linie_Label").sum()
    agg = agg.reindex([l for l in LINIEN_FARBEN if l in agg.index])
    if agg.empty:
        return None

    agg["PlusMinus"] = agg["Linie-Plus"] - agg["Linie-Minus"]
    agg = agg.reset_index()
    agg["Label"] = [
        f'{pm:+.0f}<br>'
        f'<span style="color:{FARBEN["label_gut"]}">{p:.0f}</span>'
        f'\u00a0\u00a0'
        f'<span style="color:{FARBEN["label_schlecht"]}">{m:.0f}</span>'
        for pm, p, m in zip(agg["PlusMinus"], agg["Linie-Plus"], agg["Linie-Minus"])
    ]
    fig = px.bar(agg, x="Linie_Label", y="PlusMinus", title="Plus-Minus je Linie",
                 text="Label", color="Linie_Label", color_discrete_map=LINIEN_FARBEN)
    fig.update_traces(textposition='inside', textangle=0)
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


def tab_pro_spieler(df_in, zeige_gespielt=False):
    _zeige(plot_top(df_in, "T", "Tore"))
    _zeige(plot_top(df_in, "A", "Assists"))
    _zeige(plot_top(df_in, "Punkte", "Punkte (T+A)"))
    _zeige(plot_top(df_in, "PlusMinus", "Plus-Minus"))
    _zeige(plot_top(df_in, "Strafen", "Strafen"))
    _zeige(plot_bully(df_in))
    if hat_erweiterte_daten(df_in):
        _zeige(plot_summe(df_in, SPALTE_BLOCK, "Geblockte Schüsse"))
        _zeige(plot_fangquote(df_in))
        _zeige(plot_summe(df_in, SPALTE_BALLEROBERUNG, "Balleroberungen"))
        _zeige(plot_summe(df_in, SPALTE_SCHUESSE, "Schüsse pro Spieler"))
        _zeige(plot_quote(df_in, SPALTE_SAT, SPALTE_SCHUESSE, "Schüsse aufs Tor"))
        _zeige(plot_quote(df_in, "T", SPALTE_SAT, "Torquote aus den Torschüssen"))
    if hat_spezial_daten(df_in):
        _zeige_oder(plot_quote(df_in, "Powerplay-Plus", "Powerplay-Gesamt",
                               "Powerplay-Erfolgsquote"),
                    "Powerplay-Erfolgsquote: keine Powerplay-Situation erfasst.")
        _zeige_oder(plot_quote(df_in, "Boxplay-Plus", "Boxplay-Gesamt",
                               "Boxplay-Erfolgsquote"),
                    "Boxplay-Erfolgsquote: keine Boxplay-Situation erfasst.")
    if zeige_gespielt:
        _zeige(plot_gespielt(df_in))


def tab_pro_linie(df_in):
    _zeige(plot_linie_plusminus(df_in))
    _zeige(plot_linie_summe(df_in, "Strafen", "Strafen je Linie"))
    _zeige(plot_linie_quote(df_in, "Bully-Plus", "Bully-Gesamt", "Bully-Gewinnquote je Linie"))
    if hat_erweiterte_daten(df_in):
        _zeige(plot_linie_summe(df_in, SPALTE_BLOCK, "Geblockte Schüsse je Linie"))
        _zeige(plot_linie_summe(df_in, SPALTE_BALLEROBERUNG, "Balleroberungen je Linie"))
        _zeige(plot_linie_summe(df_in, SPALTE_SCHUESSE, "Schüsse je Linie"))
        _zeige(plot_linie_quote(df_in, SPALTE_SAT, SPALTE_SCHUESSE, "Schüsse aufs Tor je Linie"))
        _zeige(plot_linie_quote(df_in, "T", SPALTE_SAT, "Torquote aus den Torschüssen je Linie"))
    if hat_spezial_daten(df_in):
        # je Situation sind im Powerplay 3 Spieler markiert, im Boxplay 2
        _zeige_oder(plot_linie_quote(df_in, "Powerplay-Plus", "Powerplay-Gesamt",
                                     "Powerplay-Erfolgsquote je Linie", teiler=3),
                    "Powerplay-Erfolgsquote je Linie: keine Powerplay-Situation erfasst.")
        _zeige_oder(plot_linie_quote(df_in, "Boxplay-Plus", "Boxplay-Gesamt",
                                     "Boxplay-Erfolgsquote je Linie", teiler=2),
                    "Boxplay-Erfolgsquote je Linie: keine Boxplay-Situation erfasst.")


def tab_team(df_in, gegentore=None, situationen=None):
    _zeige_oder(plot_torschuss_anteile(df_in, gegentore),
                "Anteil von uns geblockten Torschüssen: keine Block-Daten erfasst.")
    _zeige_oder(plot_abschlussquote(df_in),
                "Abschlussquote: keine Schuss-Daten erfasst.")
    _zeige_oder(plot_spezial_team(situationen, "Powerplay"),
                "Powerplay-Erfolg: keine Überzahl erfasst.")
    _zeige_oder(plot_spezial_team(situationen, "Boxplay"),
                "Boxplay-Erfolg: keine Unterzahl erfasst.")


def render_tabs(df_in, gegentore=None, zeige_gespielt=False, team_extra=None, situationen=None):
    t_spieler, t_team, t_linie = st.tabs(["Pro Spieler", "Team", "Pro Linie"])
    with t_spieler:
        tab_pro_spieler(df_in, zeige_gespielt=zeige_gespielt)
    with t_team:
        tab_team(df_in, gegentore=gegentore, situationen=situationen)
        if team_extra is not None:
            team_extra()
    with t_linie:
        tab_pro_linie(df_in)


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
            players = df_saison[(df_saison[MATCH_COL] == selected_match_id) & (df_saison["Linie"].astype(str) == str(linie))]["Name"].tolist()
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
        render_tabs(df_for_plots, gegentore=tore_g,
                    situationen=team_situationen(wygo[wygo[MATCH_COL] == selected_match_id]))

# ---------------------------
# If "Alle Spiele" selected: show full dashboard (as before) plus wygo season stats fixed
# ---------------------------
if selection == "Alle Spiele":
    # df_saison ist bereits aufbereitet

    # Plots
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
        render_tabs(df_saison, gegentore=_gegentore, zeige_gespielt=True,
                    team_extra=zeige_wygo_kennzahlen,
                    situationen=team_situationen(
                        wygo_saison[wygo_saison[MATCH_COL].isin(_ids_mit_daten)]))


    