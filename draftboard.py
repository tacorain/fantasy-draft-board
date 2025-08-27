import streamlit as st
import pandas as pd
import re
import json
import requests

# -----------------------------
# Helpers
# -----------------------------
def clean_position(pos: str) -> str:
    """Remove depth chart numbers (WR2 -> WR)."""
    return re.sub(r"\d+$", "", pos) if pos else pos

def toggle_drafted(name):
    st.session_state.drafted[name] = not st.session_state.drafted.get(name, False)

def export_state():
    export = {
        "rankings": st.session_state.rankings.to_dict(),
        "tiers": st.session_state.tiers,
        "drafted": st.session_state.drafted,
    }
    return json.dumps(export)

def import_state(data):
    parsed = json.loads(data)
    st.session_state.rankings = pd.DataFrame(parsed["rankings"])
    st.session_state.tiers = parsed["tiers"]
    st.session_state.drafted = parsed["drafted"]

def fetch_ringer_rankings():
    url = "https://www.theringer.com/fantasy-football/2025?draft=ppr"
    resp = requests.get(url)
    text = resp.text

    # Regex to grab rows of rankings (approximation — may need adjusting if site changes)
    pattern = re.compile(
        r"(\d+)\.\s+([A-Za-z\.\'\-\s]+)\s+([A-Z]{2,3})?\s+([A-Z]{1,3}\d*)?\s*Bye\s*(\d+)?",
        re.MULTILINE
    )

    rows = []
    for m in pattern.finditer(text):
        rank, player, team, pos, bye = m.groups()
        pos = clean_position(pos)
        rows.append([rank, player.strip(), team or "", pos or "", bye or ""])

    df = pd.DataFrame(rows, columns=["Rank", "Player", "Team", "Pos", "Bye"])

    # Save CSV locally
    df.to_csv("ringer_rankings.csv", index=False)
    return df

# -----------------------------
# Streamlit App
# -----------------------------
st.title("Fantasy Draft Board")

if "rankings" not in st.session_state:
    st.session_state.rankings = pd.DataFrame()
if "tiers" not in st.session_state:
    st.session_state.tiers = {pos: {i: [] for i in range(1, 6)} for pos in ["QB", "RB", "WR", "TE"]}
if "drafted" not in st.session_state:
    st.session_state.drafted = {}

# Sidebar actions
with st.sidebar:
    st.subheader("Data")
    uploaded = st.file_uploader("Upload rankings CSV or export JSON", type=["csv", "json"])
    if uploaded:
        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(uploaded)
            df["Pos"] = df["Pos"].apply(clean_position)
            st.session_state.rankings = df
        else:  # json
            data = uploaded.read().decode("utf-8")
            import_state(data)

    if st.button("Fetch Ringer Rankings"):
        df = fetch_ringer_rankings()
        st.success("Ringer rankings saved as ringer_rankings.csv")

    export_json = export_state()
    st.download_button("Export Board", export_json, file_name="draftboard_export.json")

# Layout: Left = Rankings, Right = Tiers
col1, col2 = st.columns([1, 2])

# -----------------------------
# Left Column: Overall Rankings
# -----------------------------
with col1:
    st.subheader("Overall Rankings")

    if not st.session_state.rankings.empty:
        for i, row in st.session_state.rankings.iterrows():
            name = row["Player"]
            team = row.get("Team", "")
            pos = row.get("Pos", "")
            drafted = st.session_state.drafted.get(name, False)

            label = f"{name} ({team} - {pos})"
            if drafted:
                label = f"~~{label}~~"

            cols = st.columns([4, 1, 1])
            with cols[0]:
                st.markdown(label, unsafe_allow_html=True)
            with cols[1]:
                if st.button("✓", key=f"draft_{name}"):
                    toggle_drafted(name)
            with cols[2]:
                tier_choice = st.selectbox(
                    "",
                    [1, 2, 3, 4, 5],
                    index=0,
                    key=f"tier_{name}",
                    label_visibility="collapsed",
                )
                if st.button("→", key=f"add_{name}"):
                    pos_clean = clean_position(pos)
                    if pos_clean in st.session_state.tiers:
                        st.session_state.tiers[pos_clean][tier_choice].append(name)

# -----------------------------
# Right Column: Tiers
# -----------------------------
with col2:
    st.subheader("Position Tiers")

    for pos in st.session_state.tiers:
        st.markdown(f"### {pos}")
        tier_cols = st.columns(5)
        for t in range(1, 6):
            with tier_cols[t - 1]:
                st.markdown(f"**Tier {t}**")
                for player in st.session_state.tiers[pos][t]:
                    drafted = st.session_state.drafted.get(player, False)
                    display = f"~~{player}~~" if drafted else player
                    if st.button(display, key=f"tierdraft_{pos}_{t}_{player}"):
                        toggle_drafted(player)
