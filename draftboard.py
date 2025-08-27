import streamlit as st
import pandas as pd

st.set_page_config(page_title="Fantasy Draft Board", layout="wide")

st.title("🏈 Fantasy Football Draft Board with Manual Tiering")

# --- File uploader ---
uploaded_file = st.file_uploader("Upload your player rankings CSV", type=["csv"])

if uploaded_file:
    players = pd.read_csv(uploaded_file)

    # --- Check required columns ---
    required_cols = {"Name", "Position"}
    if not required_cols.issubset(players.columns):
        st.error(f"CSV must include at least these columns: {required_cols}")
        st.stop()

    # --- Initialize state ---
    if "tiers" not in st.session_state:
        st.session_state.tiers = {pos: {i: [] for i in range(1, 6)} for pos in players["Position"].unique()}
    if "drafted" not in st.session_state:
        st.session_state.drafted = set()

    # --- Sidebar position filter ---
    position = st.sidebar.selectbox("Select Position", sorted(players["Position"].unique()))

    # --- Filter players by position ---
    pos_players = players[players["Position"] == position]["Name"].tolist()

    # Players not yet in any tier
    assigned = [p for tier in st.session_state.tiers[position].values() for p in tier]
    unassigned = [p for p in pos_players if p not in assigned]

    st.subheader(f"{position} Tier Board")

    # --- Unassigned pool ---
    st.markdown("**Unassigned Players**")
    chosen = st.multiselect("Move to a tier:", unassigned)

    # Pick tier to move them into
    tier_choice = st.selectbox("Choose tier:", [1, 2, 3, 4, 5])
    if st.button("Add to Tier"):
        for p in chosen:
            st.session_state.tiers[position][tier_choice].append(p)

    # --- Show tiers ---
    cols = st.columns(5)
    for i, col in enumerate(cols, start=1):
        with col:
            st.markdown(f"### Tier {i}")
            for p in st.session_state.tiers[position][i]:
                if p in st.session_state.drafted:
                    st.markdown(f"~~{p}~~")  # strikethrough if drafted
                else:
                    if st.button(f"Draft {p}", key=f"{position}_{i}_{p}"):
                        st.session_state.drafted.add(p)

else:
    st.info("👆 Upload a CSV file to get started.")
