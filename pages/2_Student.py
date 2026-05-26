
import streamlit as st
from sheets.google_sheets import (
    submit_decision,
    get_player_history,
    all_players_submitted
)
from simulation.engine import run_period

st.title("Student Dashboard")

session_id = st.text_input("Session ID")
player_name = st.text_input("Player Name")

st.header("Decisions")

price = st.number_input("Set Cola Price", 0.5, 20.0, 2.5)
ad_budget = st.number_input("Advertising Budget", 0, 1000000, 10000)
competitor_price = st.number_input("Competitor Price Estimate", 0.5, 20.0, 2.7)
competitor_ad = st.number_input("Competitor Advertising Estimate", 0, 1000000, 12000)

if st.button("Submit Decisions"):

    decisions = {
        "price": price,
        "ad_budget": ad_budget,
        "competitor_price": competitor_price,
        "competitor_ad": competitor_ad
    }

    submit_decision(
        session_id=session_id,
        player_name=player_name,
        decisions=decisions
    )

    st.success("Decisions submitted.")

    if all_players_submitted(session_id):
        run_period(session_id)
        st.success("All players submitted. Simulation executed.")
    else:
        st.info("Waiting for other players.")

st.divider()

st.header("Historical Results")

history = get_player_history(session_id, player_name)

if len(history) > 0:
    st.dataframe(history)
