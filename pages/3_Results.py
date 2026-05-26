
import streamlit as st
import pandas as pd
from sheets.google_sheets import get_outcomes

st.title("Results Dashboard")

session_id = st.text_input("Session ID")

if st.button("Load Results"):

    outcomes = get_outcomes(session_id)

    if len(outcomes) > 0:

        df = pd.DataFrame(outcomes)

        st.dataframe(df)

        st.line_chart(df[["revenue", "profit"]])

    else:
        st.info("No results yet.")
