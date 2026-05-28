"""
core/page_runner.py — Single entry point for all 9 role pages.

Layout order (per spec):
  1. Banner
  2. Decision slider (choice variable)
  3. Shock banner (always active)
  4. Equilibrium alert
  5. Results table
  6. Decision history (auto-recorded, downloadable)
  7. Market Charts (at the bottom)
  8. Footer
"""
from __future__ import annotations
import dataclasses
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
    render_eq_alert, render_results_table,
    render_history, render_charts,
    _shock_banner,
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

    # ── Guard: redirect if student hasn't confirmed this product+role ──
    confirmed_product = st.session_state.get("confirmed_product")
    confirmed_role    = st.session_state.get("confirmed_role")
    if confirmed_product != product or confirmed_role != role:
        st.warning(
            "⚠️ Please go to the **Home / Setup** page, choose your product "
            "and role, then return here via the sidebar link."
        )
        st.page_link("app.py", label="🏠 Go to Home / Setup")
        st.stop()

    # ── Sidebar navigation ──
    render_sidebar_nav(product, role)

    # ── Banner ──
    role_banner(product, role)

    # ── MarketState (stale-object safe) ──
    state_key = f"ms_{product}_{role}_v{_MARKET_STATE_VERSION}"
    ms_base = _get_or_reset_ms(state_key, product)

    # ── Sidebar: fixed market conditions only (no choice vars, no shocks) ──
    ms_after_sidebar = render_sidebar(ms_base, role)

    # ── Shocks: always on, auto seed ──
    ms_after_shocks, active_shocks = render_shock_controls(ms_after_sidebar)

    # ── Main: decision slider + correlated draw ──
    ms_final, choice_val = render_choice_slider(ms_after_shocks, role)
    st.session_state[state_key] = ms_final

    # ── Shock banner ──
    _shock_banner(active_shocks, ms_final)

    # ── Equilibrium ──
    eq  = find_equilibrium(ms_final)
    fin = compute_financials(eq, ms_final)

    # ── Equilibrium alert ──
    render_eq_alert(ms_final, eq, role)

    # ── Results table ──
    render_results_table(eq, fin, ms_final, role, choice_val)

    # ── Decision history (auto-recorded, with Excel download) ──
    render_history(eq, fin, ms_final, role, choice_val, scenario="")

    # ── Market Charts — at the bottom ──
    render_charts(ms_final, eq, fin, role)

    # ── Footer ──
    st.markdown("---")
    mode = "Correlated" if not st.session_state.get("experiment_mode") else "Free-play"
    st.markdown(
        f"<small style='color:#999'>{emoji} {product.title()} · "
        f"{ROLE_EMOJI[role]} {role_lbl} · Mode: {mode}</small>",
        unsafe_allow_html=True,
    )
