import streamlit as st
import pandas as pd
import io
import math
import re
import csv

st.set_page_config(page_title="Fantasy Draft Board", layout="wide")
st.title("🏈 Fantasy Football Draft Board")

# --- Initialize session state ---
if "players_dict" not in st.session_state:
    st.session_state.players_dict = {}
if "tiers" not in st.session_state:
    st.session_state.tiers = {}

# --- Helper to rebuild tiers ---
def rebuild_tiers():
    positions = set([p["pos"] for p in st.session_state.players_dict.values()])
    st.session_state.tiers = {pos: {i: [] for i in range(1,6)} for pos in positions}
    for name, data in st.session_state.players_dict.items():
        t = data["tier"]
        if t:
            st.session_state.tiers[data["pos"]][t].append({"name": name, "team": data["team"]})


# --- Upload and fetch interface ---
col1, col2, col3 = st.columns([2,2,2])
with col1:
    uploaded_file = st.file_uploader("Upload initial rankings CSV", type=["csv"])
with col2:
    imported_board = st.file_uploader("Upload saved draft board CSV", type=["csv"])

# --- Add this section somewhere near your file import/export UI ---

st.header("Import Ringer Rankings")

ringer_text = st.text_area("Paste raw Ringer rankings text here:", height=300)

if st.button("Process Ringer Rankings"):
    cleaned_rows = []
    for line in ringer_text.splitlines():
        line = line.strip()
        # Skip headers, section dividers, and empty lines
        if not line or line.startswith(("Rk", "RUNNING", "WIDE", "TIGHT", "DEFENSES", "KICKERS")):
            continue

        # Pattern: Rank, Player, Team, Pos, Bye, $Value, Tier
        pattern = r"^(\d+)\s+([\w\.'-]+(?:\s[\w\.'-]+)*)\s+([A-Z]{2,3})\s+([A-Z]{1,3}\d*)?\s*(\d+)\s+\$(\d+)(?:\s+([A-F]))?"
        m = re.match(pattern, line)
        if m:
            rank, player, team, pos, bye, val, tier = m.groups()
            
            # Normalize position: remove depth chart numbers (WR2 -> WR)
            if pos:
                pos = re.sub(r"\d+$", "", pos)
        
            cleaned_rows.append([
                rank, player, team, pos or "", bye, val, tier or ""
            ])
            
    if cleaned_rows:
        # Save to CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Rank", "Name", "Team", "Pos", "Bye", "Value", "Tier"])
        writer.writerows(cleaned_rows)

        st.success(f"Processed {len(cleaned_rows)} players from Ringer rankings!")

        st.download_button(
            label="Download Cleaned CSV",
            data=output.getvalue(),
            file_name="ringer_rankings.csv",
            mime="text/csv",
        )
    else:
        st.error("No players could be parsed. Double-check the text format.")
        
# --- Load CSV files into session state ---
if imported_board:
    df = pd.read_csv(imported_board)
elif uploaded_file:
    df = pd.read_csv(uploaded_file)
else:
    df = None

if df is not None:
    for row in df.itertuples():
        name = row.Name
        if name not in st.session_state.players_dict:
            tier_val = 0
            if hasattr(row, "Tier") and row.Tier is not None and not (isinstance(row.Tier, float) and math.isnan(row.Tier)):
                tier_val = int(row.Tier)
            drafted_val = bool(getattr(row, "Drafted", False)) if hasattr(row, "Drafted") else False
            st.session_state.players_dict[name] = {
                "pos": row.Position,
                "team": getattr(row, "Team", ""),
                "tier": tier_val,
                "drafted": drafted_val,
                "rank": getattr(row, "Rank", None)
            }
    rebuild_tiers()

# --- Main Draft Board ---
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
                st.markdown(f"~~{player_label}~~") if drafted else st.markdown(player_label)

            with cols[1]:
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
                    format_func=lambda x: f"Tier {x}" if x>0 else "None",
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
    st.info("👆 Upload a CSV or fetch rankings to get started!")
