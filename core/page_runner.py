"""
core/page_runner.py — Single entry point for all 9 role pages.

Layout:
  1. Banner
  2. Decision slider
  3. Results table (table only, no profit signal)
  4. Decision history (auto-recorded, market conditions included)
  5. Market Charts (bottom)
  6. Footer

Shocks are role-aware: render_shock_controls receives role + choice_val
so it can amplify eps_d or eps_s proportional to the student's deviation
from the default value (item 7).
"""
from __future__ import annotations
import streamlit as st

from core.model import (
    MarketState, make_market_state,
    find_equilibrium, compute_financials,
    _MARKET_STATE_VERSION,
)
from core.ui import (
    inject_css, role_banner,
    render_sidebar_nav, render_sidebar, render_shock_controls,
    render_choice_slider,
    render_results_table,
    render_history, render_charts,
    PRODUCT_EMOJI, ROLE_LABEL, ROLE_EMOJI,
)

_REQUIRED_FIELDS = {
    "eps_d", "eps_s", "eta_c1p", "eta_c2p",
    "eta_c1a", "eta_c2a", "eta_c1wc", "eta_c2wc",
    "comp1_ad_k", "comp2_ad_k", "_version",
    "input_scarcity", "regulatory_burden", "health_trend",
}


def _is_valid_ms(obj, product: str) -> bool:
    if not isinstance(obj, MarketState):                       return False
    if getattr(obj, "_version", -1) != _MARKET_STATE_VERSION: return False
    if obj.product != product:                                 return False
    return all(hasattr(obj, f) for f in _REQUIRED_FIELDS)


def _get_or_reset_ms(key: str, product: str) -> MarketState:
    existing = st.session_state.get(key)
    if _is_valid_ms(existing, product):
        return existing
    fresh = make_market_state(product)
    st.session_state[key] = fresh
    return fresh


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

    # ── Guard: auto-confirm if missing from session_state ──
    # When st.switch_page() is used, session_state IS preserved, so confirmed_*
    # will already be set. If a student navigates directly via URL, we still
    # accept them — each page file hardcodes its own product+role, so the page
    # itself IS the access control. We just ensure confirmed_* is set so the
    # sidebar nav and history keys work correctly.
    if st.session_state.get("confirmed_product") != product:
        st.session_state["confirmed_product"] = product
    if st.session_state.get("confirmed_role") != role:
        st.session_state["confirmed_role"] = role

    # ── Sidebar nav ──
    render_sidebar_nav(product, role)

    # ── Banner ──
    role_banner(product, role)

    # ── MarketState ──
    state_key = f"ms_{product}_{role}_v{_MARKET_STATE_VERSION}"
    ms_base = _get_or_reset_ms(state_key, product)

    # ── Sidebar: fixed market conditions ──
    ms_after_sidebar = render_sidebar(ms_base, role)

    # ── Decision slider (before shocks — we need choice_val for shock amplification) ──
    # We pass ms_after_sidebar to get the slider position; shocks applied after.
    ms_for_slider, choice_val = render_choice_slider(ms_after_sidebar, role)

    # ── Shocks: role-aware amplification (item 7) ──
    # Pass role + choice_val so eps_d/eps_s are amplified appropriately.
    ms_after_shocks, _shocks = render_shock_controls(
        ms_for_slider, role=role, choice_val=choice_val
    )

    ms_final = ms_after_shocks
    st.session_state[state_key] = ms_final

    # ── Equilibrium ──
    eq  = find_equilibrium(ms_final)
    fin = compute_financials(eq, ms_final)

    # ── Results table (table only — no profit signal) ──
    render_results_table(eq, fin, ms_final, role, choice_val)

    # ── Decision history ──
    render_history(eq, fin, ms_final, role, choice_val, scenario="")

    # ── Market Charts ──
    render_charts(ms_final, eq, fin, role)

    # ── Footer ──
    st.markdown("---")
    mode = "Correlated" if not st.session_state.get("experiment_mode") else "Free-play"
    st.markdown(
        f"<small style='color:#999'>{emoji} {product.title()} · "
        f"{ROLE_EMOJI[role]} {role_lbl} · Mode: {mode}</small>",
        unsafe_allow_html=True,
    )
