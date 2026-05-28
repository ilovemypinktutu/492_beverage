"""
core/ui.py
==========
Shared Streamlit UI helpers, CSS, metric cards, and chart builders.
Imported by app.py and all role pages.
"""
from __future__ import annotations
import math
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from core.model import (
    MarketState, EquilibriumResult, Financials,
    find_equilibrium, compute_financials,
    sweep_price, sweep_ad, sweep_wholesale,
    PRODUCT_DEFAULTS,
)

# ---------------------------------------------------------------------------
# Brand palette
# ---------------------------------------------------------------------------
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
# CSS injection
# ---------------------------------------------------------------------------
def inject_css(product: str = "soda") -> None:
    color = PRODUCT_COLOR.get(product, "#1B3A6B")
    st.markdown(f"""
<style>
  /* ── global ── */
  [data-testid="stSidebar"] {{ background: #F4F6FB; }}
  .block-container {{ padding-top: 1.2rem; }}

  /* ── role banner ── */
  .role-banner {{
    background: linear-gradient(135deg, {color}EE, {color}99);
    border-radius: 12px; padding: 1rem 1.5rem;
    color: white; margin-bottom: 1.2rem;
  }}
  .role-banner h2 {{ margin: 0; font-size: 1.5rem; }}
  .role-banner p  {{ margin: 0.2rem 0 0; font-size: 0.88rem; opacity: 0.9; }}

  /* ── metric cards ── */
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

  /* ── section header ── */
  .shdr {{
    font-size: 1rem; font-weight: 700; color: {color};
    border-bottom: 2px solid #E0E8F0;
    padding-bottom: 4px; margin: 1.1rem 0 0.7rem;
  }}

  /* ── choice slider highlight ── */
  .choice-box {{
    background: linear-gradient(135deg, {color}18, {color}08);
    border: 1.5px solid {color}55; border-radius: 12px;
    padding: 1rem 1.2rem; margin-bottom: 1rem;
  }}
  .choice-box h3 {{ color: {color}; margin: 0 0 0.5rem; font-size: 1.05rem; }}
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
    color = PRODUCT_COLOR.get(product, "#1B3A6B")
    pe    = PRODUCT_EMOJI[product]
    re    = ROLE_EMOJI[role]
    rl    = ROLE_LABEL[role]
    comp  = PRODUCT_DEFAULTS[product]
    c1    = comp["comp1"].title()
    c2    = comp["comp2"].title()
    st.markdown(f"""
    <div class="role-banner">
      <h2>{pe} {product.title()} Market &nbsp;·&nbsp; {re} {rl}</h2>
      <p>Competitors: {c1} &amp; {c2} &nbsp;|&nbsp;
         Your decision variable is highlighted below.</p>
    </div>""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar — student-visible controls only (role-dependent)
# ---------------------------------------------------------------------------
def render_sidebar(ms: MarketState, role: str) -> MarketState:
    """
    Render only the controls the student is allowed to see and modify.
    Returns an updated MarketState.
    """
    product = ms.product
    d       = PRODUCT_DEFAULTS[product]
    color   = PRODUCT_COLOR[product]
    c1_name = d["comp1"].title()
    c2_name = d["comp2"].title()
    emoji   = PRODUCT_EMOJI[product]

    st.sidebar.markdown(f"## {emoji} Market Controls")
    st.sidebar.caption(
        "Adjust the variables below. Your primary decision variable "
        "is shown on the main page."
    )

    # ── Competitor prices (always visible) ──
    with st.sidebar.expander(f"🏷️ Competitor Retail Prices", expanded=True):
        comp1_price = st.sidebar.slider(
            f"{c1_name} price ($/unit)",
            0.50, 8.00, float(ms.comp1_price), 0.05,
            key="cp1")
        comp2_price = st.sidebar.slider(
            f"{c2_name} price ($/unit)",
            0.50, 8.00, float(ms.comp2_price), 0.05,
            key="cp2")

    # ── Ad spends (all three visible, own ad is primary for ad_manager) ──
    with st.sidebar.expander("📢 Advertising Spend ($K/week)", expanded=True):
        if role == "ad_manager":
            # Own ad spend is the main decision — shown in sidebar too for compactness
            own_ad = st.sidebar.slider(
                f"Your {product.title()} ad spend", 1.0, 300.0,
                float(ms.ad_spend_k), 1.0, key="own_ad")
        else:
            own_ad = st.sidebar.slider(
                f"{product.title()} ad spend", 1.0, 300.0,
                float(ms.ad_spend_k), 1.0, key="own_ad")
        comp1_ad = st.sidebar.slider(
            f"{c1_name} ad spend", 1.0, 300.0,
            float(ms.comp1_ad_k), 1.0, key="c1ad")
        comp2_ad = st.sidebar.slider(
            f"{c2_name} ad spend", 1.0, 300.0,
            float(ms.comp2_ad_k), 1.0, key="c2ad")

    # ── Wholesale prices (all three visible, own wc is primary for manufacturer) ──
    with st.sidebar.expander("🏭 Wholesale Costs ($/unit)", expanded=True):
        if role == "manufacturer":
            own_wc = st.sidebar.slider(
                f"Your {product.title()} wholesale price",
                0.20, 5.00, float(ms.wholesale_cost), 0.05, key="own_wc")
        else:
            own_wc = st.sidebar.slider(
                f"{product.title()} wholesale cost",
                0.20, 5.00, float(ms.wholesale_cost), 0.05, key="own_wc")
        comp1_wc = st.sidebar.slider(
            f"{c1_name} wholesale cost", 0.20, 5.00,
            float(ms.comp1_wholesale), 0.05, key="c1wc")
        comp2_wc = st.sidebar.slider(
            f"{c2_name} wholesale cost", 0.20, 5.00,
            float(ms.comp2_wholesale), 0.05, key="c2wc")

    # Scenario label
    scenario = st.sidebar.text_input("Scenario label", "My Scenario", key="scenario")

    # Build updated MarketState
    import dataclasses
    updated = dataclasses.replace(
        ms,
        comp1_price   = comp1_price,
        comp2_price   = comp2_price,
        ad_spend_k    = own_ad,
        comp1_ad_k    = comp1_ad,
        comp2_ad_k    = comp2_ad,
        wholesale_cost= own_wc,
        comp1_wholesale= comp1_wc,
        comp2_wholesale= comp2_wc,
    )
    return updated, scenario


# ---------------------------------------------------------------------------
# Primary decision slider (main page, highlighted)
# ---------------------------------------------------------------------------
def render_choice_slider(ms: MarketState, role: str):
    """
    Render the student's primary decision slider prominently.
    Returns (updated_ms, choice_value).
    """
    import dataclasses
    product = ms.product
    color   = PRODUCT_COLOR[product]
    d       = PRODUCT_DEFAULTS[product]

    st.markdown('<div class="choice-box">', unsafe_allow_html=True)

    if role == "price_setter":
        st.markdown(f"<h3>🏷️ Set Your Retail Price ($/unit)</h3>", unsafe_allow_html=True)
        lo, hi, step = 0.50, 8.00, 0.01
        val = st.slider("Retail price", lo, hi, float(ms.own_price), step,
                        key="main_choice",
                        help="This is your primary decision. Drag to explore profit.")
        st.caption(f"Selected: **${val:.2f}/unit** &nbsp;|&nbsp; "
                   f"Wholesale cost: **${ms.wholesale_cost:.2f}/unit** &nbsp;|&nbsp; "
                   f"Contribution margin: **${val - ms.wholesale_cost:.2f}/unit**")
        updated = dataclasses.replace(ms, own_price=val)

    elif role == "ad_manager":
        st.markdown(f"<h3>📢 Set Your Ad Spend ($K/week)</h3>", unsafe_allow_html=True)
        lo, hi, step = 1.0, 300.0, 1.0
        val = st.slider("Ad spend ($K/week)", lo, hi, float(ms.ad_spend_k), step,
                        key="main_choice",
                        help="Higher ad spend boosts demand but costs money. Find the sweet spot.")
        st.caption(f"Selected: **${val:.0f}K/week** &nbsp;|&nbsp; "
                   f"Annual ad budget: **${val*52:.0f}K**")
        updated = dataclasses.replace(ms, ad_spend_k=val)

    else:  # manufacturer
        st.markdown(f"<h3>🏭 Set Your Wholesale Price ($/unit)</h3>", unsafe_allow_html=True)
        lo, hi, step = 0.20, 5.00, 0.05
        val = st.slider("Wholesale price to retailer", lo, hi,
                        float(ms.wholesale_cost), step,
                        key="main_choice",
                        help="Higher wholesale price earns more per unit but reduces retailer supply.")
        unit_cost = val * 0.40
        st.caption(f"Selected: **${val:.2f}/unit** &nbsp;|&nbsp; "
                   f"Your unit cost (est.): **${unit_cost:.2f}** &nbsp;|&nbsp; "
                   f"Your unit margin: **${val - unit_cost:.2f}**")
        updated = dataclasses.replace(ms, wholesale_cost=val)

    st.markdown('</div>', unsafe_allow_html=True)
    return updated, val


# ---------------------------------------------------------------------------
# Metric row
# ---------------------------------------------------------------------------
def render_metrics(eq: EquilibriumResult, fin: Financials,
                   ms: MarketState, role: str) -> None:
    section("📈 Equilibrium & Financial Results")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    profitable = eq.quantity_eq >= fin.break_even_units
    bep_str = (f"{fin.break_even_units:,.0f}" if fin.break_even_units != float("inf") else "∞")

    with c1: metric_card("Eq. Price",    f"${eq.price_eq:.3f}", "market-clearing")
    with c2: metric_card("Eq. Quantity", f"{eq.quantity_eq:,.0f}", "units/week")
    with c3: metric_card("Revenue",      fmtk(fin.revenue), "weekly")
    with c4: metric_card("Gross Profit", fmtk(fin.gross_profit),
                         f"{fin.gross_margin_pct:.1f}% margin")
    with c5: metric_card("Net Profit",   fmtk(fin.net_profit),
                         f"{fin.net_margin_pct:.1f}% margin",
                         profit=(fin.net_profit >= 0))
    with c6: metric_card("Break-even",   f"{bep_str} u/wk",
                         "✅ Profitable" if profitable else "❌ Below BEP",
                         profit=profitable)

    # Manufacturer gets extra row
    if role == "manufacturer":
        ca, cb = st.columns(2)
        with ca:
            metric_card("Manufacturer Revenue", fmtk(fin.manufacturer_revenue),
                        "wholesale × qty")
        with cb:
            metric_card("Manufacturer Profit", fmtk(fin.manufacturer_profit),
                        "after mfr costs", profit=(fin.manufacturer_profit >= 0))


# ---------------------------------------------------------------------------
# Equilibrium alert
# ---------------------------------------------------------------------------
def render_eq_alert(ms: MarketState, eq: EquilibriumResult, role: str) -> None:
    if role == "price_setter":
        gap = ms.own_price - eq.price_eq
        if abs(gap) < 0.03:
            st.success(f"✅ Your price **${ms.own_price:.2f}** is at equilibrium "
                       f"(**${eq.price_eq:.3f}**). Market clears cleanly.")
        elif gap > 0:
            st.warning(f"📉 Your price **${ms.own_price:.2f}** is **${gap:.2f} above** "
                       f"equilibrium (${eq.price_eq:.3f}). Expect excess supply — "
                       f"unsold inventory builds up.")
        else:
            st.warning(f"📈 Your price **${ms.own_price:.2f}** is **${abs(gap):.2f} below** "
                       f"equilibrium (${eq.price_eq:.3f}). Excess demand — "
                       f"you're underpricing, leaving margin on the table.")
    elif role == "ad_manager":
        st.info(f"📢 At **${ms.ad_spend_k:.0f}K/week** ad spend, equilibrium clears at "
                f"**${eq.price_eq:.3f}/unit** with **{eq.quantity_eq:,.0f} units/week**. "
                f"Watch the profit curve for the optimal ad budget.")
    else:
        st.info(f"🏭 Wholesale price **${ms.wholesale_cost:.2f}/unit** → retailer equilibrium "
                f"at **${eq.price_eq:.3f}** with **{eq.quantity_eq:,.0f} units/week**. "
                f"Higher wholesale boosts your margin but shrinks supply volume.")


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def render_charts(ms: MarketState, eq: EquilibriumResult,
                  fin: Financials, role: str) -> None:
    section("📊 Market Charts")
    product = ms.product
    color   = PRODUCT_COLOR[product]

    # Choose tabs based on role
    if role == "price_setter":
        tabs = st.tabs(["Supply & Demand", "Profit vs Price",
                        "Revenue Breakdown", "Competitor Impact"])
    elif role == "ad_manager":
        tabs = st.tabs(["Profit vs Ad Spend", "Supply & Demand",
                        "Revenue Breakdown", "Ad Effectiveness"])
    else:
        tabs = st.tabs(["Profit vs Wholesale", "Supply & Demand",
                        "Revenue Breakdown", "Mfr vs Retailer Profit"])

    # ── Tab A ──
    with tabs[0]:
        if role == "price_setter":
            _chart_sd(ms, eq, color)
        elif role == "ad_manager":
            _chart_ad_profit(ms, eq, color)
        else:
            _chart_wc_profit(ms, eq, color)

    # ── Tab B ──
    with tabs[1]:
        if role == "price_setter":
            _chart_price_profit(ms, eq, color)
        else:
            _chart_sd(ms, eq, color)

    # ── Tab C — Revenue breakdown ──
    with tabs[2]:
        _chart_pie(fin, eq, color)

    # ── Tab D ──
    with tabs[3]:
        if role == "price_setter":
            _chart_competitor_impact(ms, eq, color)
        elif role == "ad_manager":
            _chart_ad_effectiveness(ms, eq, color)
        else:
            _chart_mfr_retailer(ms, eq, color)


def _chart_sd(ms, eq, color):
    rows = sweep_price(ms, p_min=0.50, p_max=7.00, steps=80)
    px   = [r["price"] for r in rows]
    qd   = [r["qd"]    for r in rows]
    qs   = [r["qs"]    for r in rows]
    fig  = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=px, y=qd, name="Demand",
                             line=dict(color=color, width=2.5),
                             fill="tozeroy", fillcolor=f"{color}12"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=px, y=qs, name="Supply",
                             line=dict(color="#2ECC71", width=2.5, dash="dash"),
                             fill="tozeroy", fillcolor="#2ECC7112"),
                  secondary_y=False)
    ex = [r["excess"] for r in rows]
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
    fig.update_layout(title="Supply & Demand Curves", height=420,
                      legend=dict(orientation="h", y=1.08),
                      plot_bgcolor="#FAFCFF", paper_bgcolor="#FAFCFF",
                      margin=dict(l=0, r=0, t=50, b=0))
    fig.update_xaxes(title_text="Price ($/unit)")
    fig.update_yaxes(title_text="Units/week", secondary_y=False)
    fig.update_yaxes(title_text="Excess demand", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)


def _chart_price_profit(ms, eq, color):
    rows = sweep_price(ms, p_min=0.50, p_max=7.00, steps=80)
    px   = [r["price"]  for r in rows]
    pf   = [r["profit"] for r in rows]
    # Find local maximum
    best_i = max(range(len(pf)), key=lambda i: pf[i])
    opt_p  = px[best_i]
    opt_pf = pf[best_i]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=px, y=pf, name="Net Profit",
                             line=dict(color=color, width=2.5),
                             fill="tozeroy", fillcolor=f"{color}10"))
    fig.add_hline(y=0, line_color="#C0392B", line_dash="dash", line_width=1)
    fig.add_vline(x=eq.price_eq, line_color="#27AE60", line_dash="dash",
                  line_width=1.5,
                  annotation_text=f"Eq ${eq.price_eq:.2f}")
    fig.add_vline(x=ms.own_price, line_color="#8E44AD", line_dash="dot",
                  line_width=1.5, annotation_text="Your price")
    fig.add_trace(go.Scatter(x=[opt_p], y=[opt_pf],
                             mode="markers+text",
                             marker=dict(size=12, color="#E74C3C"),
                             text=[f"Max π\n${opt_p:.2f}"],
                             textposition="top center",
                             name="Profit max"))
    fig.update_layout(title="Net Profit vs. Retail Price",
                      height=420, plot_bgcolor="#FAFCFF", paper_bgcolor="#FAFCFF",
                      margin=dict(l=0, r=0, t=50, b=0))
    fig.update_xaxes(title_text="Retail price ($/unit)")
    fig.update_yaxes(title_text="Net Profit ($)")
    st.plotly_chart(fig, use_container_width=True)

    if abs(ms.own_price - opt_p) > 0.10:
        st.info(f"💡 Profit is maximized at approximately **${opt_p:.2f}/unit** "
                f"(Net profit: **{fmtk(opt_pf)}**). "
                f"Your current price is **${ms.own_price:.2f}**.")


def _chart_ad_profit(ms, eq, color):
    rows = sweep_ad(ms, ad_min=1.0, ad_max=300.0, steps=80)
    ax   = [r["ad"]     for r in rows]
    pf   = [r["profit"] for r in rows]
    best_i = max(range(len(pf)), key=lambda i: pf[i])
    opt_ad = ax[best_i]
    opt_pf = pf[best_i]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ax, y=pf, name="Net Profit",
                             line=dict(color=color, width=2.5),
                             fill="tozeroy", fillcolor=f"{color}10"))
    fig.add_hline(y=0, line_color="#C0392B", line_dash="dash")
    fig.add_vline(x=ms.ad_spend_k, line_color="#8E44AD", line_dash="dot",
                  annotation_text="Current spend")
    fig.add_trace(go.Scatter(x=[opt_ad], y=[opt_pf],
                             mode="markers+text",
                             marker=dict(size=12, color="#E74C3C"),
                             text=[f"Max π\n${opt_ad:.0f}K"],
                             textposition="top center", name="Profit max"))
    fig.update_layout(title="Net Profit vs. Ad Spend",
                      height=420, plot_bgcolor="#FAFCFF", paper_bgcolor="#FAFCFF",
                      margin=dict(l=0, r=0, t=50, b=0))
    fig.update_xaxes(title_text="Ad spend ($K/week)")
    fig.update_yaxes(title_text="Net Profit ($)")
    st.plotly_chart(fig, use_container_width=True)

    if abs(ms.ad_spend_k - opt_ad) > 5:
        st.info(f"💡 Profit is maximized at approximately **${opt_ad:.0f}K/week** "
                f"(Net profit: **{fmtk(opt_pf)}**). "
                f"Your current spend is **${ms.ad_spend_k:.0f}K/week**.")


def _chart_wc_profit(ms, eq, color):
    rows = sweep_wholesale(ms, wc_min=0.20, wc_max=4.50, steps=80)
    wx   = [r["wc"]         for r in rows]
    rpf  = [r["profit"]     for r in rows]
    mpf  = [r["mfr_profit"] for r in rows]
    best_i  = max(range(len(mpf)), key=lambda i: mpf[i])
    opt_wc  = wx[best_i]
    opt_mpf = mpf[best_i]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=wx, y=mpf, name="Manufacturer Profit",
                             line=dict(color=color, width=2.5),
                             fill="tozeroy", fillcolor=f"{color}10"))
    fig.add_trace(go.Scatter(x=wx, y=rpf, name="Retailer Net Profit",
                             line=dict(color="#2ECC71", width=1.8, dash="dash")))
    fig.add_hline(y=0, line_color="#C0392B", line_dash="dash")
    fig.add_vline(x=ms.wholesale_cost, line_color="#8E44AD", line_dash="dot",
                  annotation_text="Current WC")
    fig.add_trace(go.Scatter(x=[opt_wc], y=[opt_mpf],
                             mode="markers+text",
                             marker=dict(size=12, color="#E74C3C"),
                             text=[f"Max π\n${opt_wc:.2f}"],
                             textposition="top center", name="Mfr max"))
    fig.update_layout(title="Manufacturer Profit vs. Wholesale Price",
                      height=420, plot_bgcolor="#FAFCFF", paper_bgcolor="#FAFCFF",
                      margin=dict(l=0, r=0, t=50, b=0))
    fig.update_xaxes(title_text="Wholesale price ($/unit)")
    fig.update_yaxes(title_text="Profit ($)")
    st.plotly_chart(fig, use_container_width=True)

    if abs(ms.wholesale_cost - opt_wc) > 0.10:
        st.info(f"💡 Your manufacturer profit peaks at **${opt_wc:.2f}/unit** wholesale "
                f"(Profit: **{fmtk(opt_mpf)}**). "
                f"Your current price is **${ms.wholesale_cost:.2f}**.")


def _chart_pie(fin, eq, color):
    labels = ["COGS", "Ad Spend", "Transport", "Fixed OH", "Tax"]
    vals   = [fin.cogs, fin.ad_expense, fin.transport_expense,
              fin.fixed_overhead, fin.tax_amount]
    np_val = fin.net_profit
    if np_val > 0:
        labels.append("Net Profit")
        vals.append(np_val)
        colors = [color, "#0D7377", "#2980B9", "#8E44AD", "#E67E22", "#1A7A45"]
    else:
        colors = [color, "#0D7377", "#2980B9", "#8E44AD", "#E67E22"]
    fig = go.Figure(go.Pie(labels=labels, values=vals, hole=0.42,
                           marker_colors=colors, textinfo="label+percent"))
    fig.update_layout(title=f"Revenue Breakdown  (Total: {fmtk(fin.revenue)})",
                      height=420, plot_bgcolor="#FAFCFF", paper_bgcolor="#FAFCFF",
                      margin=dict(l=0, r=0, t=50, b=0))
    st.plotly_chart(fig, use_container_width=True)


def _chart_competitor_impact(ms, eq, color):
    """Show how changing competitor prices affects own equilibrium price & profit."""
    import dataclasses, numpy as np
    c1_range  = [round(0.50 + i * 0.15, 2) for i in range(50)]
    own_prices = []
    profits    = []
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
                  annotation_text=f"Current {PRODUCT_DEFAULTS[ms.product]['comp1'].title()} price")
    fig.update_layout(title=f"Impact of {PRODUCT_DEFAULTS[ms.product]['comp1'].title()} Price on Your Market",
                      height=420, plot_bgcolor="#FAFCFF", paper_bgcolor="#FAFCFF",
                      margin=dict(l=0, r=0, t=50, b=0))
    fig.update_xaxes(title_text=f"{PRODUCT_DEFAULTS[ms.product]['comp1'].title()} price ($/unit)")
    fig.update_yaxes(title_text="Your Eq. Price ($/unit)", secondary_y=False)
    fig.update_yaxes(title_text="Your Net Profit ($)", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)


def _chart_ad_effectiveness(ms, eq, color):
    """Return on ad spend: profit per $K of ad spend."""
    rows = sweep_ad(ms, ad_min=1.0, ad_max=300.0, steps=80)
    ax   = [r["ad"]                          for r in rows]
    roi  = [r["profit"] / (r["ad"] * 1000) if r["ad"] > 0 else 0 for r in rows]
    qty  = [r["qty"]                         for r in rows]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=ax, y=roi, name="Profit per $ Ad Spend",
                             line=dict(color=color, width=2.5)),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=ax, y=qty, name="Eq. Quantity",
                             line=dict(color="#2ECC71", width=2, dash="dash")),
                  secondary_y=True)
    fig.add_vline(x=ms.ad_spend_k, line_color="#8E44AD", line_dash="dot",
                  annotation_text="Current")
    fig.update_layout(title="Ad Effectiveness: Return per Dollar Spent",
                      height=420, plot_bgcolor="#FAFCFF", paper_bgcolor="#FAFCFF",
                      margin=dict(l=0, r=0, t=50, b=0))
    fig.update_xaxes(title_text="Ad spend ($K/week)")
    fig.update_yaxes(title_text="Profit / Ad dollar", secondary_y=False)
    fig.update_yaxes(title_text="Units/week", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)


def _chart_mfr_retailer(ms, eq, color):
    """Stacked comparison: manufacturer vs retailer profit as wholesale changes."""
    rows = sweep_wholesale(ms, wc_min=0.20, wc_max=4.50, steps=80)
    wx   = [r["wc"]         for r in rows]
    rpf  = [r["profit"]     for r in rows]
    mpf  = [r["mfr_profit"] for r in rows]
    tot  = [r + m           for r, m in zip(rpf, mpf)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=wx, y=mpf, name="Manufacturer Profit",
                             stackgroup="one", line=dict(color=color)))
    fig.add_trace(go.Scatter(x=wx, y=rpf, name="Retailer Profit",
                             stackgroup="one", line=dict(color="#2ECC71")))
    fig.add_vline(x=ms.wholesale_cost, line_color="#8E44AD", line_dash="dot",
                  annotation_text="Current WC")
    fig.update_layout(title="Channel Profit Split: Manufacturer vs Retailer",
                      height=420, plot_bgcolor="#FAFCFF", paper_bgcolor="#FAFCFF",
                      margin=dict(l=0, r=0, t=50, b=0))
    fig.update_xaxes(title_text="Wholesale price ($/unit)")
    fig.update_yaxes(title_text="Profit ($)")
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Sensitivity table
# ---------------------------------------------------------------------------
def render_sensitivity_table(ms: MarketState, eq: EquilibriumResult,
                             fin: Financials, role: str) -> None:
    import pandas as pd
    section("🔍 Sensitivity Table")

    rows = sweep_price(ms, p_min=0.50, p_max=7.00, steps=25)
    data = []
    for r in rows:
        rev  = r["price"] * r["qs"]
        cogs = ms.wholesale_cost * r["qs"]
        opex = (ms.ad_spend_k + ms.transport_cost_k + ms.fixed_overhead_k) * 1000
        pf   = (rev - cogs - opex) * (1 - ms.tax_rate_pct / 100)
        near = "✅" if abs(r["price"] - eq.price_eq) < 0.14 else ""
        data.append({
            "Price": f"${r['price']:.2f}",
            "Qd":    f"{r['qd']:,.0f}",
            "Qs":    f"{r['qs']:,.0f}",
            "Excess": f"{r['excess']:+,.0f}",
            "Revenue": fmtk(rev),
            "Net Profit": fmtk(pf),
            "≈ Eq?": near,
        })
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Export buttons
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
