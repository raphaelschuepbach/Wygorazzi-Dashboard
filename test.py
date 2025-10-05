import streamlit as st
import pandas as pd
import os

# ---------- Konfiguration ----------
CSV_FILE = "Spieler_Statistik_25_26_live1s.csv"
SPIELER = [
    "C.Loosli", "D.Geissbühler", "B.Lüthi", "L.Leuenberger", "R.Schüpbach",
    "M.Geissbühler", "C.Mühle", "N.Nyffenegger", "M.Nyffeler", "R.Moser",
    "B.Jordi", "T.Loosli", "M.Nyffenegger"
]

SPALTEN = [
    "Name", "Match_id", "Gegner", "Linie", "Gespielt", "T", "A", "+", "-",
    "Strafen", "Bully +", "Bully -", "Boxplay +", "Boxplay -",
    "Powerplay +", "Powerplay -"
]

NUMERIC_COLS = [
    "T", "A", "+", "-", "Strafen",
    "Bully +", "Bully -", "Boxplay +", "Boxplay -",
    "Powerplay +", "Powerplay -"
]

# ---------- Initialisierung ----------
def make_empty_df():
    rows = []
    for name in SPIELER:
        row = {c: "" for c in SPALTEN}
        row["Name"] = name
        row["Match_id"] = ""
        row["Gegner"] = ""
        row["Linie"] = ""
        row["Gespielt"] = "Nein"
        for nc in NUMERIC_COLS:
            row[nc] = 0
        rows.append(row)
    return pd.DataFrame(rows)

if 'df' not in st.session_state:
    if os.path.exists(CSV_FILE):
        df0 = pd.read_csv(CSV_FILE)
        for c in SPALTEN:
            if c not in df0.columns:
                df0[c] = 0 if c in NUMERIC_COLS else ""
        for name in SPIELER:
            if name not in df0["Name"].values:
                new = make_empty_df()
                new = new[new["Name"] == name]
                df0 = pd.concat([df0, new], ignore_index=True)
        for nc in NUMERIC_COLS:
            df0[nc] = pd.to_numeric(df0[nc], errors='coerce').fillna(0).astype(int)
        df0["Gespielt"] = df0["Gespielt"].fillna("Nein")
        df0["Linie"] = df0["Linie"].fillna("")
        st.session_state['df'] = df0[SPALTEN].copy()
    else:
        st.session_state['df'] = make_empty_df()

df = st.session_state['df']

# ---------- Seite Kopf ----------
st.set_page_config(page_title="Live-Spielerstatistik", layout="wide")
st.title("📲 Live-Erfassung — Spielstatistik")

col1, col2, col3 = st.columns([3,3,1])
with col1:
    match_input = st.text_input("Spiel-ID", value=df["Match_id"].iloc[0], key="match_input")
with col2:
    gegner_input = st.text_input("Gegner", value=df["Gegner"].iloc[0], key="gegner_input")
with col3:
    auto_save = st.checkbox("Auto-Save", value=True)

# Callback-Funktion für "Neuer Match"
def reset_match():
    df = st.session_state['df'].copy()
    df["Linie"] = ""
    df["Gespielt"] = "Nein"
    for nc in NUMERIC_COLS:
        df[nc] = 0
    st.session_state['df'] = df
    
    # Match-ID und Gegner zurücksetzen
    st.session_state["match_input"] = ""
    st.session_state["gegner_input"] = ""
    
    # Checkbox- und Selectbox-Keys zurücksetzen
    for name in SPIELER:
        st.session_state[f"linie_{name}"] = "-"   
        st.session_state[f"played_{name}"] = False

    st.success("Neuer Match gestartet! Alte Daten bleiben in CSV erhalten.")


# Button zum Reset
st.button("🆕 Neuer Match", on_click=reset_match)

# Match/Gegner in df schreiben
df["Match_id"] = st.session_state["match_input"]
df["Gegner"] = st.session_state["gegner_input"]



# ---------- Anzeige Spieler mit Buttons ----------
linie_order = {"1": 1, "2": 2, "3": 3}
df['__sort'] = df['Linie'].map(linie_order).fillna(999).astype(int)
display_df = df.sort_values(by=['__sort', 'Name']).reset_index(drop=True)
display_df = display_df.drop(columns="__sort")

# CSS für Buttons
st.markdown("""
<style>
div.stButton > button { height:36px; font-size:14px; }
</style>
""", unsafe_allow_html=True)

def maybe_save():
    df = st.session_state['df'].copy()
    if not auto_save:
        return

    # Normiertes Match-ID-String (keine Leerzeichen)
    match_id = str(df["Match_id"].iloc[0]).strip()
    if match_id == "" or match_id.lower() == "nan":
        return  # nichts speichern, wenn keine Match-ID gesetzt ist

    # Vorbereiten: numerische Spalten in df sauber machen
    for nc in NUMERIC_COLS:
        df[nc] = pd.to_numeric(df[nc], errors='coerce').fillna(0).astype(int)

    # Normiere Name + Match_id in df
    df["Match_id"] = df["Match_id"].astype(str).str.strip()
    df["Name"] = df["Name"].astype(str).str.strip()

    # CSV einlesen (wenn vorhanden) und ebenfalls normalisieren
    if os.path.exists(CSV_FILE):
        csv_df = pd.read_csv(CSV_FILE, dtype=str).fillna("")
        # sicherstellen, dass alle erwarteten Spalten vorhanden sind
        for c in SPALTEN:
            if c not in csv_df.columns:
                csv_df[c] = "" if c not in NUMERIC_COLS else "0"
        # Normalisieren für Vergleich
        csv_df["Match_id"] = csv_df["Match_id"].astype(str).str.strip()
        csv_df["Name"] = csv_df["Name"].astype(str).str.strip()
        # numerische Spalten konvertieren
        for nc in NUMERIC_COLS:
            csv_df[nc] = pd.to_numeric(csv_df[nc], errors='coerce').fillna(0).astype(int)

        # alte Zeilen für diese Match-ID entfernen
        csv_df = csv_df[csv_df["Match_id"] != match_id]

        # neue Zeilen hinzufügen
        csv_df = pd.concat([csv_df, df], ignore_index=True, sort=False)
    else:
        csv_df = df.copy()

    # Doppelungen sicher entfernen: pro Match+Name nur eine Zeile behalten
    csv_df = csv_df.drop_duplicates(subset=["Match_id", "Name"], keep="last")

    # Optional: nur erwartete Spalten in dieser Reihenfolge speichern
    csv_df = csv_df.reindex(columns=SPALTEN)

    # Atomar speichern (tmp -> replace)
    tmp_file = CSV_FILE + ".tmp"
    csv_df.to_csv(tmp_file, index=False)
    os.replace(tmp_file, CSV_FILE)
    #st.success(f"Daten für Match '{match_id}' gespeichert!")



# Anzeige mit Buttons
for i, row in display_df.iterrows():
    name = row["Name"]
    st.markdown(f"### 👤 {name}")

    cols_top = st.columns([1,1] + [1]*len(NUMERIC_COLS))

    # Linie
    cur_line = str(df.loc[df["Name"] == name, "Linie"].values[0])
    line_options = ["-", "1", "2", "3", "Goalie"]

    # Eindeutiger Key: Name + Index + Match-ID
    select_key = f"linie_{name}_{i}_{st.session_state['match_input']}"

    new_line = cols_top[0].selectbox(
        "Linie",
        line_options,
        index=line_options.index(cur_line) if cur_line in line_options else 0,
        key=select_key



    )

    if new_line != cur_line:
    # "-" wird als leere Linie gespeichert
        df.loc[df["Name"] == name, "Linie"] = new_line if new_line != "-" else ""
    
    # Automatisch Gespielt setzen, wenn Linie gewählt (außer "-")
        if new_line != "-":
            df.loc[df["Name"] == name, "Gespielt"] = "Ja"
    
        maybe_save()


    # Gespielt
    cur_play = df.loc[df["Name"] == name, "Gespielt"].values[0]
    checked = True if cur_play=="Ja" else False
    val_checked = cols_top[1].checkbox("Gespielt", value=checked, key=f"played_{name}")
    if val_checked != checked:
        df.loc[df["Name"]==name,"Gespielt"] = "Ja" if val_checked else "Nein"
        maybe_save()

    # Plus / Minus Buttons für alle numerischen Spalten
    for j, col_label in enumerate(NUMERIC_COLS):
        col = cols_top[j+2]
        col.markdown(f"**{col_label}**")
        plus_key = f"{name}_{col_label}_plus"
        minus_key = f"{name}_{col_label}_minus"
        c1, c2 = col.columns([1,1])
        if c1.button("➕", key=plus_key):
            df.loc[df["Name"]==name, col_label] += 1
            maybe_save()
        if c2.button("➖", key=minus_key):
            df.loc[df["Name"]==name, col_label] = max(0, df.loc[df["Name"]==name, col_label].values[0]-1)
            maybe_save()
        col.caption(f"{df.loc[df['Name']==name,col_label].values[0]}")

st.session_state['df'] = df

