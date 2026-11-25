import html as _html

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
# Die App laeuft auf dunklem Grund (.streamlit/config.toml). Die Flaechen sind
# neutrales Grau ohne Blaustich; die Bedienung bleibt einfarbig (Text auf
# Grund), Farbe tragen nur die Daten (Blau, Orange) und der Ausgang (Gruen,
# Rot). "akzent" ist die eine Stelle fuer die Vereinsfarbe - das Leuchtgelb
# aus dem Logo: Linie unter dem Kopf, aktiver Reiter, Marke an jedem Abschnitt.
FARBEN = {
    "bg": "#0F1011",
    "flaeche": "#18191B",
    "flaeche_hell": "#222326",
    "rand": "#34363A",
    "text": "#F4F4F2",
    "gedaempft": "#9EA1A7",
    "akzent": "#DDEB2F",
    # eine Stufe neben der Flaeche: Spuren der Meter, feine Trennlinien
    "spur": "#2A2C2F",
    "rand_fein": "#25272A",
    "gedaempft_hell": "#CFD1D5",
    # kraeftigere Linie: unter Tabellenkoepfen, um Felder beim Ueberfahren
    "linie": "#5B5E64",
    # die eine Datenfarbe - duenne Marken vertragen ein kraeftiges Blau
    "balken": "#3987E5",
    # Gruen und Rot fuer den Ausgang - als Paar geprueft: bleiben auch bei
    # Rot-Gruen-Schwaeche unterscheidbar (und stehen nie ohne Zahl oder Wort)
    "gut": "#0CA30C",
    "schlecht": "#E66767",
    "neutral": "#9B9EA4",
    "warn": "#FAB219",
    # Beschriftung in den Balken (dunkel) bzw. ausserhalb (hell)
    "label_innen": "#0F1011",
    "label_aussen": "#F4F4F2",
    "label_gut": "#14532D",
    "label_schlecht": "#7F1D1D",
}

# Drei Farben, die auch bei Rot-Gruen-Schwaeche auseinanderzuhalten sind
# (geprueft). Gruen und Rot bleiben fuer "gut" und "schlecht" reserviert -
# eine Linie soll nicht aussehen wie ein Urteil.
LINIEN_FARBEN = {
    "Linie 1": "#3987E5",
    "Linie 2": "#D95926",
    "Linie 3": "#199E70",
}

# ---------------------------
# Page config & CSS
# ---------------------------
st.set_page_config(page_title="UHC Wygorazzi — Statistik", page_icon="🏑",
                   layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&family=Barlow+Condensed:wght@500;600;700&display=swap');

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
      --balken: {FARBEN["balken"]};
      --spur: {FARBEN["spur"]};
      --rand-fein: {FARBEN["rand_fein"]};
      --gedaempft-hell: {FARBEN["gedaempft_hell"]};
      --linie: {FARBEN["linie"]};
      /* zwei Schnitte einer Familie: schmal fuer Titel, Etiketten und grosse
         Zahlen, normal fuer Text und Tabellen */
      --schmal: 'Barlow Condensed', 'Arial Narrow', sans-serif;
      --schrift: 'Barlow', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    /* Streamlit-Eigenwerbung und Werkzeugleiste ausblenden */
    [data-testid="stHeader"], [data-testid="stToolbar"],
    [data-testid="stDecoration"], #MainMenu, footer {{display:none !important;}}

    html, body, .stApp, [class*="st-"], button, input, select, textarea {{
      font-family:var(--schrift);
    }}
    .stApp {{background:var(--bg);}}

    /* Inhalt mittig halten, trotz wide layout */
    .block-container, [data-testid="stMainBlockContainer"] {{
      max-width:1180px; padding-top:1.6rem; padding-bottom:3rem;
    }}

    /* Formularfelder an die dunkle Oberflaeche angleichen */
    [data-baseweb="select"] > div {{
      background:var(--flaeche) !important; border-color:var(--rand) !important;
      border-radius:2px !important;
    }}
    /* beim Ueberfahren und im Fokus die Textfarbe statt der Akzentfarbe von
       Streamlit */
    [data-baseweb="select"] > div:hover {{border-color:var(--linie) !important;}}
    [data-baseweb="select"] > div:focus-within {{border-color:var(--text) !important;}}
    [data-baseweb="popover"] [data-baseweb="menu"],
    [data-baseweb="popover"] ul[role="listbox"] {{border-radius:2px !important;}}
    label[data-testid="stWidgetLabel"] p {{
      font-family:var(--schmal); font-size:13px !important; font-weight:600 !important;
      letter-spacing:0.07em; text-transform:uppercase; color:var(--gedaempft) !important;
    }}

    /* Kopf: der Vereinsname gross und schmal gesetzt, darunter eine kraeftige
       Linie - wie der Kopf eines Matchblatts */
    .kopf {{
      display:flex; align-items:flex-end; justify-content:space-between; gap:16px;
      border-bottom:3px solid var(--akzent); padding:0 0 9px 0; margin:0 0 6px 0;
    }}
    .kopf-name {{
      font-family:var(--schmal); font-size:42px; font-weight:700; line-height:.95;
      text-transform:uppercase; letter-spacing:.005em; color:var(--text);
    }}
    .kopf-unter {{
      font-family:var(--schmal); font-size:16px; font-weight:500; line-height:1.2;
      text-transform:uppercase; letter-spacing:.14em; color:var(--gedaempft);
      white-space:nowrap;
    }}
    /* Zwischentitel fuer einen Teil der Seite (Pro Spieler) */
    .kicker {{
      font-family:var(--schmal); font-size:28px; font-weight:700; line-height:1;
      text-transform:uppercase; letter-spacing:.01em; color:var(--text);
      margin:2px 0 8px 0;
    }}
    .subtle {{color:var(--gedaempft); font-size:14px;}}
    .small-metric {{font-size:13px; color:var(--gedaempft);}}

    /* Diagrammkarten (st.container(border=True)) */
    [data-testid="stVerticalBlockBorderWrapper"]:has(.chart-titel) {{
      border:0 !important; border-radius:0; margin-bottom:16px;
    }}
    /* kein negativer Abstand - der schob das Diagramm ueber die Ueberschrift */
    .chart-titel {{
      font-family:var(--schmal); font-size:19px; font-weight:600;
      text-transform:uppercase; letter-spacing:.045em; color:var(--text) !important;
      line-height:1.2; margin:0 0 9px 0;
    }}
    .chart-leer {{
      font-size:13px; color:var(--gedaempft); padding:14px 4px 20px 4px;
    }}

    .karte {{
      background:var(--flaeche); border:0; border-radius:0; padding:0;
      margin-bottom:12px;
    }}

    /* Saisonbilanz: ein Band aus Feldern mit feinen Trennlinien - oben das
       Wort, darunter die Zahl; rechts die Resultate in zeitlicher Folge */
    .saison {{display:flex; flex-wrap:wrap; align-items:stretch;}}
    .kpi-reihe {{display:flex; flex:0 0 auto; margin:0;}}
    .kpi {{
      flex:0 0 auto; min-width:84px; padding:12px 22px 12px 18px;
      border-right:1px solid var(--rand);
    }}
    .kpi .bez, .saison-form .bez {{
      font-family:var(--schmal); font-size:13px; font-weight:600;
      letter-spacing:.07em; text-transform:uppercase; color:var(--gedaempft);
    }}
    .kpi .wert {{
      font-family:var(--schmal); font-size:32px; font-weight:700; color:var(--text);
      line-height:1; margin-top:5px; white-space:nowrap;
      font-variant-numeric:tabular-nums;
    }}
    .kpi .wert .gut {{color:var(--gut);}}
    .kpi .wert .schlecht {{color:var(--schlecht);}}
    .kpi .wert .neutral {{color:var(--neutral);}}
    .saison-form {{flex:1 1 280px; min-width:0; padding:12px 18px 12px 18px;}}

    /* Resultate: ein Feld je Spiel, die Farbe sagt den Ausgang */
    .chips {{display:flex; flex-wrap:wrap; gap:4px; margin-top:7px;}}
    a.chip {{
      display:inline-block; min-width:40px; box-sizing:border-box; text-align:center;
      font-family:var(--schmal); font-size:16px; font-weight:700; line-height:1;
      padding:5px 6px; border-radius:2px; text-decoration:none;
      color:{FARBEN["label_innen"]}; cursor:pointer;
      font-variant-numeric:tabular-nums; transition:filter .1s ease;
    }}
    a.chip:hover {{filter:brightness(1.2);}}
    .chip.sieg {{background:var(--gut);}}
    .chip.remis {{background:var(--neutral);}}
    .chip.nieder {{background:var(--schlecht);}}

    /* ---------- Torliste ----------
       Eine Gruppe (Spieler, Halbzeit) ist eine Karte: oben der Kopf, darunter
       die Tore als Zeilen mit Haarlinien dazwischen. Jede Zeile ist ein
       Spaltenpaar von Streamlit - links der Text, rechts der Abspielknopf. */
    [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .tg-kopf) {{
      gap:0 !important; background:var(--flaeche); border:0;
      border-radius:0; padding:0 0 6px 0;
    }}
    /* Streamlit zieht Textbloecke um 1rem hoch - die Zeilen stuenden sonst
       ineinander */
    [data-testid="stMarkdownContainer"]:has(> .tg-kopf),
    [data-testid="stMarkdownContainer"]:has(> .tz),
    [data-testid="stMarkdownContainer"]:has(> .tz-ohne),
    [data-testid="stMarkdownContainer"]:has(> .tl-info),
    [data-testid="stMarkdownContainer"]:has(> .lt),
    [data-testid="stMarkdownContainer"]:has(> .lt-punkt),
    [data-testid="stMarkdownContainer"]:has(> .lt-pause) {{margin-bottom:0 !important;}}
    /* Der Kopf bleibt beim Scrollen oben stehen, bis die naechste Gruppe
       kommt. Kleben muss der Behaelter, nicht der Text darin: nur der
       Behaelter ist ein direktes Kind der Karte und kann in ihr wandern. */
    [data-testid="stElementContainer"]:has(.tg-kopf) {{position:sticky; top:0; z-index:5;}}
    .tg-kopf {{
      display:flex; align-items:baseline; justify-content:space-between; gap:12px;
      padding:16px 16px 12px 16px; border-radius:0;
      background:linear-gradient(var(--akzent), var(--akzent)) 16px 0 / 28px 3px no-repeat
                 var(--flaeche);
    }}
    .tg-kopf b {{
      font-family:var(--schmal); font-size:19px; font-weight:600;
      text-transform:uppercase; letter-spacing:.045em; color:var(--text);
    }}
    .tg-kopf .tg-n {{
      font-style:normal; font-size:28px; font-weight:700; line-height:1;
      letter-spacing:0; margin-left:10px; font-variant-numeric:tabular-nums;
    }}
    .tg-kopf span {{
      font-size:13px; color:var(--gedaempft); white-space:nowrap;
      font-variant-numeric:tabular-nums;
    }}
    /* die Zeile: Text links, Knopf rechts - nie untereinander */
    [data-testid="stHorizontalBlock"]:has(.tz) {{
      flex-wrap:nowrap !important; align-items:center !important; gap:10px !important;
      padding:0 12px 0 16px; border-top:1px solid var(--rand-fein);
      transition:background .12s ease;
    }}
    [data-testid="stHorizontalBlock"]:has(.tz):hover,
    [data-testid="stHorizontalBlock"]:has(.tz.offen) {{background:var(--flaeche-hell);}}
    [data-testid="stHorizontalBlock"]:has(.tz) > [data-testid="stColumn"] {{
      min-width:0 !important; width:auto !important; margin:0 !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.tz)
      > [data-testid="stColumn"]:first-child {{flex:1 1 auto !important;}}
    [data-testid="stHorizontalBlock"]:has(.tz)
      > [data-testid="stColumn"]:last-child {{flex:0 0 auto !important;}}
    /* Raster der Zeile: Haupttext | Zeit | Mitspieler | Entstehung | Linie |
       Stand. So stehen die Angaben in der ganzen Liste untereinander. */
    .tz {{
      display:grid; align-items:center; column-gap:14px; padding:11px 0;
      grid-template-columns:minmax(0, 1fr) 92px 168px 216px 76px 40px;
      font-size:13px; color:var(--gedaempft); line-height:1.3;
    }}
    .tz-u {{display:contents;}}
    .tz > span, .tz-u > span {{
      min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
    }}
    .tz-h b {{font-size:14px; font-weight:500; color:var(--text);}}
    .tz-h small {{font-size:12px; color:var(--gedaempft); margin-left:9px;}}
    .tz-z, .tz-s {{font-variant-numeric:tabular-nums;}}
    .tz-m b {{font-weight:500; color:var(--gedaempft-hell);}}
    /* Linie: ein Punkt in der Linienfarbe, der Name daneben in Textfarbe */
    .tz-l i {{
      display:inline-block; width:7px; height:7px; border-radius:50%;
      margin-right:6px;
    }}
    .tz-l i + i {{margin-left:-3px;}}
    .tz-s {{font-size:14px; font-weight:700; color:var(--text); text-align:right;}}
    /* Abspielknopf: rund und leise, die Akzentfarbe erst bei Beruehrung und
       solange das Video offen ist */
    [data-testid="stHorizontalBlock"]:has(.tz, .lt) button[data-testid^="stBaseButton"] {{
      width:34px; height:34px; min-height:0; padding:0; border-radius:50%;
      border:1px solid var(--rand); background:transparent; color:var(--text);
    }}
    [data-testid="stHorizontalBlock"]:has(.tz, .lt) button[data-testid^="stBaseButton"]:hover {{
      border-color:var(--akzent); color:var(--akzent); background:transparent;
    }}
    [data-testid="stHorizontalBlock"]:has(.tz.offen, .lt.offen) button[data-testid^="stBaseButton"],
    [data-testid="stHorizontalBlock"]:has(.tz.offen, .lt.offen) button[data-testid^="stBaseButton"]:hover {{
      background:var(--akzent); border-color:var(--akzent);
      color:{FARBEN["label_innen"]};
    }}
    /* das Symbol etwas groesser, als Streamlit es setzt */
    [data-testid="stHorizontalBlock"]:has(.tz, .lt) button span[role="img"] {{
      font-size:21px !important; line-height:1; vertical-align:middle !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.tz, .lt) button p {{line-height:1; margin:0;}}
    /* ohne Video: gleicher Platz, damit der Spielstand buendig bleibt */
    .tz-ohne {{
      width:34px; height:34px; display:flex; align-items:center;
      justify-content:center; color:var(--gedaempft); opacity:.45; font-size:12px;
    }}
    /* das Video: dunkler Streifen in der Karte, der Clip mittig und nicht
       breiter als noetig - sonst springt die Seite um einen halben Bildschirm */
    [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .tg-kopf)
      > [data-testid="stElementContainer"]:has(> video) {{
      background:var(--bg); padding:14px 16px; border-top:1px solid var(--rand-fein);
    }}
    [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .tg-kopf) video {{
      display:block; width:100%; max-width:780px; margin:0 auto;
      border-radius:2px; background:#000;
    }}
    /* die Zeile ueber der Liste: wie viele Tore, Gegentore und Clips */
    .tl-info {{
      display:flex; flex-wrap:wrap; gap:4px 20px; font-size:13px;
      color:var(--gedaempft); padding:2px 2px 6px 2px;
    }}
    .tl-info b {{
      color:var(--text); font-weight:600; margin-right:5px;
      font-variant-numeric:tabular-nums;
    }}
    /* ---------- Liveticker ----------
       Ein Spiel als Zeitstrahl: in der Mitte die Linie, die Abspielknoepfe
       sind ihre Knoten. Links stehen unsere Tore, rechts die des Gegners. */
    .tg-kopf.spiel {{
      display:grid; grid-template-columns:minmax(0, 1fr) auto minmax(0, 1fr);
      align-items:center; column-gap:18px; padding:14px 16px 13px 16px;
      border-bottom:1px solid var(--rand-fein);
    }}
    .tg-kopf.spiel b:first-child {{text-align:right;}}
    .lt-res {{text-align:center; line-height:1.15;}}
    .lt-res strong {{
      display:block; font-family:var(--schmal); font-size:32px; font-weight:700;
      line-height:1; color:var(--text); font-variant-numeric:tabular-nums;
      white-space:nowrap;
    }}
    .lt-res small {{font-size:12px; color:var(--gedaempft);}}
    /* die Zeile: drei Spalten von Streamlit - links, Linie, rechts */
    [data-testid="stHorizontalBlock"]:has(.lt) {{
      flex-wrap:nowrap !important; align-items:stretch !important;
      gap:0 !important; padding:0 16px;
    }}
    [data-testid="stHorizontalBlock"]:has(.lt.offen) {{background:var(--flaeche-hell);}}
    [data-testid="stHorizontalBlock"]:has(.lt) > [data-testid="stColumn"] {{
      min-width:0 !important; width:auto !important; margin:0 !important;
      flex:1 1 0 !important; display:flex; flex-direction:column;
      justify-content:center;
    }}
    /* die mittlere Spalte traegt die Linie, der Knopf sitzt darauf - auf der
       Hoehe der ersten Textzeile, wo auch die Spieluhr steht */
    [data-testid="stHorizontalBlock"]:has(.lt) > [data-testid="stColumn"]:nth-child(2) {{
      flex:0 0 54px !important; position:relative; align-items:center;
      justify-content:flex-start !important; align-self:stretch !important;
      padding-top:3px;
    }}
    [data-testid="stHorizontalBlock"]:has(.lt) > [data-testid="stColumn"]:nth-child(2)::before,
    .lt-pause::before {{
      content:""; position:absolute; left:50%; top:0; bottom:0; width:2px;
      margin-left:-1px; background:var(--rand);
    }}
    [data-testid="stHorizontalBlock"]:has(.lt) > [data-testid="stColumn"]:nth-child(2)
      > [data-testid="stVerticalBlock"] {{
      position:relative; align-items:center; width:auto;
    }}
    /* der Knoten: deckt die Linie ab, der Rand sagt, wer getroffen hat */
    [data-testid="stHorizontalBlock"]:has(.lt) button[data-testid^="stBaseButton"],
    [data-testid="stHorizontalBlock"]:has(.lt) button[data-testid^="stBaseButton"]:hover {{
      background:var(--flaeche);
    }}
    [data-testid="stHorizontalBlock"]:has(.lt.wir) button[data-testid^="stBaseButton"] {{
      border-color:var(--gut);
    }}
    [data-testid="stHorizontalBlock"]:has(.lt.sie) button[data-testid^="stBaseButton"] {{
      border-color:var(--schlecht);
    }}
    [data-testid="stHorizontalBlock"]:has(.lt.offen) button[data-testid^="stBaseButton"],
    [data-testid="stHorizontalBlock"]:has(.lt.offen) button[data-testid^="stBaseButton"]:hover {{
      background:var(--akzent); border-color:var(--akzent);
    }}
    /* ohne Video: ein kleiner Punkt statt des Knopfs */
    .lt-punkt {{
      width:12px; height:12px; box-sizing:border-box; border-radius:50%;
      background:var(--flaeche); border:2px solid var(--gedaempft); margin:11px auto;
    }}
    [data-testid="stHorizontalBlock"]:has(.lt.wir) .lt-punkt {{border-color:var(--gut);}}
    [data-testid="stHorizontalBlock"]:has(.lt.sie) .lt-punkt {{border-color:var(--schlecht);}}
    /* ein Tor: oben Schuetze, Spielstand und Spieluhr - die Uhr steht immer
       der Linie am naechsten -, darunter klein Assist, Entstehung und Linie */
    .lt {{
      padding:9px 14px 9px 0; text-align:right; min-width:0;
      font-size:13px; color:var(--gedaempft); line-height:1.35;
    }}
    .lt.sie {{padding:9px 0 9px 14px; text-align:left;}}
    .lt-z {{display:flex; align-items:center; justify-content:flex-end; gap:10px;}}
    .lt.sie .lt-z {{flex-direction:row-reverse;}}
    .lt-n {{
      font-size:14px; font-weight:600; color:var(--text); min-width:0;
      overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
    }}
    .lt.sie .lt-n {{font-weight:500; color:var(--gedaempft-hell);}}
    .lt-sm {{display:flex; align-items:center; gap:8px; flex:0 0 auto;}}
    .lt.sie .lt-sm {{flex-direction:row-reverse;}}
    .lt-s {{
      font-family:var(--schmal); font-size:15px; font-weight:700; color:var(--text);
      font-variant-numeric:tabular-nums; background:var(--flaeche-hell);
      border:1px solid var(--rand); border-radius:2px; padding:1px 6px;
      min-width:38px; box-sizing:border-box; text-align:center;
    }}
    .lt-m {{
      min-width:36px; font-size:13px; color:var(--gedaempft-hell);
      font-variant-numeric:tabular-nums;
    }}
    .lt-u {{
      display:flex; flex-wrap:wrap; justify-content:flex-end; gap:1px 10px;
      margin-top:2px;
    }}
    .lt.sie .lt-u {{justify-content:flex-start;}}
    .lt-u b {{font-weight:500; color:var(--gedaempft-hell);}}
    /* Marken auf der Linie: Halbzeiten und Schluss */
    .lt-pause {{position:relative; text-align:center; padding:9px 0 7px 0; line-height:1.2;}}
    .lt-pause.start::before {{top:50%;}}
    .lt-pause.ende::before {{bottom:50%;}}
    .lt-pause span {{
      position:relative; display:inline-block; padding:3px 10px;
      border-radius:2px; background:var(--flaeche-hell);
      border:1px solid var(--rand); font-family:var(--schmal); font-size:13px;
      font-weight:600; letter-spacing:.08em; text-transform:uppercase;
      color:var(--gedaempft-hell); font-variant-numeric:tabular-nums;
    }}
    .lt-pause small {{
      position:relative; display:block; width:max-content; margin:4px auto 0 auto;
      padding:1px 8px; background:var(--flaeche); font-size:12px;
      color:var(--gedaempft); font-variant-numeric:tabular-nums;
    }}
    /* sticky bricht, sobald ein Vorfahr den Ueberlauf abschneidet */
    [data-testid="stVerticalBlock"], [data-testid="stElementContainer"],
    [data-testid="stHorizontalBlock"], [data-testid="stColumn"],
    [data-baseweb="tab-panel"], .stTabs, .stTabs > div {{overflow:visible !important;}}
    /* Resultat eines einzelnen Spiels - bleibt auch schmal einzeilig */
    .scoreboard {{
      display:flex; align-items:center; justify-content:space-between; gap:10px;
      padding:16px 20px;
    }}
    .scoreboard .team {{flex:1 1 0; min-width:0;}}
    .scoreboard .team-right {{text-align:right;}}
    .scoreboard .team-name {{
      font-family:var(--schmal); font-weight:700; font-size:24px; line-height:1.05;
      text-transform:uppercase; letter-spacing:.02em; color:var(--text);
      overflow-wrap:anywhere;
    }}
    .scoreboard .score {{flex:0 0 auto; text-align:center;}}
    .scoreboard .score-value {{
      font-family:var(--schmal); font-size:48px; font-weight:700; color:var(--text);
      line-height:1; font-variant-numeric:tabular-nums;
    }}

    /* Aufstellung nach Linien: drei Felder nebeneinander, je Linie eines */
    .linien-raster {{
      display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:12px;
      margin-bottom:6px;
    }}
    .line-card {{background:var(--flaeche); padding:13px 16px 13px 16px;}}
    .line-card strong {{
      display:block; font-family:var(--schmal); color:var(--text); font-size:16px;
      font-weight:600; letter-spacing:0.06em; text-transform:uppercase;
      padding-bottom:8px; margin-bottom:9px; border-bottom:1px solid var(--rand);
    }}
    .player-name {{color:var(--text); font-size:14px; margin:6px 0 0 0;}}
    .line-card .subtle {{color:var(--gedaempft); font-style:italic;}}

    /* Reiter: schmal und versal, der aktive mit einer kraeftigen Linie in
       der Textfarbe - nicht in der Akzentfarbe von Streamlit */
    .stTabs [data-baseweb="tab-list"] {{gap:30px; border-bottom:1px solid var(--rand);}}
    .stTabs [data-baseweb="tab"] {{
      padding-left:0; padding-right:0; color:var(--gedaempft) !important;
    }}
    .stTabs [data-baseweb="tab"] p {{
      font-family:var(--schmal); font-size:18px; font-weight:600;
      text-transform:uppercase; letter-spacing:.07em; color:inherit !important;
    }}
    .stTabs [data-baseweb="tab"]:hover,
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{color:var(--text) !important;}}
    .stTabs [data-baseweb="tab-highlight"] {{
      background:var(--akzent) !important; height:3px !important;
    }}
    .stTabs [data-baseweb="tab-border"] {{background:transparent !important;}}

    /* ---------- Karten ----------
       Der Rahmenbehaelter von Streamlit heisst seit 1.5x anders - die Regel
       weiter oben (stVerticalBlockBorderWrapper) greift dort nicht mehr.
       Diese hier trifft die Karte selbst: den Block, dessen direktes Kind
       den Titel traegt. */
    [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .chart-titel) {{
      /* flach und eckig, ohne Rand; die kurze Marke oben links ist das
         einzige Zierstueck. Unten mehr Platz: Streamlit zieht den letzten
         Textblock um 1rem hoch */
      background:linear-gradient(var(--akzent), var(--akzent)) 16px 0 / 28px 3px no-repeat
                 var(--flaeche);
      border:0 !important; border-radius:0; padding:19px 16px 20px 16px;
    }}
    /* Kartenpaare gleich hoch: die kuerzere Liste zieht mit der laengeren */
    [data-testid="stColumn"]:has(.chart-titel) > [data-testid="stVerticalBlock"] {{height:100%;}}
    [data-testid="stColumn"]:has(.chart-titel) > [data-testid="stVerticalBlock"]
      > [data-testid="stLayoutWrapper"] {{flex:1 1 auto;}}
    [data-testid="stColumn"]:has(.chart-titel) > [data-testid="stVerticalBlock"]
      > [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {{height:100%;}}
    /* Die Schriftregel oben erfasst auch die Symbolschrift - ohne diese
       Zeile steht im Ausklapper "keyboard_arrow_right" als Text. */
    [data-testid="stIconMaterial"] {{
      font-family:"Material Symbols Rounded", "Material Symbols Outlined" !important;
    }}

    /* ---------- Karten: graue Unterzeile unter dem Titel ---------- */
    .chart-unter {{
      font-size:13px; color:var(--gedaempft); line-height:1.45;
      margin:-5px 0 12px 0; max-width:780px;
    }}

    /* ---------- Balkenliste: Name | Balken | Wert | Zusatz ---------- */
    .bl {{
      display:grid; grid-template-columns:minmax(0, max-content) minmax(40px, 1fr) max-content;
      column-gap:12px; row-gap:10px; align-items:center; padding:2px 2px 12px 2px;
    }}
    .bl.z4 {{grid-template-columns:minmax(0, max-content) minmax(40px, 1fr) max-content max-content;}}
    .bl-n {{
      font-size:14px; color:var(--text); max-width:190px; white-space:nowrap;
      overflow:hidden; text-overflow:ellipsis;
    }}
    .bl-n.mehr {{white-space:normal; line-height:1.25; max-width:210px;}}
    .bl-n.weit {{max-width:340px;}}
    .bl-s {{position:relative; height:8px;}}
    .bl-s.spur {{background:var(--spur); border-radius:1px;}}
    .bl-s i {{
      position:absolute; left:0; top:0; bottom:0; min-width:3px;
      background:var(--balken); border-radius:0 1px 1px 0;
    }}
    .bl-s.spur i {{border-radius:1px;}}
    /* feine Marke in der Spur, z.B. bei 50 % */
    .bl-s b {{
      position:absolute; top:-4px; bottom:-4px; width:1px;
      background:var(--gedaempft); opacity:.75;
    }}
    /* Bilanz: von der Mitte nach beiden Seiten */
    .bl-s.mitte::before {{
      content:""; position:absolute; left:50%; top:-5px; bottom:-5px;
      width:1px; background:var(--rand);
    }}
    .bl-s.mitte i.pos {{left:50%; background:var(--gut); border-radius:0 1px 1px 0;}}
    .bl-s.mitte i.neg {{
      left:auto; right:50%; background:var(--schlecht); border-radius:1px 0 0 1px;
    }}
    .bl-w {{
      font-size:14px; font-weight:600; color:var(--text); text-align:right;
      font-variant-numeric:tabular-nums; white-space:nowrap;
    }}
    .bl-z {{
      font-size:12px; color:var(--gedaempft); white-space:nowrap;
      font-variant-numeric:tabular-nums;
    }}

    /* ---------- Zahlenpaar gut : schlecht ----------
       Tore : Gegentore, erobert : verloren - die gute Zahl gruen, die
       schlechte rot. Die Reihenfolge sagt dasselbe wie die Farbe. */
    .gr {{white-space:nowrap; font-variant-numeric:tabular-nums;}}
    .gr .p {{color:var(--gut);}}
    .gr .m {{color:var(--schlecht);}}
    .gr .t {{color:var(--gedaempft); margin:0 1px;}}
    .gr b {{font-weight:inherit;}}
    /* in der Tabelle klein hinter der Zahl, in fester Breite - so bleiben
       die Zahlen davor untereinander */
    .rl-wrap table.rl .gr {{
      display:inline-block; min-width:44px; margin-left:8px; text-align:right;
      font-size:12px; font-weight:400;
    }}
    /* als eigener Zelleninhalt (Tore gegen einen Gegner) in voller Groesse */
    .rl-wrap table.rl .gr.voll {{min-width:0; margin-left:0; font-size:inherit;}}

    /* ---------- Tore je Paar ----------
       Der Balken ist nach Torschuetze geteilt. Der Punkt vor dem Namen und
       die Zahl dahinter tragen dieselbe Farbe wie sein Teil des Balkens. */
    .pa-b {{display:flex; gap:2px; height:8px;}}
    .pa-b span {{min-width:3px;}}
    .pa-b span:last-child {{border-radius:0 1px 1px 0;}}
    .pk {{
      display:inline-block; width:7px; height:7px; border-radius:50%;
      margin-right:6px; vertical-align:1px;
    }}
    /* Punkt und Name bleiben zusammen, umgebrochen wird nur am Pluszeichen */
    .pa-n {{white-space:nowrap;}}
    .pa-p {{color:var(--gedaempft); margin:0 7px;}}
    .pa-z {{font-variant-numeric:tabular-nums;}}
    .pa-z b {{font-weight:600;}}

    /* ---------- Verlauf gegen einen Gegner ----------
       ein Kaestchen je Spiel: Sieg gruen, Unentschieden grau, Niederlage rot */
    .vl {{display:inline-flex; gap:3px; vertical-align:middle;}}
    .vl i {{width:9px; height:9px; border-radius:1px; background:var(--neutral);}}
    .vl i.s {{background:var(--gut);}}
    .vl i.n {{background:var(--schlecht);}}

    /* ---------- Stapelliste und Segmentbalken ---------- */
    .st-s {{min-width:0;}}
    .st-b {{display:flex; gap:2px; height:20px;}}
    .st-b span {{
      display:flex; align-items:center; justify-content:center; min-width:0;
      overflow:hidden; font-size:12px; font-weight:600; white-space:nowrap;
      font-variant-numeric:tabular-nums;
    }}
    .st-b span:first-child {{border-radius:1px 0 0 1px;}}
    .st-b span:last-child {{border-radius:0 1px 1px 0;}}
    .st-b span:only-child {{border-radius:1px;}}
    .leg {{
      display:flex; flex-wrap:wrap; gap:6px 18px; font-size:13px;
      color:var(--gedaempft); padding:0 2px 12px 2px;
    }}
    .leg span {{display:inline-flex; align-items:center; white-space:nowrap;}}
    .leg i {{width:9px; height:9px; border-radius:1px; margin-right:7px; flex:0 0 auto;}}
    .leg b {{color:var(--text); font-weight:600; margin-left:7px;}}
    /* ein zweiter Teil der Legende, abgesetzt: er erklaert etwas anderes
       (im Spielverlauf die Farben der Tore im Resultat) */
    .leg span.ab {{padding-left:18px; border-left:1px solid var(--rand);}}

    /* ---------- Rangtabelle ---------- */
    .rl-wrap {{overflow-x:auto; margin:0 -2px 8px -2px; padding-bottom:2px;}}
    .rl-wrap table.rl {{
      width:100%; border-collapse:collapse; font-size:14px; margin:0;
      border:0 !important;
    }}
    .rl-wrap table.rl th, .rl-wrap table.rl td {{
      border:0 !important; border-bottom:1px solid var(--rand-fein) !important;
      background:transparent !important; text-align:right; white-space:nowrap;
      padding:9px 12px; font-variant-numeric:tabular-nums;
    }}
    .rl-wrap table.rl th {{
      font-family:var(--schmal); font-size:13.5px; font-weight:600; letter-spacing:.07em;
      text-transform:uppercase; color:var(--gedaempft);
      border-bottom:1px solid var(--linie) !important; padding-top:4px;
    }}
    .rl-wrap table.rl td {{color:var(--gedaempft-hell);}}
    .rl-wrap table.rl tr:last-child td {{border-bottom:0 !important;}}
    .rl-wrap table.rl .l {{text-align:left;}}
    .rl-wrap table.rl td.name {{color:var(--text); font-weight:500;}}
    .rl-wrap table.rl .rang {{color:var(--gedaempft); width:1%; padding-right:4px;}}
    .rl-wrap table.rl th.akt {{color:var(--text);}}
    .rl-wrap table.rl td.akt {{color:var(--text); font-weight:600; width:34%;}}
    .rl-wrap table.rl td.plus {{color:var(--gut);}}
    .rl-wrap table.rl td.minus {{color:var(--schlecht);}}
    .rl .zelle {{display:flex; align-items:center; justify-content:flex-end; gap:12px;}}
    .rl .zahl {{min-width:38px; text-align:right;}}
    .rl .mini {{position:relative; flex:1 1 auto; min-width:60px; height:6px;}}
    .rl .mini i {{
      position:absolute; left:0; top:0; bottom:0; min-width:3px;
      background:var(--balken); border-radius:0 1px 1px 0;
    }}
    .rl .mini.mitte::before {{
      content:""; position:absolute; left:50%; top:-4px; bottom:-4px;
      width:1px; background:var(--rand);
    }}
    .rl .mini.mitte i.pos {{left:50%; background:var(--gut);}}
    .rl .mini.mitte i.neg {{
      left:auto; right:50%; background:var(--schlecht); border-radius:1px 0 0 1px;
    }}

    /* viele Spalten (Rangliste mit Schuessen, Blocks und Ballwerten): der
       Balken der aktiven Spalte gibt Platz ab, die Zellen ruecken zusammen.
       Nur am grossen Bildschirm - am Handy gelten die Regeln weiter unten. */
    @media (min-width: 641px) {{
        .rl-wrap table.rl.viel td.akt {{width:22%;}}
        .rl-wrap table.rl.viel th, .rl-wrap table.rl.viel td {{
          padding-left:9px; padding-right:9px;
        }}
    }}
    /* ohne Balken (Rangliste der Spieler): die sortierte Spalte ist nur fett
       und so schmal wie die anderen */
    .rl-wrap table.rl.schlicht td.akt,
    .rl-wrap table.rl.viel.schlicht td.akt {{width:auto;}}
    /* Legende der Kuerzel unter der Tabelle */
    .rl-leg {{
      font-size:12px; color:var(--gedaempft); line-height:1.65;
      padding:2px 2px 10px 2px;
    }}
    .rl-leg b {{color:var(--gedaempft-hell); font-weight:600; margin-right:3px;}}
    .rl-leg span {{white-space:nowrap;}}

    /* ---------- Kennzahl-Kacheln ----------
       flache Felder: oben das Wort, gross die Zahl in der schmalen Schrift */
    .kacheln {{
      display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));
      gap:12px; margin:0 0 16px 0;
    }}
    .kachel {{
      background:var(--flaeche); border:0; border-radius:0;
      padding:15px 18px 15px 18px; min-width:0;
    }}
    .k-bez {{
      font-family:var(--schmal); font-size:14px; font-weight:600; letter-spacing:.07em;
      text-transform:uppercase; color:var(--gedaempft);
    }}
    .k-wert {{
      font-family:var(--schmal); font-size:46px; font-weight:700; color:var(--text);
      line-height:1; margin-top:8px; font-variant-numeric:tabular-nums;
    }}
    .k-wert small {{
      font-size:22px; font-weight:600; color:var(--gedaempft); margin-left:3px;
    }}
    .k-meter {{
      position:relative; height:4px; background:var(--spur);
      margin:12px 0 10px 0; overflow:hidden;
    }}
    .k-meter i {{
      position:absolute; left:0; top:0; bottom:0; background:var(--balken);
    }}
    .k-text {{font-size:13px; color:var(--gedaempft); line-height:1.4; margin-top:8px;}}
    .k-meter + .k-text {{margin-top:0;}}
    .k-delta {{font-size:12.5px; font-weight:600; margin-top:8px;}}
    .k-delta.gut {{color:var(--gut);}}
    .k-delta.schlecht {{color:var(--schlecht);}}
    .k-delta.neutral {{color:var(--gedaempft);}}
    .kacheln.klein {{grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:12px;}}
    .kacheln.klein .kachel {{padding:13px 15px 12px 15px;}}
    .kacheln.klein .k-wert {{font-size:34px; margin-top:6px;}}
    .kacheln.klein .k-wert small {{font-size:17px;}}
    .abschnitt {{
      font-family:var(--schmal); font-size:21px; font-weight:600;
      text-transform:uppercase; letter-spacing:.04em; color:var(--text);
      margin:24px 0 12px 0;
    }}
    .abschnitt span {{
      font-family:var(--schrift); font-weight:400; text-transform:none;
      letter-spacing:0; color:var(--gedaempft); font-size:13px; margin-left:10px;
    }}

    /* ---------- Game Score: woraus die Zahl besteht ----------
       Je Spieler ein gestapelter Balken. Rechts der Nulllinie steht, was die
       Zahl hebt, links, was sie senkt; --null ist die Lage der Nulllinie. */
    .gs {{
      display:grid; align-items:center; column-gap:12px; row-gap:11px;
      grid-template-columns:minmax(0, max-content) minmax(80px, 1fr) max-content max-content;
      padding:4px 2px 12px 2px;
    }}
    /* Eine feine Linie durch die Mitte jeder Zeile fuehrt vom Balken zur
       Zahl dahinter - bei kurzen Balken faende das Auge sie sonst nicht. */
    .gs-s {{
      position:relative; height:20px;
      background:linear-gradient(var(--rand), var(--rand)) center / 100% 1px no-repeat;
    }}
    .gs-s::before {{
      content:""; position:absolute; left:var(--null, 0%); top:-5px; bottom:-5px;
      width:1px; margin-left:-.5px; background:var(--gedaempft); opacity:.55;
      z-index:1;
    }}
    /* der Balken deckt die Linie ab, auch in den Fugen zwischen den Teilen */
    .gs-t {{
      position:absolute; top:0; bottom:0; display:flex; gap:2px;
      background:var(--flaeche);
    }}
    /* eine schmale Fuge an der Nulllinie, damit sie sichtbar bleibt */
    .gs-t.pos {{padding-left:1.5px;}}
    .gs-t.neg {{padding-right:1.5px;}}
    .gs-t span {{
      display:flex; align-items:center; justify-content:center; min-width:0;
      overflow:hidden; font-size:12px; font-weight:600; white-space:nowrap;
      font-variant-numeric:tabular-nums;
    }}
    .gs-t.pos span:last-child {{border-radius:0 1px 1px 0;}}
    .gs-t.neg span:first-child {{border-radius:1px 0 0 1px;}}

    /* ---------- Torhueter im Vergleich ----------
       Raster mit Kopfzeile: Name | Meter | Quote | Einzelwerte (--n Stueck) */
    .tw {{
      display:grid; align-items:center; column-gap:26px; row-gap:13px;
      grid-template-columns:max-content minmax(140px, 1fr) max-content repeat(var(--n, 4), max-content);
      padding:2px 2px 12px 2px;
    }}
    .tw-k {{
      font-family:var(--schmal); font-size:13.5px; font-weight:600; letter-spacing:.07em;
      text-transform:uppercase; color:var(--gedaempft);
    }}
    .tw-k.r, .tw-q, .tw-d {{text-align:right;}}
    .tw-n {{font-size:14px; font-weight:500; color:var(--text); white-space:nowrap;}}
    .tw-q {{
      font-size:14px; font-weight:600; color:var(--text); white-space:nowrap;
      font-variant-numeric:tabular-nums;
    }}
    .tw-u {{display:contents;}}
    .tw-d {{
      font-size:14px; color:var(--gedaempft-hell); white-space:nowrap;
      font-variant-numeric:tabular-nums;
    }}

    /* ---------- Vergleichsbalken der Spielerkarte ---------- */
    /* je Kennzahl eine Spur bis zum besten Wert der Mannschaft, darauf der
       eigene Wert als Marke */
    .vg {{
      display:grid; grid-template-columns:minmax(120px, 190px) 1fr max-content;
      column-gap:18px; row-gap:18px; align-items:center; padding:8px 2px 14px 2px;
    }}
    .vg-n {{font-size:14px; color:var(--text); line-height:1.25;}}
    .vg-n small {{display:block; font-size:11px; color:var(--gedaempft);}}
    .vg-s {{
      position:relative; height:6px; border-radius:1px; background:var(--spur);
      margin:0 24px;
    }}
    .vg-s i {{
      position:absolute; top:0; bottom:0; border-radius:1px;
      background:var(--balken);
    }}
    /* Nullmarke - nur wo es Werte unter null gibt (Plus-Minus) */
    .vg-s b {{
      position:absolute; top:-7px; bottom:-7px; width:1px;
      background:var(--gedaempft); opacity:.7;
    }}
    /* der Wert sitzt als Marke am Ende des Balkens: Flaeche und heller Text,
       die Farbe traegt nur der Rand */
    .vg-p {{
      position:absolute; top:50%; transform:translate(-50%, -50%);
      min-width:30px; height:24px; padding:0 8px; border-radius:2px;
      box-sizing:border-box; display:flex; align-items:center;
      justify-content:center; background:var(--flaeche);
      border:1.5px solid var(--balken); font-size:12px; font-weight:700;
      color:var(--text); white-space:nowrap; font-variant-numeric:tabular-nums;
    }}
    /* wenig ist gut (Ballverluste, Strafen): grau statt blau, damit ein
       langer Balken hier nicht wie eine Leistung aussieht */
    .vg-s.wenig i {{background:var(--gedaempft);}}
    .vg-s.wenig .vg-p {{border-color:var(--gedaempft);}}
    .vg-w {{
      font-size:13px; color:var(--text); text-align:right; white-space:nowrap;
      font-variant-numeric:tabular-nums;
    }}
    .vg-w small {{font-size:12px; color:var(--gedaempft); margin-left:10px;}}

    /* ---------- Umschalter (segmented control) ----------
       eckig, die aktive Wahl hell gefuellt - ohne die Akzentfarbe von
       Streamlit */
    [data-testid="stButtonGroup"] button[data-testid^="stBaseButton-segmented_control"] {{
      border-radius:0 !important; border-color:var(--rand) !important;
      background:transparent !important; color:var(--gedaempft-hell) !important;
      box-shadow:none !important;
    }}
    [data-testid="stButtonGroup"] button[data-testid^="stBaseButton-segmented_control"]:hover {{
      border-color:var(--linie) !important; color:var(--text) !important;
    }}
    [data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"],
    [data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"]:hover {{
      background:var(--text) !important; border-color:var(--text) !important;
      color:var(--bg) !important;
    }}
    [data-testid="stButtonGroup"] button p {{
      font-size:14px; font-weight:500; color:inherit !important;
    }}
    [data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"] p {{
      font-weight:600;
    }}

    /* ---------- Kleinteile von Streamlit ---------- */
    hr {{border-color:var(--rand) !important;}}
    [data-testid="stMarkdownContainer"] h3 {{
      font-family:var(--schmal); font-size:23px; font-weight:600;
      text-transform:uppercase; letter-spacing:.04em; color:var(--text);
    }}
    [data-testid="stAlert"] > div, [data-testid="stAlertContainer"] {{
      border-radius:2px !important;
    }}

    /* Handy */
    @media (max-width: 640px) {{
        .block-container, [data-testid="stMainBlockContainer"] {{
            padding-left:1rem; padding-right:1rem; padding-top:1.2rem;
        }}
        .kopf {{padding-bottom:7px;}}
        .kopf-name {{font-size:31px;}}
        .kopf-unter {{font-size:12.5px; letter-spacing:.1em;}}
        /* Saisonband: vier Felder nebeneinander, die Saison steht schon im
           Auswahlfeld darueber; die Resultate darunter */
        .kpi-reihe {{
          flex:1 1 100%; display:grid; grid-template-columns:repeat(4, 1fr);
          border-bottom:1px solid var(--rand);
        }}
        .linien-raster {{grid-template-columns:1fr; gap:8px;}}
        .kpi {{min-width:0; padding:10px 8px 10px 12px;}}
        .kpi.saison-zelle {{display:none;}}
        .kpi:last-child {{border-right:0;}}
        .kpi .wert {{font-size:25px;}}
        .saison-form {{padding:10px 12px 12px 12px;}}
        .scoreboard {{padding:12px;}}
        .scoreboard .score-value {{font-size:36px;}}
        .scoreboard .team-name {{font-size:17px;}}
        /* Torzeilen: oben Haupttext und Spielstand, darunter das Uebrige.
           Leere Angaben fallen weg, lange brechen um. */
        [data-testid="stHorizontalBlock"]:has(.tz) {{
          gap:8px !important; padding:0 10px 0 12px;
        }}
        .tz {{
          grid-template-columns:minmax(0, 1fr) auto; column-gap:10px;
          row-gap:3px; padding:10px 0;
        }}
        .tz-h {{grid-column:1; grid-row:1;}}
        .tz-s {{grid-column:2; grid-row:1;}}
        .tz-u {{
          display:flex; flex-wrap:wrap; gap:2px 10px;
          grid-column:1 / -1; grid-row:2;
        }}
        .tz-u > span {{font-size:12px;}}
        .tz-u > span:empty {{display:none;}}
        /* Liveticker: die Seiten sind schmal - der Schuetze steht oben,
           Spielstand und Uhr darunter, lange Angaben brechen um */
        [data-testid="stHorizontalBlock"]:has(.lt) {{padding:0 8px;}}
        [data-testid="stHorizontalBlock"]:has(.lt)
          > [data-testid="stColumn"]:nth-child(2) {{
          flex:0 0 44px !important; padding-top:0;
        }}
        .lt {{padding:8px 6px 8px 0;}}
        .lt.sie {{padding:8px 0 8px 6px;}}
        .lt-z, .lt.sie .lt-z {{flex-direction:column; gap:3px;}}
        .lt-z {{align-items:flex-end;}}
        .lt.sie .lt-z {{align-items:flex-start;}}
        .lt-n {{max-width:100%; font-size:14px;}}
        .lt-u {{gap:0 8px; font-size:12px;}}
        .tg-kopf.spiel {{column-gap:10px; padding:12px 10px 11px 10px;}}
        .tg-kopf.spiel b {{font-size:16px;}}
        .lt-res strong {{font-size:25px;}}
        .tg-kopf {{padding:15px 12px 10px 12px; background-position:12px 0;}}
        [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .tg-kopf)
          > [data-testid="stElementContainer"]:has(> video) {{padding:10px 10px;}}

        /* auf schmalen Bildschirmen weniger Abstand, damit alle Reiter passen */
        .stTabs [data-baseweb="tab-list"] {{gap:16px;}}
        .stTabs [data-baseweb="tab"] p {{font-size:16px; letter-spacing:.05em;}}
        h2 {{font-size:20px !important;}}
        h3 {{font-size:17px !important;}}

        /* Listen, Kacheln und Schieber enger */
        .bl {{column-gap:9px;}}
        .bl-n {{max-width:116px; font-size:13px;}}
        .bl-n.mehr {{max-width:124px;}}
        .bl-n.weit {{max-width:168px; white-space:normal; line-height:1.25;}}
        .bl-z {{font-size:11px;}}
        /* Kopfzeile der Saison: "Differenz" brach mitten im Wort um */
        .kpi .bez {{font-size:11.5px; letter-spacing:.04em; white-space:nowrap;}}
        /* Tabelle: alle Spalten sollen ohne Schieben Platz haben - der
           feine Balken weicht, die Reihenfolge sagt dasselbe */
        .rl .mini {{display:none;}}
        .rl .zahl {{min-width:0;}}
        .rl-wrap table.rl .rang {{padding-left:2px;}}
        .kacheln, .kacheln.klein {{grid-template-columns:repeat(2, minmax(0, 1fr)); gap:10px;}}
        .kachel {{padding:13px 14px 12px 14px;}}
        .k-wert {{font-size:36px;}}
        .rl-wrap table.rl th, .rl-wrap table.rl td {{padding:8px 5px;}}
        .rl-wrap table.rl td.akt {{width:auto;}}
        /* breite Tabelle: seitlich schieben, der Name bleibt stehen */
        .rl-wrap table.rl.viel td.name, .rl-wrap table.rl.viel th.name {{
          position:sticky; left:0; z-index:1;
          background:var(--flaeche) !important;
          box-shadow:8px 0 8px -8px rgba(0, 0, 0, .65);
        }}
        /* ein Schatten am rechten Rand zeigt, dass es seitlich weitergeht -
           er verschwindet, sobald man am Ende angekommen ist */
        .rl-wrap:has(table.viel) {{
          background:
            linear-gradient(to left, var(--flaeche) 40%, transparent)
              right center / 34px 100% no-repeat local,
            linear-gradient(to left, rgba(0, 0, 0, .6), transparent)
              right center / 16px 100% no-repeat scroll;
        }}
        .rl-leg {{font-size:12px;}}
        /* Game Score: oben Name und Zahl, darunter der Balken ueber die
           ganze Breite. Die Zahlen in den Teilen haetten keinen Platz. */
        .gs {{
          grid-template-columns:1fr max-content max-content;
          grid-auto-flow:row dense; column-gap:10px; row-gap:5px;
        }}
        .gs .bl-n {{grid-column:1; max-width:none;}}
        .gs .bl-w {{grid-column:2;}}
        .gs .bl-z {{grid-column:3;}}
        .gs-s {{grid-column:1 / -1; height:16px; margin-bottom:9px;}}
        .gs-t span {{font-size:0;}}
        /* Torhueter: oben Name und Quote, darunter der Meter, dann die
           Einzelwerte als Zeile - jeder mit seinem Wort dahinter */
        .tw {{
          grid-template-columns:1fr max-content; grid-auto-flow:row dense;
          column-gap:10px; row-gap:6px;
        }}
        .tw-k {{display:none;}}
        .tw-n {{grid-column:1;}}
        .tw-q {{grid-column:2;}}
        .tw .bl-s {{grid-column:1 / -1;}}
        .tw-u {{
          display:flex; flex-wrap:wrap; gap:1px 14px; grid-column:1 / -1;
          margin-bottom:10px;
        }}
        .tw-d {{font-size:12px; color:var(--gedaempft); text-align:left;}}
        .tw-d::after {{content:" " attr(data-e);}}
        /* Vergleichsbalken: oben Name und Rang, darunter die Spur ueber
           die ganze Breite */
        .vg {{
          grid-template-columns:1fr max-content; grid-auto-flow:row dense;
          column-gap:10px; row-gap:8px;
        }}
        .vg-n {{grid-column:1;}}
        .vg-w {{grid-column:2;}}
        .vg-w small {{display:block; margin-left:0;}}
        .vg-s {{grid-column:1 / -1; margin:8px 24px 14px 24px;}}
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

# Eine Zeile je Spiel und Linie: was der Gegner abgeschlossen hat, waehrend
# diese Linie auf dem Feld war. Wird mit Erfassung_Wygo.py gefuellt.
GEGNER_DATEI = "Gegner_Abschluesse.csv"
if os.path.exists(GEGNER_DATEI):
    gegner_ab = pd.read_csv(GEGNER_DATEI)
    gegner_ab.columns = gegner_ab.columns.str.strip()
else:
    gegner_ab = pd.DataFrame(columns=["Match_Id", "Linie",
                                      "Gegner aufs Tor gehalten", "Gegner daneben"])

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
normalize_match_col(gegner_ab)


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


# Erst seit dieser Saison sind die Spiele so erfasst, dass sich Linien und ein
# einzelnes Spiel als Mannschaft auswerten lassen. Davor gibt es den Reiter
# Linien nicht, und bei einem einzelnen Spiel nur den Reiter Spieler.
ALLE_REITER_AB = "26/27"


def aeltere_saison(saison):
    """True fuer Saisons vor ALLE_REITER_AB."""
    return saison_sort_key(saison) < saison_sort_key(ALLE_REITER_AB)

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
    '<div class="kopf"><div class="kopf-name">UHC Wygorazzi</div>'
    '<div class="kopf-unter">Spielerstatistik</div></div>',
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
    """Bilanz der Saison auf einen Blick: ein Band aus Kennzahlen, rechts die
    Resultate in zeitlicher Folge."""
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

    # je Feld oben das Wort, darunter die Zahl - (Zahl, Wort, Zusatzklasse)
    kpis = [
        (f"{saison}", "Saison", " saison-zelle"),
        (f"{len(zeilen)}", "Spiele", ""),
        (f"<span class='gut'>{siege}</span>–{remis}–<span class='schlecht'>{nieder}</span>",
         "S – U – N", ""),
        (f"{int(tore.sum())}:{int(gegen.sum())}", "Tore", ""),
        (f"<span class='{diff_klasse}'>{f'{diff:+d}'.replace('-', '−')}</span>",
         "Differenz", ""),
    ]
    kpi_html = "".join(
        f"<div class='kpi{k}'><div class='bez'>{b}</div><div class='wert'>{w}</div></div>"
        for w, b, k in kpis
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
        f"<div class='karte saison'>"
        f"<div class='kpi-reihe'>{kpi_html}</div>"
        f"<div class='saison-form'><div class='bez'>Resultate</div>"
        f"<div class='chips'>{''.join(chips)}</div></div>"
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
                "Strafen", "Block", "Schüsse", "Balleroberung", "Schüsse aufs Tor",
                "Ballverlust"]:
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
# ---------------------------
# Erweiterte Statistiken (nur fuer Saisons, in denen die neuen Spalten erfasst sind)
# ---------------------------
SPALTE_BLOCK = "Block"
SPALTE_SCHUESSE = "Schüsse"
SPALTE_BALLEROBERUNG = "Balleroberung"
SPALTE_SAT = "Schüsse aufs Tor"
SPALTE_BALLVERLUST = "Ballverlust"
SPALTE_GEHALTEN = "Gegner aufs Tor gehalten"
SPALTE_DANEBEN = "Gegner daneben"
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


def _einsaetze(df_in):
    """Wie viele Spiele die Auswahl umfasst und wer wie oft dabei war."""
    da = (df_in[df_in["Gespielt"].astype(str).str.strip() == "Ja"]
          if "Gespielt" in df_in.columns else df_in)
    return df_in[MATCH_COL].nunique(), da.groupby("Name")[MATCH_COL].nunique()


def stammspieler(df_in):
    """Namen, die mindestens die Haelfte der Spiele dabei waren.

    Wer zwei Einsaetze hat, stuende sonst mit einer Handvoll Werten neben
    Spielern mit der ganzen Saison - das verzerrt jede Rangliste. Es geht
    dabei nur um die Anzeige im Spieler-Tab: in den Team- und Linienwerten
    zaehlen die Schuesse und Tore dieser Spieler unveraendert mit.
    """
    if df_in.empty or "Name" not in df_in.columns:
        return set()
    gesamt, anzahl = _einsaetze(df_in)
    return set(anzahl[anzahl >= gesamt / 2].index)


def nur_stammspieler(df_in, mit_punkten=False):
    """Die Auswahl auf die Stammspieler eingrenzen.

    mit_punkten=True laesst zusaetzlich jeden stehen, der hier einen Punkt
    gemacht hat - in die Tor- und Assistliste gehoert ein Treffer, auch wenn
    er aus zwei Einsaetzen stammt.
    """
    namen = stammspieler(df_in)
    if mit_punkten and "Punkte" in df_in.columns:
        punkte = df_in.groupby("Name")["Punkte"].sum()
        namen |= set(punkte[punkte > 0].index)
    return df_in[df_in["Name"].isin(namen)]


def _zahl(v):
    """Ganze Zahlen ohne Nachkommastelle, sonst eine."""
    return f"{v:.0f}" if abs(v - round(v)) < 1e-9 else f"{v:.1f}"


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


ACHSEN_SCHRIFT = 12        # Ticks etwas kleiner als der Rest, sonst wachsen
PLOT_SCHRIFT = 13          # die gedrehten Namen nach unten davon
# dieselbe Schrift wie die Seite - sie ist dort schon geladen
PLOT_SCHRIFTART = "Barlow, 'Segoe UI', sans-serif"
TITEL_PLATZ = 45           # Hoehe fuer den Titel ueber dem Diagramm
ZEICHENFLAECHE = 255       # soviel bleibt fuers Diagramm selbst, immer gleich


def _achsen_platz(fig):
    """Wieviel Platz die gedrehte Achsenbeschriftung unten braucht.

    Feste 115 Pixel waren bei kurzen Beschriftungen verschenkte Hoehe. Hier
    wird aus der laengsten Zeile geschaetzt; automargin von Plotly vergroessert
    im Browser nach, falls die Schaetzung zu knapp ist.
    """
    texte = list(fig.layout.xaxis.ticktext or [])
    if not texte:
        texte = [x for tr in fig.data for x in (tr.x if tr.x is not None else [])
                 if x is not None]
    zeilen = [re.sub("<[^>]+>", "", str(t))
              for text in texte for t in str(text).split("<br>")]
    laengste = max((len(z) for z in zeilen), default=0)
    return int(min(170, max(55, 28 + laengste * ACHSEN_SCHRIFT * 0.55)))


def _style_plot(fig, tickangle="auto", textfix=True):
    """Einheitliche Formatierung - kompakt genug fuer Handy-Bildschirme.

    tickangle="auto" laesst die Beschriftung waagrecht und ueberlaesst es
    Plotly, sie zu drehen, wenn es eng wird. `textfix=False` für gestapelte
    Balken: dort kennt Plotly kein 'outside'.
    """
    gedreht = tickangle not in (0, "auto")
    unten = _achsen_platz(fig) if gedreht else 52
    winkel = None if tickangle == "auto" else tickangle
    fig.update_layout(
        yaxis_title=None,
        xaxis_title=None,
        title_x=0.02,
        title_font_size=16,
        font=dict(family=PLOT_SCHRIFTART, size=PLOT_SCHRIFT),
        # gedrehte Beschriftungen brauchen unten Platz, waagrechte nicht.
        # Die Hoehe waechst mit: sonst nimmt eine lange Beschriftung dem
        # Diagramm die Flaeche weg und es wirkt gequetscht.
        margin=dict(t=TITEL_PLATZ, b=unten, l=8, r=8),
        height=min(470, max(350, TITEL_PLATZ + ZEICHENFLAECHE + unten)),
        # Legende unter den Plot, damit sie auf dem Handy keine Breite frisst
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0),
    )
    fig.update_layout(
        colorway=[FARBEN["balken"], FARBEN["gut"], FARBEN["warn"], FARBEN["schlecht"]],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=FARBEN["text"],
        title_font_color=FARBEN["text"],
        # schlanke, eckige Marken; der Rest der Spalte bleibt Luft
        bargap=0.42, bargroupgap=0.12, barcornerradius=1,
        # kein Ziehen, kein Zoom - sonst verfaengt sich der Finger im Diagramm
        dragmode=False,
        hoverlabel=dict(bgcolor=FARBEN["flaeche_hell"], bordercolor=FARBEN["rand"],
                        font=dict(family=PLOT_SCHRIFTART, color=FARBEN["text"],
                                  size=13)),
        xaxis=dict(tickangle=winkel, automargin=True, showgrid=False,
                   fixedrange=True,
                   tickfont=dict(size=ACHSEN_SCHRIFT, color=FARBEN["gedaempft"]),
                   linecolor=FARBEN["rand"], tickcolor=FARBEN["rand"]),
        # das Gitter tritt zurueck: haarfein und nur eine Stufe neben der Karte
        yaxis=dict(automargin=True, fixedrange=True,
                   tickfont=dict(size=ACHSEN_SCHRIFT, color=FARBEN["gedaempft"]),
                   gridcolor=FARBEN["rand_fein"], gridwidth=1,
                   zerolinecolor=FARBEN["rand"], zerolinewidth=1),
    )
    # Schrift bleibt in den Textfarben - die Farbe traegt die Marke
    mehrere = len(fig.data) > 1
    fig.update_traces(
        insidetextfont_color=FARBEN["label_innen"],
        outsidetextfont_color=FARBEN["label_aussen"],
        hovertemplate=("%{x}<br>%{fullData.name}: <b>%{y}</b><extra></extra>"
                       if mehrere else "%{x}<br><b>%{y}</b><extra></extra>"),
        selector=dict(type="bar"))
    if textfix:
        _textposition_anpassen(fig)
    return fig


def _ballverlust_spiele(df_in):
    """Feldspieler aus den Spielen, in denen Ballverluste gezaehlt wurden.

    Sonst stuende eine Null fuer "hatte keinen Ballverlust" und fuer "wurde
    nie erfasst" - und in der Bilanz zaehlten Balleroberungen aus Spielen
    mit, fuer die es die Gegenseite gar nicht gibt.
    """
    d = nur_feldspieler(df_in)
    if SPALTE_BALLVERLUST not in d.columns or d.empty:
        return None
    je_spiel = d.groupby(MATCH_COL)[SPALTE_BALLVERLUST].sum()
    erfasst = set(je_spiel[je_spiel > 0].index)
    if not erfasst:
        return None
    return d[d[MATCH_COL].isin(erfasst)]


def _eintrag(fig, hinweis=None, breit=False, unter=None):
    """Plot fuers Kartenraster vorbereiten - der Titel wandert in die Karte.

    breit=True erzwingt die volle Breite, auch wenn der Plot wenige
    Kategorien hat. unter ist die graue Unterzeile der Karte: der Titel
    bleibt kurz, die Erklaerung steht darunter.
    """
    if fig is None:
        return (hinweis or "Keine Daten", None, 0)
    titel = fig.layout.title.text or ""
    if unter:
        titel = f"{titel}\n{unter}"
    # title_text="" statt title=None: None landet im Browser als "undefined"
    fig.update_layout(title_text="",
                      margin=dict(t=4, b=fig.layout.margin.b, l=8,
                                  r=fig.layout.margin.r))
    kategorien = len({str(x) for tr in fig.data
                      for x in (tr.x if tr.x is not None else [])})
    return (titel, fig, 999 if breit else kategorien)


def _eintrag_html(titel, inhalt, unter=None, breit=False):
    """Eine Karte aus einem HTML-Baustein. Ohne Inhalt entfaellt sie ganz -
    eine leere Karte waere nur Rauschen."""
    if inhalt is None:
        return None
    return (f"{titel}\n{unter}" if unter else titel, inhalt, 999 if breit else 0)


# Hover ja, Ziehen und Zoomen nein: mit dragmode=False (in _style_plot) laesst
# sich die Seite auf dem Handy auch ueber einem Diagramm weiterschieben.
PLOT_KONFIG = {"displayModeBar": False, "scrollZoom": False,
               "doubleClick": False, "showTips": False}


def _karte(titel, inhalt, hoehe=None):
    """Eine Karte: Titel, graue Unterzeile (nach einem Zeilenumbruch im
    Titel), darunter eine Figur oder ein HTML-Baustein."""
    haupt, _, unter = str(titel).partition("\n")
    with st.container(border=True):
        kopf = f"<div class='chart-titel'>{haupt}</div>"
        if unter:
            kopf += f"<div class='chart-unter'>{unter}</div>"
        st.markdown(kopf, unsafe_allow_html=True)
        if inhalt is None:
            st.markdown("<div class='chart-leer'>keine Daten in dieser Auswahl</div>",
                        unsafe_allow_html=True)
            return
        if isinstance(inhalt, str):
            st.markdown(inhalt, unsafe_allow_html=True)
            return
        if hoehe:
            inhalt.update_layout(height=hoehe)
        st.plotly_chart(inhalt, width="stretch", config=PLOT_KONFIG)


def raster(*eintraege, schmal_bis=6):
    """Kompakte Karten paarweise nebeneinander, breite ueber die volle Breite.

    Streamlit stapelt die Spalten auf schmalen Bildschirmen von selbst.
    """
    wartend = []

    def leeren():
        while wartend:
            paar = wartend[:2]
            del wartend[:2]
            for spalte, (titel, inhalt, _) in zip(st.columns(len(paar), gap="medium"), paar):
                with spalte:
                    _karte(titel, inhalt, hoehe=330)

    for eintrag in eintraege:
        if eintrag is None:
            continue
        titel, inhalt, anzahl = eintrag
        if inhalt is None or anzahl <= schmal_bis:
            wartend.append(eintrag)
        else:
            leeren()
            _karte(titel, inhalt)
    leeren()


# ---------------------------
# Powerplay / Boxplay
# Plus  = Powerplay mit eigenem Tor bzw. Boxplay ohne Gegentor (Erfolg)
# Minus = Powerplay ohne Tor bzw. Boxplay mit Gegentor (Misserfolg)
# ---------------------------
SPEZIAL_SPALTEN = ["Powerplay-Plus", "Powerplay-Minus", "Boxplay-Plus", "Boxplay-Minus"]

def hat_spezial_daten(df_in):
    vorhanden = [c for c in SPEZIAL_SPALTEN if c in df_in.columns]
    if not vorhanden or df_in.empty:
        return False
    return float(df_in[vorhanden].fillna(0).to_numpy().sum()) > 0


# ---------------------------
# Auswertungen pro Linie (Torhüter und Ersatzbank zählen nicht mit)
# ---------------------------
LINIEN = ["1", "2", "3"]


def nur_linien(df_in):
    d = df_in[df_in["Linie"].astype(str).isin(LINIEN)].copy()
    d["Linie_Label"] = "Linie " + d["Linie"].astype(str)
    return d


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


# ---------------------------
# Bausteine aus HTML: Tabelle, Balkenliste, Meter, Stapel, Kacheln
# ---------------------------
# Ranglisten, Quoten und Einzelwerte sind keine Diagramme im engeren Sinn -
# sie lesen sich als Liste besser: Namen waagrecht, duenne Balken, die Zahl
# rechts davon. Plotly bleibt fuer das, was wirklich eine Achse braucht
# (Verlaeufe ueber Spiele und Spielminuten).
class Html(str):
    """Fertiger HTML-Baustein fuer eine Karte - im Unterschied zur Figur."""


def _e(text):
    return _html.escape(str(text), quote=True)


def _zf(wert, nachkomma=0, vorzeichen=False):
    """Zahl fuer Listen und Tabellen: feste Stellen, echtes Minuszeichen."""
    wert = float(wert)
    if round(wert, nachkomma) == 0:
        wert = 0.0                       # kein "-0.00"
    text = (f"{wert:+.{nachkomma}f}" if vorzeichen and wert
            else f"{wert:.{nachkomma}f}")
    return text.replace("-", "−")


def gut_schlecht(gut, schlecht, trenner=":", voll=False):
    """Zwei Zahlen als Paar - die gute gruen, die schlechte rot: Tore und
    Gegentore, eroberte und verlorene Baelle. voll=True, wenn das Paar in
    einer Tabelle allein in der Zelle steht statt klein hinter einer Zahl."""
    return Html(f"<span class='gr{' voll' if voll else ''}'>"
                f"<span class='p'>{_zf(gut)}</span>"
                f"<span class='t'>{_e(trenner)}</span>"
                f"<span class='m'>{_zf(schlecht)}</span></span>")


def farbpaar(links, rechts, farben, trenner=":"):
    """Zwei Zahlen als Paar in zwei frei gewaehlten Farben - fuer Stellen, an
    denen Gruen und Rot schon etwas anderes bedeuten (im Spielverlauf die
    Fuehrung und den Rueckstand)."""
    return Html(f"<span class='gr'><b style='color:{farben[0]}'>{_zf(links)}</b>"
                f"<span class='t'>{_e(trenner)}</span>"
                f"<b style='color:{farben[1]}'>{_zf(rechts)}</b></span>")


def balkenliste(zeilen, nachkomma=0, anhang="", spur=False, bezug=None,
                marke=None, namen=""):
    """Liegende, duenne Balken: Name, Balken, Wert und ein grauer Zusatz.

    zeilen: [(Name, Wert, Zusatz)] in der Reihenfolge der Anzeige; der
    Zusatz darf fertiges HTML sein (Html).
    spur=True zeichnet die volle Strecke dahinter - fuer Quoten, bei denen
    100 % ein festes Ende ist (Meter). bezug ist der Wert der vollen Breite,
    sonst der groesste der Liste. marke setzt einen feinen Strich in die
    Spur, etwa bei 50 %. namen="weit" laesst lange Namen stehen (Paare),
    namen="mehr" bricht sie um (Ursachen in einer schmalen Karte).
    """
    zeilen = [z for z in (zeilen or []) if z is not None]
    if not zeilen:
        return None
    voll = float(bezug) if bezug else max(float(w) for _, w, _ in zeilen)
    voll = voll if voll > 0 else 1.0
    mit_zusatz = any(z for _, _, z in zeilen)
    strich = (f"<b style='left:{100 * float(marke) / voll:.1f}%'></b>"
              if marke is not None else "")
    teile = []
    for name, wert, zusatz in zeilen:
        breite = max(0.0, min(100.0, 100.0 * float(wert) / voll))
        fuellung = f"<i style='width:{breite:.1f}%'></i>" if breite > 0 else ""
        teile.append(
            f"<div class='bl-n {namen}' title='{_e(name)}'>{_e(name)}</div>"
            f"<div class='bl-s{' spur' if spur else ''}'>{fuellung}{strich}</div>"
            f"<div class='bl-w'>{_zf(wert, nachkomma)}{anhang}</div>"
            + (f"<div class='bl-z'>"
               f"{zusatz if isinstance(zusatz, Html) else _e(zusatz)}</div>"
               if mit_zusatz else ""))
    return Html(f"<div class='bl{' z4' if mit_zusatz else ''}'>{''.join(teile)}</div>")


def bilanzliste(zeilen, nachkomma=0):
    """Bilanz je Zeile: von der Mitte nach rechts gut, nach links schlecht.

    zeilen: [(Name, Wert, Zusatz)]. Die Mitte ist null, die laengste Bilanz
    fuellt eine Haelfte ganz aus.
    """
    zeilen = [z for z in (zeilen or []) if z is not None]
    if not zeilen:
        return None
    voll = max(abs(float(w)) for _, w, _ in zeilen) or 1.0
    mit_zusatz = any(z for _, _, z in zeilen)
    teile = []
    for name, wert, zusatz in zeilen:
        wert = float(wert)
        breite = min(50.0, 50.0 * abs(wert) / voll)
        seite = "pos" if wert > 0 else "neg"
        fuellung = (f"<i class='{seite}' style='width:{breite:.1f}%'></i>"
                    if round(wert, nachkomma) else "")
        teile.append(
            f"<div class='bl-n' title='{_e(name)}'>{_e(name)}</div>"
            f"<div class='bl-s mitte'>{fuellung}</div>"
            f"<div class='bl-w'>{_zf(wert, nachkomma, vorzeichen=True)}</div>"
            + (f"<div class='bl-z'>"
               f"{zusatz if isinstance(zusatz, Html) else _e(zusatz)}</div>"
               if mit_zusatz else ""))
    return Html(f"<div class='bl{' z4' if mit_zusatz else ''}'>{''.join(teile)}</div>")


def _auf_farbe(hexfarbe):
    """Schriftfarbe, die auf dieser Fuellung lesbar ist."""
    return _textfarbe(_rgb(hexfarbe))


def stapelliste(zeilen, farben, beschriftung=None, bezug=None, legende=True,
                legende_dazu=None):
    """Gestapelte liegende Balken mit einer Legende darueber.

    zeilen: [(Name, {Teil: Wert}, Text rechts)], farben: {Teil: Farbe} in der
    Reihenfolge des Stapels. Zwischen den Teilen bleibt eine schmale Fuge in
    der Farbe der Karte - sie trennt, ohne dass es einen Rand braucht. Ein
    Teil bekommt seine Zahl nur, wenn sie hineinpasst. legende_dazu
    ({Name: Farbe}) haengt abgesetzt weitere Eintraege an die Legende - fuer
    Farben, die nicht im Balken, sondern im Text rechts vorkommen.
    """
    zeilen = [z for z in (zeilen or []) if z is not None]
    if not zeilen:
        return None
    summen = [sum(float(v or 0) for v in teile.values()) for _, teile, _ in zeilen]
    voll = float(bezug) if bezug else (max(summen) or 1.0)
    schreiben = beschriftung or (lambda w: _zf(w))
    teile_html = []
    for (name, teile, rechts), summe in zip(zeilen, summen):
        segmente = []
        for teil, farbe in farben.items():
            wert = float(teile.get(teil, 0) or 0)
            if wert <= 0:
                continue
            text = schreiben(wert) if wert / voll >= 0.07 else ""
            segmente.append(
                f"<span style='flex:{wert:.4f} 1 0;background:{farbe};"
                f"color:{_auf_farbe(farbe)}' title='{_e(teil)}: "
                f"{_e(schreiben(wert))}'>{_e(text)}</span>")
        breite = max(0.0, min(100.0, 100.0 * summe / voll))
        teile_html.append(
            f"<div class='bl-n mehr' title='{_e(name)}'>{_e(name)}</div>"
            f"<div class='st-s'><div class='st-b' style='width:{breite:.1f}%'>"
            f"{''.join(segmente)}</div></div>"
            f"<div class='bl-w'>"
            f"{rechts if isinstance(rechts, Html) else _e(rechts)}</div>")
    kopf = ""
    if legende:
        eintraege = [f"<span><i style='background:{farbe}'></i>{_e(teil)}</span>"
                     for teil, farbe in farben.items()]
        for nr, (teil, farbe) in enumerate((legende_dazu or {}).items()):
            klasse = " class='ab'" if nr == 0 else ""
            eintraege.append(f"<span{klasse}><i style='background:{farbe}'></i>"
                             f"{_e(teil)}</span>")
        kopf = "<div class='leg'>" + "".join(eintraege) + "</div>"
    return Html(f"{kopf}<div class='bl st'>{''.join(teile_html)}</div>")


def rangtabelle(zeilen, spalten, aktiv=None, erste="Spieler", rang=True,
                balken=True, viel=None):
    """Tabelle mit einer hervorgehobenen Spalte.

    zeilen: Liste von Dicts in der Reihenfolge der Anzeige, mit "Name".
    spalten: [dict(key, kopf, art, nachkomma, anhang, hilfe)] - art ist
    "zahl", "bilanz" (mit Vorzeichen und Farbe) oder "text". Die aktive
    Spalte bekommt einen feinen Balken neben der Zahl: so traegt genau eine
    Spalte die Betonung, die anderen bleiben ruhige Zahlen. balken=False
    laesst ihn weg - dann ist die aktive Spalte nur fett gesetzt. Eine
    Textzelle darf fertiges HTML sein (Html). viel=True erzwingt die enge
    Fassung, die sich am Handy seitlich schieben laesst.
    """
    if not zeilen:
        return None
    hoechste = {}
    for sp in spalten:
        if sp.get("art", "zahl") in ("zahl", "bilanz"):
            hoechste[sp["key"]] = max(
                (abs(float(z.get(sp["key"], 0) or 0)) for z in zeilen), default=0) or 1.0
    kopf = (["<th class='l rang'>#</th>"] if rang else []) + [f"<th class='l name'>{_e(erste)}</th>"]
    for sp in spalten:
        klasse = "akt" if sp["key"] == aktiv else ""
        hilfe = f" title='{_e(sp['hilfe'])}'" if sp.get("hilfe") else ""
        kopf.append(f"<th class='{klasse}'{hilfe}>{_e(sp['kopf'])}</th>")
    koerper = []
    platz, vorher = 0, None
    for nr, z in enumerate(zeilen, 1):
        zellen = []
        if rang:
            wert_aktiv = z.get(aktiv) if aktiv else None
            if wert_aktiv is None or vorher is None or wert_aktiv != vorher:
                platz = nr                      # Gleichstand teilt sich den Rang
            vorher = wert_aktiv
            # ohne Wert in der sortierten Spalte gibt es auch keinen Rang
            zellen.append("<td class='l rang'>"
                          f"{'' if aktiv and wert_aktiv is None else platz}</td>")
        zellen.append(f"<td class='l name'>{_e(z['Name'])}</td>")
        for sp in spalten:
            art, key = sp.get("art", "zahl"), sp["key"]
            roh = z.get(key)
            ist_aktiv = key == aktiv
            if art == "text" or roh is None:
                # ohne Wert: leer, oder was die Spalte dafuer vorsieht ("–")
                inhalt = (roh if isinstance(roh, Html)
                          else _e(sp.get("leer", "") if roh is None else roh))
                zellen.append(f"<td class='{'akt' if ist_aktiv else ''}'>{inhalt}</td>")
                continue
            wert = float(roh)
            nk = sp.get("nachkomma", 0)
            # <Spalte>_zusatz in der Zeile ist fertiges HTML hinter der Zahl
            text = (_zf(wert, nk, vorzeichen=(art == "bilanz")) + sp.get("anhang", "")
                    + (z.get(key + "_zusatz") or ""))
            ton = ""
            if art == "bilanz" and round(wert, nk):
                ton = " plus" if wert > 0 else " minus"
            tipp = f" title='{_e(z[key + '_tipp'])}'" if z.get(key + "_tipp") else ""
            if not ist_aktiv:
                zellen.append(f"<td class='{ton.strip()}'{tipp}>{text}</td>")
                continue
            if not balken:
                zellen.append(f"<td class='akt{ton}'{tipp}>{text}</td>")
                continue
            if art == "bilanz":
                breite = min(50.0, 50.0 * abs(wert) / hoechste[key])
                seite = "pos" if wert > 0 else "neg"
                balken = (f"<span class='mini mitte'>"
                          + (f"<i class='{seite}' style='width:{breite:.1f}%'></i>"
                             if round(wert, nk) else "") + "</span>")
            else:
                breite = max(0.0, min(100.0, 100.0 * wert / hoechste[key]))
                balken = (f"<span class='mini'>"
                          + (f"<i style='width:{breite:.1f}%'></i>" if breite > 0 else "")
                          + "</span>")
            zellen.append(f"<td class='akt{ton}'{tipp}><div class='zelle'>{balken}"
                          f"<span class='zahl'>{text}</span></div></td>")
        koerper.append(f"<tr>{''.join(zellen)}</tr>")
    # ab neun Spalten rueckt die Tabelle zusammen und laesst sich am Handy
    # seitlich schieben (Klasse viel)
    if viel is None:
        viel = len(spalten) > 8
    klasse = "rl" + (" viel" if viel else "") + ("" if balken else " schlicht")
    return Html(f"<div class='rl-wrap'><table class='{klasse}'><thead><tr>{''.join(kopf)}"
                f"</tr></thead><tbody>{''.join(koerper)}</tbody></table></div>")


def kacheln(eintraege, klein=False):
    """Kennzahl-Kacheln: grosse Zahl, feiner Meter, ein erklaerender Satz.

    eintraege: [dict(bez, wert, einheit, anteil, text, delta, delta_ton)].
    anteil (0..1) zeichnet den Meter; delta ist ein fertiger Satz zum
    Vergleich, delta_ton "gut", "schlecht" oder "neutral".
    """
    eintraege = [k for k in (eintraege or []) if k is not None]
    if not eintraege:
        return None
    teile = []
    for k in eintraege:
        meter = ""
        if k.get("anteil") is not None:
            breite = max(0.0, min(100.0, 100.0 * float(k["anteil"])))
            meter = f"<div class='k-meter'><i style='width:{breite:.1f}%'></i></div>"
        einheit = f"<small>{_e(k['einheit'])}</small>" if k.get("einheit") else ""
        text = f"<div class='k-text'>{_e(k['text'])}</div>" if k.get("text") else ""
        delta = (f"<div class='k-delta {k.get('delta_ton', 'neutral')}'>"
                 f"{_e(k['delta'])}</div>") if k.get("delta") else ""
        teile.append(f"<div class='kachel'><div class='k-bez'>{_e(k['bez'])}</div>"
                     f"<div class='k-wert'>{_e(k['wert'])}{einheit}</div>"
                     f"{meter}{text}{delta}</div>")
    return Html(f"<div class='kacheln{' klein' if klein else ''}'>{''.join(teile)}</div>")


def vergleichsliste(zeilen):
    """Vergleichsbalken der Spielerkarte: je Kennzahl eine Spur, die beim
    besten Wert der Mannschaft endet, darauf der eigene Wert als Marke.

    zeilen: [dict(name, hinweis, lage, null, wert, rang, best, wenig)].
    lage und null sind Anteile der Spur (0..1): lage ist der eigene Wert,
    null der Nullpunkt. Der liegt nur dort nicht ganz links, wo es Werte
    unter null gibt (Plus-Minus). Gefuellt wird vom Nullpunkt bis zum Wert.
    """
    if not zeilen:
        return None
    teile = []
    for z in zeilen:
        lage = 100 * max(0.0, min(1.0, float(z["lage"])))
        null = 100 * max(0.0, min(1.0, float(z.get("null") or 0)))
        von, bis = min(lage, null), max(lage, null)
        fuellung = (f"<i style='left:{von:.1f}%;width:{bis - von:.1f}%'></i>"
                    if bis > von else "")
        marke = f"<b style='left:{null:.1f}%'></b>" if null > 0 else ""
        klein = f"<small>{_e(z['hinweis'])}</small>" if z.get("hinweis") else ""
        teile.append(
            f"<div class='vg-n'>{_e(z['name'])}{klein}</div>"
            + ("<div class='vg-s wenig' title='Wenig ist gut'>" if z.get("wenig")
               else "<div class='vg-s'>") + f"{fuellung}{marke}"
            f"<span class='vg-p' style='left:{lage:.1f}%'>{_e(z['wert'])}</span></div>"
            f"<div class='vg-w'>{_e(z['rang'])}<small>{_e(z['best'])}</small></div>")
    return Html(f"<div class='vg'>{''.join(teile)}</div>")


# ---------------------------
# Daten fuer die Bausteine
# ---------------------------
SORTIERUNG = {
    # Anzeige im Schalter -> Spalte der Tabelle, in der Reihenfolge der Spalten
    "Tore": "T", "Assists": "A", "Punkte": "Punkte",
    "Plus-Minus": "PlusMinus", "Strafen": "Strafen",
}

# Die uebrigen Zutaten des Game Score stehen mit in der Rangliste, wo sie
# erfasst sind: so sieht man in einer Zeile, woraus die Zahl entsteht.
# Anzeige im Schalter -> (Spalte, Kuerzel im Tabellenkopf, Wort in der Legende)
RANGLISTE_ZUSATZ = {
    "Schüsse": (SPALTE_SCHUESSE, "Sch", "Schüsse"),
    "Schüsse aufs Tor": (SPALTE_SAT, "SaT", "Schüsse aufs Tor"),
    "Blocks": (SPALTE_BLOCK, "Blk", "geblockte Schüsse"),
    "Balleroberungen": (SPALTE_BALLEROBERUNG, "BE", "Balleroberungen"),
    "Ballverluste": (SPALTE_BALLVERLUST, "BV", "Ballverluste"),
}


def rangliste_zusatz(df_in):
    """Die Zusatzspalten, die es in dieser Auswahl gibt - im Aufbau von
    RANGLISTE_ZUSATZ. Leer in Saisons ohne Schuesse und Ballwerte.

    Ballverluste sind erst teilweise erfasst: ohne eine einzige Zahl waere
    die Spalte eine Reihe Nullen und faellt weg.
    """
    if df_in is None or df_in.empty or not hat_erweiterte_daten(df_in):
        return {}
    return {anzeige: eintrag for anzeige, eintrag in RANGLISTE_ZUSATZ.items()
            if eintrag[0] in df_in.columns
            and (eintrag[0] != SPALTE_BALLVERLUST
                 or _ballverlust_spiele(df_in) is not None)}


def spieler_rangliste(df_in, sortiert="Punkte", mit_einsaetzen=True):
    """Die Rangliste als eine Tabelle: Einsaetze, Tore, Assists, Punkte,
    Plus-Minus und Strafen - dazu, wo erfasst, Schuesse, Blocks und
    Ballwerte, also alles, woraus der Game Score gerechnet wird. Sortiert
    nach der gewaehlten Spalte, darunter die Legende der Kuerzel."""
    if df_in is None or df_in.empty or "Name" not in df_in.columns:
        return None
    d = df_in.copy()
    for sp in ("T", "A", "Punkte", "Plus", "Minus", "PlusMinus", "Strafen"):
        d[sp] = pd.to_numeric(d[sp], errors="coerce").fillna(0) if sp in d.columns else 0
    _, einsaetze = _einsaetze(d)
    summe = d.groupby("Name")[["T", "A", "Punkte", "Plus", "Minus",
                               "PlusMinus", "Strafen"]].sum()
    summe["Sp"] = einsaetze.reindex(summe.index).fillna(0).astype(int)
    # Schuesse, Blocks und Ballwerte nur aus Einsaetzen im Feld - wie in den
    # Karten darunter und im Game Score: beim Torhueter bedeutet Block
    # Paraden. Wer nur im Tor stand, bekommt dort einen Strich statt einer Zahl.
    zusatz = rangliste_zusatz(d)
    feld = nur_feldspieler(d)
    for spalte, _kopf, _wort in zusatz.values():
        summe[spalte] = feld.groupby("Name")[spalte].sum().reindex(summe.index)
    wahl = {**SORTIERUNG, **{anzeige: e[0] for anzeige, e in zusatz.items()}}
    schluessel = wahl.get(sortiert, "Punkte")
    # Gleichstand: erst die Punkte, dann der Name - sonst springt die
    # Reihenfolge von Aufruf zu Aufruf. Zeilen ohne Wert stehen zuunterst.
    summe = summe.reset_index()
    summe = summe.sort_values([schluessel, "Punkte", "Name"],
                              ascending=[False, False, True])
    zeilen = []
    for _, r in summe.iterrows():
        zeile = {
            "Name": r["Name"], "Sp": int(r["Sp"]), "T": r["T"], "A": r["A"],
            "Punkte": r["Punkte"], "PlusMinus": r["PlusMinus"],
            "Strafen": r["Strafen"],
            # hinter der Bilanz, woraus sie besteht: Tore und Gegentore,
            # waehrend der Spieler auf dem Feld stand
            "PlusMinus_zusatz": gut_schlecht(r["Plus"], r["Minus"]),
        }
        for spalte, _kopf, _wort in zusatz.values():
            zeile[spalte] = None if pd.isna(r[spalte]) else r[spalte]
        zeilen.append(zeile)
    spalten = []
    if mit_einsaetzen:
        spalten.append(dict(key="Sp", kopf="Sp", hilfe="Einsätze", wort="Einsätze"))
    spalten += [
        dict(key="T", kopf="T", hilfe="Tore", wort="Tore"),
        dict(key="A", kopf="A", hilfe="Assists", wort="Assists"),
        dict(key="Punkte", kopf="P", hilfe="Punkte = Tore + Assists", wort="Punkte"),
        dict(key="PlusMinus", kopf="+/−", art="bilanz",
             wort="Plus-Minus (Tore : Gegentore)",
             hilfe="Tore minus Gegentore, während der Spieler auf dem Feld stand"),
        dict(key="Strafen", kopf="Str", hilfe="Strafen", wort="Strafen"),
    ]
    spalten += [dict(key=spalte, kopf=kopf, hilfe=wort[:1].upper() + wort[1:],
                     wort=wort, leer="–")
                for spalte, kopf, wort in zusatz.values()]
    # nur Zahlen, kein Balken: bei elf Spalten lenkt er mehr ab, als er zeigt
    tabelle = rangtabelle(zeilen, spalten, aktiv=schluessel, balken=False)
    if tabelle is None:
        return None
    # Die Kuerzel stehen ausgeschrieben unter der Tabelle - am Handy gibt es
    # keinen Mauszeiger, der sie verraet.
    legende = " · ".join(f"<span><b>{_e(sp['kopf'])}</b>{_e(sp['wort'])}</span>"
                         for sp in spalten)
    return Html(f"{tabelle}<div class='rl-leg'>{legende}</div>")


def quotenliste(df_in, zaehler, nenner, ohne_torhueter=True, teiler=1,
                gruppe="Name", sortieren=True, wort="von"):
    """Quote je Zeile als Meter: Fuellung, Prozent und die Zahlen dahinter.

    Wer keinen einzigen Versuch hat, fehlt - eine Quote aus null Versuchen
    ist keine Null, sondern nichts. `teiler` rechnet Spielermarkierungen in
    Situationen um (im Powerplay sind je Situation 3 Spieler markiert).
    """
    d = nur_feldspieler(df_in) if ohne_torhueter else df_in
    if (d is None or d.empty or zaehler not in d.columns
            or nenner not in d.columns):
        return None
    agg = d.groupby(gruppe)[[zaehler, nenner]].sum()
    agg = agg[agg[nenner] > 0]
    if agg.empty:
        return None
    agg["Quote"] = 100 * agg[zaehler] / agg[nenner]
    if sortieren:
        agg = agg.sort_values(["Quote", nenner], ascending=[False, False],
                              kind="stable")
    zeilen = [(name, r["Quote"],
               f"{_zahl(r[zaehler] / teiler)} {wort} {_zahl(r[nenner] / teiler)}")
              for name, r in agg.iterrows()]
    return balkenliste(zeilen, anhang=" %", spur=True, bezug=100)


def torhueterliste(df_in, mit_schnitt=True):
    """Die Torhueter im Vergleich: die Fangquote - Paraden von allen Schuessen
    aufs Tor - als Meter, dahinter die Einsaetze und was pro Spiel anfiel.

    Eine Quote aus einem einzigen Einsatz sagt weniger als eine aus fuenf;
    darum stehen die Spiele daneben. Bei einem einzelnen Spiel
    (mit_schnitt=False) stehen statt der Schnitte dessen Zahlen da.
    """
    tw = nur_torhueter(df_in)
    if tw.empty or SPALTE_BLOCK not in tw.columns or "Minus" not in tw.columns:
        return None
    agg = tw.groupby("Name").agg(Spiele=(MATCH_COL, "nunique"),
                                 Paraden=(SPALTE_BLOCK, "sum"),
                                 Gegentore=("Minus", "sum"))
    agg["Schuesse"] = agg["Paraden"] + agg["Gegentore"]
    agg = agg[agg["Schuesse"] > 0]
    if agg.empty:
        return None
    agg["Quote"] = 100 * agg["Paraden"] / agg["Schuesse"]
    agg = agg.sort_values(["Quote", "Schuesse"], ascending=[False, False],
                          kind="stable")
    if mit_schnitt:
        koepfe = ["gehalten", "Spiele", "Paraden pro Spiel", "Gegentore pro Spiel"]
    else:
        koepfe = ["gehalten", "Paraden", "Gegentore"]
    teile = ["<div class='tw-k'>Torhüter</div><div class='tw-k'>Fangquote</div>"
             "<div class='tw-k'></div>"
             + "".join(f"<div class='tw-k r'>{_e(k)}</div>" for k in koepfe)]
    for name, r in agg.iterrows():
        spiele = max(int(r["Spiele"]), 1)
        gehalten = f"{r['Paraden']:.0f} von {r['Schuesse']:.0f}"
        if mit_schnitt:
            # (Wert, Wort dahinter am Handy - dort gibt es keine Kopfzeile)
            werte = [(gehalten, "gehalten"),
                     (f"{spiele}", "Spiel" if spiele == 1 else "Spiele"),
                     (f"ø {r['Paraden'] / spiele:.1f}", "Paraden pro Spiel"),
                     (f"ø {r['Gegentore'] / spiele:.1f}", "Gegentore pro Spiel")]
        else:
            werte = [(gehalten, "gehalten"),
                     (f"{r['Paraden']:.0f}", "Paraden"),
                     (f"{r['Gegentore']:.0f}", "Gegentore")]
        breite = max(0.0, min(100.0, float(r["Quote"])))
        teile.append(
            f"<div class='tw-n'>{_e(name)}</div>"
            f"<div class='bl-s spur'><i style='width:{breite:.1f}%'></i></div>"
            f"<div class='tw-q'>{r['Quote']:.0f} %</div><div class='tw-u'>"
            + "".join(f"<div class='tw-d' data-e='{_e(wort)}'>{_e(wert)}</div>"
                      for wert, wort in werte) + "</div>")
    return Html(f"<div class='tw' style='--n:{len(koepfe)}'>{''.join(teile)}</div>")


def ballbilanzliste(df_in):
    """Balleroberungen minus Ballverluste, mit den beiden Einzelwerten."""
    d = _ballverlust_spiele(df_in)
    if d is None or SPALTE_BALLEROBERUNG not in d.columns:
        return None
    top = d.groupby("Name")[[SPALTE_BALLEROBERUNG, SPALTE_BALLVERLUST]].sum()
    top["Bilanz"] = top[SPALTE_BALLEROBERUNG] - top[SPALTE_BALLVERLUST]
    top = top.sort_values("Bilanz", ascending=False, kind="stable")
    return bilanzliste(
        [(n, r["Bilanz"], gut_schlecht(r[SPALTE_BALLEROBERUNG],
                                       r[SPALTE_BALLVERLUST], " : "))
         for n, r in top.iterrows()])


def einsatzliste(df_in):
    """Wer wie oft gespielt hat - als Meter gegen die Anzahl Spiele."""
    if "Gespielt" not in df_in.columns or df_in.empty:
        return None
    gesamt, anzahl = _einsaetze(df_in)
    anzahl = anzahl[anzahl > 0].sort_values(ascending=False, kind="stable")
    if anzahl.empty or not gesamt:
        return None
    return balkenliste([(n, w, f"von {gesamt}") for n, w in anzahl.items()],
                       spur=True, bezug=gesamt)


# Die zwei Farben eines Paars: der erstgenannte Spieler, der zweitgenannte.
# Die ersten beiden Plaetze der geprueften Palette - auch bei
# Rot-Gruen-Schwaeche zu trennen, und weder Gruen noch Rot: wer von beiden
# trifft, ist kein Urteil.
PAAR_FARBEN = ("#3987E5", "#D95926")


def paarliste(tore_zeilen, hoechstens=12):
    """Welches Paar zusammen am meisten trifft - aus der Spalte Assist.

    Gezaehlt wird in beide Richtungen: legt A dem B auf oder B dem A, gehoert
    das Tor demselben Paar. Der Balken ist nach Torschuetze geteilt; der
    haeufigere steht vorn. Der Punkt vor seinem Namen, sein Teil des Balkens
    und seine Zahl dahinter tragen dieselbe Farbe.
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
        # der haeufigere Torschuetze steht vorn; Tore = Zuspiele des Partners
        tore_a, tore_b = teile.get(b_name, 0), teile.get(a_name, 0)
        zeilen.append((a_name, b_name, tore_a, tore_b) if tore_a >= tore_b
                      else (b_name, a_name, tore_b, tore_a))
    zeilen.sort(key=lambda z: (-(z[2] + z[3]), f"{z[0]} + {z[1]}"))
    zeilen = zeilen[:hoechstens]
    voll = max(t1 + t2 for _, _, t1, t2 in zeilen) or 1
    vorn, hinten = PAAR_FARBEN
    html = []
    for erst, zweit, t1, t2 in zeilen:
        breite = 100.0 * (t1 + t2) / voll
        stuecke = "".join(f"<span style='flex:{n} 1 0;background:{farbe}'></span>"
                          for n, farbe in ((t1, vorn), (t2, hinten)) if n > 0)
        html.append(
            f"<div class='bl-n weit' title='{_e(erst)} + {_e(zweit)}'>"
            f"<span class='pa-n'><i class='pk' style='background:{vorn}'></i>"
            f"{_e(erst)}</span><span class='pa-p'>+</span>"
            f"<span class='pa-n'><i class='pk' style='background:{hinten}'></i>"
            f"{_e(zweit)}</span></div>"
            f"<div class='bl-s'><div class='pa-b' style='width:{breite:.1f}%'>"
            f"{stuecke}</div></div>"
            f"<div class='bl-w'>{t1 + t2}</div>"
            f"<div class='bl-z pa-z'><b style='color:{vorn}'>{t1}</b> : "
            f"<b style='color:{hinten}'>{t2}</b></div>")
    return Html(f"<div class='bl z4'>{''.join(html)}</div>")


def kategorienliste(tore_zeilen, art="Gegentor", linie=None):
    """Tore oder Gegentore nach Ursache.

    Fuer die ganze Mannschaft gestapelt nach der Linie, die auf dem Feld war;
    fuer eine einzelne Linie eine schlichte Rangliste.
    """
    d = kategorie_zaehlung(tore_zeilen, art, linie)
    if d.empty:
        return None
    gesamt = d.groupby("Kategorie")["Anzahl"].sum().sort_values(ascending=False)
    if linie is not None:
        return balkenliste([(k, n, "") for k, n in gesamt.items()], namen="mehr")
    zeilen = []
    for kategorie, anzahl in gesamt.items():
        teile = {r["Linie_Label"]: r["Anzahl"]
                 for _, r in d[d["Kategorie"] == kategorie].iterrows()}
        zeilen.append((kategorie, teile, f"{int(anzahl)}"))
    return stapelliste(zeilen, LINIEN_FARBEN)


# Die Tore im Resultat rechts neben dem Balken: unsere und die des Gegners.
# Blau und Orange - Gruen und Rot bedeuten im Balken schon Fuehrung und
# Rueckstand, dieselben Farben an den Zahlen laesen sich wie ein Urteil.
RESULTAT_FARBEN = {"Unsere Tore": "#3987E5", "Gegentore": "#D95926"}
LAGEN_FARBEN = {"in Führung": FARBEN["gut"], "Unentschieden": FARBEN["neutral"],
                "im Rückstand": FARBEN["schlecht"]}


def spielstandliste(tore_zeilen, spiele=None):
    """Je Spiel die Zeit in Fuehrung, im Gleichstand und im Rueckstand.

    Jeder Balken ist gleich lang (die volle Spielzeit) - so sieht man auf
    einen Blick, welche Spiele wir kontrolliert haben. Rechts das Resultat:
    ein Spiel kann lange gefuehrt und trotzdem verloren werden.
    """
    folgen = _torfolge(tore_zeilen)
    if not folgen:
        return None
    namen = dict(_spielfolge(spiele)) if spiele is not None else {}
    reihenfolge = [mid for mid, _ in _spielfolge(spiele)] if spiele is not None else []
    ergebnis = {}
    if spiele is not None and not spiele.empty:
        for _, r in spiele.iterrows():
            eigen = pd.to_numeric(r.get("Tore Wygorazzi"), errors="coerce")
            gegen = pd.to_numeric(r.get("Tore Gegner"), errors="coerce")
            if not pd.isna(eigen) and not pd.isna(gegen):
                # unsere Tore und die des Gegners in zwei Farben, die die
                # Legende nennt - so ist klar, welche Zahl unsere ist
                ergebnis[r.get(MATCH_COL)] = farbpaar(
                    int(eigen), int(gegen), list(RESULTAT_FARBEN.values()))
    je_spiel = {}
    for mid, folge in folgen:
        minuten = {z: 0.0 for z in ZUSTAENDE}
        stand, vorher = 0, 0.0
        for minute, eigen, _hz in folge:
            minuten[_lage(stand)] += max(0.0, minute - vorher)
            stand += 1 if eigen else -1
            vorher = minute
        minuten[_lage(stand)] += max(0.0, _spiel_dauer(folge) - vorher)
        je_spiel[mid] = minuten
    folge_ids = [m for m in reihenfolge if m in je_spiel] + \
                [m for m in je_spiel if m not in reihenfolge]
    zeilen = [(namen.get(mid, f"Spiel {int(mid)}"), je_spiel[mid],
               ergebnis.get(mid, "")) for mid in folge_ids]
    return stapelliste(zeilen, LAGEN_FARBEN, beschriftung=_mmss,
                       legende_dazu=RESULTAT_FARBEN)


def team_quoten(df_in, situationen):
    """Die vier Mannschaftsquoten als (Zaehler, Nenner) - oder None.

    Powerplay und Boxplay kommen aus Statistik_Wygo.csv (je Situation eine
    Zaehlung), die Abschlusswerte aus den Spielerzeilen.
    """
    werte = {}
    sit = situationen or {}
    for name, plus, minus in (("Powerplay", "Powerplay-Plus", "Powerplay-Minus"),
                              ("Boxplay", "Boxplay-Plus", "Boxplay-Minus")):
        gut = float(sit.get(plus, 0) or 0)
        gesamt = gut + float(sit.get(minus, 0) or 0)
        if gesamt > 0:
            werte[name] = (gut, gesamt)
    if (df_in is not None and not df_in.empty
            and SPALTE_SCHUESSE in df_in.columns and SPALTE_SAT in df_in.columns):
        feld = nur_feldspieler(df_in)
        schuesse = float(pd.to_numeric(feld[SPALTE_SCHUESSE], errors="coerce").fillna(0).sum())
        sat = float(pd.to_numeric(feld[SPALTE_SAT], errors="coerce").fillna(0).sum())
        tore = float(pd.to_numeric(feld["T"], errors="coerce").fillna(0).sum())
        if schuesse > 0:
            werte["Schüsse aufs Tor"] = (sat, schuesse)
        if sat > 0:
            werte["Torquote"] = (tore, sat)
    return werte


TEAM_KACHEL_TEXT = {
    # Name: (Satz mit {z} und {n}, hoeher ist besser?)
    "Powerplay": "{z} von {n} Überzahlspielen mit eigenem Tor",
    "Boxplay": "{z} von {n} Unterzahlspielen ohne Gegentor",
    "Schüsse aufs Tor": "{z} von {n} Schüssen gingen aufs Tor",
    "Torquote": "{z} Tore aus {n} Schüssen aufs Tor",
}


def team_kacheln(df_in, situationen, vergleich=None):
    """Kennzahl-Kacheln der Mannschaft, auf Wunsch mit dem Vorsaison-Wert.

    vergleich: (Bezeichnung, team_quoten der Vergleichssaison).
    """
    werte = team_quoten(df_in, situationen)
    if not werte:
        return None
    eintraege = []
    for name, satz in TEAM_KACHEL_TEXT.items():
        if name not in werte:
            continue
        z, n = werte[name]
        quote = 100 * z / n
        kachel = dict(bez=name, wert=f"{quote:.0f}", einheit=" %",
                      anteil=z / n, text=satz.format(z=_zahl(z), n=_zahl(n)))
        if vergleich and name in vergleich[1]:
            vz, vn = vergleich[1][name]
            unterschied = quote - 100 * vz / vn
            if abs(unterschied) < 0.5:
                kachel.update(delta=f"wie {vergleich[0]}", delta_ton="neutral")
            else:
                pfeil = "▲" if unterschied > 0 else "▼"
                kachel.update(
                    delta=f"{pfeil} {abs(unterschied):.0f} Punkte gegenüber {vergleich[0]}",
                    delta_ton="gut" if unterschied > 0 else "schlecht")
        eintraege.append(kachel)
    return kacheln(eintraege)


def abwehr_kacheln(df_in, gegentore=None):
    """Was aus den gegnerischen Schuessen auf unser Tor wurde - als Kacheln
    wie die Quoten darueber: die Gesamtzahl, dann die drei Ausgaenge mit
    ihrem Anteil."""
    if df_in is None or df_in.empty or SPALTE_BLOCK not in df_in.columns:
        return None
    feld, tw = nur_feldspieler(df_in), nur_torhueter(df_in)
    geblockt = float(feld[SPALTE_BLOCK].sum())
    gehalten = float(tw[SPALTE_BLOCK].sum()) if not tw.empty else 0.0
    if gegentore is None:
        gegentore = float(tw["Minus"].sum()) if not tw.empty else 0.0
    gegentore = float(gegentore)
    # ohne erfasste Blocks und Paraden gaebe es nur Gegentore zu zeigen
    if (geblockt + gehalten) <= 0:
        return None
    gesamt = geblockt + gehalten + gegentore
    spiele = int(df_in[MATCH_COL].nunique())
    eintraege = [dict(bez="Schüsse auf unser Tor", wert=_zahl(gesamt),
                      text=f"ø {gesamt / spiele:.1f} pro Spiel" if spiele > 1 else "")]
    for bez, wert, satz in (
            ("Von uns geblockt", geblockt, "{z} von {n} Schüssen geblockt"),
            ("Vom Torhüter gehalten", gehalten, "{z} von {n} Schüssen gehalten"),
            ("Gegentor", gegentore, "{z} von {n} Schüssen im Tor")):
        eintraege.append(dict(bez=bez, wert=f"{100 * wert / gesamt:.0f}", einheit=" %",
                              anteil=wert / gesamt,
                              text=satz.format(z=_zahl(wert), n=_zahl(gesamt))))
    return kacheln(eintraege)


def linien_tabelle(df_in, tore_zeilen=None):
    """Die drei Linien nebeneinander - eine Zeile je Linie.

    Neben Toren, Gegentoren und Strafen dieselben Zahlen wie in der Rangliste
    der Spieler und in derselben Reihenfolge: Schuesse, Schuesse aufs Tor,
    Blocks, Balleroberungen und - wo erfasst - Ballverluste.
    """
    d = nur_linien(df_in)
    if d.empty:
        return None
    bilanz = linien_bilanz(tore_zeilen)
    mit_toren = any(w["Tor"] or w["Gegentor"] for w in bilanz.values())
    zusatz = rangliste_zusatz(df_in)
    zeilen = []
    for linie in LINIEN:
        teil = d[d["Linie"].astype(str) == linie]
        if teil.empty:
            continue
        z = {"Name": f"Linie {linie}"}
        if mit_toren:
            z.update(Tore=bilanz[linie]["Tor"], Gegentore=bilanz[linie]["Gegentor"],
                     PlusMinus=bilanz[linie]["Tor"] - bilanz[linie]["Gegentor"])
        for anzeige, (spalte, _kurz, _wort) in zusatz.items():
            z[anzeige] = float(pd.to_numeric(teil[spalte], errors="coerce").fillna(0).sum())
        z["Strafen"] = float(teil["Strafen"].sum()) if "Strafen" in teil.columns else 0
        zeilen.append(z)
    if not zeilen:
        return None
    spalten = []
    if mit_toren:
        spalten += [dict(key="Tore", kopf="Tore"),
                    dict(key="Gegentore", kopf="Gegentore"),
                    dict(key="PlusMinus", kopf="+/−", art="bilanz",
                         hilfe="Tore minus Gegentore mit dieser Linie auf dem Feld")]
    spalten += [dict(key=anzeige, kopf=anzeige) for anzeige in zusatz]
    spalten.append(dict(key="Strafen", kopf="Strafen"))
    return rangtabelle(zeilen, spalten, aktiv="PlusMinus" if mit_toren else None,
                       erste="Linie", rang=False)


# Unsere Abschluesse und die des Gegners hinter dem Balken - dieselben zwei
# Farben wie bei den Toren im Spielverlauf: Blau wir, Orange der Gegner.
ABSCHLUSS_FARBEN = {"Wygorazzi": "#3987E5", "Gegner": "#D95926"}


def corsiliste(df_in, tore_zeilen):
    """Je Linie ihr Anteil an allen Abschlussversuchen, waehrend sie spielte.

    Hinter dem Anteil stehen die zwei Zahlen dazu - unsere Abschluesse und
    die des Gegners, jede in ihrer Farbe. Die Legende darueber nennt sie.
    """
    je_linie, _team, _anzahl = corsi_zahlen(df_in, tore_zeilen)
    if je_linie.empty:
        return None
    je_linie = je_linie.sort_values("Linie_Label")
    wir, gegner = ABSCHLUSS_FARBEN.values()
    liste = balkenliste(
        [(r["Linie_Label"], r["CF%"],
          Html(f"<span class='pa-z'><b style='color:{wir}'>{r['CF']:.0f}</b> : "
               f"<b style='color:{gegner}'>{r['CA']:.0f}</b></span>"))
         for _, r in je_linie.iterrows()],
        anhang=" %", spur=True, bezug=100, marke=50)
    legende = "".join(f"<span><i style='background:{farbe}'></i>{_e(name)}</span>"
                      for name, farbe in ABSCHLUSS_FARBEN.items())
    return Html(f"<div class='leg'>{legende}</div>{liste}")


def gegnertrefferliste(df_in, tore_zeilen):
    """Was der Gegner aus seinen Torschuessen macht, waehrend die Linie spielt."""
    je_linie, _team, _anzahl = corsi_zahlen(df_in, tore_zeilen)
    if je_linie.empty:
        return None
    d = je_linie.copy()
    d["aufs Tor"] = d["Gegentore"] + d["gehalten"]
    d = d[d["aufs Tor"] > 0].sort_values("Linie_Label")
    if d.empty:
        return None
    return balkenliste(
        [(r["Linie_Label"], 100 * r["Gegentore"] / r["aufs Tor"],
          f"{r['Gegentore']:.0f} von {r['aufs Tor']:.0f}")
         for _, r in d.iterrows()],
        anhang=" %", spur=True, bezug=100)


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


def auswahl_schalter(titel, optionen, schluessel, vorgabe, on_change=None):
    """Ein Umschalter, bei dem immer genau eine Wahl aktiv ist.

    st.segmented_control laesst sich durch einen zweiten Klick abwaehlen und
    steht dann leer da. Hier bleibt in dem Fall die bisherige Wahl stehen;
    eine Wahl, die es unter den Optionen nicht (mehr) gibt - etwa nach dem
    Wechsel in eine Saison ohne diese Spalte -, faellt auf die Vorgabe zurueck.
    """
    gemerkt = f"{schluessel}_gemerkt"
    if st.session_state.get(schluessel) not in optionen:
        zuletzt = st.session_state.get(gemerkt)
        st.session_state[schluessel] = zuletzt if zuletzt in optionen else vorgabe
    wahl = st.segmented_control(titel, optionen, key=schluessel,
                                on_change=on_change) or vorgabe
    st.session_state[gemerkt] = wahl
    return wahl


def tab_pro_spieler(df_in, zeige_gespielt=False, spiele=None):
    # Gezeigt wird, wer mindestens die Haelfte der Spiele dabei war; wer
    # gepunktet hat, steht zusaetzlich in der Rangliste. Fangquote und
    # Einsaetze bleiben vollstaendig - Torhueter wechseln sich ab, und wer
    # wie oft gespielt hat, gehoert vollzaehlig aufs Blatt.
    stamm = nur_stammspieler(df_in)
    punkte = nur_stammspieler(df_in, mit_punkten=True)
    mehrere = df_in[MATCH_COL].nunique() > 1
    # Sortieren laesst sich nach jeder Spalte der Tabelle. Eine Wahl, die es
    # in dieser Auswahl nicht gibt (Saison ohne Schuesse und Ballwerte), faellt
    # auf die Punkte zurueck.
    zusatz = rangliste_zusatz(punkte)
    sortiert = auswahl_schalter(
        "Rangliste sortiert nach", list(SORTIERUNG) + list(zusatz),
        "spieler_sortierung", "Punkte")
    erweitert = hat_erweiterte_daten(df_in)

    eintraege = [_eintrag_html(
        "Rangliste", spieler_rangliste(punkte, sortiert, mit_einsaetzen=mehrere),
        unter=f"Sortiert nach {sortiert}", breit=True)]
    # Schuesse, Blocks, Balleroberungen und Ballverluste stehen als Zahlen in
    # der Rangliste - eigene Karten dafuer gibt es nicht mehr.
    if erweitert:
        eintraege += [
            _eintrag_html("Schüsse aufs Tor",
                          quotenliste(stamm, SPALTE_SAT, SPALTE_SCHUESSE),
                          unter="Anteil der Schüsse, die aufs Tor kamen"),
            _eintrag_html("Torquote", quotenliste(stamm, "T", SPALTE_SAT),
                          unter="Tore aus den Schüssen aufs Tor"),
            # Ballverluste sind erst teilweise erfasst - ohne Zahlen entfaellt
            # die Karte
            _eintrag_html("Ballgewinn und Ballverlust", ballbilanzliste(stamm),
                          unter="Balleroberungen minus Ballverluste"),
        ]
    eintraege.append(_eintrag_html(
        "Bully-Gewinnquote", quotenliste(stamm, "Bully-Plus", "Bully-Gesamt"),
        unter="Gewonnene von allen gespielten Bullys"))
    if erweitert:
        eintraege.append(_eintrag_html(
            "Torhüter-Fangquote", torhueterliste(df_in, mit_schnitt=mehrere),
            unter="Paraden von allen Schüssen aufs Tor", breit=True))
    if hat_spezial_daten(df_in):
        eintraege += [
            _eintrag_html("Powerplay",
                          quotenliste(stamm, "Powerplay-Plus", "Powerplay-Gesamt"),
                          unter="Powerplay mit Tor"),
            _eintrag_html("Boxplay",
                          quotenliste(stamm, "Boxplay-Plus", "Boxplay-Gesamt"),
                          unter="Boxplay ohne Gegentor"),
        ]
    # Game Score nach den einzelnen Zahlen, die er zusammenfasst, und direkt
    # vor dem Punkteverlauf. Ueber die ganze Breite, damit man im Balken sieht,
    # woraus die Zahl besteht - eine Zahl, deren Rechnung man nicht sieht,
    # glaubt einem niemand. Die Gewichte stehen in der Legende.
    eintraege.append(_eintrag_html(
        "Game Score", gamescore_grafik(stamm, mit_schnitt=mehrere),
        unter="Jede Aktion zählt mit ihrem Gewicht aus der Legende – zusammen "
              "ergibt das den Game Score.", breit=True))
    # Wer wann geliefert hat - braucht die volle Breite
    if spiele is not None:
        teppich = plot_punkte_teppich(punkte, spiele)
        if teppich is not None:
            eintraege.append(_eintrag(
                teppich, breit=True,
                unter="Punkte je Spiel"))
    if zeige_gespielt:
        eintraege.append(_eintrag_html("Einsätze", einsatzliste(df_in),
                                       unter="Bestrittene Spiele", breit=True))
    raster(*eintraege)


def tab_pro_linie(df_in, tore_zeilen=None):
    linien = nur_linien(df_in)

    def quote(zaehler, nenner, teiler=1):
        return quotenliste(linien, zaehler, nenner, ohne_torhueter=False,
                           teiler=teiler, gruppe="Linie_Label", sortieren=False)

    eintraege = [
        _eintrag_html("Linien im Vergleich", linien_tabelle(df_in, tore_zeilen),
                      breit=True),
    ]
    # zuerst der eigene Abschluss: wie viel aufs Tor kommt und was daraus wird
    if hat_erweiterte_daten(df_in):
        eintraege += [
            _eintrag_html("Schüsse aufs Tor", quote(SPALTE_SAT, SPALTE_SCHUESSE),
                          unter="Anteil der Schüsse, die aufs Tor kamen"),
            _eintrag_html("Torquote", quote("T", SPALTE_SAT),
                          unter="Tore aus den Schüssen aufs Tor"),
        ]
    eintraege += [
        # dann die Gegenseite, solange die Linie spielt: was der Gegner aus
        # seinen Schuessen macht ...
        _eintrag_html("Trefferquote des Gegners",
                      gegnertrefferliste(df_in, tore_zeilen),
                      unter="Gegentore aus den gegnerischen Schüssen aufs Tor"),
        # ... und wer mehr zum Abschluss kommt. Corsi nur, wo
        # Gegner_Abschluesse.csv Zahlen hat
        _eintrag_html("Abschlussversuche", corsiliste(df_in, tore_zeilen),
                      unter="Anteil an allen Abschlüssen, während die Linie "
                            "spielte"),
    ]
    if hat_spezial_daten(df_in):
        # je Situation sind im Powerplay 3 Spieler markiert, im Boxplay 2
        eintraege += [
            _eintrag_html("Powerplay",
                          quote("Powerplay-Plus", "Powerplay-Gesamt", teiler=3),
                          unter="Überzahlspiele mit eigenem Tor"),
            _eintrag_html("Boxplay",
                          quote("Boxplay-Plus", "Boxplay-Gesamt", teiler=2),
                          unter="Unterzahlspiele ohne Gegentor"),
        ]
    raster(*eintraege)
    # Je Linie das eigene Ursachenbild, Tore links und Gegentore rechts. In
    # einem eigenen Raster je Linie: so bleibt das Paar zusammen, auch wenn
    # oben eine ungerade Zahl Karten steht oder eine Seite leer ist.
    for linie in LINIEN:
        raster(*[_eintrag_html(f"{ART_KURZ[art]} nach Ursache — Linie {linie}",
                               kategorienliste(tore_zeilen, art=art, linie=linie))
                 for art in ("Tor", "Gegentor")])


# ---------------------------
# Saisonverlauf, Torzeiten und Gegnerbilanz
# ---------------------------
def _spiel_label(zeile):
    """'25.10 Merenschwand' - kurz genug fuer die Achse."""
    tag = str(zeile.get("Datum_label", ""))
    tag = "" if tag.startswith("ohne") else tag[:6].rstrip(".") + " "
    return f"{tag}{str(zeile.get('Gegner', ''))[:14]}"


def chronologisch(spiele):
    """Die Spiele der Auswahl in zeitlicher Folge, jedes nur einmal.

    Alle Karten mit Spielen auf der x-Achse gehen hierdurch, damit das
    aelteste Spiel ueberall links steht - sonst liest man zwei Karten
    nebeneinander in entgegengesetzter Richtung.
    """
    if spiele is None or spiele.empty or MATCH_COL not in spiele.columns:
        return pd.DataFrame()
    d = spiele.sort_values(["Datum_parsed", MATCH_COL], na_position="first")
    return d[d[MATCH_COL].notna() & ~d[MATCH_COL].duplicated()]


def _spielfolge(spiele):
    """Die Spiele der Auswahl in zeitlicher Folge: [(Match_Id, Beschriftung), ...]."""
    return [(r[MATCH_COL], _spiel_label(r))
            for _, r in chronologisch(spiele).iterrows()]


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


# Die Kategorie steht als Spalte in Tore.csv, nur bei Gegentoren. Auf der
# Achse umgebrochen: ein gedrehter Text von 33 Zeichen frisst sonst die halbe
# Karte.
ART_KURZ = {"Tor": "Tore", "Gegentor": "Gegentore"}


def _linien_von(roh):
    """'1+3' -> ['1', '3'] - gemischte Formation zaehlt fuer beide Linien."""
    teile = [t.strip().removesuffix(".0")
             for t in str(roh or "").replace(";", "+").split("+")]
    return [t for t in teile if t in LINIEN]


def kategorie_zaehlung(tore_zeilen, art="Gegentor", linie=None):
    """Tore oder Gegentore je Kategorie und Linie zaehlen.

    Wie bei linien_bilanz zaehlt ein Treffer mit gemischter Formation ("1+3")
    fuer beide Linien - die Summe kann deshalb ueber der Trefferzahl liegen.
    Mit linie="2" bleibt nur diese eine Linie uebrig.
    """
    if (tore_zeilen is None or tore_zeilen.empty
            or "Kategorie" not in tore_zeilen.columns):
        return pd.DataFrame()
    ist_tor = tore_zeilen["Art"].astype(str).str.strip() == "Tor"
    d = tore_zeilen[ist_tor if art == "Tor" else ~ist_tor].copy()
    d["Kategorie"] = d["Kategorie"].astype(str).str.strip()
    d = d[~d["Kategorie"].isin(("", "nan", "None"))]
    if d.empty:
        return pd.DataFrame()
    zeilen = [{"Kategorie": k, "Linie_Label": f"Linie {l}"}
              for k, roh in zip(d["Kategorie"], d["Linie"])
              for l in _linien_von(roh)
              if linie is None or l == str(linie)]
    if not zeilen:
        return pd.DataFrame()
    return (pd.DataFrame(zeilen).groupby(["Kategorie", "Linie_Label"])
            .size().reset_index(name="Anzahl"))


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


REAKTION_FENSTER = 3        # Minuten


def plot_reaktion(tore_zeilen):
    """Was in den Minuten nach einem Tor passiert.

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
    # zwei Gruppen mit je zwei Balken - ohne viel Luft waeren es Bloecke
    fig.update_layout(bargap=0.6, bargroupgap=0.1)
    hoechster = float(daten["Anzahl"].max())
    fig.update_yaxes(dtick=2 if hoechster <= 12 else 5,
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


def _lage(differenz):
    """Welche der drei Lagen ein Torverhaeltnis bedeutet."""
    if differenz > 0:
        return "in Führung"
    return "im Rückstand" if differenz < 0 else "Unentschieden"


def _mmss(minuten):
    """0.4 -> '0:24'. Dezimalminuten liest am Balken niemand."""
    s = int(round(float(minuten) * 60))
    return f"{s // 60}:{s % 60:02d}"


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


# ---------------------------
# Corsi: alle Abschlussversuche beider Seiten
# ---------------------------
def _gegner_abschluesse(ids):
    """Die erfassten Gegner-Abschluesse der gewaehlten Spiele, als Zahlen."""
    if gegner_ab.empty:
        return pd.DataFrame()
    d = gegner_ab[gegner_ab[MATCH_COL].isin(ids)].copy()
    for sp in (SPALTE_GEHALTEN, SPALTE_DANEBEN):
        d[sp] = pd.to_numeric(d.get(sp), errors="coerce").fillna(0)
    return d


def corsi_zahlen(df_in, tore_zeilen):
    """CF und CA je Linie und fuers Team.

    CF sind unsere Abschlussversuche (Spalte Schuesse), CA die des Gegners:
    Gegentore, vom Torhueter gehalten, von uns geblockt und daneben. Gerechnet
    wird nur ueber Spiele, fuer die Gegner_Abschluesse.csv Zahlen hat - sonst
    fehlten zwei der vier Teile und die Quote saehe viel zu gut aus.

    Die gehaltenen Schuesse zaehlen auf beiden Ebenen verschieden: fuers Team
    gelten alle Paraden des Torhueters, je Linie nur die, die sich auch einer
    Linie zuordnen lassen. In Unterzahl steht keine Linie als Einheit auf dem
    Feld - diese Schuesse fehlen deshalb bei den Linien und sind trotzdem im
    Teamwert. Die Summe ueber die Linien ist also kleiner als der Teamwert.

    Zurueck kommt (Tabelle je Linie, Teamwerte, Anzahl Spiele). Beim Team
    zaehlt jede Zeile einmal, je Linie zaehlt eine gemischte Formation ("1+3")
    fuer beide - wie bei linien_bilanz.
    """
    leer = (pd.DataFrame(), {}, 0)
    if df_in is None or df_in.empty or SPALTE_SCHUESSE not in df_in.columns:
        return leer
    g = _gegner_abschluesse(set(df_in[MATCH_COL].dropna().unique()))
    if g.empty:
        return leer
    ids = set(g[MATCH_COL].dropna().unique())
    d = df_in[df_in[MATCH_COL].isin(ids)]
    feld = nur_feldspieler(d)
    if feld.empty:
        return leer

    cf = feld.groupby(feld["Linie"].astype(str))[SPALTE_SCHUESSE].sum()
    geblockt = feld.groupby(feld["Linie"].astype(str))[SPALTE_BLOCK].sum()

    gegentore = {l: 0 for l in LINIEN}
    anzahl_gegentore = 0
    if tore_zeilen is not None and not tore_zeilen.empty:
        t = tore_zeilen[(tore_zeilen[MATCH_COL].isin(ids))
                        & (tore_zeilen["Art"].astype(str).str.strip() == "Gegentor")]
        anzahl_gegentore = len(t)
        for roh in t["Linie"]:
            for l in _linien_von(roh):
                gegentore[l] += 1

    gehalten = {l: 0.0 for l in LINIEN}
    daneben = {l: 0.0 for l in LINIEN}
    for _, r in g.iterrows():
        for l in _linien_von(r.get("Linie")):
            gehalten[l] += float(r[SPALTE_GEHALTEN])
            daneben[l] += float(r[SPALTE_DANEBEN])

    zeilen = []
    for l in LINIEN:
        fuer = float(cf.get(l, 0))
        gegen = (gegentore[l] + gehalten[l] + float(geblockt.get(l, 0)) + daneben[l])
        if fuer + gegen <= 0:
            continue
        zeilen.append({"Linie_Label": f"Linie {l}", "CF": fuer, "CA": gegen,
                       "Gegentore": gegentore[l], "gehalten": gehalten[l],
                       "geblockt": float(geblockt.get(l, 0)), "daneben": daneben[l],
                       "CF%": 100 * fuer / (fuer + gegen)})

    team_cf = float(feld[SPALTE_SCHUESSE].sum())
    # fuers Team alle Paraden, nicht nur die einer Linie zugeordneten
    paraden = float(nur_torhueter(d)[SPALTE_BLOCK].sum())
    team_ca = (anzahl_gegentore + paraden + float(feld[SPALTE_BLOCK].sum())
               + float(g[SPALTE_DANEBEN].sum()))
    team = {"CF": team_cf, "CA": team_ca,
            "CF%": 100 * team_cf / (team_cf + team_ca) if team_cf + team_ca else 0}
    return pd.DataFrame(zeilen), team, len(ids)


def plot_corsi_team(df_in, tore_zeilen, spiele,
                    titel="Abschlussversuche"):
    """Je Spiel unsere Versuche gegen seine, mit dem Anteil darunter."""
    if spiele is None or spiele.empty:
        return None
    zeilen = []
    for mid, label in _spielfolge(spiele):
        _je_linie, team, anzahl = corsi_zahlen(
            df_in[df_in[MATCH_COL] == mid],
            None if tore_zeilen is None else tore_zeilen[tore_zeilen[MATCH_COL] == mid])
        if not anzahl:
            continue
        zeilen.append({"Spiel": label, **team})
    if not zeilen:
        return None
    daten = pd.DataFrame(zeilen)

    def zeile(r, seite, wert, anteil):
        return {"Spiel": r["Spiel"], "Seite": seite, "Versuche": r[wert],
                "Label": (f"{r[wert]:.0f}<br><span style='font-size:11px;"
                          f"color:{FARBEN['gedaempft']}'>{anteil:.0f} %</span>")}

    lang = pd.DataFrame(
        [zeile(r, "wir", "CF", r["CF%"]) for _, r in daten.iterrows()]
        + [zeile(r, "Gegner", "CA", 100 - r["CF%"]) for _, r in daten.iterrows()])
    fig = px.bar(lang, x="Spiel", y="Versuche", color="Seite", barmode="group",
                 title=titel, text="Label",
                 category_orders={"Spiel": list(daten["Spiel"]),
                                  "Seite": ["wir", "Gegner"]},
                 color_discrete_map={"wir": FARBEN["gut"],
                                     "Gegner": FARBEN["schlecht"]})
    fig.update_traces(textposition="outside", textangle=0, cliponaxis=False)
    fig.update_layout(legend_title_text="")
    fig = _style_plot(fig, textfix=False)
    _spiel_achse(fig, daten["Spiel"])
    fig.update_layout(bargap=0.3, bargroupgap=0.18,
                      legend=dict(orientation="h", yanchor="bottom", y=1.0,
                                  xanchor="right", x=1))
    hoch = float(lang["Versuche"].max())
    fig.update_yaxes(range=[0, hoch * 1.3], title_text=None)
    return fig



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
    skala = [[0.0, FARBEN["flaeche_hell"]], [0.35, "#1A501D"], [1.0, FARBEN["gut"]]]
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
                x=folge[si][1], y=beschriftung[zi], showarrow=False,
                text=f"<b>{text}</b>" if wert else text,
                font=dict(size=12,
                          color=_textfarbe(_skala_farbe(skala, wert / spanne))))
    fig = _style_plot(fig, textfix=False)
    _spiel_achse(fig, [l for _, l in folge])
    fig.update_traces(hovertemplate="%{y}<br>%{x}: <b>%{z}</b><extra></extra>")
    fig.update_layout(coloraxis_showscale=False, height=max(340, 34 * len(namen) + 110))
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
    for _, spiel in chronologisch(spiele).iterrows():
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
                "Label": (f"{r[schuss_sp]:.0f}<br><span style='font-size:11px;"
                          f"color:{FARBEN['gedaempft']}'>{r[tor_sp]:.0f} Tore</span>")}

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
    _spiel_achse(fig, daten["Spiel"])
    # und etwas Abstand zwischen den beiden Balken eines Spiels, sonst
    # kleben "2 Tore" und "7 Tore" aneinander
    fig.update_layout(bargap=0.3, bargroupgap=0.18,
                      legend=dict(orientation="h", yanchor="bottom", y=1.0,
                                  xanchor="right", x=1))
    hoch = float(lang["Torschüsse"].max())
    fig.update_yaxes(range=[0, hoch * 1.4], title_text=None)
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
#   Ballverlust      spiegelbildlich zur Balleroberung                  = -0.07
#                    Streng gerechnet waere es -0.08, weil der Gegner
#                    etwas besser verwertet als wir (31.9 % zu 28.7 %);
#                    die Symmetrie ist den Unterschied nicht wert.
# Unveraendert bei Doms Werten, weil dort unsere Zahlen passen: Assist 0.70
# (0.71 Assists je Tor bei uns, 0.67 in der NHL), Plus/Minus +-0.15 (der Term
# wiegt bei uns 61 % des Tor-Terms, in der NHL 74 %) und Strafe -0.15 (unsere
# Boxplay-Quote ist aus 3 Strafen in 6 Spielen nicht zu schaetzen).
# Das Bully (+-0.01 bei Dom) bleibt auf Wunsch des Trainers draussen.
GAME_SCORE_GEWICHTE = {
    "T": 0.75, "A": 0.70, "Schüsse aufs Tor": 0.21, SPALTE_BLOCK: 0.16,
    SPALTE_BALLEROBERUNG: 0.07, SPALTE_BALLVERLUST: -0.07, "Strafen": -0.15,
    "Plus": 0.15, "Minus": -0.15,
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


# Wie die Grafik den Game Score zerlegt: (Anzeige, Spalten, Farbe), in der
# Reihenfolge des Stapels. Nur Plus und Minus stehen als eine Bilanz da; alles
# andere einzeln, auch Balleroberungen und Ballverluste (so gewuenscht).
# Die Farben sind die acht Plaetze der geprueften Palette. Rechts der
# Nulllinie liegen sie in deren fester Folge, links folgt auf das Plus-Minus
# erst Violett, dann Rot - so sind direkte Nachbarn im Stapel auch bei
# Rot-Gruen-Schwaeche zu trennen (Gelb neben Rot fiele durch). Gruen liegt auf
# den Blocks, die nie abziehen, Rot auf den Strafen, die immer abziehen.
GAME_SCORE_TEILE = [
    ("Tore", ("T",), "#3987E5"),
    ("Assists", ("A",), "#D95926"),
    ("Schüsse aufs Tor", (SPALTE_SAT,), "#199E70"),
    ("Plus-Minus", ("Plus", "Minus"), "#C98500"),
    ("Balleroberungen", (SPALTE_BALLEROBERUNG,), "#D55181"),
    ("Blocks", (SPALTE_BLOCK,), "#0CA30C"),
    ("Ballverluste", (SPALTE_BALLVERLUST,), "#9085E9"),
    ("Strafen", ("Strafen",), "#E66767"),
]


def game_score_teile(df_in):
    """Der Game Score je Feldspieler, zerlegt nach GAME_SCORE_TEILE.

    Zurueck kommen zwei Tabellen mit einer Zeile je Spieler: der Beitrag je
    Teil (Anzahl mal Gewicht, aufsummiert) und die gezaehlten Aktionen je
    Rohspalte - die braucht der Hinweis am Balken fuer die Rechnung.
    """
    d = nur_feldspieler(df_in)
    spalten = [s for s in GAME_SCORE_GEWICHTE if s in d.columns]
    if d.empty or not spalten:
        return pd.DataFrame(), pd.DataFrame()
    werte = d[spalten].apply(pd.to_numeric, errors="coerce").fillna(0)
    anzahl = werte.groupby(d["Name"]).sum()
    teile = pd.DataFrame(index=anzahl.index)
    for anzeige, gruppe, _farbe in GAME_SCORE_TEILE:
        teile[anzeige] = sum((GAME_SCORE_GEWICHTE[s] * anzahl[s]
                              for s in gruppe if s in anzahl.columns),
                             pd.Series(0.0, index=anzahl.index))
    return teile, anzahl


def _gewicht_text(gruppe):
    """Das Gewicht eines Teils fuer die Legende: '+0.75', bei einer Bilanz
    mit gleichen Gewichten nach beiden Seiten '±0.15'."""
    gewichte = [GAME_SCORE_GEWICHTE[s] for s in gruppe]
    if len(gewichte) == 2 and gewichte[0] == -gewichte[1]:
        return "±" + _zf(abs(gewichte[0]), 2)
    return " / ".join(_zf(g, 2, vorzeichen=True) for g in gewichte)


def gamescore_grafik(df_in, mit_schnitt=True):
    """Game Score je Spieler als gestapelter Balken - woraus die Zahl besteht.

    Rechts der Nulllinie steht, was die Zahl hebt, links, was sie senkt; die
    Summe steht als Zahl dahinter, bei mehreren Spielen mit dem Schnitt pro
    Spiel. Alle Balken teilen sich einen Massstab. In der Legende steht hinter
    jedem Teil sein Gewicht je Aktion, am Balken (Mauszeiger) die Rechnung.
    """
    tabelle = game_score(df_in)
    if tabelle.empty or float(tabelle["GameScore"].abs().max()) == 0:
        return None
    teile, anzahl = game_score_teile(df_in)
    if teile.empty:
        return None
    plus = teile.clip(lower=0).sum(axis=1)
    minus = (-teile.clip(upper=0)).sum(axis=1)
    voll = float(plus.max() + minus.max()) or 1.0
    null = 100 * float(minus.max()) / voll
    zeilen = []
    for _, r in tabelle.iterrows():
        name = r["Name"]
        if name not in teile.index:
            continue
        rechts, links = [], []
        for anzeige, gruppe, farbe in GAME_SCORE_TEILE:
            wert = float(teile.at[name, anzeige])
            if round(wert, 2) == 0:
                continue
            rechnung = ", ".join(
                f"{_zahl(float(anzahl.at[name, s]))} × "
                f"{_zf(GAME_SCORE_GEWICHTE[s], 2, vorzeichen=True)}"
                for s in gruppe if s in anzahl.columns)
            tipp = f"{anzeige}: {rechnung} = {_zf(wert, 2, vorzeichen=True)}"
            # die Zahl nur, wo sie in den Teil passt
            zahl = _zf(wert, 1) if abs(wert) / voll >= 0.045 else ""
            # mal 1000: flex-Werte, die zusammen unter 1 bleiben, fuellen den
            # Balken nur zu diesem Bruchteil - bei einem einzelnen Spiel
            # waeren die Teile zu kurz
            (rechts if wert > 0 else links).append(
                f"<span style='flex:{1000 * abs(wert):.1f} 1 0;background:{farbe};"
                f"color:{_auf_farbe(farbe)}' title='{_e(tipp)}'>{zahl}</span>")
        breite_r = 100 * float(plus[name]) / voll
        breite_l = 100 * float(minus[name]) / voll
        balken = ""
        if links:
            # von der Nulllinie nach aussen gestapelt: der erste Teil liegt innen
            balken += (f"<div class='gs-t neg' style='left:{null - breite_l:.2f}%;"
                       f"width:{breite_l:.2f}%'>{''.join(reversed(links))}</div>")
        if rechts:
            balken += (f"<div class='gs-t pos' style='left:{null:.2f}%;"
                       f"width:{breite_r:.2f}%'>{''.join(rechts)}</div>")
        schnitt = f"ø {r['pro Spiel']:.2f}" if mit_schnitt else ""
        zeilen.append(
            f"<div class='bl-n' title='{_e(name)}'>{_e(name)}</div>"
            f"<div class='gs-s'>{balken}</div>"
            f"<div class='bl-w'>{_zf(r['GameScore'], 1)}</div>"
            f"<div class='bl-z'>{schnitt}</div>")
    if not zeilen:
        return None
    # in der Legende nur, was in dieser Auswahl vorkommt
    legende = "".join(
        f"<span><i style='background:{farbe}'></i>{_e(anzeige)}"
        f"<b>{_gewicht_text(gruppe)}</b></span>"
        for anzeige, gruppe, farbe in GAME_SCORE_TEILE
        if float(teile[anzeige].abs().max()) > 0)
    return Html(f"<div class='leg'>{legende}</div>"
                f"<div class='gs' style='--null:{null:.2f}%'>{''.join(zeilen)}</div>")


# ---------------------------
# Spielerkarte: ein Spieler gegen den Rest der Mannschaft
# ---------------------------
# Je Kennzahl steht der echte Wert da - die Summe der Auswahl oder die Quote
# - und der Balken reicht so weit, wie dieser Wert im Verhaeltnis zum besten
# der Mannschaft ist: wer halb so viele Tore hat wie der Beste, steht in der
# Mitte der Spur. Summen bevorzugen, wer oefter gespielt hat; die Einsaetze
# stehen im selben Reiter in der Rangliste und in der Karte Einsaetze.
# Zuoberst steht der Game Score - die eine Zahl, die alle anderen
# zusammenfasst (KARTE_GAME_SCORE).
#
# wenig_gut dreht nur die Rangfolge um (bei Ballverlusten und Strafen ist der
# Kleinste der Beste). Der Balken bleibt die Zahl selbst - eine Spur, auf der
# 2 Ballverluste weiter rechts stehen als 8, liest niemand richtig. Dafuer
# sind diese Zeilen grau statt blau.
# (Anzeige, Zaehler, Nenner oder None fuer eine Summe, wenig_gut)
KARTE_KENNZAHLEN = [
    ("Tore", "T", None, False),
    ("Assists", "A", None, False),
    ("Punkte", "Punkte", None, False),
    ("Plus-Minus", "PlusMinus", None, False),
    ("Schüsse", SPALTE_SCHUESSE, None, False),
    ("Schüsse aufs Tor", SPALTE_SAT, SPALTE_SCHUESSE, False),
    ("Torquote", "T", SPALTE_SAT, False),
    ("Bullyquote", "Bully-Plus", "Bully-Gesamt", False),
    ("Blocks", SPALTE_BLOCK, None, False),
    ("Balleroberungen", SPALTE_BALLEROBERUNG, None, False),
    ("Ballverluste", SPALTE_BALLVERLUST, None, True),
    ("Strafen", "Strafen", None, True),
]

KARTE_GAME_SCORE = "Game Score"

# Unter drei Vergleichsspielern ist ein Rang nur noch eine umstaendliche
# Art, "erster von zwei" zu sagen.
MIN_VERGLEICH = 3


def spieler_kennzahlen(df_in):
    """Je Feldspieler eine Zeile mit allen Kennzahlen der Spielerkarte:
    Summen der Auswahl und Quoten in Prozent.

    Nur Stammspieler: wer zwei Einsaetze hat, verzerrt mit einem
    Gluecksspiel jede Quote, an der sich die anderen messen.
    """
    d = nur_stammspieler(nur_feldspieler(df_in))
    if d.empty or "Name" not in d.columns:
        return pd.DataFrame()
    _, einsaetze = _einsaetze(d)
    werte = {}
    for anzeige, zaehler, nenner, _wenig_gut in KARTE_KENNZAHLEN:
        if zaehler not in d.columns:
            continue
        oben = d.groupby("Name")[zaehler].sum()
        if nenner is None:
            werte[anzeige] = oben.astype(float)
        elif nenner in d.columns:
            unten = d.groupby("Name")[nenner].sum()
            werte[anzeige] = 100 * oben / unten.where(unten > 0)
    if not werte:
        return pd.DataFrame()
    tabelle = pd.DataFrame(werte)
    tabelle["Spiele"] = einsaetze.reindex(tabelle.index).fillna(0).astype(int)
    # der Game Score und sein Schnitt pro Spiel, aus derselben Rechnung wie
    # in der Grafik weiter oben
    gs = game_score(d)
    if not gs.empty:
        gs = gs.set_index("Name")
        tabelle[KARTE_GAME_SCORE] = gs["GameScore"].reindex(tabelle.index)
        tabelle[KARTE_GAME_SCORE + " pro Spiel"] = gs["pro Spiel"].reindex(tabelle.index)
    return tabelle


def spielerkarte_zeilen(df_in, name):
    """Die Zeilen der Spielerkarte: je Kennzahl der eigene Wert, seine Lage
    auf der Spur, der Rang und der beste Wert der Mannschaft.

    Die Spur reicht von null bis zum hoechsten Wert der Mannschaft. Nur beim
    Plus-Minus und beim Game Score gibt es Werte unter null - dort beginnt
    sie beim tiefsten, und eine Marke zeigt, wo null liegt.
    """
    tabelle = spieler_kennzahlen(df_in)
    if tabelle.empty or name not in tabelle.index:
        return []
    feld = nur_feldspieler(df_in)
    eigen = feld[feld["Name"].astype(str) == str(name)]
    zeilen = []
    # zuoberst der Game Score, dann die einzelnen Kennzahlen
    for anzeige, zaehler, nenner, wenig_gut in (
            [(KARTE_GAME_SCORE, None, None, False)] + KARTE_KENNZAHLEN):
        if anzeige not in tabelle.columns:
            continue
        gueltig = tabelle[anzeige].dropna()
        if name not in gueltig.index or len(gueltig) < MIN_VERGLEICH:
            continue
        oben = max(0.0, float(gueltig.max()))
        unten = min(0.0, float(gueltig.min()))
        spanne = oben - unten
        if spanne <= 0:
            continue          # ueberall null: nicht erfasst oder nichts zu vergleichen
        wert = float(gueltig[name])
        # Rang 1 ist der Beste - bei Ballverlusten und Strafen also der mit
        # den wenigsten
        rang = int(gueltig.rank(ascending=wenig_gut, method="min")[name])
        best = float(gueltig.min() if wenig_gut else gueltig.max())
        if anzeige == KARTE_GAME_SCORE:
            wert_text, best_text = _zf(wert, 1), _zf(best, 1)
            schnitt = float(tabelle.at[name, KARTE_GAME_SCORE + " pro Spiel"])
            hinweis = f"ø {_zf(schnitt, 2)} pro Spiel"
        elif nenner is None:
            bilanz = zaehler == "PlusMinus"
            wert_text = _zf(wert, 0, vorzeichen=bilanz)
            best_text = _zf(best, 0, vorzeichen=bilanz)
            # kein Text unter dem Namen: dass hier wenig gut ist, zeigen der
            # graue Balken und der Rang
            hinweis = ""
        else:
            wert_text, best_text = f"{wert:.0f} %", f"{best:.0f} %"
            hinweis = (f"{_zahl(float(eigen[zaehler].sum()))} von "
                       f"{_zahl(float(eigen[nenner].sum()))}")
        zeilen.append(dict(
            name=anzeige, hinweis=hinweis, lage=(wert - unten) / spanne,
            null=-unten / spanne, wert=wert_text,
            rang=f"Rang {rang} von {len(gueltig)}",
            best=f"Bestwert {best_text}", wenig=wenig_gut))
    return zeilen


def _spiel_achse(fig, labels):
    """Spielnamen zweizeilig und waagrecht: oben das Datum, darunter der
    Gegner. Wird es eng (Handy, viele Spiele), dreht Plotly sie von selbst."""
    labels = list(dict.fromkeys(str(l) for l in labels))
    fig.update_xaxes(tickmode="array", tickvals=labels,
                     ticktext=[l.replace(" ", "<br>", 1) for l in labels],
                     tickangle=None)
    return fig


def plot_spieler_verlauf(df_in, name, spiele=None):
    """Game Score des Spielers Spiel fuer Spiel - der Formverlauf.

    Dieselbe Rechnung wie in der Mannschaftsuebersicht, nur fuer einen
    einzigen Spieler und nicht zusammengezaehlt. Daran sieht man, ob eine
    gute Saisonzahl aus einem Ausreisser stammt oder aus Bestaendigkeit.
    """
    d = nur_feldspieler(df_in)
    d = d[d["Name"].astype(str) == str(name)]
    if d.empty:
        return None
    if "Gespielt" in d.columns:
        d = d[d["Gespielt"].astype(str).str.strip() == "Ja"]
    if d.empty:
        return None
    punkte = sum(gewicht * pd.to_numeric(d[spalte], errors="coerce").fillna(0)
                 for spalte, gewicht in GAME_SCORE_GEWICHTE.items()
                 if spalte in d.columns)
    d = d.assign(GameScore=punkte)
    je_spiel = d.groupby(MATCH_COL)["GameScore"].sum()
    if je_spiel.empty:
        return None
    namen = dict(_spielfolge(spiele)) if spiele is not None else {}
    folge = [mid for mid, _ in _spielfolge(spiele)] if spiele is not None \
        else list(je_spiel.index)
    reihen = [(namen.get(mid, f"Spiel {mid}"), float(je_spiel[mid]))
              for mid in folge if mid in je_spiel.index]
    if not reihen:
        return None
    daten = pd.DataFrame(reihen, columns=["Spiel", "GameScore"])
    schnitt = float(daten["GameScore"].mean())
    # An jedem Punkt steht sein Wert (so gewuenscht) - bei einer Handvoll
    # Spielen ist dafuer Platz.
    daten["Label"] = [f"{v:.1f}" for v in daten["GameScore"]]
    r, g, b = (int(c * 255) for c in _rgb(FARBEN["balken"]))
    fig = px.line(daten, x="Spiel", y="GameScore", text="Label", markers=True,
                  title=f"Form über die Saison — {name}")
    fig.update_traces(
        line=dict(color=FARBEN["balken"], width=2),
        marker=dict(size=9, color=FARBEN["balken"],
                    line=dict(color=FARBEN["flaeche"], width=2)),
        fill="tozeroy", fillcolor=f"rgba({r},{g},{b},0.10)",
        textposition="top center", textfont=dict(color=FARBEN["text"], size=12),
        cliponaxis=False, showlegend=False,
        hovertemplate="%{x}<br><b>%{y:.1f}</b><extra></extra>")
    fig = _style_plot(fig, tickangle=0, textfix=False)
    _spiel_achse(fig, daten["Spiel"])
    # Die eigene Mittellinie, nicht die der Mannschaft: die Frage ist, an
    # welchen Tagen er ueber seinem eigenen Schnitt war.
    fig.add_hline(y=schnitt, line_width=1, line_dash="dot",
                  line_color=FARBEN["gedaempft"],
                  annotation_text=f"sein Schnitt {schnitt:.1f}",
                  annotation_font_color=FARBEN["gedaempft"],
                  annotation_font_size=11,
                  annotation_position="top left")
    hoch = float(daten["GameScore"].max())
    tief = min(0.0, float(daten["GameScore"].min()))
    fig.update_yaxes(range=[tief - 0.4, hoch + max(0.9, hoch * 0.3)],
                     title_text=None)
    fig.update_layout(height=320)
    return fig


def zeige_spielerkarte(df_in, spiele=None, tore_zeilen=None, spiel_namen=None):
    """Ein Spieler fuer sich: Auswahl, Vergleich mit der Mannschaft,
    Formverlauf und die Videos seiner Tore und Assists."""
    tabelle = spieler_kennzahlen(df_in)
    if tabelle.empty:
        st.markdown("<div class='chart-leer'>Für eine Spielerkarte braucht es "
                    "mehrere Spiele mit erfassten Werten.</div>",
                    unsafe_allow_html=True)
        return
    namen = sorted(tabelle.index)
    if len(namen) < MIN_VERGLEICH:
        st.markdown(f"<div class='chart-leer'>Erst ab {MIN_VERGLEICH} "
                    "Stammspielern lässt sich sinnvoll vergleichen.</div>",
                    unsafe_allow_html=True)
        return
    links, _rest = st.columns([1, 2])
    with links:
        # der Abschnitt heisst schon "Pro Spieler" - das Feld braucht keine
        # eigene Ueberschrift
        name = st.selectbox("Spieler", namen, key="karte_spieler",
                            label_visibility="collapsed")

    _karte(f"{name} im Vergleich mit der Mannschaft\n"
           "Der Balken zeigt den Saisonwert im Verhältnis zum besten Wert "
           "der Mannschaft.",
           vergleichsliste(spielerkarte_zeilen(df_in, name)))

    verlauf = plot_spieler_verlauf(df_in, name, spiele)
    if verlauf is not None:
        v_titel, v_fig, _unused = _eintrag(
            verlauf, unter="Game Score je Spiel · die gepunktete Linie ist "
                           "sein eigener Schnitt")
        _karte(v_titel, v_fig)

    if tore_zeilen is not None:
        karte_videos(tore_zeilen, name, spiel_namen or {})


def _gegner_spiele(alle_spiele):
    """Alle Spiele mit den Hilfsspalten der Gegnerbilanz, in zeitlicher Folge.

    Aus aelteren Saisons fehlt das Datum - dort ordnet die Match_Id.
    """
    d = alle_spiele.copy()
    d["_gegner"] = d["Gegner"].astype(str).str.strip()
    d["_tore"] = pd.to_numeric(d["Tore Wygorazzi"], errors="coerce").fillna(0)
    d["_gegen"] = pd.to_numeric(d["Tore Gegner"], errors="coerce").fillna(0)
    d["_sieg"], d["_remis"] = _ja("Sieg", d), _ja("Unentschieden", d)
    d["_nieder"] = _ja("Niederlage", d)
    d["_jahr"] = d[SEASON_COL].map(saison_sort_key)
    folge = ["_jahr"] + [s for s in ("Datum_parsed", MATCH_COL) if s in d.columns]
    return d.sort_values(folge, na_position="first", kind="stable")


def bilanz_gegner(alle_spiele):
    """Bilanz gegen jeden Gegner ueber alle Saisons zusammen - je Gegner eine
    Zeile fuer die Tabelle: Spiele, Siege, Unentschieden, Niederlagen, Tore,
    Tordifferenz, der Verlauf als Kaestchen und die Saison der letzten
    Begegnung."""
    if alle_spiele is None or alle_spiele.empty or "Gegner" not in alle_spiele.columns:
        return []
    zeilen = []
    for gegner, g in _gegner_spiele(alle_spiele).groupby("_gegner", sort=False):
        tore, gegentore = int(g["_tore"].sum()), int(g["_gegen"].sum())
        kaestchen = []
        for _, r in g.iterrows():
            ausgang = "s" if r["_sieg"] else "n" if r["_nieder"] else "u"
            tipp = (f"{r[SEASON_COL]} · {str(r.get('Format', '')).strip()} · "
                    f"{int(r['_tore'])}:{int(r['_gegen'])}")
            kaestchen.append(f"<i class='{ausgang}' title='{_e(tipp)}'></i>")
        zeilen.append({
            "Name": gegner, "Sp": len(g), "S": int(g["_sieg"].sum()),
            "U": int(g["_remis"].sum()), "N": int(g["_nieder"].sum()),
            "Tore": gut_schlecht(tore, gegentore, voll=True),
            "Differenz": tore - gegentore,
            "Verlauf": Html(f"<span class='vl'>{''.join(kaestchen)}</span>"),
            "Zuletzt": str(g.iloc[-1][SEASON_COL]),
        })
    return zeilen


def gegner_kacheln(g, andere):
    """Die Bilanz gegen einen Gegner als Kacheln. Unter den Toren steht der
    Schnitt pro Spiel und daneben derselbe Schnitt gegen alle anderen Gegner -
    daran sieht man, ob wir gegen diesen besser oder schlechter aussehen als
    sonst."""
    spiele = len(g)
    tore, gegentore = int(g["_tore"].sum()), int(g["_gegen"].sum())
    erste, letzte = str(g.iloc[0][SEASON_COL]), str(g.iloc[-1][SEASON_COL])

    def schnitt(spalte):
        sonst = (f" · gegen alle anderen ø {andere[spalte].mean():.2f}"
                 if len(andere) else "")
        return f"ø {g[spalte].mean():.2f} pro Spiel{sonst}"

    return kacheln([
        dict(bez="Spiele", wert=f"{spiele}",
             text=erste if erste == letzte else f"{erste} bis {letzte}"),
        dict(bez="S – U – N", wert=f"{int(g['_sieg'].sum())} – "
                                   f"{int(g['_remis'].sum())} – {int(g['_nieder'].sum())}"),
        dict(bez="Tore", wert=f"{tore}", text=schnitt("_tore")),
        dict(bez="Gegentore", wert=f"{gegentore}", text=schnitt("_gegen")),
        dict(bez="Tordifferenz", wert=_zf(tore - gegentore, 0, vorzeichen=True),
             text=f"ø {_zf((tore - gegentore) / spiele, 2, vorzeichen=True)} pro Spiel"),
    ], klein=True)


def _liga_text(wert):
    """3.0 -> '3. Liga'; leer, wenn nichts eingetragen ist."""
    liga = pd.to_numeric(wert, errors="coerce")
    return "" if pd.isna(liga) else f"{int(liga)}. Liga"


AUSGANG_WORT = {"s": "Sieg", "u": "Unentschieden", "n": "Niederlage"}


def gegner_spieltabelle(g):
    """Die Spiele gegen einen Gegner als Liste, das juengste zuoberst: wann,
    in welchem Wettbewerb, in welcher Liga beide spielten, und wie es ausging."""
    zeilen = []
    for _, r in g.iloc[::-1].iterrows():
        ausgang = "s" if r["_sieg"] else "n" if r["_nieder"] else "u"
        tag = str(r.get("Datum_label", ""))
        zeilen.append({
            "Name": "–" if not tag or tag.startswith("ohne") else tag,
            "Saison": str(r[SEASON_COL]),
            "Wettbewerb": str(r.get("Format", "")).strip(),
            "Wir": _liga_text(r.get("Liga Wygorazzi")),
            "Gegner": _liga_text(r.get("Liga Gegner")),
            "Resultat": gut_schlecht(int(r["_tore"]), int(r["_gegen"]), voll=True),
            "Ausgang": Html(f"<span class='vl'><i class='{ausgang}'></i></span> "
                            f"{AUSGANG_WORT[ausgang]}"),
        })
    spalten = [
        dict(key="Saison", kopf="Saison", art="text"),
        dict(key="Wettbewerb", kopf="Wettbewerb", art="text"),
        dict(key="Wir", kopf="Unsere Liga", art="text"),
        dict(key="Gegner", kopf="Liga Gegner", art="text"),
        dict(key="Resultat", kopf="Resultat", art="text",
             hilfe="Unsere Tore : Gegentore"),
        dict(key="Ausgang", kopf="Ausgang", art="text"),
    ]
    return rangtabelle(zeilen, spalten, erste="Datum", rang=False, balken=False,
                       viel=True)


def gegner_torschuetzen(g):
    """Wer gegen diesen Gegner trifft und auflegt - aus den Spielerdaten, die
    es erst fuer die juengeren Saisons gibt.

    Zurueck: (Liste oder None, Anzahl der Spiele mit Spielerdaten).
    """
    ids = set(g[MATCH_COL].dropna())
    d = df[df[MATCH_COL].isin(ids)] if MATCH_COL in df.columns else df.iloc[0:0]
    if d.empty or "Name" not in d.columns:
        return None, 0
    d = preprocess_player_stats(d.copy())
    erfasst = int(d[MATCH_COL].nunique())
    summe = d.groupby("Name")[["T", "A"]].sum()
    summe["P"] = summe["T"] + summe["A"]
    summe = summe[summe["P"] > 0].reset_index().sort_values(
        ["P", "T", "Name"], ascending=[False, False, True])
    if summe.empty:
        return None, erfasst
    zeilen = [(r["Name"], r["P"],
               f"{r['T']:.0f} {'Tor' if r['T'] == 1 else 'Tore'} · "
               f"{r['A']:.0f} {'Assist' if r['A'] == 1 else 'Assists'}")
              for _, r in summe.iterrows()]
    return balkenliste(zeilen), erfasst


# Anzeige im Schalter -> Spalte der Tabelle
BILANZ_SORTIERUNG = {"Spiele": "Sp", "Siege": "S", "Niederlagen": "N",
                     "Tordifferenz": "Differenz"}


def _gegner_detail(alle, gegner):
    """Alles zu den Spielen gegen einen Gegner: Kennzahlen, darunter die
    Liste der Spiele - und, wo es Spielerdaten gibt, zur Wahl die
    Torschuetzen. alle sind die Spiele aus _gegner_spiele()."""
    g = alle[alle["_gegner"] == str(gegner)]
    if g.empty:
        return
    st.markdown(f"<div class='abschnitt'>Spiele gegen {_e(gegner)}</div>"
                + gegner_kacheln(g, alle[alle["_gegner"] != str(gegner)]),
                unsafe_allow_html=True)
    schuetzen, erfasst = gegner_torschuetzen(g)
    # Wer trifft, laesst sich nur zeigen, wo es Spielerdaten gibt. Ohne sie
    # bleibt die Liste - ein Schalter mit einer einzigen Wahl waere Ballast.
    ansicht = "Spiele"
    if schuetzen is not None:
        ansicht = auswahl_schalter("Ansicht", ["Spiele", "Torschützen"],
                                   "gegner_ansicht", "Spiele")
    if ansicht == "Torschützen":
        st.markdown(
            "<div class='chart-unter'>Tore und Assists gegen diesen Gegner · "
            f"erfasst in {erfasst} von {len(g)} Spielen</div>" + schuetzen,
            unsafe_allow_html=True)
    else:
        st.markdown(gegner_spieltabelle(g), unsafe_allow_html=True)


@st.fragment
def zeige_gegnerbilanz(alle_spiele):
    """Bilanz gegen jeden Gegner: die Tabelle ueber alle Saisons, sortierbar,
    darunter auf Wunsch alles zu den Spielen gegen einen Gegner.

    Als Fragment: Umsortieren und Auswaehlen laden nur diese Karte neu.
    """
    zeilen = bilanz_gegner(alle_spiele)
    if not zeilen:
        return
    spalten = [
        dict(key="Sp", kopf="Sp", hilfe="Spiele"),
        dict(key="S", kopf="S", hilfe="Siege"),
        dict(key="U", kopf="U", hilfe="Unentschieden"),
        dict(key="N", kopf="N", hilfe="Niederlagen"),
        dict(key="Tore", kopf="Tore", art="text", hilfe="Unsere Tore : Gegentore"),
        dict(key="Differenz", kopf="+/−", art="bilanz", hilfe="Tordifferenz"),
        dict(key="Verlauf", kopf="Verlauf", art="text",
             hilfe="Ein Kästchen je Spiel, das jüngste rechts"),
        dict(key="Zuletzt", kopf="Zuletzt", art="text",
             hilfe="Saison der letzten Begegnung"),
    ]
    with st.container(border=True):
        st.markdown("<div class='chart-titel'>Bilanz gegen jeden Gegner</div>"
                    "<div class='chart-unter'>Alle Saisons zusammengezählt</div>",
                    unsafe_allow_html=True)
        sortiert = auswahl_schalter("Sortiert nach", list(BILANZ_SORTIERUNG),
                                    "gegner_sortierung", "Spiele")
        schluessel = BILANZ_SORTIERUNG[sortiert]
        # Gleichstand: erst die Tordifferenz, dann der Name
        zeilen.sort(key=lambda z: (-z[schluessel], -z["Differenz"], z["Name"]))
        # immer alle Gegner (so gewuenscht), nicht nur die haeufigsten
        st.markdown(
            rangtabelle(zeilen, spalten, aktiv=schluessel, erste="Gegner",
                        rang=False, balken=False, viel=True)
            + "<div class='rl-leg'><span><b>Sp</b>Spiele</span> · "
              "<span><b>S</b>Siege</span> · <span><b>U</b>Unentschieden</span> · "
              "<span><b>N</b>Niederlagen</span> · <span><b>+/−</b>Tordifferenz</span>"
              " · <span><b>Verlauf</b>ein Kästchen je Spiel, das jüngste rechts</span>"
              "</div>", unsafe_allow_html=True)
        gegner = st.selectbox(
            "Spiele gegen einen Gegner ansehen", sorted(z["Name"] for z in zeilen),
            index=None, placeholder="Gegner wählen", key="gegner_detail")
        if gegner:
            _gegner_detail(_gegner_spiele(alle_spiele), gegner)


def tab_team(df_in, gegentore=None, situationen=None, spiele=None, tore_zeilen=None,
             paar_zeilen=None, vergleich=None):
    # Zuerst die Kennzahlen als Kacheln, danach die Verlaufsanalysen.
    oben = team_kacheln(df_in, situationen, vergleich)
    if oben is not None:
        st.markdown(oben, unsafe_allow_html=True)
    # darunter im selben Stil, was aus den Schuessen auf unser Tor wurde
    abwehr = abwehr_kacheln(df_in, gegentore)
    if abwehr is not None:
        st.markdown(abwehr, unsafe_allow_html=True)
    eintraege = [
        # Die Paare lohnen sich erst ueber eine ganze Saison - bei einem
        # einzelnen Spiel waeren es ein paar Zeilen mit lauter Einsern.
        _eintrag_html("Tore je Paar", paarliste(paar_zeilen),
                      unter="Einer legt auf, der andere trifft – die Farbe "
                            "zeigt, wer wie oft getroffen hat.", breit=True),
    ]
    torzeiten = plot_tore_minuten(tore_zeilen)
    if torzeiten is not None:
        eintraege.append(_eintrag(torzeiten, breit=True,
                                  unter="Tore und Gegentore je Abschnitt von "
                                        f"{TOR_FENSTER} Minuten"))
    # erst woher unsere Tore kommen, direkt daneben die Gegentore
    for art in ("Tor", "Gegentor"):
        eintraege.append(_eintrag_html(
            f"{ART_KURZ[art]} nach Ursache", kategorienliste(tore_zeilen, art=art)))
    eintraege.append(_eintrag_html(
        "Spielverlauf", spielstandliste(tore_zeilen, spiele),
        unter="Spielzeit in Führung, im Gleichstand und im Rückstand",
        breit=True))
    # Reaktion, Torschuesse und Abschlussversuche - alles aus den Torzeiten
    # und Spielerzeilen. plot_spielverlauf (Tordifferenz-Kurve) ist
    # ausgehaengt (Wunsch vom 2026-10-31); die Funktion bleibt stehen.
    for fig, unter in (
            # der Titel sagt schon alles - keine Unterzeile
            (plot_reaktion(paar_zeilen), None),
            (plot_torschuesse(df_in, spiele),
             "Schüsse aufs Tor je Spiel, darunter die Tore daraus"),
            (plot_corsi_team(df_in, tore_zeilen, spiele),
             "Alle Abschlussversuche je Spiel, darunter der Anteil")):
        if fig is not None:
            eintraege.append(_eintrag(fig, breit=True, unter=unter))
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
    """Lokale Datei bevorzugen, sonst einbetten. Der Clip startet von selbst:
    wer auf Abspielen drueckt, will nicht ein zweites Mal druecken muessen."""
    pfad = _clip_pfad(zeile)
    if pfad:
        st.video(pfad, autoplay=True)
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


def _feld(zeile, spalte):
    """Text eines Feldes - leer statt 'nan', wenn nichts eingetragen ist."""
    inhalt = str(zeile.get(spalte) or "").strip()
    return "" if inhalt.lower() == "nan" else inhalt


def _zeit_text(zeile, mit_halbzeit=True):
    """Spieluhr, davor die Halbzeit - bei Toren aus einer Videoluecke fehlt
    die Zeit. Im Spielverlauf steht die Halbzeit im Kopf der Karte, dort
    genuegt die Uhr."""
    zeit = _feld(zeile, "Zeit") or "—"
    return f"HZ{int(zeile['Halbzeit'])} · {zeit}" if mit_halbzeit else zeit


def _torschuetze(zeile):
    """Name des Schuetzen - bei Gegentoren ist das Feld leer bzw. NaN."""
    return _feld(zeile, "Spieler") or "Gegentor"


def _linie_html(zeile):
    """Die Linie, die beim Tor auf dem Feld stand: ein Punkt in der
    Linienfarbe und der Name daneben. Eine gemischte Formation ('1+3')
    bekommt zwei Punkte."""
    linien = _linien_von(zeile.get("Linie"))
    if not linien:
        return ""
    punkte = "".join(
        "<i style='background:{}'></i>".format(
            LINIEN_FARBEN.get(f"Linie {l}", FARBEN["neutral"])) for l in linien)
    return f"{punkte}Linie {'+'.join(linien)}"


def _mit_html(wort, name):
    """'Assist C.Loosli' - das Wort grau, der Name eine Spur heller."""
    return f"{_e(wort)} <b>{_e(name)}</b>" if name else ""


def tor_inhalt(haupt, neben="", zeit="", mit="", wie="", linie="", stand=""):
    """Das Innere einer Torzeile als Raster: der Haupttext mit grauem
    Nebentext, dahinter Zeit, Mitspieler, Entstehung und Linie, rechts der
    Spielstand nach dem Tor. mit und linie sind fertiges HTML, alles andere
    wird maskiert.
    """
    klein = f"<small>{_e(neben)}</small>" if neben else ""
    return (f"<span class='tz-h'><b>{_e(haupt)}</b>{klein}</span>"
            f"<span class='tz-u'><span class='tz-z'>{_e(zeit)}</span>"
            f"<span class='tz-m'>{mit}</span>"
            f"<span class='tz-w'>{_e(wie)}</span>"
            f"<span class='tz-l'>{linie}</span></span>"
            f"<span class='tz-s'>{_e(stand)}</span>")


def _saison_inhalt(zeile, spiel_namen, mit=""):
    """Torzeile der Listen ueber mehrere Spiele: vorne der Gegner mit dem
    Datum, dann Zeit, Mitspieler, Entstehung, Linie und Spielstand."""
    mid = zeile[MATCH_COL]
    datum, _, gegner = str(spiel_namen.get(mid, f"Spiel {mid}")).partition(" vs ")
    return tor_inhalt(haupt=gegner or datum, neben=datum if gegner else "",
                      zeit=_zeit_text(zeile), mit=mit,
                      wie=_feld(zeile, "Kategorie"), linie=_linie_html(zeile),
                      stand=_feld(zeile, "Stand"))


def _gruppen_kopf(titel, zusatz="", anzahl=None):
    """Kopf einer Gruppenkarte: links der Name, rechts leise der Zusatz.
    anzahl setzt eine Zahl gross direkt neben den Namen ("Tore 7")."""
    zahl = f"<i class='tg-n'>{_e(anzahl)}</i>" if anzahl is not None else ""
    return (f"<div class='tg-kopf'><b>{_e(titel)}{zahl}</b>"
            f"<span>{_e(zusatz)}</span></div>")


def _anzahl(n, einzahl, mehrzahl):
    return f"<span><b>{n}</b>{einzahl if n == 1 else mehrzahl}</span>"


def _tore_info(zeilen):
    """Die Zeile ueber der Liste: wie viele Tore, Gegentore und Clips."""
    ist_tor = zeilen["Art"].astype(str).str.strip() == "Tor"
    clips = sum(1 for _, r in zeilen.iterrows() if _hat_video(r))
    st.markdown(
        "<div class='tl-info'>"
        + _anzahl(int(ist_tor.sum()), "Tor", "Tore")
        + _anzahl(int((~ist_tor).sum()), "Gegentor", "Gegentore")
        + f"<span><b>{clips}</b>mit Video</span></div>", unsafe_allow_html=True)


def _abspielknopf(zeile, offen, schluessel, kennung, knopf):
    """Der runde Knopf zu einem Tor - Abspielen, oder Schliessen, solange das
    Video offen ist. False, wenn es zu dem Tor kein Video gibt: dann setzt
    die Zeile ihren eigenen Platzhalter."""
    if not _hat_video(zeile):
        return False
    st.button(":material/close:" if offen else ":material/play_arrow:", key=knopf,
              help="Video schliessen" if offen else "Video abspielen",
              on_click=_tor_waehlen, args=(schluessel, kennung))
    return True


def _clip_zeile(box, zeile, inhalt, schluessel, kennung, knopf):
    """Eine Torzeile mit Abspielknopf - das Video erscheint direkt darunter.

    box ist die Karte der Gruppe, inhalt das HTML aus tor_inhalt(). kennung
    unterscheidet die Zeilen einer Liste, knopf ist der Schluessel des Knopfs.
    """
    offen = st.session_state.get(schluessel) == kennung
    links, rechts = box.columns([12, 1], vertical_alignment="center")
    links.markdown(f"<div class='tz{' offen' if offen else ''}'>{inhalt}</div>",
                   unsafe_allow_html=True)
    with rechts:
        if not _abspielknopf(zeile, offen, schluessel, kennung, knopf):
            st.markdown("<div class='tz-ohne' title='Kein Video'>—</div>",
                        unsafe_allow_html=True)
    if offen:
        with box:
            _abspielen(zeile)


# ---------------------------
# Liveticker: ein Spiel als Zeitstrahl
# ---------------------------
def _ticker_spiele(zeilen, spiel_namen, spiele):
    """Die Spiele der Auswahl fuer den Ticker, das juengste zuerst:
    [dict(mid, datum, gegner, wir, sie)].

    Datum und Gegner kommen aus spiel_namen ('13.09.2026 vs Vallemaggia'),
    Reihenfolge und Resultat aus der Spieltabelle. Fehlt das Resultat dort,
    zaehlt der Stand nach dem letzten erfassten Tor.
    """
    folge = [mid for mid, _ in _spielfolge(spiele)]
    rang = {mid: i for i, mid in enumerate(folge)}
    ergebnis = {}
    if spiele is not None and not spiele.empty:
        for _, r in spiele.iterrows():
            wir = pd.to_numeric(r.get("Tore Wygorazzi"), errors="coerce")
            sie = pd.to_numeric(r.get("Tore Gegner"), errors="coerce")
            if pd.notna(wir) and pd.notna(sie):
                ergebnis[r[MATCH_COL]] = (int(wir), int(sie))
    aus = []
    for mid in sorted(zeilen[MATCH_COL].dropna().unique(),
                      key=lambda m: (rang.get(m, -1), m), reverse=True):
        datum, _, gegner = str(spiel_namen.get(mid, f"Spiel {mid}")).partition(" vs ")
        if mid in ergebnis:
            wir, sie = ergebnis[mid]
        else:
            letzter = zeilen[zeilen[MATCH_COL] == mid].sort_values("Nr").iloc[-1]
            wir, _, sie = (_feld(letzter, "Stand") or "0:0").partition(":")
        aus.append(dict(mid=mid, datum=datum if gegner else "",
                        gegner=gegner or datum, wir=wir, sie=sie))
    return aus


def ticker_inhalt(zeile):
    """Ein Tor im Ticker: oben Schuetze, Spielstand und Spieluhr, darunter
    klein Assist, Entstehung und Linie."""
    unten = [_mit_html("Assist", _feld(zeile, "Assist")),
             _e(_feld(zeile, "Kategorie"))]
    unten = "".join(f"<span>{teil}</span>" for teil in unten if teil)
    linie = _linie_html(zeile)
    if linie:
        unten += f"<span class='tz-l'>{linie}</span>"
    return (f"<div class='lt-z'><span class='lt-n'>{_e(_torschuetze(zeile))}</span>"
            f"<span class='lt-sm'><span class='lt-s'>{_e(_feld(zeile, 'Stand'))}</span>"
            f"<span class='lt-m'>{_e(_zeit_text(zeile, mit_halbzeit=False))}</span>"
            f"</span></div><div class='lt-u'>{unten}</div>")


def _ticker_zeile(box, zeile, schluessel, kennung, knopf):
    """Ein Tor auf dem Zeitstrahl: links, wenn wir getroffen haben, rechts
    beim Gegentor. In der Mitte sitzt der Abspielknopf als Knoten auf der
    Linie; das Video erscheint direkt darunter."""
    offen = st.session_state.get(schluessel) == kennung
    ist_tor = str(zeile.get("Art", "")).strip() == "Tor"
    klassen = "lt " + ("wir" if ist_tor else "sie") + (" offen" if offen else "")
    links, mitte, rechts = box.columns([10, 1, 10], vertical_alignment="center")
    (links if ist_tor else rechts).markdown(
        f"<div class='{klassen}'>{ticker_inhalt(zeile)}</div>",
        unsafe_allow_html=True)
    with mitte:
        if not _abspielknopf(zeile, offen, schluessel, kennung, knopf):
            st.markdown("<div class='lt-punkt' title='Kein Video'></div>",
                        unsafe_allow_html=True)
    if offen:
        with box:
            _abspielen(zeile)


def _ticker_marke(titel, zusatz="", lage=""):
    """Eine Marke auf der Linie: Halbzeit oder Schluss."""
    klein = f"<small>{_e(zusatz)}</small>" if zusatz else ""
    return (f"<div class='lt-pause {lage}'><span>{_e(titel)}</span>{klein}</div>")


def _ticker_karte(spiel, zeilen, schluessel, knopf):
    """Ein Spiel als Liveticker in einer Karte.

    Im Kopf stehen die beiden Mannschaften und das Resultat - links wir,
    rechts der Gegner, und so stehen darunter auch die Tore. spiel ist ein
    Eintrag aus _ticker_spiele(), zeilen sind die Tore dieses Spiels.
    """
    box = st.container()
    box.markdown(
        "<div class='tg-kopf spiel'><b>Wygorazzi</b>"
        f"<div class='lt-res'><strong>{_e(spiel['wir'])} : {_e(spiel['sie'])}</strong>"
        f"<small>{_e(spiel['datum'])}</small></div>"
        f"<b>{_e(spiel['gegner'])}</b></div>", unsafe_allow_html=True)
    # nach Nr: die ist chronologisch vergeben und auch ohne Zeit vorhanden
    stand = "0:0"
    erste = True
    for halbzeit, g in zeilen.sort_values("Nr").groupby("Halbzeit", sort=True,
                                                         dropna=False):
        titel = f"{int(halbzeit)}. Halbzeit" if pd.notna(halbzeit) else "Ohne Zeit"
        pause = (f"Pausenstand {stand}"
                 if pd.notna(halbzeit) and int(halbzeit) > 1 else "")
        box.markdown(_ticker_marke(titel, pause, "start" if erste else ""),
                     unsafe_allow_html=True)
        erste = False
        for _, r in g.iterrows():
            kennung = f"{int(r['Nr'])}_{r[MATCH_COL]}"
            _ticker_zeile(box, r, schluessel, kennung, f"{knopf}_{kennung}")
        stand = _feld(g.iloc[-1], "Stand") or stand
    box.markdown(_ticker_marke(f"Schluss {spiel['wir']}:{spiel['sie']}", lage="ende"),
                 unsafe_allow_html=True)


@st.fragment
def tab_tore(zeilen, spiel_namen=None, spiele=None):
    """Die Tore eines Spiels als Liveticker. Das Video erscheint direkt unter
    dem angeklickten Tor.

    Als Fragment: ein Klick laedt nur diese Liste neu statt der ganzen Seite.
    """
    if zeilen.empty:
        st.caption("Für dieses Spiel sind keine Tore erfasst.")
        return

    _tore_info(zeilen)
    for spiel in _ticker_spiele(zeilen, spiel_namen or {}, spiele):
        schluessel = f"tor_{_als_id(spiel['mid'])}"
        _ticker_karte(spiel, zeilen[zeilen[MATCH_COL] == spiel["mid"]],
                      schluessel, schluessel)


TORE_ANSICHTEN = ["Spieler", "Spiel"]


def _ansicht_gewechselt():
    """Beim Umschalten das offene Video schliessen - es stuende sonst in der
    anderen Ansicht an anderer Stelle offen und liefe von vorn. Ein zweiter
    Klick auf die aktive Ansicht wechselt nichts und laesst es in Ruhe."""
    if st.session_state.get("tore_ansicht") in TORE_ANSICHTEN:
        st.session_state["tor_saison"] = None


@st.fragment
def tab_tore_saison(zeilen, spiel_namen, spiele=None):
    """Alle Tore der Saison - nach Spieler (je Spieler eine Karte) oder nach
    Spiel (je Spiel ein Liveticker).

    Das Video erscheint direkt unter dem angeklickten Tor - auf dem Handy
    muesste man sonst nach jedem Klick wieder hochscrollen.
    """
    if zeilen.empty:
        st.caption("Für diese Saison sind keine Tore erfasst.")
        return

    ansicht = auswahl_schalter("Tore sortiert nach", TORE_ANSICHTEN, "tore_ansicht",
                               "Spieler", on_change=_ansicht_gewechselt)
    _tore_info(zeilen)
    schluessel = "tor_saison"

    if ansicht == "Spiel":
        for spiel in _ticker_spiele(zeilen, spiel_namen, spiele):
            _ticker_karte(spiel, zeilen[zeilen[MATCH_COL] == spiel["mid"]],
                          schluessel, "ticker")
        return

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

        # Kopf und Zeilen in einen gemeinsamen Container: das ist die Karte,
        # und nur darin kann der klebende Kopf wandern.
        gruppe_box = st.container()
        gruppe_box.markdown(_gruppen_kopf(name, zusatz), unsafe_allow_html=True)

        # Gegentore nach der Linie ordnen, die auf dem Feld stand
        sortier = (["Linie", MATCH_COL, "Nr"] if name == "Gegentore"
                   and "Linie" in g.columns else [MATCH_COL, "Nr"])
        for _, r in g.sort_values(sortier).iterrows():
            kennung = f"{int(r['Nr'])}_{r[MATCH_COL]}"
            _clip_zeile(
                gruppe_box, r,
                _saison_inhalt(r, spiel_namen,
                               mit=_mit_html("Assist", _feld(r, "Assist"))),
                schluessel, kennung, f"saison_{kennung}")


@st.fragment
def karte_videos(zeilen, name, spiel_namen):
    """Die Tore und Assists eines Spielers zum Anschauen - zuunterst in der
    Spielerkarte. Dieselben Zeilen und derselbe Player wie im Reiter Tore.

    Als Fragment: ein Klick laedt nur diese Liste neu statt der ganzen Seite.
    """
    eigene = zeilen[zeilen["Art"].astype(str).str.strip() == "Tor"]

    def von(spalte):
        if spalte not in eigene.columns:
            return eigene.iloc[0:0]
        return eigene[eigene[spalte].astype(str).str.strip() == str(name)]

    # (Ueberschrift, Zeilen, Spalte des Mitspielers, wie er heisst)
    gruppen = [("Tore", von("Spieler"), "Assist", "Assist"),
               ("Assists", von("Assist"), "Spieler", "Tor")]
    st.markdown("<div class='abschnitt'>Mit Video</div>",
                unsafe_allow_html=True)
    if all(g.empty for _, g, _, _ in gruppen):
        st.markdown(f"<div class='chart-leer'>Für {_e(name)} sind in dieser "
                    "Auswahl keine Tore oder Assists erfasst.</div>",
                    unsafe_allow_html=True)
        return

    schluessel = "tor_karte"
    for titel, g, mit_spalte, mit_wort in gruppen:
        if g.empty:
            continue
        box = st.container()
        # die Anzahl gross neben dem Wort - sie ist hier die Hauptsache
        box.markdown(_gruppen_kopf(titel, anzahl=len(g)), unsafe_allow_html=True)
        for _, r in g.sort_values([MATCH_COL, "Nr"]).iterrows():
            # der Name gehoert in die Kennung: sonst bliebe das Video offen,
            # wenn man zum Mitspieler wechselt, der dasselbe Tor vorbereitet hat
            kennung = f"{name}_{titel}_{int(r['Nr'])}_{r[MATCH_COL]}"
            _clip_zeile(
                box, r,
                _saison_inhalt(r, spiel_namen,
                               mit=_mit_html(mit_wort, _feld(r, mit_spalte))),
                schluessel, kennung, f"karte_{kennung}")


def render_tabs(df_in, gegentore=None, zeige_gespielt=False, team_extra=None,
                situationen=None, tore_zeilen=None, tore_saison=None, spiel_namen=None,
                spiele=None, alle_spiele=None, vergleich=None,
                mit_team=True, mit_linien=True):
    """Die Reiter der Auswertung. mit_team und mit_linien lassen die beiden
    Reiter weg (aeltere Saisons); Tore gibt es nur, wo Tore erfasst sind."""
    saison_modus = tore_saison is not None
    quelle = tore_saison if saison_modus else tore_zeilen   # auch fuer die Linienbilanz
    zeige_tore = quelle is not None and not quelle.empty
    # Die Spielerkarte vergleicht einen Spieler mit der Mannschaft - in einem
    # einzelnen Spiel waere dieser Vergleich eine Momentaufnahme aus einer
    # Handvoll Aktionen, darum erst ab mehreren Spielen.
    zeige_karte = df_in[MATCH_COL].nunique() > 1
    beschriftung = (["Spieler"] + (["Team"] if mit_team else [])
                    + (["Linien"] if mit_linien else [])
                    + (["Tore"] if zeige_tore else []))
    reiter = dict(zip(beschriftung, st.tabs(beschriftung)))
    with reiter["Spieler"]:
        tab_pro_spieler(df_in, zeige_gespielt=zeige_gespielt, spiele=spiele)
        if zeige_karte:
            # Der einzelne Spieler steht zuunterst im selben Reiter, als
            # Abschnitt "Pro Spieler" (vorher ein eigener Reiter Spielerkarte).
            st.markdown("---")
            st.markdown("<div class='kicker'>Pro Spieler</div>",
                        unsafe_allow_html=True)
            # Videos nur, wo fuer die Auswahl ueberhaupt Tore erfasst sind
            zeige_spielerkarte(df_in, spiele=spiele, spiel_namen=spiel_namen,
                               tore_zeilen=quelle if zeige_tore else None)
    if "Team" in reiter:
        with reiter["Team"]:
            tab_team(df_in, gegentore=gegentore, situationen=situationen,
                     spiele=spiele, tore_zeilen=quelle,
                     paar_zeilen=quelle if saison_modus else None,
                     vergleich=vergleich)
            if team_extra is not None:
                team_extra()
            if alle_spiele is not None:
                # ganz unten, nach den Saison- und Gesamtkennzahlen
                zeige_gegnerbilanz(alle_spiele)
    if "Linien" in reiter:
        with reiter["Linien"]:
            tab_pro_linie(df_in, quelle)
    if "Tore" in reiter:
        with reiter["Tore"]:
            if saison_modus:
                tab_tore_saison(tore_saison, spiel_namen or {}, spiele)
            else:
                tab_tore(tore_zeilen, spiel_namen, spiele)


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
    # je Linie ein Feld, alle drei in einem Block - so gehoeren Titel und
    # Namen sichtbar zusammen
    _felder = []
    for linie in ["1", "2", "3"]:
        players = df_for_plots[df_for_plots["Linie"].astype(str) == str(linie)]["Name"].tolist()
        _namen = ("".join(f"<div class='player-name'>{_e(p)}</div>" for p in players)
                  or "<div class='subtle'>Keine Spieler</div>")
        _felder.append(f"<div class='line-card'><strong>Linie {linie}</strong>{_namen}</div>")
    st.markdown(f"<div class='linien-raster'>{''.join(_felder)}</div>",
                unsafe_allow_html=True)

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
                    spiel_namen=_namen_spiel,
                    # in aelteren Saisons bleibt beim einzelnen Spiel nur
                    # der Reiter Spieler
                    mit_team=not aeltere_saison(selected_saison),
                    mit_linien=not aeltere_saison(selected_saison))

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

        kopf = ("Alle Saisons zusammen" if titel == "Gesamt"
                else f"Saison {_e(titel)}<span>{_e(liga)}. Liga</span>")
        st.markdown(
            f"<div class='abschnitt'>{kopf}</div>" + kacheln([
                dict(bez="Spiele", wert=f"{anz_spiele}"),
                dict(bez="S – U – N",
                     wert=f"{siege_sum} – {unentschieden_sum} – {niederlagen_sum}"),
                dict(bez="Tore", wert=f"{tore_wygo_sum}",
                     text=f"ø {avg_tore_wygo:.2f} pro Spiel"),
                dict(bez="Gegentore", wert=f"{tore_gegner_sum}",
                     text=f"ø {avg_tore_gegner:.2f} pro Spiel"),
                dict(bez="Tordifferenz",
                     wert=_zf(tordifferenz, 0, vorzeichen=True)),
            ], klein=True), unsafe_allow_html=True)

    def zeige_wygo_kennzahlen():
        st.markdown("---")
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
        # Vergleich mit der Vorsaison fuer die Mannschaftskacheln - nur ueber
        # Spiele, fuer die es dort auch Spielerzeilen gibt
        _vergleich = None
        _aeltere = [x for x in saison_options
                    if saison_sort_key(x) < saison_sort_key(selected_saison)]
        if _aeltere:
            _wygo_vor = wygo[wygo[SEASON_COL] == _aeltere[0]]
            if "Format" in _wygo_vor.columns:
                _wygo_vor = _wygo_vor[~_wygo_vor["Format"].astype(str).str.strip()
                                      .str.lower().eq("cup")]
            _df_vor = df[df[MATCH_COL].isin(_wygo_vor[MATCH_COL].dropna())].copy()
            if not _df_vor.empty:
                _df_vor = preprocess_player_stats(_df_vor)
                _quoten_vor = team_quoten(_df_vor, team_situationen(
                    _wygo_vor[_wygo_vor[MATCH_COL].isin(_df_vor[MATCH_COL].unique())]))
                if _quoten_vor:
                    _vergleich = (_aeltere[0], _quoten_vor)
        render_tabs(df_saison, gegentore=_gegentore, zeige_gespielt=True,
                    team_extra=zeige_wygo_kennzahlen, vergleich=_vergleich,
                    spiele=wygo_saison, alle_spiele=wygo,
                    situationen=team_situationen(
                        wygo_saison[wygo_saison[MATCH_COL].isin(_ids_mit_daten)]),
                    tore_saison=tore[tore[MATCH_COL].isin(wygo_saison[MATCH_COL])],
                    spiel_namen=_spiel_namen,
                    mit_linien=not aeltere_saison(selected_saison))


    