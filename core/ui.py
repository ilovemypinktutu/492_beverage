"""
core/ui.py — Shared Streamlit UI helpers.

Changes in this version
-----------------------
- Charts: only Revenue Breakdown + Cost Breakdown (pie/donut)
- No price sensitivity table
- Metrics replaced by a compact results table (units sold, revenue, costs, profit)
- History table: each slider move appends a row; student can download as Excel
- Correlated simulation mode: draws other choice vars from conditional distribution
- Sidebar shows only fixed market conditions (not the 9 choice vars or shocks)
  with tooltip help text on each control
- Glossary removed from page (now a standalone sidebar page)
"""
from __future__ import annotations
import dataclasses
import io
import math
import random
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from core.model import (
    MarketState, EquilibriumResult, Financials,
    find_equilibrium, compute_financials,
    draw_shocks, apply_shocks,
    PRODUCT_DEFAULTS, _MARKET_STATE_VERSION,
)

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
def _hex_to_rgba(hex_color: str, alpha: float = 0.12) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

PRODUCT_COLOR = {"coffee": "#6F4E37", "soda": "#1B3A6B", "beer": "#C9A227"}
PRODUCT_EMOJI = {"coffee": "☕", "soda": "🥤", "beer": "🍺"}
ROLE_EMOJI    = {"price_setter": "🏷️", "ad_manager": "📢", "manufacturer": "🏭"}
ROLE_LABEL    = {
    "price_setter": "Price Setter",
    "ad_manager":   "Ad Spend Manager",
    "manufacturer": "Wholesale Price Setter",
}

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
def inject_css(product: str = "soda") -> None:
    color = PRODUCT_COLOR.get(product, "#1B3A6B")
    st.markdown(f"""
<style>
  [data-testid="stSidebarNav"] {{ display: none !important; }}
  [data-testid="stSidebar"] {{ background: #F4F6FB; }}
  .block-container {{ padding-top: 1.2rem; }}
  .role-banner {{
    background: linear-gradient(135deg, {color}dd, {color}88);
    border-radius: 12px; padding: 1rem 1.5rem;
    color: white; margin-bottom: 1.2rem;
  }}
  .role-banner h2 {{ margin: 0; font-size: 1.5rem; }}
  .role-banner p  {{ margin: 0.2rem 0 0; font-size: 0.88rem; opacity: 0.9; }}
  .mc {{
    background: #F7FAFD; border-radius: 10px;
    padding: 0.85rem 1.1rem; border-left: 4px solid {color};
    margin-bottom: 0.5rem;
  }}
  .mc .lbl {{ font-size: 0.75rem; color: #666; font-weight: 600;
              text-transform: uppercase; letter-spacing: .05em; }}
  .mc .val {{ font-size: 1.45rem; font-weight: 700; color: {color}; }}
  .mc .sub {{ font-size: 0.72rem; color: #888; margin-top: 2px; }}
  .pos {{ color: #1a7a45 !important; }}
  .neg {{ color: #c0392b !important; }}
  .shdr {{
    font-size: 1rem; font-weight: 700; color: {color};
    border-bottom: 2px solid #E0E8F0;
    padding-bottom: 4px; margin: 1.1rem 0 0.7rem;
  }}
  .choice-box {{
    background: {_hex_to_rgba(color, 0.06)};
    border: 1.5px solid {color}55; border-radius: 12px;
    padding: 1rem 1.2rem; margin-bottom: 1rem;
  }}
  .choice-box h3 {{ color: {color}; margin: 0 0 0.5rem; font-size: 1.05rem; }}
  .shock-box {{
    background: #FFF8EC; border: 1px solid #F5A623;
    border-radius: 10px; padding: 0.8rem 1rem; margin-bottom: 0.8rem;
  }}
  .shock-box p {{ margin: 0; font-size: 0.82rem; color: #7A5500; }}
  .mode-badge {{
    display:inline-block; padding:3px 10px; border-radius:20px;
    font-size:0.8rem; font-weight:600;
    background:#E8F4E8; color:#1a7a45; margin-bottom:0.5rem;
  }}
</style>
""", unsafe_allow_html=True)


def fmtk(v: float) -> str:
    sign = "-" if v < 0 else ""
    av   = abs(v)
    if av >= 1_000_000: return f"{sign}${av/1e6:,.2f}M"
    if av >= 1_000:     return f"{sign}${av/1e3:,.1f}K"
    return f"{sign}${av:,.2f}"

def section(title: str) -> None:
    st.markdown(f'<div class="shdr">{title}</div>', unsafe_allow_html=True)

def role_banner(product: str, role: str) -> None:
    pe  = PRODUCT_EMOJI[product]; re = ROLE_EMOJI[role]; rl = ROLE_LABEL[role]
    d   = PRODUCT_DEFAULTS[product]
    c1  = d["comp1"].title(); c2 = d["comp2"].title()
    exp = st.session_state.get("experiment_mode", False)
    mode = "🔬 Free-play" if exp else "📊 Correlated"
    st.markdown(f"""
    <div class="role-banner">
      <h2>{pe} {product.title()} · {re} {rl}</h2>
      <p>Competitors: {c1} &amp; {c2} &nbsp;·&nbsp; Mode: {mode}</p>
    </div>""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar navigation (always shown on role pages)
# ---------------------------------------------------------------------------
def render_sidebar_nav(product: str, role: str) -> None:
    PAGE_MAP = {
        ("coffee","price_setter"): ("pages/1_Coffee_Price_Setter.py",  "☕ Coffee — Price Setter"),
        ("coffee","ad_manager"):   ("pages/2_Coffee_Ad_Manager.py",    "☕ Coffee — Ad Manager"),
        ("coffee","manufacturer"): ("pages/3_Coffee_Manufacturer.py",  "☕ Coffee — Manufacturer"),
        ("soda",  "price_setter"): ("pages/4_Soda_Price_Setter.py",   "🥤 Soda — Price Setter"),
        ("soda",  "ad_manager"):   ("pages/5_Soda_Ad_Manager.py",     "🥤 Soda — Ad Manager"),
        ("soda",  "manufacturer"): ("pages/6_Soda_Manufacturer.py",   "🥤 Soda — Manufacturer"),
        ("beer",  "price_setter"): ("pages/7_Beer_Price_Setter.py",   "🍺 Beer — Price Setter"),
        ("beer",  "ad_manager"):   ("pages/8_Beer_Ad_Manager.py",     "🍺 Beer — Ad Manager"),
        ("beer",  "manufacturer"): ("pages/9_Beer_Manufacturer.py",   "🍺 Beer — Manufacturer"),
    }
    with st.sidebar:
        st.markdown("### 🧃 Navigation")
        st.page_link("app.py",               label="🏠 Home / Setup")
        st.page_link("pages/00_How_It_Works.py", label="ℹ️ How It Works")
        st.page_link("pages/0_Glossary.py", label="📖 Glossary")
        key = (product, role)
        if key in PAGE_MAP:
            path, label = PAGE_MAP[key]
            st.markdown("---")
            st.markdown("**Your simulation:**")
            st.page_link(path, label=f"▶ {label}")


# ---------------------------------------------------------------------------
# Sidebar — fixed market conditions (NOT the 9 choice vars, NOT shocks)
# Tooltips via the `help` parameter explain each variable
# ---------------------------------------------------------------------------
def render_sidebar(ms: MarketState, role: str) -> MarketState:
    """
    Show only the fixed market-condition controls.
    The 9 choice variables (own_price, ad_spend_k, wholesale_cost,
    comp1_price, comp2_price, comp1_ad_k, comp2_ad_k,
    comp1_wholesale, comp2_wholesale) are NOT shown here.
    Shocks are also excluded.
    Returns updated MarketState and scenario label.
    """
    with st.sidebar:
        st.markdown("---")
        st.markdown("#### ⚙️ Market Conditions")
        st.caption("These are the fixed background conditions of your market.")

        with st.expander("📍 Demographics", expanded=False):
            income = st.slider(
                "Local income ($K/yr)",
                25.0, 150.0, float(ms.local_income_k), 1.0,
                help="Median household income in the market area. Higher income → more spending on beverages.")
            unemp = st.slider(
                "Unemployment rate (%)",
                0.0, 20.0, float(ms.unemployment_pct), 0.5,
                help="Local unemployment rate. Higher unemployment reduces consumer spending power.")
            pop_dens = st.slider(
                "Population density (people/sq mi)",
                100.0, 30000.0, float(ms.pop_density), 100.0,
                help="Number of people per square mile. Denser areas support higher total sales volume.")
            age_idx = st.slider(
                "Shopper age index (yrs)",
                18.0, 65.0, float(ms.age_index), 1.0,
                help="Average age of the primary consumer base. Demand peaks for younger adults (~28 yrs) and declines for older demographics.")

        with st.expander("🌤️ Environment", expanded=False):
            season = st.slider(
                "Season index",
                0.50, 1.50, float(ms.season_index), 0.01,
                help="Seasonal demand multiplier: 1.0 = average week, 1.5 = peak summer, 0.5 = winter trough.")
            temp_f = st.slider(
                "Temperature (°F)",
                -10.0, 110.0, float(ms.temperature_f), 1.0,
                help="Average weekly outdoor temperature. Warm weather boosts cold-beverage demand; extreme cold depresses it.")

        with st.expander("😊 Satisfaction Scores", expanded=False):
            csat = st.slider(
                "Consumer satisfaction (0–10)",
                0.0, 10.0, float(ms.consumer_sat), 0.1,
                help="Brand loyalty and customer satisfaction. Higher scores boost demand. Effect is quadratic — gains diminish above ~7.5.")
            esat = st.slider(
                "Employee satisfaction (0–10)",
                0.0, 10.0, float(ms.employee_sat), 0.1,
                help="Workforce morale at the retail/distribution level. Higher satisfaction improves operational efficiency and increases supply.")

        with st.expander("🏭 Operations", expanded=False):
            cap_util = st.slider(
                "Capacity utilization (%)",
                10.0, 100.0, float(ms.capacity_util_pct), 1.0,
                help="Percentage of production/distribution capacity currently in use. Higher utilization increases quantity supplied.")
            energy = st.slider(
                "Energy cost index",
                0.5, 3.0, float(ms.energy_cost_idx), 0.05,
                help="Energy cost relative to baseline (1.0 = normal). Higher energy costs raise production and refrigeration expenses, reducing supply.")
            scarcity = st.slider(
                "Input scarcity (0–1)",
                0.0, 1.0, float(ms.input_scarcity), 0.01,
                help="How constrained key raw materials are (sugar, CO₂, hops, coffee beans). 0 = none, 1 = severe shortage.")
            reg_burden = st.slider(
                "Regulatory burden (0–1)",
                0.0, 1.0, float(ms.regulatory_burden), 0.01,
                help="Composite compliance cost index. Includes labeling, health inspections, and alcohol licensing. Higher burden reduces supply.")
            store_cnt = st.slider(
                "Store count",
                1, 50, int(ms.store_count),
                help="Number of retail outlets actively stocking the product. More stores distribute more total supply.")
            health = st.slider(
                "Health trend (−1 to +1)",
                -1.0, 1.0, float(ms.health_trend), 0.05,
                help="Market-level health-consciousness. Positive = health-aware market (hurts soda/beer, slightly helps coffee). Negative = less health-focused.")


    return dataclasses.replace(
        ms,
        local_income_k    = income,
        unemployment_pct  = unemp,
        pop_density       = pop_dens,
        age_index         = age_idx,
        season_index      = season,
        temperature_f     = temp_f,
        consumer_sat      = csat,
        employee_sat      = esat,
        capacity_util_pct = cap_util,
        energy_cost_idx   = energy,
        input_scarcity    = scarcity,
        regulatory_burden = reg_burden,
        store_count       = float(store_cnt),
        health_trend      = health,
    )


# ---------------------------------------------------------------------------
# Correlated mode — structured, role-specific draws (per spec)
# ---------------------------------------------------------------------------
# All variables are drawn via a log-normal helper:
#   drawn = base * exp(beta * dev + sigma_iid * z)
# where dev = (student_choice - product_default) / product_default
# and z ~ N(0,1) is pure iid noise.
#
# Structural rules (per spec):
#
# MANUFACTURER (sets wholesale price WC)
#   • Own retail price  ↑ with WC (beta=0.85) — retailer passes cost through
#   • Competitor prices NOT correlated (beta=0) — per spec simplification
#   • Supply shock eps_s ↓ with WC (structural beta_s = -0.20 * dev)
#
# AD MANAGER (sets ad spend)
#   • Own retail price  ↑ with Ad (beta=0.60) — premium positioning signal
#   • Competitor prices NOT correlated (beta=0) — per spec simplification
#   • Demand shock eps_d ↑ with Ad (structural component = +0.18 * dev)
#
# PRICE SETTER (sets retail price)
#   • Competitor prices ↑ with own price (beta=0.70) — strategic complementarity
#   • Own wholesale cost co-moves (beta=0.60) — common cost shock
#   • Demand shock eps_d ↑ with price (structural component = +0.15 * dev)
#
# Pure iid shocks (sigma=0.06) are added on top of structural components in
# all roles. These are the ONLY disturbances present in experiment mode.
# ---------------------------------------------------------------------------
def _draw_correlated_others(ms: MarketState, role: str,
                             choice_val: float, seed: int) -> tuple:
    """
    Draw correlated market variables and correlated shocks.
    Returns (updated_ms, shocks_dict).
    """
    d   = PRODUCT_DEFAULTS[ms.product]
    rng = random.Random(seed)

    def draw(base: float, beta: float, dev: float, sigma_idio: float) -> float:
        z = rng.gauss(0.0, 1.0)
        return max(base * math.exp(beta * dev + sigma_idio * z), 0.01)

    # Pure iid shocks — always drawn, uncorrelated with choice variable
    sigma_iid = 0.06
    eps_d_iid = rng.gauss(0.0, 1.0) * sigma_iid
    eps_s_iid = rng.gauss(0.0, 1.0) * sigma_iid

    # Default levels
    own_price_def = d["own_price"];   own_ad_def = d["ad_default"]
    own_wc_def    = d["wc_default"]
    c1_name = d["comp1"];  c2_name = d["comp2"]
    c1p_def  = d["comp1_price"];  c2p_def  = d["comp2_price"]
    c1a_def  = d["comp1_ad"];     c2a_def  = d["comp2_ad"]
    c1wc_def = PRODUCT_DEFAULTS[c1_name]["wc_default"]
    c2wc_def = PRODUCT_DEFAULTS[c2_name]["wc_default"]
    bg = 0.08  # background noise std for structurally unlinked variables

    if role == "manufacturer":
        dev = (choice_val - own_wc_def) / (own_wc_def + 1e-9)
        own_price = draw(own_price_def, 0.85,  dev, 0.08)  # retailer passes WC through
        c1p  = draw(c1p_def,  0.00, dev, bg)   # no structural link
        c2p  = draw(c2p_def,  0.00, dev, bg)
        c1a  = draw(c1a_def,  0.00, dev, bg)
        c2a  = draw(c2a_def,  0.00, dev, bg)
        c1wc = draw(c1wc_def, 0.00, dev, bg)
        c2wc = draw(c2wc_def, 0.00, dev, bg)
        own_ad = draw(own_ad_def, 0.00, dev, bg)
        # Supply shock: higher WC → retailer more reluctant → negative supply shock
        eps_s = -0.20 * dev + eps_s_iid
        eps_d =  0.00       + eps_d_iid

    elif role == "ad_manager":
        dev = (choice_val - own_ad_def) / (own_ad_def + 1e-9)
        own_price = draw(own_price_def, 0.60, dev, 0.08)  # premium positioning
        c1p  = draw(c1p_def,  0.00, dev, bg)   # no structural link
        c2p  = draw(c2p_def,  0.00, dev, bg)
        c1a  = draw(c1a_def,  0.15, dev, bg)   # mild ad arms-race
        c2a  = draw(c2a_def,  0.15, dev, bg)
        c1wc = draw(c1wc_def, 0.00, dev, bg)
        c2wc = draw(c2wc_def, 0.00, dev, bg)
        own_wc = draw(own_wc_def, 0.00, dev, bg)
        # Demand shock: higher Ad → positive demand boost beyond model term
        eps_d =  0.18 * dev + eps_d_iid
        eps_s =  0.00       + eps_s_iid
        ms_out = dataclasses.replace(ms,
            own_price=own_price, ad_spend_k=choice_val, wholesale_cost=own_wc,
            comp1_price=c1p, comp2_price=c2p,
            comp1_ad_k=c1a, comp2_ad_k=c2a,
            comp1_wholesale=c1wc, comp2_wholesale=c2wc,
            eps_d=eps_d, eps_s=eps_s)
        return ms_out, {"eps_d": eps_d, "eps_s": eps_s}

    else:  # price_setter
        dev = (choice_val - own_price_def) / (own_price_def + 1e-9)
        c1p  = draw(c1p_def,  0.70, dev, 0.10)  # strategic complementarity
        c2p  = draw(c2p_def,  0.70, dev, 0.10)
        own_wc = draw(own_wc_def, 0.60, dev, 0.08)  # common cost shock
        c1wc = draw(c1wc_def, 0.15, dev, bg)
        c2wc = draw(c2wc_def, 0.15, dev, bg)
        c1a  = draw(c1a_def,  0.10, dev, bg)
        c2a  = draw(c2a_def,  0.10, dev, bg)
        own_ad = draw(own_ad_def, 0.10, dev, bg)
        # Demand shock: higher price signals quality → mild positive demand shock
        eps_d = 0.15 * dev + eps_d_iid
        eps_s = 0.00       + eps_s_iid
        ms_out = dataclasses.replace(ms,
            own_price=choice_val, ad_spend_k=own_ad, wholesale_cost=own_wc,
            comp1_price=c1p, comp2_price=c2p,
            comp1_ad_k=c1a, comp2_ad_k=c2a,
            comp1_wholesale=c1wc, comp2_wholesale=c2wc,
            eps_d=eps_d, eps_s=eps_s)
        return ms_out, {"eps_d": eps_d, "eps_s": eps_s}

    # manufacturer path (ad_manager and price_setter return early)
    ms_out = dataclasses.replace(ms,
        own_price=own_price, ad_spend_k=own_ad, wholesale_cost=choice_val,
        comp1_price=c1p, comp2_price=c2p,
        comp1_ad_k=c1a, comp2_ad_k=c2a,
        comp1_wholesale=c1wc, comp2_wholesale=c2wc,
        eps_d=eps_d, eps_s=eps_s)
    return ms_out, {"eps_d": eps_d, "eps_s": eps_s}

# ---------------------------------------------------------------------------
# Primary decision slider
# ---------------------------------------------------------------------------
def render_choice_slider(ms: MarketState, role: str):
    product = ms.product
    exp_mode = st.session_state.get("experiment_mode", False)

    st.markdown('<div class="choice-box">', unsafe_allow_html=True)

    if role == "price_setter":
        st.markdown("<h3>🏷️ Set Your Retail Price ($/unit)</h3>",
                    unsafe_allow_html=True)
        val = st.slider("Retail price", 0.50, 8.00, float(ms.own_price), 0.01,
                        key="main_choice",
                        help="Your primary decision. Move to explore how profit changes.")
        st.caption(f"Selected: **${val:.2f}/unit**")
    elif role == "ad_manager":
        st.markdown("<h3>📢 Set Your Ad Spend ($K/week)</h3>",
                    unsafe_allow_html=True)
        val = st.slider("Ad spend ($K/week)", 1.0, 300.0, float(ms.ad_spend_k), 1.0,
                        key="main_choice",
                        help="More ads boost demand but returns diminish. Find the profit peak.")
        st.caption(f"Selected: **${val:.0f}K/week**")
    else:
        st.markdown("<h3>🏭 Set Your Wholesale Price ($/unit)</h3>",
                    unsafe_allow_html=True)
        val = st.slider("Wholesale price to retailer", 0.20, 5.00,
                        float(ms.wholesale_cost), 0.05, key="main_choice",
                        help="Higher WC earns more margin per unit but reduces retailer supply volume.")
        st.caption(f"Selected: **${val:.2f}/unit**")

    st.markdown('</div>', unsafe_allow_html=True)

    # Apply correlated draw if in correlated mode
    if not exp_mode:
        seed = st.session_state.get("corr_seed", 0)
        ms_out, _corr_shocks = _draw_correlated_others(ms, role, val, seed=seed)
    else:
        # Free-play: patch only the student's choice variable
        if role == "price_setter":
            ms_out = dataclasses.replace(ms, own_price=val)
        elif role == "ad_manager":
            ms_out = dataclasses.replace(ms, ad_spend_k=val)
        else:
            ms_out = dataclasses.replace(ms, wholesale_cost=val)

    return ms_out, val


# ---------------------------------------------------------------------------
# Results table (replaces metric cards)
# ---------------------------------------------------------------------------
def render_results_table(eq: EquilibriumResult, fin: Financials,
                          ms: MarketState, role: str, choice_val: float) -> None:
    section("📊 Equilibrium & Financial Results")

    mode = "🔬 Free-play" if st.session_state.get("experiment_mode") else "📊 Correlated"
    role_lbl = ROLE_LABEL[role]

    # Build a one-row summary dict
    if role == "price_setter":
        choice_col = "Price ($/unit)"; choice_disp = f"${choice_val:.2f}"
    elif role == "ad_manager":
        choice_col = "Ad Spend ($K/wk)"; choice_disp = f"${choice_val:.0f}K"
    else:
        choice_col = "Wholesale ($/unit)"; choice_disp = f"${choice_val:.2f}"

    row = {
        choice_col:        choice_disp,
        "Eq. Price":       f"${eq.price_eq:.3f}",
        "Units Sold":      f"{fin.q_sold:,.0f}",
        "Revenue":         fmtk(fin.revenue),
        "Variable Cost":   fmtk(fin.cogs),
        "Gross Profit":    fmtk(fin.gross_profit),
        "OpEx":            fmtk(fin.total_opex),
        "Net Profit":      fmtk(fin.net_profit),
        "Gross Margin":    f"{fin.gross_margin_pct:.1f}%",
        "Net Margin":      f"{fin.net_margin_pct:.1f}%",
    }
    if role == "manufacturer":
        row["Mfr Revenue"] = fmtk(fin.manufacturer_revenue)
        row["Mfr Profit"]  = fmtk(fin.manufacturer_profit)

    st.dataframe(pd.DataFrame([row]), use_container_width=True, hide_index=True)






# ---------------------------------------------------------------------------
# History table — append each run, download as Excel
# ---------------------------------------------------------------------------
def render_history(eq: EquilibriumResult, fin: Financials,
                   ms: MarketState, role: str,
                   choice_val: float, scenario: str) -> None:
    section("📋 Decision History")

    hist_key = f"history_{ms.product}_{role}"
    if hist_key not in st.session_state:
        st.session_state[hist_key] = []

    if role == "price_setter":
        choice_col = "Price ($/unit)"; choice_disp = round(choice_val, 2)
    elif role == "ad_manager":
        choice_col = "Ad Spend ($K/wk)"; choice_disp = round(choice_val, 1)
    else:
        choice_col = "Wholesale ($/unit)"; choice_disp = round(choice_val, 2)

    # Resolve actual competitor product names for this product
    d     = PRODUCT_DEFAULTS[ms.product]
    c1nm  = d["comp1"].title()   # e.g. "Soda" for coffee
    c2nm  = d["comp2"].title()   # e.g. "Beer" for coffee

    new_row = {
        # ── Choice variable ──
        choice_col:                          choice_disp,
        # ── Financial outcomes ──
        "Eq. Price ($)":                     round(eq.price_eq, 4),
        "Units Sold":                        int(fin.q_sold),
        "Revenue ($)":                       round(fin.revenue, 2),
        "Variable Cost ($)":                 round(fin.cogs, 2),
        "Gross Profit ($)":                  round(fin.gross_profit, 2),
        "OpEx ($)":                          round(fin.total_opex, 2),
        "Net Profit ($)":                    round(fin.net_profit, 2),
        "Gross Margin (%)":                  round(fin.gross_margin_pct, 2),
        "Net Margin (%)":                    round(fin.net_margin_pct, 2),
        # ── Competitor choice variables (actual names, not Comp1/Comp2) ──
        f"{c1nm} Price ($)":                 round(ms.comp1_price, 4),
        f"{c2nm} Price ($)":                 round(ms.comp2_price, 4),
        f"{c1nm} Ad ($K/wk)":               round(ms.comp1_ad_k, 2),
        f"{c2nm} Ad ($K/wk)":               round(ms.comp2_ad_k, 2),
        f"{c1nm} Wholesale ($)":             round(ms.comp1_wholesale, 4),
        f"{c2nm} Wholesale ($)":             round(ms.comp2_wholesale, 4),
        "Own Wholesale ($)":                 round(ms.wholesale_cost, 4),
        "Own Ad ($K/wk)":                    round(ms.ad_spend_k, 2),
        # ── Market conditions ──
        "Local Income ($K/yr)":              round(ms.local_income_k, 1),
        "Unemployment (%)":                  round(ms.unemployment_pct, 1),
        "Pop Density":                       round(ms.pop_density, 0),
        "Temperature (°F)":                  round(ms.temperature_f, 1),
        "Season Index":                      round(ms.season_index, 2),
        "Consumer Sat":                      round(ms.consumer_sat, 1),
        "Employee Sat":                      round(ms.employee_sat, 1),
        "Health Trend":                      round(ms.health_trend, 2),
        "Input Scarcity":                    round(ms.input_scarcity, 2),
        "Reg. Burden":                       round(ms.regulatory_burden, 2),
        "Energy Cost Idx":                   round(ms.energy_cost_idx, 2),
        "Store Count":                       int(ms.store_count),
        "Cap. Utilization (%)":              round(ms.capacity_util_pct, 1),
    }
    if role == "manufacturer":
        new_row["Mfr Revenue ($)"] = round(fin.manufacturer_revenue, 2)
        new_row["Mfr Profit ($)"]  = round(fin.manufacturer_profit, 2)

    # Auto-record every result — deduplicate on choice value
    history = st.session_state[hist_key]

    # Migrate any stale rows: rename old "COGS ($)" key → "Variable Cost ($)"
    # and old generic "Comp1"/"Comp2" keys → actual product names.
    # This handles sessions that were open before the rename.
    rename_map = {
        "COGS ($)": "Variable Cost ($)",
        "Comp1 Price ($)": f"{c1nm} Price ($)",
        "Comp2 Price ($)": f"{c2nm} Price ($)",
        "Comp1 Ad ($K/wk)": f"{c1nm} Ad ($K/wk)",
        "Comp2 Ad ($K/wk)": f"{c2nm} Ad ($K/wk)",
        "Comp1 Wholesale ($)": f"{c1nm} Wholesale ($)",
        "Comp2 Wholesale ($)": f"{c2nm} Wholesale ($)",
    }
    for old_row in history:
        for old_key, new_key in rename_map.items():
            if old_key in old_row and new_key not in old_row:
                old_row[new_key] = old_row.pop(old_key)

    if not history or history[-1].get(choice_col) != choice_disp:
        history.append(new_row)
        # Advance shock seed so next slider move gets a fresh draw
        st.session_state['shock_seed_auto'] = st.session_state.get('shock_seed_auto', 42) + 1

    if st.button("🗑️ Clear history", use_container_width=True,
                 help="Remove all recorded results from this session."):
        st.session_state[hist_key] = []
        history = []

    if history:
        df = pd.DataFrame(history)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Download as Excel
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Decision History")
        buf.seek(0)
        st.download_button(
            "📥 Download history as Excel",
            data=buf.getvalue(),
            file_name=f"{ms.product}_{role}_history.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        st.caption("No results recorded yet. Move the slider to generate your first result.")




# ---------------------------------------------------------------------------
# Charts — Revenue Breakdown + Cost Breakdown only
# ---------------------------------------------------------------------------
def render_charts(ms: MarketState, eq: EquilibriumResult,
                  fin: Financials, role: str) -> None:
    section("📊 Market Charts")
    color = PRODUCT_COLOR[ms.product]
    tab1, tab2 = st.tabs(["Revenue Breakdown", "Cost Breakdown"])

    with tab1:
        _chart_revenue_pie(fin, color)
    with tab2:
        _chart_cost_bar(fin, color)


def _chart_revenue_pie(fin: Financials, color: str) -> None:
    """Donut: how revenue is split between costs, taxes, and profit."""
    labels = ["Variable Cost", "Ad Spend", "Transport", "Fixed OH", "Tax"]
    vals   = [max(fin.cogs, 0), max(fin.ad_expense, 0),
              max(fin.transport_expense, 0), max(fin.fixed_overhead, 0),
              max(fin.tax_amount, 0)]
    colors = [color, "#0D7377", "#2980B9", "#8E44AD", "#E67E22"]

    if fin.net_profit > 0:
        labels.append("Net Profit")
        vals.append(fin.net_profit)
        colors.append("#1A7A45")

    if sum(vals) <= 0:
        st.caption("No revenue to display at current settings.")
        return

    fig = go.Figure(go.Pie(
        labels=labels, values=vals, hole=0.45,
        marker_colors=colors, textinfo="label+percent",
        hovertemplate="%{label}: $%{value:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        title=f"Revenue Breakdown — Total: {fmtk(fin.revenue)}",
        height=400, plot_bgcolor="#FAFCFF", paper_bgcolor="#FAFCFF",
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(orientation="v", x=1.02, y=0.5),
    )
    st.plotly_chart(fig, use_container_width=True)


def _chart_cost_bar(fin: Financials, color: str) -> None:
    """Horizontal bar: cost components stacked vs gross profit."""
    categories = ["Variable Cost", "Ad Spend", "Transport", "Fixed OH", "Tax", "Net Profit"]
    values = [fin.cogs, fin.ad_expense, fin.transport_expense,
              fin.fixed_overhead, fin.tax_amount, fin.net_profit]
    colors_bar = [color, "#0D7377", "#2980B9", "#8E44AD", "#E67E22",
                  "#1A7A45" if fin.net_profit >= 0 else "#E74C3C"]

    fig = go.Figure()
    for cat, val, col in zip(categories, values, colors_bar):
        fig.add_trace(go.Bar(
            name=cat, x=[val], y=["Weekly P&L"],
            orientation="h",
            marker_color=col,
            hovertemplate=f"{cat}: $%{{x:,.0f}}<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack",
        title="Cost & Profit Components (weekly $)",
        height=260,
        plot_bgcolor="#FAFCFF", paper_bgcolor="#FAFCFF",
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(orientation="h", y=-0.3),
        xaxis_title="Dollars ($)",
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Shock banner
# ---------------------------------------------------------------------------
def _shock_banner(shocks: dict | None, ms: MarketState) -> None:
    if not shocks:
        return
    d_pct = (math.exp(shocks["eps_d"]) - 1) * 100
    s_pct = (math.exp(shocks["eps_s"]) - 1) * 100
    d  = PRODUCT_DEFAULTS[ms.product]
    c1 = d["comp1"].title(); c2 = d["comp2"].title()
    c1p = (shocks["eta_c1p"] - 1) * 100
    c2p = (shocks["eta_c2p"] - 1) * 100
    st.markdown(
        f'<div class="shock-box"><p>'
        f'⚡ <strong>Active shocks</strong> — '
        f'Demand: <strong>{d_pct:+.1f}%</strong>, '
        f'Supply: <strong>{s_pct:+.1f}%</strong>, '
        f'{c1} price: <strong>{c1p:+.1f}%</strong>, '
        f'{c2} price: <strong>{c2p:+.1f}%</strong>'
        f'</p></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Shock controls — pure iid only (experiment mode); no-op in correlated mode
# ---------------------------------------------------------------------------
def render_shock_controls(ms: MarketState,
                          role: str = "price_setter",
                          choice_val: float | None = None):
    """
    Experiment mode: apply pure iid eps_d and eps_s (uncorrelated with anything).
    Correlated mode: shocks already embedded inside _draw_correlated_others;
                     return ms unchanged.
    """
    exp_mode = st.session_state.get("experiment_mode", False)
    if not exp_mode:
        return ms, None   # shocks already in ms from _draw_correlated_others

    # Experiment mode — pure iid only (spec item 7)
    seed = st.session_state.get("shock_seed_auto", 42)
    rng  = random.Random(int(seed))
    sigma_iid = 0.06
    eps_d = rng.gauss(0.0, 1.0) * sigma_iid
    eps_s = rng.gauss(0.0, 1.0) * sigma_iid
    ms2 = dataclasses.replace(ms, eps_d=eps_d, eps_s=eps_s,
                              eta_c1p=1.0, eta_c2p=1.0,
                              eta_c1a=1.0, eta_c2a=1.0,
                              eta_c1wc=1.0, eta_c2wc=1.0)
    return ms2, {"eps_d": eps_d, "eps_s": eps_s}

# ---------------------------------------------------------------------------
# Equilibrium alert
# ---------------------------------------------------------------------------
def render_eq_alert(ms: MarketState, eq: EquilibriumResult, role: str) -> None:
    if role == "price_setter":
        gap = ms.own_price - eq.price_eq
        if abs(gap) < 0.03:
            st.success(f"✅ Your price **${ms.own_price:.2f}** is at market equilibrium "
                       f"(**${eq.price_eq:.3f}**). The market clears cleanly.")
        elif gap > 0:
            st.warning(f"📉 Your price **${ms.own_price:.2f}** is **${gap:.2f} above** "
                       f"equilibrium (${eq.price_eq:.3f}) — excess supply. "
                       f"Unsold inventory builds up.")
        else:
            st.warning(f"📈 Your price **${ms.own_price:.2f}** is **${abs(gap):.2f} below** "
                       f"equilibrium (${eq.price_eq:.3f}) — excess demand. "
                       f"You're selling out but underpricing.")
    elif role == "ad_manager":
        st.info(
            f"📢 At **${ms.ad_spend_k:.0f}K/week** ad spend, equilibrium clears at "
            f"**${eq.price_eq:.3f}/unit** with **{min(eq.quantity_demanded, eq.quantity_supplied):,.0f}** units/week."
        )
    else:
        st.info(
            f"🏭 Wholesale **${ms.wholesale_cost:.2f}/unit** → retailer equilibrium "
            f"at **${eq.price_eq:.3f}** with **{min(eq.quantity_demanded, eq.quantity_supplied):,.0f}** units/week."
        )


# render_export removed per spec (no "Export Current Scenario" section)
