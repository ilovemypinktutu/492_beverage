"""
core/page_runner.py
===================
Single function that renders a complete role+product simulation page.
All 9 pages call this with their product/role constants.
"""
from __future__ import annotations
import streamlit as st
from core.model import make_market_state, find_equilibrium, compute_financials
from core.ui import (
    inject_css, role_banner, render_sidebar,
    render_choice_slider, render_metrics,
    render_eq_alert, render_charts,
    render_sensitivity_table, render_export,
    PRODUCT_EMOJI, ROLE_LABEL, ROLE_EMOJI, PRODUCT_COLOR,
)


def run_page(product: str, role: str) -> None:
    """
    Render the full simulation page for a given product × role combination.

    Called by each of the 9 page files with their fixed constants.
    The entire UI — CSS, banner, sidebar, decision slider, metrics,
    charts, sensitivity table, and export — is handled here.
    """
    # ── Page-level Streamlit config (must be first call in each page) ──
    emoji = PRODUCT_EMOJI[product]
    role_lbl = ROLE_LABEL[role]
    st.set_page_config(
        page_title=f"{product.title()} · {role_lbl}",
        page_icon=emoji,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ── CSS injection (product-coloured theme) ──
    inject_css(product)

    # ── Role banner ──
    role_banner(product, role)

    # ── Build initial MarketState from product defaults ──
    # We keep state in st.session_state so sliders don't reset
    state_key = f"ms_{product}_{role}"
    if state_key not in st.session_state:
        st.session_state[state_key] = make_market_state(product)
    ms_base = st.session_state[state_key]

    # ── Sidebar: competitor prices, all ad spends, all wholesale costs ──
    ms_after_sidebar, scenario = render_sidebar(ms_base, role)

    # ── Main panel: primary decision slider (highlighted) ──
    ms_final, choice_val = render_choice_slider(ms_after_sidebar, role)

    # Persist updated state
    st.session_state[state_key] = ms_final

    # ── Solve equilibrium ──
    eq  = find_equilibrium(ms_final)
    fin = compute_financials(eq, ms_final)

    # ── Equilibrium alert ──
    render_eq_alert(ms_final, eq, role)

    # ── Metric cards ──
    render_metrics(eq, fin, ms_final, role)

    # ── Charts (role-specific tabs) ──
    render_charts(ms_final, eq, fin, role)

    # ── Price sensitivity table ──
    render_sensitivity_table(ms_final, eq, fin, role)

    # ── Export ──
    render_export(ms_final, eq, fin, scenario)

    # ── Footer ──
    color = PRODUCT_COLOR[product]
    st.markdown("---")
    st.markdown(
        f"<small style='color:#999'>Beverage Market Simulator · "
        f"{emoji} {product.title()} · {ROLE_EMOJI[role]} {role_lbl} · "
        f"Equilibrium solved via bisection + Newton-Raphson</small>",
        unsafe_allow_html=True,
    )
