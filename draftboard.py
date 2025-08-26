import streamlit as st

st.title("Fantasy Draft Board")

players = ["Patrick Mahomes", "Josh Allen", "Jalen Hurts"]
drafted = st.multiselect("Mark drafted players:", players)

st.write("Remaining Players:")
st.write([p for p in players if p not in drafted])
