import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Fantasy Draft Board", layout="wide")
st.title("🏈 Fantasy Football Draft Board")

# --- File uploaders ---
col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("Upload your initial player rankings CSV", type=["csv"])
with col2:
    imported_board = st.file_uploader("Or upload a previously exported draft board CSV", type=["csv"])

# --- Initialize session state ---
if "tiers" not in st.session_state:
    st.session_state.tiers = {}
if "drafted" not in st.session_state:
    st.session_state.drafted = set()
if "players" not in st.session_state:
    st.session_state.players = None  # full list of all players

# --- Helper to toggle drafted status ---
def toggle_drafted(name):
    if name in st.session_state.drafted:
        st.session_state.drafted.remove(name)
    else:
        st.session_state.drafted.add(name)

# --- Load imported board ---
if imported_board:
    board_df = pd.read_csv(imported_board)

    # Full rankings for left panel
    st.session_state.players = board_df[["Name", "Position", "Team", "Rank"]].copy()

    # Initialize tiers
    st.session_state.tiers = {pos: {i: [] for i in range(1, 6)} for pos in board_df["Position"].unique()}
    st.session_state.drafted = set()

    # Populate tiers and drafted status
    for row in board_df.itertuples():
        name = row.Name
        pos = row.Position
        team = getattr(row, "Team", "")
        tier = getattr(row, "Tier", None)
        drafted = getattr(row, "Drafted", False)

        if pd.notna(tier):
            tier = int(tier)
            st.session_state.tiers[pos][tier].append({"name": name, "team": team})

        if drafted:
            st.session_state.drafted.add(name)

elif uploaded_file:
    players_df = pd.read_csv(uploaded_file)
    required_cols = {"Name", "Position", "Team"}
    if not required_cols.issubset(players_df.columns):
        st.error(f"CSV must include at least these columns: {required_cols}")
        st.stop()

    st.session_state.players = players_df

    if not st.session_state.tiers:
        st.session_state.tiers = {
            pos: {i: [] for i in range(1, 6)} for pos in players_df["Position"].unique()
        }

# --- Main layout ---
if st.session_state.players is not None:
    left, right = st.columns([1, 2])

    # --- Left: Overall Rankings ---
    with left:
        st.subheader("📋 Overall Rankings")
        search_query = st.text_input("Search players by name", "").strip().lower()

        players_to_show = st.session_state.players
        if search_query:
            players_to_show = players_to_show[players_to_show["Name"].str.lower().str.contains(search_query)]

        for row in players_to_show.itertuples():
            player_name = row.Name
            pos = row.Position
            team = getattr(row, "Team", "")
            rank = getattr(row, "Rank", None)

            drafted = player_name in st.session_state.drafted
            player_label = f"{rank}. {player_name} ({team}, {pos})" if pd.notna(rank) else f"{player_name} ({team}, {pos})"

            cols = st.columns([3, 1, 1])

            # Player label
            with cols[0]:
                if drafted:
                    st.markdown(f"~~{player_label}~~")
                else:
                    st.markdown(player_label)

            # Tier assignment
            with cols[1]:
                tier_choice = st.selectbox(
                    "", [None, 1, 2, 3, 4, 5],
                    key=f"tier_{player_name}",
                    label_visibility="collapsed"
                )
                if tier_choice:
                    # Remove from other tiers
                    for t in st.session_state.tiers.get(pos, {}):
                        st.session_state.tiers[pos][t] = [
                            pt for pt in st.session_state.tiers[pos][t] if pt["name"] != player_name
                        ]
                    st.session_state.tiers[pos][tier_choice].append({"name": player_name, "team": team})

            # Draft button
            with cols[2]:
                if st.button("Draft", key=f"draft_{player_name}"):
                    toggle_drafted(player_name)

    # --- Right: Tier Boards ---
    with right:
        st.subheader("🎯 Tier Board by Position")
        for pos in sorted(st.session_state.tiers.keys()):
            st.markdown(f"### {pos}")
            pos_cols = st.columns(5)
            for i, col in enumerate(pos_cols, start=1):
                with col:
                    st.markdown(f"**Tier {i}**")
                    # Iterate over a copy
                    for player in st.session_state.tiers[pos][i][:]:
                        name = player["name"]
                        team = player["team"]
                        display_text = f"{name} ({team})"
                        key = f"tierdraft_{pos}_{i}_{name}"
                        if name in st.session_state.drafted:
                            st.markdown(f"~~{display_text}~~")
                        else:
                            if st.button(display_text, key=key):
                                toggle_drafted(name)

    st.divider()
    st.subheader("📤 Export Tiered Board")

    # --- Export ---
    export_data = []
    for idx, row in st.session_state.players.iterrows():
        name = row.Name
        pos = row.Position
        team = row.Team
        rank = row.Rank if "Rank" in row else None
        # find tier if assigned
        tier_assigned = None
        for t in st.session_state.tiers.get(pos, {}):
            if any(pt["name"] == name for pt in st.session_state.tiers[pos][t]):
                tier_assigned = t
                break

        export_data.append({
            "Name": name,
            "Position": pos,
            "Team": team,
            "Rank": rank,
            "Tier": tier_assigned,
            "Drafted": name in st.session_state.drafted
        })

    export_df = pd.DataFrame(export_data)
    buffer = io.StringIO()
    export_df.to_csv(buffer, index=False)
    st.download_button(
        label="Download board as CSV",
        data=buffer.getvalue(),
        file_name="tiered_draft_board.csv",
        mime="text/csv"
    )

else:
    st.info("👆 Upload either an initial rankings CSV or a saved draft board CSV to get started.")
