import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from io import StringIO

# ---------------------------
# Streamlit Page Config
# ---------------------------
st.set_page_config(
    page_title="Spielerstatistik UHC Wygorazzi",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# Styling (kleine CSS-Verbesserungen)
# ---------------------------
st.markdown(
    """
    <style>
    .big-title {font-size:26px; font-weight:700; color:#0b3d91; margin-bottom:0.2rem;}
    .subtle {color: #6b7280;}
    .result-box {background:linear-gradient(90deg, rgba(11,61,145,0.06), rgba(255,255,255,0.0)); padding:12px; border-radius:10px;}
    .line-card {background:#fff; padding:12px; border-radius:8px; box-shadow: 0 1px 6px rgba(0,0,0,0.06);}
    .player-name {font-size:14px; margin:2px 0;}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# CSV einlesen
# ---------------------------
# Passe hier bei Bedarf die Dateinamen / Pfade an
df = pd.read_csv("Spieler_Statistik_25_26.csv")
wygo = pd.read_csv("Statistik_Wygo.csv", sep=',')

# ---------------------------
# Spaltennamen säubern (trim)
# ---------------------------
df.columns = df.columns.str.strip()
wygo.columns = wygo.columns.str.strip()

# ---------------------------
# Wichtige Annahme: beide DataFrames haben die Match-ID-Spalte 'Match_Id'
# (User hat bestätigt: heißt in beiden 'Match_Id')
# ---------------------------
MATCH_COL = "Match_Id"

# ---------------------------
# Datum parsen (wygo) und Label vorbereiten
# ---------------------------
# Stelle sicher, dass 'Datum' existiert
if "Datum" in wygo.columns:
    # Versuche parse, falls Format unterschiedlich: errors='coerce' -> NaT falls ungültig
    wygo["Datum_parsed"] = pd.to_datetime(wygo["Datum"], errors="coerce")
    # Fallback: wenn NaT, dann Rohwert als string
    wygo["Datum_label"] = wygo["Datum_parsed"].dt.strftime("%Y-%m-%d")
    wygo.loc[wygo["Datum_label"].isna(), "Datum_label"] = wygo.loc[wygo["Datum_label"].isna(), "Datum"].astype(str)
else:
    wygo["Datum_label"] = "N/A"

# ---------------------------
# Sicherstellen, dass Gegner-Spalte einen Namen hat; mögliche Varianten behandeln
# ---------------------------
# Versuche gängige Namen, sonst nimm first non-numeric string column
if "Gegner" not in wygo.columns:
    # suche mögliche Alternativen
    for alt in ["Gegnername", "Opponent", "Team", "Gegner Name"]:
        if alt in wygo.columns:
            wygo.rename(columns={alt: "Gegner"}, inplace=True)
            break
    # wenn immer noch nicht vorhanden, erstelle eine placeholder-Spalte
    if "Gegner" not in wygo.columns:
        wygo["Gegner"] = "Gegner unbekannt"

# ---------------------------
# Ergebnis-Spalten: sichere Benennung / Trimmen von Leerzeichen
# ---------------------------
wygo.columns = wygo.columns.str.replace('\xa0', ' ')  # geschützte Leerzeichen bereinigen
# Nach deinen früheren Beispielen gibt es 'Tore Wygorazzi' und 'Tore Gegner' - kontrollieren:
if "Tore Wygorazzi" not in wygo.columns and "Tore Wygorazzi " in wygo.columns:
    wygo.rename(columns={"Tore Wygorazzi ": "Tore Wygorazzi"}, inplace=True)
if "Tore Gegner" not in wygo.columns and "Tore Gegner " in wygo.columns:
    wygo.rename(columns={"Tore Gegner ": "Tore Gegner"}, inplace=True)

# Sichere bool-Spalten (Sieg / Niederlage / Unentschieden) bereinigen - falls mit Leerzeichen
for col in list(wygo.columns):
    if col.strip() != col:
        wygo.rename(columns={col: col.strip()}, inplace=True)

# Falls diese 3 Spalten als "Ja"/"Nein" vorliegen: in 1/0 umwandeln (robust)
for flag in ["Sieg", "Niederlage", "Unentschieden"]:
    if flag in wygo.columns:
        wygo[flag] = np.where(wygo[flag].astype(str).str.strip().str.lower() == "ja", 1,
                              np.where(wygo[flag].astype(str).str.strip().str.lower() == "nein", 0, wygo[flag]))

# ---------------------------
# Dropdown-Label: "vs Gegner (Datum) - Match_Id XYZ"  (lesbar & eindeutig)
# ---------------------------
wygo["Dropdown_Label"] = wygo.apply(
    lambda r: f"vs {r.get('Gegner','?')} — {r.get('Datum_label','?')}  (ID {r.get(MATCH_COL)})",
    axis=1
)

# Sortiere nach Datum falls vorhanden
if "Datum_parsed" in wygo.columns:
    wygo = wygo.sort_values(by=["Datum_parsed"], ascending=False).reset_index(drop=True)
else:
    wygo = wygo.reset_index(drop=True)

# ---------------------------
# Dropdown oben
# ---------------------------
st.markdown('<div style="display:flex; justify-content:space-between; align-items:center;">'
            '<div><h1 class="big-title">Spielerstatistik UHC Wygorazzi</h1>'
            '<div class="subtle">Saison 25/26 — interaktives Dashboard</div></div>'
            '<div style="text-align:right;"><img src="https://raw.githubusercontent.com/your/repo/logo.png" width="140" style="opacity:0.9"></div>'
            '</div>', unsafe_allow_html=True)

st.markdown("---")

# Auswahl oberhalb: Dropdown mit "Alle Spiele" + einzelne Spiele
options = ["Alle Spiele"] + wygo["Dropdown_Label"].tolist()
selection = st.selectbox("Wähle ein Spiel:", options, index=0)

# Wenn ein Spiel ausgewählt ist, extrahiere Match_Id
selected_match_id = None
if selection != "Alle Spiele":
    # extrahiere ID aus "(ID X)" am Ende
    try:
        # das Label hat "(ID <val>)" am Ende → split
        raw_id = selection.split("(ID")[-1].replace(")", "").strip()
        selected_match_id = raw_id
        # falls numerisch, konvertiere; sonst belasse
        try:
            selected_match_id = int(selected_match_id)
        except:
            pass

    except Exception:
        selected_match_id = None

# ---------------------------
# Bereich: Anzeige einzelnes Spiel
# ---------------------------
if selected_match_id is not None and selected_match_id != "Alle Spiele":
    match_row = wygo[wygo[MATCH_COL] == selected_match_id]
    if match_row.empty:
        st.error("Zum ausgewählten Match wurden keine Metadaten gefunden.")
    else:
        match_row = match_row.iloc[0]

        # Ergebniswerte robust extrahieren (Fälle mit NaN abfangen)
        try:
            tore_w = int(match_row.get("Tore Wygorazzi", 0))
        except:
            # Falls Spalte anders heißt, versuche alternative
            tore_w = int(match_row.get("Tore_Wygorazzi", 0) if match_row.get("Tore_Wygorazzi", None) is not None else 0)

        try:
            tore_g = int(match_row.get("Tore Gegner", 0))
        except:
            tore_g = int(match_row.get("Tore_Gegner", 0) if match_row.get("Tore_Gegner", None) is not None else 0)

        opponent = match_row.get("Gegner", "Gegner unbekannt")
        datum_label = match_row.get("Datum_label", "")

        # Anzeige: zentriertes Score-Layout
        st.markdown("<div class='result-box'>", unsafe_allow_html=True)
        colL, colC, colR = st.columns([3, 2, 3])
        with colL:
            st.markdown(f"**Wygorazzi**", unsafe_allow_html=True)
            st.markdown(f"<div class='subtle'>Heimteam</div>", unsafe_allow_html=True)
        with colC:
            st.markdown(f"<h2 style='text-align:center; margin:0;'>{tore_w} : {tore_g}</h2>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align:center;' class='subtle'>{datum_label}</div>", unsafe_allow_html=True)
        with colR:
            st.markdown(f"**{opponent}**", unsafe_allow_html=True)
            st.markdown(f"<div class='subtle'>Gast</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("### Aufstellung nach Linien")
        # Linien nebeneinander: 3 Spalten, Liste der Spielernamen pro Linie
        line_cols = st.columns(3)
        for i, linie in enumerate(["1", "2", "3"]):
            with line_cols[i]:
                st.markdown(f"<div class='line-card'><strong>Linie {linie}</strong><hr style='margin:6px 0;'>", unsafe_allow_html=True)
                # Filter df für Spieler dieses Matches und dieser Linie
                players = df[
                    (df[MATCH_COL] == selected_match_id) &
                    (df["Linie"].astype(str) == str(linie))
                ]["Name"].tolist()
                if players:
                    for p in players:
                        st.markdown(f"<div class='player-name'>• {p}</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='subtle'>Keine Spieler</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Spielerstatistik für dieses Match (alle Spalten)")

        # Filtere alle Spielerstats für dieses Match und zeige die komplette Tabelle
        match_players_df = df[df[MATCH_COL] == selected_match_id].copy()

        # Falls es keine Spieler gibt, Hinweis anzeigen
        if match_players_df.empty:
            st.info("Für dieses Match sind keine Spielerstatistiken im `df` vorhanden.")
        else:
            # Optional: berechne zusätzliche Spalten (falls in originalcode)
            # z.B. Punkte = T + A, PlusMinus bereits vorhanden
            if "T" in match_players_df.columns and "A" in match_players_df.columns and "Punkte" not in match_players_df.columns:
                match_players_df["Punkte"] = match_players_df["T"].fillna(0) + match_players_df["A"].fillna(0)

            # Anzeige als interaktive Tabelle
            st.dataframe(match_players_df.reset_index(drop=True), use_container_width=True)

            # Download-Button: CSV des Tabellen-Exports
            csv_buf = match_players_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Spielerstatistik als CSV herunterladen",
                data=csv_buf,
                file_name=f"Spielerstatistik_Match_{selected_match_id}.csv",
                mime="text/csv"
            )

        st.markdown("---")
        st.markdown("### Weitere Match-Kennzahlen")
        # Zeige wichtige Kennzahlen aus wygo (robust)
        cols = st.columns(6)
        def safe_get_int(row, colname):
            try:
                return int(row.get(colname, 0))
            except:
                try:
                    return int(str(row.get(colname)).strip())
                except:
                    return 0

        with cols[0]:
            st.metric("Tore Wygorazzi", f"{tore_w}")
        with cols[1]:
            st.metric("Tore Gegner", f"{tore_g}")
        with cols[2]:
            st.metric("Tordiff", f"{tore_w - tore_g:+d}")
        with cols[3]:
            sieg_val = safe_get_int(match_row, "Sieg") if "Sieg" in wygo.columns else 0
            st.metric("Sieg", "Ja" if sieg_val == 1 else "Nein")
        with cols[4]:
            nd_val = safe_get_int(match_row, "Niederlage") if "Niederlage" in wygo.columns else 0
            st.metric("Niederlage", "Ja" if nd_val == 1 else "Nein")
        with cols[5]:
            unent_val = safe_get_int(match_row, "Unentschieden") if "Unentschieden" in wygo.columns else 0
            st.metric("Unentschieden", "Ja" if unent_val == 1 else "Nein")

        st.markdown("---")

# ---------------------------
# Wenn "Alle Spiele" ausgewählt -> zeige Gesamt-Dashboard (deine bestehenden Plots)
# ---------------------------
if selection == "Alle Spiele":
    # ---------------------------
    # Vorverarbeitung & Berechnungen für df (dein vorheriger Code, bereinigt)
    # ---------------------------
    # Stelle sicher, dass 'Linie' als str vorliegt
    if "Linie" in df.columns:
        df["Linie"] = df["Linie"].astype(str)
    else:
        df["Linie"] = df.get("Linie", "0").astype(str)

    # "-" in Plus und Minus durch NaN ersetzen, dann in Zahlen umwandeln (robust)
    for col in ["Plus", "Minus"]:
        if col in df.columns:
            df[col] = df[col].replace("-", np.nan)
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    # Bully-Cols: sichere Existenz
    if "Bully-Plus" not in df.columns:
        df["Bully-Plus"] = df.get("Bully-Plus", 0)
    if "Bully-Minus" not in df.columns:
        df["Bully-Minus"] = df.get("Bully-Minus", 0)

    # PlusMinus und Punkte berechnen
    df["PlusMinus"] = df["Plus"] - df["Minus"] if ("Plus" in df.columns and "Minus" in df.columns) else df.get("PlusMinus", 0)
    if "T" in df.columns and "A" in df.columns:
        df["Punkte"] = df["T"].fillna(0) + df["A"].fillna(0)
    else:
        df["Punkte"] = df.get("Punkte", 0)

    # Bully-Statistiken aggregieren
    bully_stats = df.groupby("Name")[["Bully-Plus", "Bully-Minus"]].sum().reset_index()
    bully_stats["Bully-Gewinn %"] = 100 * bully_stats["Bully-Plus"] / (bully_stats["Bully-Plus"] + bully_stats["Bully-Minus"]).replace({0: np.nan})
    bully_stats["Bully-Gewinn %"] = bully_stats["Bully-Gewinn %"].fillna(0)

    # PlusMinus_L (Linien-Plus) falls vorhanden
    if "Linie-Plus" in df.columns and "Linie-Minus" in df.columns:
        df["PlusMinus_L"] = df["Linie-Plus"] - df["Linie-Minus"]
    else:
        df["PlusMinus_L"] = df.get("PlusMinus_L", 0)

    top3_linie = df.groupby("Linie")['PlusMinus_L'].sum().sort_values(ascending=False).reset_index()
    top3_linie = top3_linie[top3_linie["Linie"] != "0"]

    # ---------------------------
    # Funktionen für die Plots (wiederverwendet, leicht modernisiert)
    # ---------------------------
    def plot_top(df_in, column, title, color):
        top = df_in.groupby("Name")[column].sum().sort_values(ascending=False).head(13).reset_index()
        fig = px.bar(top, x="Name", y=column, title=title, text=column)
        fig.update_traces(marker_color=color, texttemplate='%{text}', textposition='inside', showlegend=False)
        fig.update_layout(yaxis=dict(dtick=1, tickmode='linear'), yaxis_title=None, xaxis_title=None, title_x=0.02)
        fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"])
        return fig

    def plot_top_bully(bully_df):
        top = bully_df.sort_values("Bully-Gewinn %", ascending=False).head(13)
        fig = px.bar(top, x="Name", y="Bully-Gewinn %", title="Bully-Gewinnquote", text="Bully-Gewinn %")
        fig.update_traces(marker_color="purple", texttemplate='%{text:.1f}%', textposition='inside', showlegend=False)
        fig.update_layout(yaxis_title=None, xaxis_title=None, title_x=0.02)
        fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"])
        return fig

    def plot_linie(top3_df):
        fig = px.bar(top3_df, x="Linie", y="PlusMinus_L", title="Plus-Minus nach Linie", text="PlusMinus_L")
        fig.update_traces(marker_color="green", texttemplate='%{text}', textposition='inside', showlegend=False)
        fig.update_layout(xaxis=dict(type="category"), yaxis_title=None, xaxis_title=None, title_x=0.02)
        fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"])
        return fig

    # ---------------------------
    # Dashboard-Hauptbereich: Plots (in 2 Spalten)
    # ---------------------------
    st.markdown("## Gesamt- und Saisonstatistiken")
    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.plotly_chart(plot_top(df, "T", "Tore (Top 13)", "royalblue"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_top(df, "A", "Assists (Top 13)", "seagreen"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_top(df, "Punkte", "Punkte (T+A) (Top 13)", "darkorange"), use_container_width=True, config={'staticPlot': True})

    with right_col:
        st.plotly_chart(plot_top(df, "PlusMinus", "Plus-Minus (Top 13)", "firebrick"), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_top_bully(bully_stats), use_container_width=True, config={'staticPlot': True})
        st.plotly_chart(plot_linie(top3_linie), use_container_width=True, config={'staticPlot': True})

    st.markdown("---")

    # ---------------------------
    # Wygo-Gesamtstatistiken (wie zuvor)
    # ---------------------------
    st.subheader("Wygo - Gesamt- und Saisonkennzahlen")
    # vorbereiten: Saisons dict
    saisons = {
        "Gesamt": wygo,
    }
    if "Saison" in wygo.columns:
        unique_saisons = wygo["Saison"].dropna().unique().tolist()
        for s in unique_saisons:
            saisons[s] = wygo[wygo["Saison"] == s]

    def zeige_statistik(df_s, titel):
        tore_wygo_sum = df_s.get('Tore Wygorazzi', 0)
        try:
            tore_wygo_sum = int(df_s['Tore Wygorazzi'].sum())
        except:
            try:
                tore_wygo_sum = int(pd.to_numeric(df_s['Tore Wygorazzi'], errors='coerce').fillna(0).sum())
            except:
                tore_wygo_sum = 0

        try:
            tore_gegner_sum = int(df_s['Tore Gegner'].sum())
        except:
            tore_gegner_sum = 0

        siege_sum = int(df_s['Sieg'].sum()) if 'Sieg' in df_s.columns else 0
        niederlagen_sum = int(df_s['Niederlage'].sum()) if 'Niederlage' in df_s.columns else 0
        unentschieden_sum = int(df_s['Unentschieden'].sum()) if 'Unentschieden' in df_s.columns else 0
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

# ---------------------------
# Footer / Hinweis
# ---------------------------
st.markdown("---")
st.markdown("<div class='subtle'>Hinweis: Wenn Spaltennamen in den CSV-Dateien leicht abweichen (zusätzliche Leerzeichen o.Ä.), versucht die App, diese automatisch zu bereinigen. "
            "Wenn etwas nicht korrekt angezeigt wird, sende mir bitte die exakten Spaltennamen oder ein kleines Beispiel-CSV.</div>", unsafe_allow_html=True)
