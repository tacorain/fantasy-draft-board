import streamlit as st
import pandas as pd
import json

st.set_page_config(layout="wide")
st.title("Fantasy Draft Board")

# ------------------
# Sidebar Controls
# ------------------
st.sidebar.header("Controls")

uploaded = st.sidebar.file_uploader("Upload saved CSV or JSON", type=["csv", "json"])
if uploaded:
    if uploaded.name.endswith(".csv"):
        df = pd.read_csv(uploaded)
        if "Drafted" not in df.columns:
            df["Drafted"] = False
        if "Tier" not in df.columns:
            df["Tier"] = None
        st.session_state.rankings = df
        st.success("CSV loaded")
    else:
        data = uploaded.read().decode("utf-8")
        records = json.loads(data)
        st.session_state.rankings = pd.DataFrame(records)
        st.success("JSON loaded")

if st.sidebar.button("Export Rankings"):
    if "rankings" in st.session_state:
        export_data = json.dumps(st.session_state.rankings.to_dict(orient="records"))
        st.sidebar.download_button("Download JSON", export_data, file_name="draftboard_export.json")

st.sidebar.subheader("Paste Rankings Text")
text_input = st.sidebar.text_area("Paste text from PDF or site here")
if st.sidebar.button("Parse Text"):
    lines = text_input.splitlines()
    rows = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 4:
            rank, player, team, pos = parts[:4]
            rows.append([rank, player, team, pos])
    if rows:
        df = pd.DataFrame(rows, columns=["Rank", "Player", "Team", "Pos"])
        df["Drafted"] = False
        df["Tier"] = None
        st.session_state.rankings = df
        st.success("Parsed rankings loaded.")

# ------------------
# Main Page Layout
# ------------------
col1, col2 = st.columns([2, 2])

with col1:
    st.subheader("Global Rankings")
    if "rankings" in st.session_state:
        df = st.session_state.rankings
        for idx, row in df.iterrows():
            cols = st.columns([4, 1, 1])
            drafted = row.get("Drafted", False)
            label = f"{row['Player']} ({row['Team']} {row['Pos']})"
            if drafted:
                label = f"~~{label}~~ ✅"
            if cols[0].button(label, key=f"draft_{row['Player']}"):
                st.session_state.rankings.at[idx, "Drafted"] = not st.session_state.rankings.at[idx, "Drafted"]
            tier_choice = cols[1].selectbox(
                "",
                [None, 1, 2, 3, 4, 5],
                index=[None, 1, 2, 3, 4, 5].index(row.get("Tier")) if row.get("Tier") in [1,2,3,4,5] else 0,
                key=f"tier_{row['Player']}",
                label_visibility="collapsed"
            )
            st.session_state.rankings.at[idx, "Tier"] = tier_choice

with col2:
    st.subheader("Tier Lists")
    if "rankings" in st.session_state:
        df = st.session_state.rankings
        for t in sorted(df["Tier"].dropna().unique()):
            st.markdown(f"### Tier {int(t)}")
            tier_df = df[df["Tier"] == t]
            st.write(", ".join(
                f"~~{p}~~" if d else p
                for p, d in zip(tier_df["Player"], tier_df["Drafted"])
            ))
