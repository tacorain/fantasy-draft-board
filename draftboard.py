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

players = None

# --- Helper to toggle drafted status ---
def toggle_drafted(player_name):
    if player_name in st.session_state.drafted:
        st.session_state.drafted.remove(player_name)
    else:
        st.session_state.drafted.add(player_name)

# --- Load imported board ---
if imported_board:
    board_df = pd.read_csv(imported_board)
    st.session_state.tiers = {}
    st.session_state.drafted = set()

    for row in board_df.itertuples():
        pos = row.Position
        tier = int(row.Tier)
        name = row.Name
        drafted = row.Drafted
        team = getattr(row, "Team", "")

        if pos not in st.session_state.tiers:
            st.session_state.tiers[pos] = {i: [] for i in range(1, 6)}

        st.session_state.tiers[pos][tier].append((name, team))
        if drafted:
            st.session_state.drafted.add(name)

    players = board_df

elif uploaded_file:
    players = pd.read_csv(uploaded_file)
    required_cols = {"Name", "Position", "Team"}
    if not required_cols.issubset(players.columns):
        st.error(f"CSV must include at least these columns: {required_cols}")
        st.stop()

    if not st.session_state.tiers:
        st.session_state.tiers = {
            pos: {i: [] for i in range(1, 6)} for pos in players["Position"].unique()
        }

# --- Main layout ---
if players is not None:
    left, right = st.columns([1, 2])

    # --- Left: Overall Rankings ---
    with left:
        st.subheader("📋 Overall Rankings")
        search_query = st.text_input("Search players by name", "").strip().lower()

        if search_query:
            filtered_players = players[players["Name"].str.lower().str.contains(search_query)]
        else:
            filtered_players = players

        for row in filtered_players.itertuples():
            player_name = row.Name
            pos = row.Position
            team = getattr(row, "Team", "")
            rank = getattr(row, "Rank", None)

            drafted = player_name in st.session_state.drafted
            player_label = f"{rank}. {player_name} ({team}, {pos})" if rank else f"{player_name} ({team}, {pos})"

            # --- One-line row with columns ---
            cols = st.columns([3, 1, 1])  # name/team, tier selector, draft toggle

            with cols[0]:
                if drafted:
                    st.markdown(f"~~{player_label}~~")
                else:
                    st.markdown(player_label)

            with cols[1]:
                tier_choice = st.selectbox(
                    "", [None, 1, 2, 3, 4, 5],
                    key=f"tier_{player_name}",
                    label_visibility="collapsed"
                )
                if tier_choice:
                    # Remove from other tiers in this position
                    for t in st.session_state.tiers.get(pos, {}):
                        st.session_state.tiers[pos][t] = [
                            pt for pt in st.session_state.tiers[pos][t] if pt[0] != player_name
                        ]
                    st.session_state.tiers[pos][tier_choice].append((player_name, team))

            with cols[2]:
                draft_label = "✓" if drafted else "⨯"
                if st.button(draft_label, key=f"draft_{player_name}"):
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
                    for name, team in st.session_state.tiers[pos][i]:
                        display_text = f"{name} ({team})"
                        if name in st.session_state.drafted:
                            st.markdown(f"~~{display_text}~~")
                        else:
                            if st.button(display_text, key=f"tierdraft_{pos}_{i}_{name}"):
                                toggle_drafted(name)

    st.divider()
    st.subheader("📤 Export Tiered Board")

    # --- Export ---
    export_data = []
    for pos in st.session_state.tiers:
        for tier, players_in_tier in st.session_state.tiers[pos].items():
            for name, team in players_in_tier:
                export_data.append({
                    "Name": name,
                    "Position": pos,
                    "Team": team,
                    "Tier": tier,
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
