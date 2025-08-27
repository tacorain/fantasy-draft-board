import streamlit as st
import pandas as pd
import io
import math

st.set_page_config(page_title="Fantasy Draft Board", layout="wide")
st.title("🏈 Fantasy Football Draft Board")

# --- File uploaders ---
col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("Upload initial rankings CSV", type=["csv"])
with col2:
    imported_board = st.file_uploader("Or upload a previously exported draft board CSV", type=["csv"])

# --- Initialize session state ---
if "players_dict" not in st.session_state:
    st.session_state.players_dict = {}  # key: player name, value: dict with pos, team, tier, drafted

if "tiers" not in st.session_state:
    st.session_state.tiers = {}

# --- Helper to rebuild tiers from players_dict ---
def rebuild_tiers():
    positions = set([p["pos"] for p in st.session_state.players_dict.values()])
    st.session_state.tiers = {pos: {i: [] for i in range(1,6)} for pos in positions}
    for name, data in st.session_state.players_dict.items():
        t = data["tier"]
        if t:
            st.session_state.tiers[data["pos"]][t].append({"name": name, "team": data["team"]})

# --- Load data ---
if imported_board:
    df = pd.read_csv(imported_board)
elif uploaded_file:
    df = pd.read_csv(uploaded_file)
else:
    df = None

if df is not None:
    # Initialize players_dict if empty
    for row in df.itertuples():
        name = row.Name
        if name not in st.session_state.players_dict:
            # Safe conversion of tier
            tier_val = 0
            if hasattr(row, "Tier"):
                raw_tier = getattr(row, "Tier")
                if raw_tier is not None and not (isinstance(raw_tier, float) and math.isnan(raw_tier)):
                    try:
                        tier_val = int(raw_tier)
                    except:
                        tier_val = 0

            drafted_val = False
            if hasattr(row, "Drafted"):
                drafted_val = bool(getattr(row, "Drafted", False))

            st.session_state.players_dict[name] = {
                "pos": row.Position,
                "team": getattr(row, "Team", ""),
                "tier": tier_val,
                "drafted": drafted_val,
                "rank": getattr(row, "Rank", None)
            }
    rebuild_tiers()

# --- Main layout ---
if st.session_state.players_dict:
    left, right = st.columns([1,2])

    # --- Left panel: Full rankings ---
    with left:
        st.subheader("📋 Overall Rankings")
        search_query = st.text_input("Search players by name", "").strip().lower()

        players_list = list(st.session_state.players_dict.items())
        if search_query:
            players_list = [(name,data) for name,data in players_list if search_query in name.lower()]

        for name, data in players_list:
            pos = data["pos"]
            team = data["team"]
            rank = data.get("rank")
            drafted = data["drafted"]
            player_label = f"{rank}. {name} ({team}, {pos})" if rank else f"{name} ({team}, {pos})"

            cols = st.columns([3,1,1])

            with cols[0]:
                if drafted:
                    st.markdown(f"~~{player_label}~~")
                else:
                    st.markdown(player_label)

            with cols[1]:
                # Safe index conversion for selectbox
                tier_val = data["tier"]
                if tier_val is None or (isinstance(tier_val, float) and math.isnan(tier_val)):
                    index = 0
                else:
                    index = int(tier_val)

                tier_choice = st.selectbox(
                    "",
                    [0,1,2,3,4,5],
                    index=index,
                    key=f"tier_{name}",
                    format_func=lambda x: f"{x}" if x>0 else "None",
                    label_visibility="collapsed"
                )
                if tier_choice != data["tier"]:
                    st.session_state.players_dict[name]["tier"] = tier_choice
                    rebuild_tiers()

            with cols[2]:
                if st.button("Draft", key=f"draft_left_{name}"):
                    st.session_state.players_dict[name]["drafted"] = not data["drafted"]
                    rebuild_tiers()

    # --- Right panel: Tier board ---
    with right:
        st.subheader("🎯 Tier Board by Position")
        for pos in sorted(st.session_state.tiers.keys()):
            st.markdown(f"### {pos}")
            pos_cols = st.columns(5)
            for i, col in enumerate(pos_cols, start=1):
                with col:
                    st.markdown(f"**Tier {i}**")
                    for player in st.session_state.tiers[pos][i][:]:
                        pname = player["name"]
                        pteam = player["team"]
                        display_text = f"{pname} ({pteam})"
                        key = f"draft_right_{pos}_{i}_{pname}"
                        if st.session_state.players_dict[pname]["drafted"]:
                            st.markdown(f"~~{display_text}~~")
                        else:
                            if st.button(display_text, key=key):
                                st.session_state.players_dict[pname]["drafted"] = True
                                rebuild_tiers()

    st.divider()
    st.subheader("📤 Export Tiered Board")

    # --- Export ---
    export_data = []
    for name, data in st.session_state.players_dict.items():
        export_data.append({
            "Name": name,
            "Position": data["pos"],
            "Team": data["team"],
            "Rank": data.get("rank"),
            "Tier": data["tier"] if data["tier"]>0 else None,
            "Drafted": data["drafted"]
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
