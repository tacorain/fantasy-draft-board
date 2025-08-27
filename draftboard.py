import streamlit as st
import pandas as pd
import re
import json

st.set_page_config(layout="wide")

# ------------------
# Helpers
# ------------------

def clean_position(pos):
    """Remove numbers from positions like WR2 -> WR"""
    return re.sub(r"\d+", "", pos)

def toggle_drafted(player_name):
    for p in st.session_state.rankings["Player"]:
        if p == player_name:
            idx = st.session_state.rankings.index[
                st.session_state.rankings["Player"] == player_name
            ][0]
            st.session_state.rankings.at[idx, "Drafted"] = not st.session_state.rankings.at[idx, "Drafted"]
            break

def export_state():
    return json.dumps(st.session_state.rankings.to_dict(orient="records"))

def import_state(data):
    records = json.loads(data)
    df = pd.DataFrame(records)
    df["Pos"] = df["Pos"].apply(clean_position)
    st.session_state.rankings = df

# ------------------
# Initial Data
# ------------------

if "rankings" not in st.session_state:
    st.session_state.rankings = pd.DataFrame(columns=["Rank", "Player", "Team", "Pos", "Drafted", "Tier"])

# ------------------
# Sidebar
# ------------------

with st.sidebar:
    st.subheader("Data")

    uploaded = st.file_uploader("Upload rankings CSV or export JSON", type=["csv", "json"])
    if uploaded:
        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(uploaded)
            if "Drafted" not in df.columns:
                df["Drafted"] = False
            if "Tier" not in df.columns:
                df["Tier"] = None
            df["Pos"] = df["Pos"].apply(clean_position)
            st.session_state.rankings = df
            st.success("CSV loaded")
        else:
            data = uploaded.read().decode("utf-8")
            import_state(data)
            st.success("JSON loaded")

    # 🔥 Text paste parser
    st.markdown("### Paste Rankings Text")
    pasted = st.text_area("Paste the raw dump from Ringer/PDF here:")
    if st.button("Parse Pasted Rankings"):
        lines = pasted.splitlines()
        rows = []
        for line in lines:
            # Example: "15. CeeDee Lamb DAL WR2"
            m = re.match(r"(\d+)\.\s+([A-Za-z\.\'\-\s]+)\s+([A-Z]{2,3})\s+([A-Z]{1,3}\d*)", line)
            if m:
                rank, player, team, pos = m.groups()
                pos = clean_position(pos)
                rows.append([rank, player.strip(), team, pos])
        if rows:
            df = pd.DataFrame(rows, columns=["Rank", "Player", "Team", "Pos"])
            df["Drafted"] = False
            df["Tier"] = None
            st.session_state.rankings = df
            st.success("Rankings parsed and loaded into draft board")
        else:
            st.warning("No valid rows found in pasted text.")

    export_json = export_state()
    st.download_button("Export Board", export_json, file_name="draftboard_export.json")

# ------------------
# Main UI
# ------------------

st.title("Fantasy Draft Board")

if st.session_state.rankings.empty:
    st.info("Upload or paste rankings to begin.")
else:
    df = st.session_state.rankings

    # Global rankings list
    st.header("Global Rankings")
    for _, row in df.sort_values(by="Rank", key=lambda x: pd.to_numeric(x, errors="coerce")).iterrows():
        cols = st.columns([4, 1, 1])
        drafted = row.get("Drafted", False)
        label = f"{row['Player']} ({row['Team']} {row['Pos']})"
        if drafted:
            label = f"~~{label}~~ ✅"

        if cols[0].button(label, key=f"draft_{row['Player']}"):
            toggle_drafted(row['Player'])

        tier_choice = cols[1].selectbox(
            "",
            [None, 1, 2, 3, 4, 5],
            index=[None, 1, 2, 3, 4, 5].index(row.get("Tier")) if row.get("Tier") in [1,2,3,4,5] else 0,
            key=f"tier_{row['Player']}",
            label_visibility="collapsed"
        )
        st.session_state.rankings.at[row.name, "Tier"] = tier_choice

    # Tiered view
    st.header("Tiered View")
    for t in sorted(df["Tier"].dropna().unique()):
        st.subheader(f"Tier {int(t)}")
        tier_df = df[df["Tier"] == t]
        st.write(", ".join(
            f"~~{p}~~" if d else p
            for p, d in zip(tier_df["Player"], tier_df["Drafted"])
        ))
