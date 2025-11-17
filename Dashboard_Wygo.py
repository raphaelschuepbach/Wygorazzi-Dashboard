import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# CSV einlesen
df = pd.read_csv("Spieler_Statistik_25_26.csv")

df['Linie'] = df['Linie'].astype(str)

# "-" in Plus und Minus durch NaN ersetzen, dann in Zahlen umwandeln
df["Plus"] = df["Plus"].replace("-", np.nan).astype(float)
df["Minus"] = df["Minus"].replace("-", np.nan).astype(float)

# NaN-Werte durch 0 ersetzen
df[["Plus", "Minus"]] = df[["Plus", "Minus"]].fillna(0)

df["Spiele"] = df["Gespielt"].map({"Ja": 1, "Nein": 0})


# Plus-Minus und Punkte berechnen
df["PlusMinus"] = (df["Plus"] - df["Minus"]) / df["Spiele"]
df["Punkte"] = df["T"] + df["A"]

# Bully-Statistiken aggregieren
bully_stats = df.groupby("Name")[["Bully-Plus", "Bully-Minus"]].sum()
bully_stats["Bully-Gewinn %"] = 100 * bully_stats["Bully-Plus"] / (bully_stats["Bully-Plus"] + bully_stats["Bully-Minus"])
bully_stats = bully_stats.reset_index()

df["PlusMinus_L"] = df["Linie-Plus"] - df["Linie-Minus"]
top3 = df.groupby("Linie")['PlusMinus_L'].sum().sort_values(ascending=False).head(4).reset_index()
top3['PlusMinus_L'] = top3['PlusMinus_L']/3
top3 = top3[top3["Linie"] != "0"]

# Funktion für Top-3 Balkendiagramm (mit dtick=1)
def plot_top3(df, column, title, color):
    top3 = df.groupby("Name")[column].sum().sort_values(ascending=False).head(13).reset_index()
    fig = px.bar(top3, x="Name", y=column, title=title, text=column)
    fig.update_traces(marker_color=color, texttemplate='%{text}', textposition='inside',
                      hoverinfo='skip', hovertemplate=None, showlegend=False)
    fig.update_layout(showlegend=False, yaxis=dict(dtick=1, tickmode='linear'),
                      yaxis_title=None, xaxis_title=None)
    fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"])
    return fig

# Spezielle Funktion für Bully-Gewinn % (ohne dtick=1)
def plot_top3_bully(bully_df):
    top3 = bully_df.sort_values("Bully-Gewinn %", ascending=False).head(13)
    fig = px.bar(top3, x="Name", y="Bully-Gewinn %", title="Bully-Gewinnquote", text="Bully-Gewinn %")
    fig.update_traces(marker_color="purple", texttemplate='%{text:.1f}%', textposition='inside',
                      hoverinfo='skip', hovertemplate=None, showlegend=False)
    fig.update_layout(showlegend=False, yaxis_title=None, xaxis_title=None)
    fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"])
    return fig

def plot_Linie(df):
    df["Linie"] = df["Linie"].astype(str)
    fig = px.bar(df, x="Linie", y="PlusMinus_L", title="Plus-Minus nach Linie", text="PlusMinus_L")
    fig.update_traces(marker_color="green", texttemplate='%{text}', textposition='inside',
                      hoverinfo='skip', hovertemplate=None, showlegend=False)
    fig.update_layout(xaxis=dict(type="category"),showlegend=False, yaxis_title=None, xaxis_title=None)
    fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"])
    return fig

# Streamlit Layout
st.set_page_config(page_title="Spielerstatistik UHC Wygorazzi", layout="centered")
st.title("Spielerstatistik UHC Wygorazzi")
st.caption("Saison 25/26 – Spielerstatistiken")

st.plotly_chart(plot_top3(df, "T", "Tore", "royalblue"), use_container_width=True, config={'staticPlot': True})
st.plotly_chart(plot_top3(df, "A", "Assists", "seagreen"), use_container_width=True, config={'staticPlot': True})
st.plotly_chart(plot_top3(df, "Punkte", "Punkte (T+A)", "darkorange"), use_container_width=True, config={'staticPlot': True})
st.plotly_chart(plot_top3(df, "PlusMinus", "Plus-Minus", "firebrick"), use_container_width=True, config={'staticPlot': True})
st.plotly_chart(plot_top3(df, "Strafen", "Strafen", "gold"), use_container_width=True, config={'staticPlot': True})
st.plotly_chart(plot_top3_bully(bully_stats), use_container_width=True, config={'staticPlot': True})
st.plotly_chart(plot_Linie(top3), use_container_width=True, config={'staticPlot': True})


# --- CSV einlesen ---
wygo = pd.read_csv('Statistik_Wygo.csv', sep=',')

# --- Ja/Nein in 1/0 umwandeln ---
wygo['Sieg'] = np.where(wygo['Sieg'] == 'Ja', 1, 0).astype(int)
wygo[' Niederlage'] = np.where(wygo[' Niederlage'] == 'Ja', 1, 0).astype(int)
wygo[' Unentschieden'] = np.where(wygo[' Unentschieden'] == 'Ja', 1, 0).astype(int)

# --- Saisons vorbereiten + Liga ---
saisons = {
    "Gesamt": wygo,
    "20/21": wygo[wygo['Saison'] == '20/21'],
    "21/22": wygo[wygo['Saison'] == '21/22'],
    "22/23": wygo[wygo['Saison'] == '22/23'],
    "23/24": wygo[wygo['Saison'] == '23/24'],
    "24/25": wygo[wygo['Saison'] == '24/25'],
    "25/26": wygo[wygo['Saison'] == '25/26']
}

def zeige_statistik(df, titel):
    # --- Kennzahlen berechnen ---
    tore_wygo_sum = df['Tore Wygorazzi'].sum()
    tore_gegner_sum = df['Tore Gegner'].sum()
    siege_sum = df['Sieg'].sum()
    niederlagen_sum = df[' Niederlage'].sum()
    unentschieden_sum = df[' Unentschieden'].sum()
    anz_spiele = len(df)
    tordifferenz = tore_wygo_sum - tore_gegner_sum

    avg_tore_wygo = tore_wygo_sum / anz_spiele if anz_spiele > 0 else 0
    avg_tore_gegner = tore_gegner_sum / anz_spiele if anz_spiele > 0 else 0
    
    liga = df[' Liga Wygorazzi'].iloc[0] if not df.empty else "N/A"

    # --- Anzeige ---
    if titel == "Gesamt":
        st.subheader("Gesamtstatistik")
    else:
        st.subheader(f"Saison {titel} - {liga}. Liga") 
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

# --- Dashboard ---
st.subheader("Gesamt- und Saisonstatistiken")
for saison, df_saison in saisons.items():
    zeige_statistik(df_saison, saison)

