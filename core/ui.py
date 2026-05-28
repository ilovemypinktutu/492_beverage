"""
core/ui.py — Shared Streamlit UI helpers, CSS, metric cards, chart builders,
             glossary, and shock controls.
"""
from __future__ import annotations
import dataclasses
import math
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from core.model import (
    MarketState, EquilibriumResult, Financials,
    find_equilibrium, compute_financials,
    sweep_price, sweep_ad, sweep_wholesale,
    draw_shocks, apply_shocks,
    PRODUCT_DEFAULTS,
)

# ---------------------------------------------------------------------------
# Color helpers  — Plotly requires proper rgba(), not hex+alpha-suffix
# ---------------------------------------------------------------------------
def _hex_to_rgba(hex_color: str, alpha: float = 0.12) -> str:
    """Convert '#RRGGBB' to 'rgba(r,g,b,alpha)' for Plotly fillcolor."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

PRODUCT_COLOR = {
    "coffee": "#6F4E37",
    "soda":   "#1B3A6B",
    "beer":   "#C9A227",
}
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
  .gloss-term {{ font-weight: 700; color: {color}; }}
  .gloss-def  {{ color: #444; font-size: 0.88rem; margin-bottom: 0.6rem; }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fmtk(v: float) -> str:
    sign = "-" if v < 0 else ""
    av   = abs(v)
    if av >= 1_000_000: return f"{sign}${av/1e6:,.2f}M"
    if av >= 1_000:     return f"{sign}${av/1e3:,.1f}K"
    return f"{sign}${av:,.2f}"

def metric_card(label: str, value: str, sub: str = "",
                profit: bool | None = None) -> None:
    extra = " pos" if profit is True else (" neg" if profit is False else "")
    st.markdown(f"""
    <div class="mc">
      <div class="lbl">{label}</div>
      <div class="val{extra}">{value}</div>
      <div class="sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

def section(title: str) -> None:
    st.markdown(f'<div class="shdr">{title}</div>', unsafe_allow_html=True)

def role_banner(product: str, role: str) -> None:
    pe  = PRODUCT_EMOJI[product]
    re  = ROLE_EMOJI[role]
    rl  = ROLE_LABEL[role]
    d   = PRODUCT_DEFAULTS[product]
    c1  = d["comp1"].title(); c2 = d["comp2"].title()
    st.markdown(f"""
    <div class="role-banner">
      <h2>{pe} {product.title()} Market &nbsp;·&nbsp; {re} {rl}</h2>
      <p>Competitors: {c1} &amp; {c2} &nbsp;|&nbsp;
         Your decision variable is highlighted below.</p>
    </div>""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Glossary
# ---------------------------------------------------------------------------
GLOSSARY: list[tuple[str, str, str]] = [
    # (term, symbol, definition)
    ("Equilibrium Price",     "P*",
     "The price at which quantity demanded equals quantity supplied. "
     "The market 'clears' — no unsold inventory and no unmet demand."),
    ("Equilibrium Quantity",  "Q*",
     "The quantity bought and sold when the market is in equilibrium."),
    ("Quantity Demanded",     "Qd",
     "The total amount consumers wish to buy at a given price. "
     "Falls when own price rises; rises when competitor prices rise."),
    ("Quantity Supplied",     "Qs",
     "The total amount sellers are willing and able to offer at a given price. "
     "Rises with price; falls when wholesale cost or upstream power increases."),
    ("Quantity Sold",         "Q_sold",
     "min(Qd, Qs) — actual units transacted. Below equilibrium price, "
     "supply is the constraint; above it, demand is."),
    ("Own-Price Elasticity",  "ε_pp",
     "% change in Qd for a 1% change in own price. "
     "Modelled as a1 (log term) + 2·a_pp·P (quadratic gradient). "
     "Coffee: −1.4, Soda: −1.6, Beer: −1.5 at baseline."),
    ("Cross-Price Elasticity","ε_pc",
     "% change in Qd for a 1% change in a competitor's price. "
     "Positive — when Soda raises its price, Coffee demand rises."),
    ("Advertising Elasticity","ε_adv",
     "% increase in Qd per 1% increase in ad spend. "
     "Diminishing returns captured by a_adv2·Adv² — doubling spend "
     "less than doubles demand."),
    ("Wholesale Cost",        "WC",
     "The price the manufacturer charges the retailer per unit. "
     "Raises COGS and shifts the supply curve left (higher WC → lower Qs)."),
    ("Contribution Margin",   "CM",
     "Revenue per unit minus variable cost per unit: P − WC. "
     "Must be positive for each unit sold to contribute to covering fixed costs."),
    ("Break-Even Volume",     "BEP",
     "Units/week at which total contribution exactly covers total fixed operating "
     "expenses: BEP = OpEx ÷ CM. Below this volume the firm loses money."),
    ("COGS",                  "COGS",
     "Cost of Goods Sold = WC × Q_sold. The direct cost of inventory."),
    ("EBIT",                  "EBIT",
     "Earnings Before Interest & Tax = Gross Profit − OpEx. "
     "Proxy for operating performance before financing and tax effects."),
    ("Net Profit",            "π",
     "EBIT × (1 − tax rate). The bottom line after all costs and taxes."),
    ("Upstream Market Power", "UP",
     "Index [0, 1] measuring the bottler/supplier's bargaining strength. "
     "Enters supply as a cubic: b5·UP + b6·UP² + b7·UP³ — "
     "accelerating margin compression up to near-monopoly levels."),
    ("Idiosyncratic Shock",   "ε",
     "Random disturbance unique to one product-period. "
     "ε_d enters ln(Qd); ε_s enters ln(Qs). Both have std ≈ 6–8%."),
    ("Correlated Shock",      "η",
     "Market-wide or sector-wide disturbance affecting all products simultaneously "
     "(e.g. a sugar-price spike or a consumer health scare). "
     "Own shocks are correlated (ρ ≈ 0.55) with a common sector factor; "
     "competitor choice variables also shift via multiplicative η terms."),
    ("Common Sector Shock",   "z₀",
     "A single normally-distributed draw that drives correlation across all products "
     "and between demand and supply. Simulates macro events — recessions, "
     "regulatory announcements, input-cost movements."),
    ("Interior Profit Maximum","π*",
     "A maximum of the profit function that occurs strictly inside the "
     "feasible range of the choice variable (not at a boundary). "
     "Exists here because demand falls steeply at high prices (quadratic term) "
     "and ad returns diminish; finding π* is the core learning objective."),
    ("Season Index",          "S",
     "Multiplier on beverage demand: 1.0 = average, 1.5 = peak summer, "
     "0.5 = winter trough. Enters as a14·ln(S)."),
    ("Log-Linear Term",       "a·ln(x)",
     "A term of the form coefficient × natural-log(variable). "
     "Implies constant elasticity: a 1% change in x shifts ln(Q) by a percentage points."),
    ("Quadratic Term",        "a·x²",
     "Adds curvature to the relationship. In demand, a_pp·P² makes "
     "the price effect stronger at higher prices, generating a profit peak. "
     "In supply, b_wc2·WC² accelerates the cost squeeze."),
    ("Cubic Term",            "a·x³",
     "Creates an S-curve or inflection in the relationship. "
     "Used for the time trend (growth → plateau → slow revival) and "
     "upstream power (mild compression → severe → slight relief at monopoly)."),
]

def render_glossary() -> None:
    section("📖 Glossary of Terms & Variables")
    search = st.text_input("Filter glossary", placeholder="e.g. elasticity, shock, profit…",
                           key="gloss_search", label_visibility="collapsed")
    query = search.strip().lower()
    shown = [(t, sym, d) for t, sym, d in GLOSSARY
             if not query or query in t.lower() or query in d.lower() or query in sym.lower()]
    if not shown:
        st.caption("No matching terms. Try a shorter keyword.")
        return
    for term, sym, defn in shown:
        st.markdown(
            f'<p><span class="gloss-term">{term}</span> '
            f'<code style="font-size:0.78rem">{sym}</code><br>'
            f'<span class="gloss-def">{defn}</span></p>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Shock panel (sidebar)
# ---------------------------------------------------------------------------
def render_shock_controls(ms: MarketState) -> tuple[MarketState, dict | None]:
    """
    Render shock/noise controls in the sidebar.
    Returns (updated_ms_with_shocks, shocks_dict_or_None).
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### 🎲 Market Shocks")
    st.sidebar.caption(
        "Simulate random market disturbances. Shocks are correlated across "
        "products and between demand and supply."
    )
    use_shocks = st.sidebar.toggle("Enable random shocks", value=False, key="use_shocks")

    if not use_shocks:
        return ms, None

    seed = st.sidebar.number_input(
        "Random seed (change to draw new shocks)", min_value=0, max_value=9999,
        value=42, step=1, key="shock_seed",
        help="Same seed = same shock draw. Change to explore different scenarios."
    )
    shocks = draw_shocks(seed=int(seed))
    ms_with = apply_shocks(ms, shocks)

    # Show shock magnitudes compactly
    col1, col2 = st.sidebar.columns(2)
    d_pct = (math.exp(shocks["eps_d"]) - 1) * 100
    s_pct = (math.exp(shocks["eps_s"]) - 1) * 100
    col1.metric("Demand shock", f"{d_pct:+.1f}%")
    col2.metric("Supply shock", f"{s_pct:+.1f}%")

    d = PRODUCT_DEFAULTS[ms.product]
    c1 = d["comp1"].title(); c2 = d["comp2"].title()
    st.sidebar.caption(
        f"{c1} price shock: {(shocks['eta_c1p']-1)*100:+.1f}%  |  "
        f"{c2} price shock: {(shocks['eta_c2p']-1)*100:+.1f}%"
    )
    return ms_with, shocks


def _shock_banner(shocks: dict | None, ms: MarketState) -> None:
    if not shocks:
        return
    d_pct = (math.exp(shocks["eps_d"]) - 1) * 100
    s_pct = (math.exp(shocks["eps_s"]) - 1) * 100
    d = PRODUCT_DEFAULTS[ms.product]
    c1 = d["comp1"].title(); c2 = d["comp2"].title()
    c1p = (shocks["eta_c1p"] - 1) * 100
    c2p = (shocks["eta_c2p"] - 1) * 100
    st.markdown(
        f'<div class="shock-box"><p>'
        f'⚡ <strong>Active market shocks</strong> (seed {st.session_state.get("shock_seed", 42)}) — '
        f'Demand: <strong>{d_pct:+.1f}%</strong>, '
        f'Supply: <strong>{s_pct:+.1f}%</strong>, '
        f'{c1} price: <strong>{c1p:+.1f}%</strong>, '
        f'{c2} price: <strong>{c2p:+.1f}%</strong>'
        f'</p></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sidebar — student market controls
# ---------------------------------------------------------------------------
def render_sidebar(ms: MarketState, role: str):
    product = ms.product
    d       = PRODUCT_DEFAULTS[product]
    c1_name = d["comp1"].title()
    c2_name = d["comp2"].title()
    emoji   = PRODUCT_EMOJI[product]

    st.sidebar.markdown(f"## {emoji} Market Controls")
    st.sidebar.caption(
        "Adjust market variables. Your primary decision is on the main page."
    )

    with st.sidebar.expander("🏷️ Competitor Retail Prices", expanded=True):
        comp1_price = st.sidebar.slider(
            f"{c1_name} price ($/unit)", 0.50, 8.00,
            float(ms.comp1_price), 0.05, key="cp1")
        comp2_price = st.sidebar.slider(
            f"{c2_name} price ($/unit)", 0.50, 8.00,
            float(ms.comp2_price), 0.05, key="cp2")

    with st.sidebar.expander("📢 Ad Spend ($K/week)", expanded=True):
        own_ad = st.sidebar.slider(
            f"{product.title()} ad spend", 1.0, 300.0,
            float(ms.ad_spend_k), 1.0, key="own_ad")
        comp1_ad = st.sidebar.slider(
            f"{c1_name} ad spend", 1.0, 300.0,
            float(ms.comp1_ad_k), 1.0, key="c1ad")
        comp2_ad = st.sidebar.slider(
            f"{c2_name} ad spend", 1.0, 300.0,
            float(ms.comp2_ad_k), 1.0, key="c2ad")

    with st.sidebar.expander("🏭 Wholesale Costs ($/unit)", expanded=True):
        own_wc = st.sidebar.slider(
            f"{product.title()} wholesale", 0.20, 5.00,
            float(ms.wholesale_cost), 0.05, key="own_wc")
        comp1_wc = st.sidebar.slider(
            f"{c1_name} wholesale", 0.20, 5.00,
            float(ms.comp1_wholesale), 0.05, key="c1wc")
        comp2_wc = st.sidebar.slider(
            f"{c2_name} wholesale", 0.20, 5.00,
            float(ms.comp2_wholesale), 0.05, key="c2wc")

    scenario = st.sidebar.text_input("Scenario label", "My Scenario", key="scenario")

    updated = dataclasses.replace(
        ms,
        comp1_price    = comp1_price,
        comp2_price    = comp2_price,
        ad_spend_k     = own_ad,
        comp1_ad_k     = comp1_ad,
        comp2_ad_k     = comp2_ad,
        wholesale_cost = own_wc,
        comp1_wholesale= comp1_wc,
        comp2_wholesale= comp2_wc,
    )
    return updated, scenario


# ---------------------------------------------------------------------------
# Primary decision slider
# ---------------------------------------------------------------------------
def render_choice_slider(ms: MarketState, role: str):
    product = ms.product

    st.markdown('<div class="choice-box">', unsafe_allow_html=True)

    if role == "price_setter":
        st.markdown("<h3>🏷️ Set Your Retail Price ($/unit)</h3>",
                    unsafe_allow_html=True)
        val = st.slider("Retail price", 0.50, 8.00, float(ms.own_price), 0.01,
                        key="main_choice",
                        help="Primary decision. The profit curve peaks at an interior point — find it.")
        st.caption(
            f"Selected: **${val:.2f}/unit** · "
            f"Wholesale cost: **${ms.wholesale_cost:.2f}** · "
            f"Contribution margin: **${val - ms.wholesale_cost:.2f}/unit**"
        )
        updated = dataclasses.replace(ms, own_price=val)

    elif role == "ad_manager":
        st.markdown("<h3>📢 Set Your Ad Spend ($K/week)</h3>",
                    unsafe_allow_html=True)
        val = st.slider("Ad spend ($K/week)", 1.0, 300.0, float(ms.ad_spend_k), 1.0,
                        key="main_choice",
                        help="More ads boost demand but costs rise linearly — find the profit peak.")
        st.caption(
            f"Selected: **${val:.0f}K/week** · "
            f"Annual budget: **${val*52:.0f}K**"
        )
        updated = dataclasses.replace(ms, ad_spend_k=val)

    else:  # manufacturer
        st.markdown("<h3>🏭 Set Your Wholesale Price ($/unit)</h3>",
                    unsafe_allow_html=True)
        val = st.slider("Wholesale price to retailer", 0.20, 5.00,
                        float(ms.wholesale_cost), 0.05, key="main_choice",
                        help="Higher wholesale earns more margin per unit but shrinks retailer supply.")
        unit_cost = val * 0.40
        st.caption(
            f"Selected: **${val:.2f}/unit** · "
            f"Your estimated unit cost: **${unit_cost:.2f}** · "
            f"Your margin: **${val - unit_cost:.2f}/unit**"
        )
        updated = dataclasses.replace(ms, wholesale_cost=val)

    st.markdown('</div>', unsafe_allow_html=True)
    return updated, val


# ---------------------------------------------------------------------------
# Metrics row
# ---------------------------------------------------------------------------
def render_metrics(eq: EquilibriumResult, fin: Financials,
                   ms: MarketState, role: str) -> None:
    section("📈 Equilibrium & Financial Results")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    profitable = eq.quantity_eq >= fin.break_even_units
    bep_str = (f"{fin.break_even_units:,.0f}"
               if fin.break_even_units != float("inf") else "∞")
    with c1: metric_card("Eq. Price",    f"${eq.price_eq:.3f}", "market-clearing")
    with c2: metric_card("Units Sold",   f"{fin.q_sold:,.0f}",  "min(Qd, Qs)/week")
    with c3: metric_card("Revenue",      fmtk(fin.revenue),      "weekly")
    with c4: metric_card("Gross Profit", fmtk(fin.gross_profit),
                         f"{fin.gross_margin_pct:.1f}% margin")
    with c5: metric_card("Net Profit",   fmtk(fin.net_profit),
                         f"{fin.net_margin_pct:.1f}% margin",
                         profit=(fin.net_profit >= 0))
    with c6: metric_card("Break-even",   f"{bep_str} u/wk",
                         "✅ Profitable" if profitable else "❌ Below BEP",
                         profit=profitable)
    if role == "manufacturer":
        ca, cb = st.columns(2)
        with ca:
            metric_card("Mfr Revenue", fmtk(fin.manufacturer_revenue), "WC × Q_sold")
        with cb:
            metric_card("Mfr Profit",  fmtk(fin.manufacturer_profit),
                        "after mfr costs", profit=(fin.manufacturer_profit >= 0))


# ---------------------------------------------------------------------------
# Equilibrium alert
# ---------------------------------------------------------------------------
def render_eq_alert(ms: MarketState, eq: EquilibriumResult, role: str) -> None:
    if role == "price_setter":
        gap = ms.own_price - eq.price_eq
        if abs(gap) < 0.03:
            st.success(f"✅ Your price **${ms.own_price:.2f}** is at equilibrium "
                       f"(**${eq.price_eq:.3f}**). The market clears with no excess.")
        elif gap > 0:
            st.warning(f"📉 Your price **${ms.own_price:.2f}** is **${gap:.2f} above** "
                       f"equilibrium (${eq.price_eq:.3f}). Excess supply — "
                       f"unsold inventory builds. Check if this is still profitable.")
        else:
            st.warning(f"📈 Your price **${ms.own_price:.2f}** is **${abs(gap):.2f} below** "
                       f"equilibrium (${eq.price_eq:.3f}). Excess demand — "
                       f"you're selling out but leaving margin on the table.")
    elif role == "ad_manager":
        st.info(f"📢 At **${ms.ad_spend_k:.0f}K/week** ad spend, equilibrium clears at "
                f"**${eq.price_eq:.3f}/unit** with **{fin_q(eq):,.0f} units/week**. "
                f"Slide the ad budget and watch the profit curve for the sweet spot.")
    else:
        st.info(f"🏭 Wholesale **${ms.wholesale_cost:.2f}/unit** → retailer equilibrium "
                f"**${eq.price_eq:.3f}** with **{fin_q(eq):,.0f} units/week**. "
                f"Higher WC boosts your margin but shrinks Qs — find the interior peak.")

def fin_q(eq: EquilibriumResult) -> float:
    return min(eq.quantity_demanded, eq.quantity_supplied)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
_CHART_BG = "#FAFCFF"
_CHART_M  = dict(l=0, r=0, t=50, b=0)

def render_charts(ms: MarketState, eq: EquilibriumResult,
                  fin: Financials, role: str) -> None:
    section("📊 Market Charts")
    color = PRODUCT_COLOR[ms.product]

    if role == "price_setter":
        tabs = st.tabs(["Supply & Demand", "Profit vs Price",
                        "Revenue Breakdown", "Competitor Impact"])
        with tabs[0]: _chart_sd(ms, eq, color)
        with tabs[1]: _chart_price_profit(ms, eq, color)
        with tabs[2]: _chart_pie(fin, color)
        with tabs[3]: _chart_competitor_impact(ms, eq, color)

    elif role == "ad_manager":
        tabs = st.tabs(["Profit vs Ad Spend", "Supply & Demand",
                        "Revenue Breakdown", "Ad Effectiveness"])
        with tabs[0]: _chart_ad_profit(ms, eq, color)
        with tabs[1]: _chart_sd(ms, eq, color)
        with tabs[2]: _chart_pie(fin, color)
        with tabs[3]: _chart_ad_effectiveness(ms, eq, color)

    else:
        tabs = st.tabs(["Profit vs Wholesale", "Supply & Demand",
                        "Revenue Breakdown", "Mfr vs Retailer"])
        with tabs[0]: _chart_wc_profit(ms, eq, color)
        with tabs[1]: _chart_sd(ms, eq, color)
        with tabs[2]: _chart_pie(fin, color)
        with tabs[3]: _chart_mfr_retailer(ms, eq, color)


def _layout(title: str, xaxis: str, yaxis: str,
            secondary: str | None = None) -> dict:
    d = dict(title=title, height=420,
             plot_bgcolor=_CHART_BG, paper_bgcolor=_CHART_BG,
             margin=_CHART_M,
             legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    return d


def _chart_sd(ms, eq, color):
    rows  = sweep_price(ms, 0.50, 7.00, 100)
    px    = [r["price"]   for r in rows]
    qd    = [r["qd"]      for r in rows]
    qs    = [r["qs"]      for r in rows]
    ex    = [r["excess"]  for r in rows]
    fill_d = _hex_to_rgba(color, 0.10)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=px, y=qd, name="Demand (Qd)",
                             line=dict(color=color, width=2.5),
                             fill="tozeroy", fillcolor=fill_d),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=px, y=qs, name="Supply (Qs)",
                             line=dict(color="#2ECC71", width=2.5, dash="dash"),
                             fill="tozeroy", fillcolor="rgba(46,204,113,0.08)"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=px, y=ex, name="Excess Demand",
                             line=dict(color="#E67E22", width=1.5, dash="dot")),
                  secondary_y=True)
    fig.add_vline(x=eq.price_eq, line_color="#C0392B", line_dash="dash",
                  line_width=1.5,
                  annotation_text=f"Eq ${eq.price_eq:.2f}",
                  annotation_position="top right")
    if hasattr(ms, "own_price"):
        fig.add_vline(x=ms.own_price, line_color="#8E44AD", line_dash="dot",
                      line_width=1.5, annotation_text="Your price",
                      annotation_position="top left")
    fig.update_layout(**_layout("Supply & Demand Curves",
                                "Price ($/unit)", "Units/week"))
    fig.update_xaxes(title_text="Price ($/unit)")
    fig.update_yaxes(title_text="Units/week", secondary_y=False)
    fig.update_yaxes(title_text="Excess demand (units)", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)


def _chart_price_profit(ms, eq, color):
    rows  = sweep_price(ms, 0.50, 7.00, 120)
    px    = [r["price"]  for r in rows]
    pf    = [r["profit"] for r in rows]
    best_i = max(range(len(pf)), key=lambda i: pf[i])
    opt_p, opt_pf = px[best_i], pf[best_i]
    fill = _hex_to_rgba(color, 0.08)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=px, y=pf, name="Net Profit",
                             line=dict(color=color, width=2.5),
                             fill="tozeroy", fillcolor=fill))
    fig.add_hline(y=0, line_color="#C0392B", line_dash="dash", line_width=1)
    fig.add_vline(x=eq.price_eq, line_color="#27AE60", line_dash="dash",
                  line_width=1.5,
                  annotation_text=f"Eq ${eq.price_eq:.2f}",
                  annotation_position="top right")
    fig.add_vline(x=ms.own_price, line_color="#8E44AD", line_dash="dot",
                  line_width=1.5, annotation_text="Your price",
                  annotation_position="top left")
    fig.add_trace(go.Scatter(x=[opt_p], y=[opt_pf],
                             mode="markers+text",
                             marker=dict(size=12, color="#E74C3C",
                                         symbol="star"),
                             text=[f"  Max π ${opt_p:.2f}"],
                             textposition="middle right",
                             name=f"Profit max"))
    fig.update_layout(**_layout("Net Profit vs. Retail Price",
                                "Retail price ($/unit)", "Net Profit ($)"))
    fig.update_xaxes(title_text="Retail price ($/unit)")
    fig.update_yaxes(title_text="Net Profit ($)")
    st.plotly_chart(fig, use_container_width=True)
    if abs(ms.own_price - opt_p) > 0.12:
        st.info(f"💡 Profit peaks at **${opt_p:.2f}/unit** "
                f"(Net profit: **{fmtk(opt_pf)}**). "
                f"Your current price is **${ms.own_price:.2f}**.")


def _chart_ad_profit(ms, eq, color):
    rows  = sweep_ad(ms, 1.0, 300.0, 100)
    ax    = [r["ad"]     for r in rows]
    pf    = [r["profit"] for r in rows]
    best_i = max(range(len(pf)), key=lambda i: pf[i])
    opt_ad, opt_pf = ax[best_i], pf[best_i]
    fill = _hex_to_rgba(color, 0.08)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ax, y=pf, name="Net Profit",
                             line=dict(color=color, width=2.5),
                             fill="tozeroy", fillcolor=fill))
    fig.add_hline(y=0, line_color="#C0392B", line_dash="dash")
    fig.add_vline(x=ms.ad_spend_k, line_color="#8E44AD", line_dash="dot",
                  annotation_text="Current spend")
    fig.add_trace(go.Scatter(x=[opt_ad], y=[opt_pf],
                             mode="markers+text",
                             marker=dict(size=12, color="#E74C3C", symbol="star"),
                             text=[f"  Max π ${opt_ad:.0f}K"],
                             textposition="middle right",
                             name="Profit max"))
    fig.update_layout(**_layout("Net Profit vs. Ad Spend",
                                "Ad spend ($K/week)", "Net Profit ($)"))
    fig.update_xaxes(title_text="Ad spend ($K/week)")
    fig.update_yaxes(title_text="Net Profit ($)")
    st.plotly_chart(fig, use_container_width=True)
    if abs(ms.ad_spend_k - opt_ad) > 5:
        st.info(f"💡 Profit peaks at **${opt_ad:.0f}K/week** "
                f"(Net profit: **{fmtk(opt_pf)}**). "
                f"Your current spend is **${ms.ad_spend_k:.0f}K/week**.")


def _chart_wc_profit(ms, eq, color):
    rows   = sweep_wholesale(ms, 0.20, 4.50, 100)
    wx     = [r["wc"]         for r in rows]
    rpf    = [r["profit"]     for r in rows]
    mpf    = [r["mfr_profit"] for r in rows]
    best_i = max(range(len(mpf)), key=lambda i: mpf[i])
    opt_wc, opt_mpf = wx[best_i], mpf[best_i]
    fill = _hex_to_rgba(color, 0.08)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=wx, y=mpf, name="Manufacturer Profit",
                             line=dict(color=color, width=2.5),
                             fill="tozeroy", fillcolor=fill))
    fig.add_trace(go.Scatter(x=wx, y=rpf, name="Retailer Net Profit",
                             line=dict(color="#2ECC71", width=1.8, dash="dash")))
    fig.add_hline(y=0, line_color="#C0392B", line_dash="dash")
    fig.add_vline(x=ms.wholesale_cost, line_color="#8E44AD", line_dash="dot",
                  annotation_text="Current WC")
    fig.add_trace(go.Scatter(x=[opt_wc], y=[opt_mpf],
                             mode="markers+text",
                             marker=dict(size=12, color="#E74C3C", symbol="star"),
                             text=[f"  Max π ${opt_wc:.2f}"],
                             textposition="middle right",
                             name="Mfr max"))
    fig.update_layout(**_layout("Manufacturer Profit vs. Wholesale Price",
                                "Wholesale price ($/unit)", "Profit ($)"))
    fig.update_xaxes(title_text="Wholesale price ($/unit)")
    fig.update_yaxes(title_text="Profit ($)")
    st.plotly_chart(fig, use_container_width=True)
    if abs(ms.wholesale_cost - opt_wc) > 0.12:
        st.info(f"💡 Manufacturer profit peaks at **${opt_wc:.2f}/unit** "
                f"(Profit: **{fmtk(opt_mpf)}**). "
                f"Your current price is **${ms.wholesale_cost:.2f}**.")


def _chart_pie(fin, color):
    labels = ["COGS", "Ad Spend", "Transport", "Fixed OH", "Tax"]
    vals   = [fin.cogs, fin.ad_expense, fin.transport_expense,
              fin.fixed_overhead, fin.tax_amount]
    colors = [color, "#0D7377", "#2980B9", "#8E44AD", "#E67E22"]
    if fin.net_profit > 0:
        labels.append("Net Profit")
        vals.append(fin.net_profit)
        colors.append("#1A7A45")
    fig = go.Figure(go.Pie(labels=labels, values=vals, hole=0.42,
                           marker_colors=colors, textinfo="label+percent"))
    fig.update_layout(title=f"Revenue Breakdown  (Total: {fmtk(fin.revenue)})",
                      height=420, plot_bgcolor=_CHART_BG, paper_bgcolor=_CHART_BG,
                      margin=_CHART_M)
    st.plotly_chart(fig, use_container_width=True)


def _chart_competitor_impact(ms, eq, color):
    d = PRODUCT_DEFAULTS[ms.product]
    c1_name = d["comp1"].title()
    c1_range = [round(0.50 + i * 0.14, 2) for i in range(55)]
    own_prices, profits = [], []
    for cp in c1_range:
        ms2  = dataclasses.replace(ms, comp1_price=cp)
        eq2  = find_equilibrium(ms2)
        fin2 = compute_financials(eq2, ms2)
        own_prices.append(eq2.price_eq)
        profits.append(fin2.net_profit)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=c1_range, y=own_prices, name="Your Eq. Price",
                             line=dict(color=color, width=2.5)),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=c1_range, y=profits, name="Your Net Profit",
                             line=dict(color="#E74C3C", width=2, dash="dash")),
                  secondary_y=True)
    fig.add_vline(x=ms.comp1_price, line_color="#8E44AD", line_dash="dot",
                  annotation_text=f"Current {c1_name} price")
    fig.update_layout(**_layout(f"Impact of {c1_name} Price on Your Market",
                                f"{c1_name} price ($/unit)", "Your Eq. Price"))
    fig.update_xaxes(title_text=f"{c1_name} price ($/unit)")
    fig.update_yaxes(title_text="Your Eq. Price ($/unit)", secondary_y=False)
    fig.update_yaxes(title_text="Your Net Profit ($)", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)


def _chart_ad_effectiveness(ms, eq, color):
    rows = sweep_ad(ms, 1.0, 300.0, 100)
    ax   = [r["ad"]    for r in rows]
    roi  = [r["profit"] / (r["ad"] * 1000) if r["ad"] > 0 else 0 for r in rows]
    qty  = [r["qty"]   for r in rows]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=ax, y=roi, name="Profit per $ Ad Spend",
                             line=dict(color=color, width=2.5)),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=ax, y=qty, name="Eq. Quantity",
                             line=dict(color="#2ECC71", width=2, dash="dash")),
                  secondary_y=True)
    fig.add_vline(x=ms.ad_spend_k, line_color="#8E44AD", line_dash="dot",
                  annotation_text="Current")
    fig.update_layout(**_layout("Ad Effectiveness: Return per Dollar Spent",
                                "Ad spend ($K/week)", "Profit / Ad dollar"))
    fig.update_xaxes(title_text="Ad spend ($K/week)")
    fig.update_yaxes(title_text="Profit / Ad dollar", secondary_y=False)
    fig.update_yaxes(title_text="Units/week", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)


def _chart_mfr_retailer(ms, eq, color):
    rows = sweep_wholesale(ms, 0.20, 4.50, 100)
    wx   = [r["wc"]         for r in rows]
    rpf  = [r["profit"]     for r in rows]
    mpf  = [r["mfr_profit"] for r in rows]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=wx, y=mpf, name="Manufacturer Profit",
                             stackgroup="one",
                             line=dict(color=color),
                             fillcolor=_hex_to_rgba(color, 0.5)))
    fig.add_trace(go.Scatter(x=wx, y=rpf, name="Retailer Profit",
                             stackgroup="one",
                             line=dict(color="#2ECC71"),
                             fillcolor="rgba(46,204,113,0.5)"))
    fig.add_vline(x=ms.wholesale_cost, line_color="#8E44AD", line_dash="dot",
                  annotation_text="Current WC")
    fig.update_layout(**_layout("Channel Profit Split: Manufacturer vs Retailer",
                                "Wholesale price ($/unit)", "Profit ($)"))
    fig.update_xaxes(title_text="Wholesale price ($/unit)")
    fig.update_yaxes(title_text="Profit ($)")
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Sensitivity table
# ---------------------------------------------------------------------------
def render_sensitivity_table(ms: MarketState, eq: EquilibriumResult,
                             fin: Financials, role: str) -> None:
    import pandas as pd
    section("🔍 Price Sensitivity Table")
    rows = sweep_price(ms, 0.50, 7.00, 25)
    data = []
    for r in rows:
        near = "✅" if abs(r["price"] - eq.price_eq) < 0.15 else ""
        data.append({
            "Price ($/u)": f"${r['price']:.2f}",
            "Qd":          f"{r['qd']:,.0f}",
            "Qs":          f"{r['qs']:,.0f}",
            "Q_sold":      f"{r['q_sold']:,.0f}",
            "Excess":      f"{r['excess']:+,.0f}",
            "Net Profit":  fmtk(r["profit"]),
            "≈ Eq?":       near,
        })
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def render_export(ms: MarketState, eq: EquilibriumResult,
                  fin: Financials, scenario: str) -> None:
    from core.export import export_xlsx, export_csv
    section("⬇️ Export Results")
    c1, c2 = st.columns(2)
    with c1:
        xlsx = export_xlsx(ms, eq, fin, scenario)
        st.download_button("📥 Download Excel (.xlsx)", data=xlsx,
                           file_name=f"{ms.product}_{scenario.replace(' ','_')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    with c2:
        csv = export_csv(ms, eq, fin, scenario)
        st.download_button("📥 Download CSV (.csv)", data=csv,
                           file_name=f"{ms.product}_{scenario.replace(' ','_')}.csv",
                           mime="text/csv", use_container_width=True)
