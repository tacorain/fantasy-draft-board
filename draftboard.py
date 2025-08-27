import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Fantasy Draft Board", layout="wide")

st.title("🏈 Fantasy Football Draft Board with Position-Aware Tiering")

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
        st.session_state.tiers = {
            pos: {i: [] for i in range(1, 6)} for pos in players["Position"].unique()
        }
    if "drafted" not in st.session_state:
        st.session_state.drafted = set()

    # --- Search bar ---
    st.subheader("📋 Overall Rankings")
    search_query = st.text_input("Search players by name", "").strip().lower()

    # --- Filter players if search query entered ---
    if search_query:
        filtered_players = players[players["Name"].str.lower().str.contains(search_query)]
    else:
        filtered_players = players

    # --- Show rankings table with controls ---
    for row in filtered_players.itertuples():
        player_name = row.Name
        pos = row.Position
        rank = row.Rank if "Rank" in players.columns else None

        # Show player with drafted status
        drafted = player_name in st.session_state.drafted
        player_label = f"{rank}. {player_name} ({pos})" if rank else f"{player_name} ({pos})"

        cols = st.columns([4, 1, 1])  # name, tier assign, draft
        with cols[0]:
            if drafted:
                st.markdown(f"~~{player_label}~~")
            else:
                st.write(player_label)

        # Assign to tier (position aware)
        with cols[1]:
            tier_choice = st.selectbox(
                "Tier", [None, 1, 2, 3, 4, 5],
                key=f"tier_{player_name}",
                label_visibility="collapsed"
            )
            if tier_choice:
                # remove from any other tier in this position
                for t in st.session_state.tiers[pos]:
                    if player_name in st.session_state.tiers[pos][t]:
                        st.session_state.tiers[pos][t].remove(player_name)
                # add to selected tier
                if player_name not in st.session_state.tiers[pos][tier_choice]:
                    st.session_state.tiers[pos][tier_choice].append(player_name)

        # Draft button
        with cols[2]:
            if st.button("Draft", key=f"draft_{player_name}"):
                if drafted:
                    st.session_state.drafted.remove(player_name)
                else:
                    st.session_state.drafted.add(player_name)

    st.divider()
    st.subheader("🎯 Tier Board (by Position)")

    # --- Show tiers for each position ---
    for pos in sorted(st.session_state.tiers.keys()):
        st.markdown(f"## {pos}")
        tier_cols = st.columns(5)
        for i, col in enumerate(tier_cols, start=1):
            with col:
                st.markdown(f"### Tier {i}")
                for p in st.session_state.tiers[pos][i]:
                    if p in st.session_state.drafted:
                        st.markdown(f"~~{p}~~")
                    else:
                        if st.button(f"Draft {p}", key=f"tierdraft_{pos}_{i}_{p}"):
                            st.session_state.drafted.add(p)

    st.divider()
    st.subheader("📤 Export Tiered Board")

    # --- Export current board ---
    export_data = []
    for pos in st.session_state.tiers:
        for tier, players_in_tier in st.session_state.tiers[pos].items():
            for p in players_in_tier:
                export_data.append({
                    "Name": p,
                    "Position": pos,
                    "Tier": tier,
                    "Drafted": p in st.session_state.drafted
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
    st.info("👆 Upload a CSV file to get started.")
