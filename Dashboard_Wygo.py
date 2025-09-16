import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# CSV einlesen
df = pd.read_csv("Spieler_Statistik_25_26.csv")

# "-" in Plus und Minus durch NaN ersetzen, dann in Zahlen umwandeln
df["Plus"] = df["Plus"].replace("-", np.nan).astype(float)
df["Minus"] = df["Minus"].replace("-", np.nan).astype(float)

# NaN-Werte durch 0 ersetzen
df[["Plus", "Minus"]] = df[["Plus", "Minus"]].fillna(0)

# Plus-Minus und Punkte berechnen
df["PlusMinus"] = df["Plus"] - df["Minus"]
df["Punkte"] = df["T"] + df["A"]

# Bully-Statistiken aggregieren
bully_stats = df.groupby("Name")[["Bully-Plus", "Bully-Minus"]].sum()
bully_stats["Bully-Gewinn %"] = 100 * bully_stats["Bully-Plus"] / (bully_stats["Bully-Plus"] + bully_stats["Bully-Minus"])
bully_stats = bully_stats.reset_index()

# Funktion für Top-3 Balkendiagramm (mit dtick=1)
def plot_top3(df, column, title, color):
    top3 = df.groupby("Name")[column].sum().sort_values(ascending=False).head(3).reset_index()
    fig = px.bar(top3, x="Name", y=column, title=title, text=column)
    fig.update_traces(marker_color=color, texttemplate='%{text}', textposition='inside',
                      hoverinfo='skip', hovertemplate=None, showlegend=False)
    fig.update_layout(showlegend=False, yaxis=dict(dtick=1, tickmode='linear'),
                      yaxis_title=None, xaxis_title=None)
    fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"])
    return fig

# Spezielle Funktion für Bully-Gewinn % (ohne dtick=1)
def plot_top3_bully(bully_df):
    top3 = bully_df.sort_values("Bully-Gewinn %", ascending=False).head(3)
    fig = px.bar(top3, x="Name", y="Bully-Gewinn %", title="Top 3 Bully-Gewinnquote", text="Bully-Gewinn %")
    fig.update_traces(marker_color="purple", texttemplate='%{text:.1f}%', textposition='inside',
                      hoverinfo='skip', hovertemplate=None, showlegend=False)
    fig.update_layout(showlegend=False, yaxis_title=None, xaxis_title=None)
    fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale"])
    return fig

# Streamlit Layout
st.set_page_config(page_title="Spielerstatistik UHC Wygorazzi", layout="centered")
st.title("Spielerstatistik UHC Wygorazzi")
st.caption("Saison 25/26 – Spielerstatistiken")

st.plotly_chart(plot_top3(df, "T", "Top 3 Tore", "royalblue"), use_container_width=True, config={'staticPlot': True})
st.plotly_chart(plot_top3(df, "A", "Top 3 Assists", "seagreen"), use_container_width=True, config={'staticPlot': True})
st.plotly_chart(plot_top3(df, "Punkte", "Top 3 Punkte (T+A)", "darkorange"), use_container_width=True, config={'staticPlot': True})
st.plotly_chart(plot_top3(df, "PlusMinus", "Top 3 Plus-Minus", "firebrick"), use_container_width=True, config={'staticPlot': True})
st.plotly_chart(plot_top3_bully(bully_stats), use_container_width=True, config={'staticPlot': True})

