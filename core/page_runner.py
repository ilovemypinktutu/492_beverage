"""
core/page_runner.py
===================
Single function called by all 9 role pages.

Defensive session-state management
-----------------------------------
MarketState grows new fields over time as the model evolves. A stale object
pickled in Streamlit's session_state (from an older code version) will be
missing those fields, causing TypeError on dataclasses.replace().

The guard below detects stale objects two ways:
  1. _version sentinel mismatch
  2. Missing any expected field (hasattr check)
Either condition triggers a fresh make_market_state() call, discarding the
stale object. Students simply lose their slider positions — no crash.
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
    inject_css, role_banner, render_sidebar, render_shock_controls,
    render_choice_slider, render_metrics, render_eq_alert, render_charts,
    render_sensitivity_table, render_export, render_glossary,
    PRODUCT_EMOJI, ROLE_LABEL, ROLE_EMOJI,
    _shock_banner,
)

# Fields that MUST exist on a valid MarketState (subset check)
_REQUIRED_FIELDS = {"eps_d", "eps_s", "eta_c1p", "eta_c2p",
                    "eta_c1a", "eta_c2a", "eta_c1wc", "eta_c2wc",
                    "comp1_ad_k", "comp2_ad_k", "_version"}


def _is_valid_ms(obj, product: str) -> bool:
    """Return True iff obj is a current, correct MarketState for product."""
    if not isinstance(obj, MarketState):
        return False
    if getattr(obj, "_version", -1) != _MARKET_STATE_VERSION:
        return False
    if obj.product != product:
        return False
    # Check all required fields exist as real attributes
    for field in _REQUIRED_FIELDS:
        if not hasattr(obj, field):
            return False
    return True


def _get_or_reset_ms(state_key: str, product: str) -> MarketState:
    """Retrieve session MarketState or create fresh if stale/missing."""
    existing = st.session_state.get(state_key)
    if _is_valid_ms(existing, product):
        return existing
    # Stale or missing — create fresh and store
    fresh = make_market_state(product)
    st.session_state[state_key] = fresh
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
    role_banner(product, role)

    # ── Retrieve or initialise MarketState (with stale-object guard) ──
    state_key = f"ms_{product}_{role}_v{_MARKET_STATE_VERSION}"
    ms_base = _get_or_reset_ms(state_key, product)

    # ── Sidebar: competitor prices, all ad spends, all wholesale costs ──
    ms_after_sidebar, scenario = render_sidebar(ms_base, role)

    # ── Sidebar: shock controls ──
    ms_after_shocks, active_shocks = render_shock_controls(ms_after_sidebar)

    # ── Main panel: primary decision slider ──
    ms_final, _choice_val = render_choice_slider(ms_after_shocks, role)

    # Persist (always a valid, current MarketState)
    st.session_state[state_key] = ms_final

    # ── Active shock banner ──
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

    # ── Price sensitivity table ──
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
