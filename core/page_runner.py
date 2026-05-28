"""
core/page_runner.py
===================
Single function called by all 9 role pages.
"""
from __future__ import annotations
import streamlit as st
from core.model import make_market_state, find_equilibrium, compute_financials
from core.ui import (
    inject_css, role_banner, render_sidebar, render_shock_controls,
    render_choice_slider, render_metrics, render_eq_alert, render_charts,
    render_sensitivity_table, render_export, render_glossary,
    PRODUCT_EMOJI, ROLE_LABEL, ROLE_EMOJI, PRODUCT_COLOR,
    _shock_banner,
)


def run_page(product: str, role: str) -> None:
    emoji    = PRODUCT_EMOJI[product]
    role_lbl = ROLE_LABEL[role]

    st.set_page_config(
        page_title=f"{product.title()} · {role_lbl}",
        page_icon=emoji,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css(product)
    role_banner(product, role)

    # ── Build / retrieve MarketState ──
    state_key = f"ms_{product}_{role}"
    if state_key not in st.session_state:
        st.session_state[state_key] = make_market_state(product)
    ms_base = st.session_state[state_key]

    # ── Sidebar: competitor controls ──
    ms_after_sidebar, scenario = render_sidebar(ms_base, role)

    # ── Sidebar: shock controls ──
    ms_after_shocks, active_shocks = render_shock_controls(ms_after_sidebar)

    # ── Main: primary decision slider ──
    ms_final, choice_val = render_choice_slider(ms_after_shocks, role)
    st.session_state[state_key] = ms_final

    # ── Shock banner (visible on main page when shocks are active) ──
    _shock_banner(active_shocks, ms_final)

    # ── Solve equilibrium ──
    eq  = find_equilibrium(ms_final)
    fin = compute_financials(eq, ms_final)

    # ── Equilibrium alert ──
    render_eq_alert(ms_final, eq, role)

    # ── Metrics ──
    render_metrics(eq, fin, ms_final, role)

    # ── Charts ──
    render_charts(ms_final, eq, fin, role)

    # ── Sensitivity table ──
    render_sensitivity_table(ms_final, eq, fin, role)

    # ── Export ──
    render_export(ms_final, eq, fin, scenario)

    # ── Glossary ──
    st.markdown("---")
    with st.expander("📖 Glossary of Terms & Variables", expanded=False):
        render_glossary()

    # ── Footer ──
    st.markdown("---")
    st.markdown(
        f"<small style='color:#999'>{emoji} {product.title()} · "
        f"{ROLE_EMOJI[role]} {role_lbl} · "
        f"Equilibrium: bisection + Newton-Raphson · "
        f"Shocks: {'active' if active_shocks else 'off'}</small>",
        unsafe_allow_html=True,
    )
