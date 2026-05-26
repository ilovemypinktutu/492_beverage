
import streamlit as st
import pandas as pd
from sheets.google_sheets import (
    add_session,
    get_sessions,
    add_player
)

st.title("Instructor Dashboard")

st.header("Create New Session")

session_id = st.text_input("Session ID", value="session_001")
num_periods = st.number_input("Number of Periods", 1, 50, 10)

if st.button("Create Session"):
    add_session(session_id, num_periods)
    st.success(f"Created {session_id}")

st.divider()

st.header("Add Player")

player_name = st.text_input("Player Name")
team_name = st.text_input("Team Name")
role = st.selectbox(
    "Role",
    [
        "Pricing Manager",
        "Marketing Manager",
        "Competitor Analyst",
        "Operations Manager"
    ]
)

if st.button("Add Player"):
    add_player(session_id, player_name, team_name, role)
    st.success("Player added")

st.divider()

st.header("Current Sessions")

sessions = get_sessions()

if len(sessions) > 0:
    st.dataframe(pd.DataFrame(sessions))
else:
    st.info("No sessions yet.")
