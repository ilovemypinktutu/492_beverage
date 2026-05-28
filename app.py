"""
app.py — Cola Retail Market Simulator (Streamlit)
==================================================
Students set the retail price; the app solves for equilibrium and shows
demand, supply, revenue, costs, and profit in real time.
All other market conditions are adjustable in the sidebar.
"""

import streamlit as st
import pandas as pd
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core.model import (
    MarketConditions,
    demand,
    supply,
    find_equilibrium,
    compute_financials,
    price_sensitivity,
)
from core.export import export_xlsx, export_csv

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Cola Market Simulator",
    page_icon="🥤",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .main-title {
        font-size: 2.1rem; font-weight: 700;
        background: linear-gradient(90deg, #1B3A6B, #0D7377);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.1rem;
    }
    .subtitle { color: #555; font-size: 0.95rem; margin-bottom: 1.5rem; }
    .metric-card {
        background: #f7fafd; border-radius: 10px;
        padding: 1rem 1.2rem; border-left: 4px solid #1B3A6B;
        margin-bottom: 0.5rem;
    }
    .metric-label { font-size: 0.8rem; color: #666; font-weight: 600;
                    text-transform: uppercase; letter-spacing: .05em; }
    .metric-value { font-size: 1.55rem; font-weight: 700; color: #1B3A6B; }
    .metric-sub   { font-size: 0.75rem; color: #888; margin-top: 2px; }
    .profit-pos   { color: #1a7a45 !important; }
    .profit-neg   { color: #c0392b !important; }
    .eq-badge {
        display: inline-block; padding: 3px 12px; border-radius: 20px;
        font-size: 0.8rem; font-weight: 600;
        background: #e8f8ee; color: #1a7a45;
    }
    .section-hdr {
        font-size: 1.05rem; font-weight: 700; color: #1B3A6B;
        border-bottom: 2px solid #e0e8f0; padding-bottom: 4px;
        margin: 1.2rem 0 0.8rem;
    }
    [data-testid="stSidebar"] { background: #f0f4fa; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fmtk(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"${v/1_000_000:,.2f}M"
    if abs(v) >= 1_000:
        return f"${v/1_000:,.1f}K"
    return f"${v:,.2f}"

def metric_card(label: str, value: str, sub: str = "", profit=None):
    extra = ""
    if profit is True:
        extra = ' profit-pos'
    elif profit is False:
        extra = ' profit-neg'
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value{extra}">{value}</div>
        <div class="metric-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — market conditions
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⚙️ Market Conditions")
    st.caption("Adjust economic and demographic inputs. Students set price above.")

    with st.expander("💰 Costs & Competitor", expanded=True):
        wholesale  = st.slider("Wholesale cost ($/unit)", 0.30, 2.00, 0.90, 0.05)
        comp_price = st.slider("Competitor price ($/unit)", 0.50, 4.00, 1.90, 0.05)
        ad_spend   = st.slider("Ad spend ($K/week)", 1.0, 200.0, 50.0, 1.0)
        trans_cost = st.slider("Transport cost ($K/week)", 1.0, 100.0, 20.0, 1.0)
        fixed_oh   = st.slider("Fixed overhead ($K/week)", 1.0, 30.0, 5.0, 0.5)
        tax_rate   = st.slider("Tax rate (%)", 0.0, 30.0, 8.0, 0.5)

    with st.expander("👥 Demographics", expanded=False):
        income     = st.slider("Local income ($K/yr)", 25.0, 150.0, 65.0, 1.0)
        unemp      = st.slider("Unemployment rate (%)", 0.0, 20.0, 5.0, 0.5)
        pop_dens   = st.slider("Population density (people/sq mi)", 100.0, 30000.0, 3000.0, 100.0)
        age_idx    = st.slider("Shopper age index (yrs)", 18.0, 65.0, 35.0, 1.0)

    with st.expander("📊 Market Dynamics", expanded=False):
        csat       = st.slider("Consumer satisfaction (0-10)", 0.0, 10.0, 7.0, 0.1)
        esat       = st.slider("Employee satisfaction (0-10)", 0.0, 10.0, 7.0, 0.1)
        upstream   = st.slider("Upstream market power (0-1)", 0.0, 1.0, 0.30, 0.01)
        season     = st.slider("Season index (0.5–1.5)", 0.50, 1.50, 1.00, 0.01)
        temp_f     = st.slider("Temperature (°F)", -10.0, 110.0, 72.0, 1.0)
        health     = st.slider("Health trend (-1 to 1)", -1.0, 1.0, 0.0, 0.05)
        cap_util   = st.slider("Capacity utilisation (%)", 10.0, 100.0, 75.0, 1.0)
        energy     = st.slider("Energy cost index", 0.5, 3.0, 1.0, 0.05)
        scarcity   = st.slider("Input scarcity (0-1)", 0.0, 1.0, 0.0, 0.01)
        reg_burden = st.slider("Regulatory burden (0-1)", 0.0, 1.0, 0.0, 0.01)
        store_cnt  = st.slider("Store count", 1, 50, 8)

    with st.expander("🏪 Store & Time", expanded=False):
        brand = st.selectbox("Brand type",
                             ["Independent", "Regional chain", "National chain"],
                             index=0)
        brand_int = ["Independent", "Regional chain", "National chain"].index(brand)
        promo = st.checkbox("In-store promotion active", value=False)
        time_m = st.slider("Time since baseline (months)", 0, 60, 0, 1)

    scenario_name = st.text_input("Scenario label (for export)", "My Scenario")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<div class="main-title">🥤 Cola Retail Market Simulator</div>',
            unsafe_allow_html=True)
st.markdown('<div class="subtitle">Set your retail price below and explore how '
            'supply, demand, and profit respond in real time.</div>',
            unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ★ STUDENT PRICE CONTROL ★  — prominent, centred
# ---------------------------------------------------------------------------
st.markdown('<div class="section-hdr">📌 Your Price Decision</div>',
            unsafe_allow_html=True)

col_price, col_info = st.columns([2, 3])
with col_price:
    own_price = st.slider(
        "**Set your retail price ($/unit)**",
        min_value=0.50, max_value=4.00, value=1.80, step=0.01,
        help="This is the key decision variable. Drag to see how market equilibrium shifts."
    )
    st.caption(f"Selected price: **${own_price:.2f}/unit**")

with col_info:
    st.info("""
    **How to use this simulator:**
    1. Drag the price slider to your chosen retail price.
    2. The app instantly solves for the **market-clearing equilibrium**.
    3. Explore the sidebar to stress-test different market conditions.
    4. Download your results as Excel or CSV when done.
    """)

# ---------------------------------------------------------------------------
# Build MarketConditions and solve equilibrium
# ---------------------------------------------------------------------------
mc = MarketConditions(
    own_price        = own_price,
    competitor_price = comp_price,
    ad_spend_k       = ad_spend,
    local_income_k   = income,
    unemployment_pct = unemp,
    consumer_sat     = csat,
    season_index     = season,
    brand            = brand_int,
    time_months      = time_m,
    pop_density      = pop_dens,
    age_index        = age_idx,
    health_trend     = health,
    promo_dummy      = 1 if promo else 0,
    temperature_f    = temp_f,
    wholesale_cost   = wholesale,
    tax_rate_pct     = tax_rate,
    transport_cost_k = trans_cost,
    upstream_power   = upstream,
    employee_sat     = esat,
    capacity_util_pct= cap_util,
    energy_cost_idx  = energy,
    input_scarcity   = scarcity,
    regulatory_burden= reg_burden,
    store_count      = float(store_cnt),
    fixed_overhead_k = fixed_oh,
)

eq  = find_equilibrium(mc)
fin = compute_financials(eq, mc)

# ---------------------------------------------------------------------------
# Key metrics row
# ---------------------------------------------------------------------------
st.markdown('<div class="section-hdr">📈 Equilibrium & Financial Results</div>',
            unsafe_allow_html=True)

c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    metric_card("Eq. Price", f"${eq.price_eq:.3f}", "market-clearing")
with c2:
    metric_card("Eq. Quantity", f"{eq.quantity_eq:,.0f}", "units / week")
with c3:
    metric_card("Revenue", fmtk(fin.revenue), "weekly")
with c4:
    metric_card("Gross Profit", fmtk(fin.gross_profit),
                f"{fin.gross_margin_pct:.1f}% margin")
with c5:
    metric_card("Net Profit", fmtk(fin.net_profit),
                f"{fin.net_margin_pct:.1f}% margin",
                profit=(fin.net_profit >= 0))
with c6:
    bep_str = f"{fin.break_even_units:,.0f} u/wk" \
              if fin.break_even_units != float("inf") else "N/A"
    profitable = eq.quantity_eq >= fin.break_even_units
    metric_card("Break-even", bep_str,
                "✅ Profitable" if profitable else "❌ Below BEP",
                profit=profitable)

# price vs eq. note
gap = own_price - eq.price_eq
if abs(gap) < 0.02:
    st.success(f"✅ Your price **${own_price:.2f}** is very close to the equilibrium "
               f"price **${eq.price_eq:.3f}** — the market clears near your price.")
elif gap > 0:
    st.warning(f"📉 Your price **${own_price:.2f}** is **${gap:.2f} above** equilibrium "
               f"(${eq.price_eq:.3f}). Excess supply: consumers shop cheaper alternatives.")
else:
    st.warning(f"📈 Your price **${own_price:.2f}** is **${abs(gap):.2f} below** equilibrium "
               f"(${eq.price_eq:.3f}). Excess demand: you're leaving money on the table.")

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
st.markdown('<div class="section-hdr">📊 Market Charts</div>',
            unsafe_allow_html=True)

rows = price_sensitivity(mc, p_min=0.50, p_max=4.00, steps=60)
prices  = [r["price"]  for r in rows]
qd_vals = [r["Qd"]     for r in rows]
qs_vals = [r["Qs"]     for r in rows]
ex_vals = [r["excess"] for r in rows]

# profit series
def _profit(r):
    rev  = r["price"] * r["Qs"]
    opex = (mc.ad_spend_k + mc.transport_cost_k + mc.fixed_overhead_k) * 1000
    return (rev - mc.wholesale_cost * r["Qs"] - opex) * (1 - mc.tax_rate_pct / 100)

profit_vals = [_profit(r) for r in rows]

tab1, tab2, tab3 = st.tabs(["Supply & Demand", "Profit Curve", "Cost Breakdown"])

with tab1:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=prices, y=qd_vals, name="Demand (Qd)",
                             line=dict(color="#1B3A6B", width=2.5),
                             fill="tozeroy", fillcolor="rgba(27,58,107,0.07)"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=prices, y=qs_vals, name="Supply (Qs)",
                             line=dict(color="#0D7377", width=2.5, dash="dash"),
                             fill="tozeroy", fillcolor="rgba(13,115,119,0.07)"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=prices, y=ex_vals, name="Excess Demand",
                             line=dict(color="#e67e22", width=1.5, dash="dot")),
                  secondary_y=True)
    # equilibrium vertical line
    fig.add_vline(x=eq.price_eq, line_color="#c0392b", line_dash="dash", line_width=1.5,
                  annotation_text=f"Eq ${eq.price_eq:.2f}", annotation_position="top right")
    # student price
    fig.add_vline(x=own_price, line_color="#8e44ad", line_dash="dot", line_width=1.5,
                  annotation_text=f"Your price ${own_price:.2f}", annotation_position="top left")
    fig.update_layout(title="Supply & Demand Curve", height=420,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02),
                      plot_bgcolor="#fafcff", paper_bgcolor="#fafcff",
                      margin=dict(l=0, r=0, t=40, b=0))
    fig.update_xaxes(title_text="Price ($/unit)")
    fig.update_yaxes(title_text="Units / week", secondary_y=False)
    fig.update_yaxes(title_text="Excess demand (units)", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    colors = ["#1a7a45" if p >= 0 else "#c0392b" for p in profit_vals]
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=prices, y=profit_vals, name="Net Profit",
                              line=dict(color="#1B3A6B", width=2.5),
                              fill="tozeroy",
                              fillcolor="rgba(27,58,107,0.08)"))
    fig2.add_hline(y=0, line_color="#c0392b", line_dash="dash", line_width=1)
    fig2.add_vline(x=eq.price_eq, line_color="#c0392b", line_dash="dash", line_width=1.5,
                   annotation_text=f"Eq ${eq.price_eq:.2f}")
    fig2.add_vline(x=own_price, line_color="#8e44ad", line_dash="dot", line_width=1.5,
                   annotation_text=f"Your price")
    fig2.update_layout(title="Net Profit vs. Price", height=420,
                       plot_bgcolor="#fafcff", paper_bgcolor="#fafcff",
                       margin=dict(l=0, r=0, t=40, b=0))
    fig2.update_xaxes(title_text="Price ($/unit)")
    fig2.update_yaxes(title_text="Net Profit ($)")
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    labels = ["COGS", "Ad Spend", "Transport", "Fixed Overhead", "Tax", "Net Profit"]
    vals_pie = [fin.cogs, fin.ad_expense, fin.transport_expense,
                fin.fixed_overhead, fin.tax_amount, max(fin.net_profit, 0)]
    colors_pie = ["#1B3A6B","#0D7377","#2980b9","#8e44ad","#e67e22","#1a7a45"]
    fig3 = go.Figure(go.Pie(labels=labels, values=vals_pie,
                            hole=0.45, marker_colors=colors_pie,
                            textinfo="label+percent"))
    fig3.update_layout(title=f"Revenue Breakdown  (Total: {fmtk(fin.revenue)})",
                       height=420,
                       plot_bgcolor="#fafcff", paper_bgcolor="#fafcff",
                       margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig3, use_container_width=True)

# ---------------------------------------------------------------------------
# Sensitivity table
# ---------------------------------------------------------------------------
st.markdown('<div class="section-hdr">🔍 Price Sensitivity Table</div>',
            unsafe_allow_html=True)

sens_rows = price_sensitivity(mc, steps=20)
table_data = []
for r in sens_rows:
    rev  = r["price"] * r["Qs"]
    opex = (mc.ad_spend_k + mc.transport_cost_k + mc.fixed_overhead_k) * 1000
    prof = (rev - mc.wholesale_cost * r["Qs"] - opex) * (1 - mc.tax_rate_pct / 100)
    near = "✅" if abs(r["price"] - eq.price_eq) < 0.08 else ""
    table_data.append({
        "Price ($/unit)": f"${r['price']:.2f}",
        "Demand (Qd)":    f"{r['Qd']:,.0f}",
        "Supply (Qs)":    f"{r['Qs']:,.0f}",
        "Excess":         f"{r['excess']:+,.0f}",
        "Revenue":        fmtk(rev),
        "Net Profit":     fmtk(prof),
        "Near Eq?":       near,
    })
st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------
st.markdown('<div class="section-hdr">⬇️ Export Results</div>',
            unsafe_allow_html=True)

dl1, dl2 = st.columns(2)
with dl1:
    xlsx_bytes = export_xlsx(mc, eq, fin, scenario=scenario_name)
    st.download_button(
        label="📥 Download Excel Workbook (.xlsx)",
        data=xlsx_bytes,
        file_name=f"cola_simulation_{scenario_name.replace(' ','_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
with dl2:
    csv_str = export_csv(mc, eq, fin, scenario=scenario_name)
    st.download_button(
        label="📥 Download CSV (.csv)",
        data=csv_str,
        file_name=f"cola_simulation_{scenario_name.replace(' ','_')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ---------------------------------------------------------------------------
# Model equation reference
# ---------------------------------------------------------------------------
with st.expander("📐 Model Equations Reference", expanded=False):
    st.markdown(r"""
**Demand (log-linear + quadratic + cubic):**
$$\ln Q_d = \alpha_0 + \alpha_1\ln P + \alpha_2\ln P_{comp} + \alpha_3\ln Adv
+ \alpha_4\ln Inc + \alpha_5 U + \alpha_6 CS + \alpha_7 CS^2
+ \alpha_8 T + \alpha_9 T^2 + \alpha_{10} T^3 + \alpha_{11}\ln S
+ \text{Brand} + \alpha_{12}\ln D + \alpha_{13} Age + \alpha_{14} Age^2
+ \alpha_{15} H + \alpha_{16} Promo + \alpha_{17} Temp + \alpha_{18} Temp^2$$

**Supply (log-linear + quadratic + cubic):**
$$\ln Q_s = \beta_0 + \beta_1\ln P + \beta_2\ln WC + \beta_3 Tax
+ \beta_4\ln Trans + \beta_5 UP + \beta_6 UP^2 + \beta_7 UP^3
+ \beta_8 ES + \beta_9 ES^2 + \beta_{10} Cap
+ \beta_{11}\ln EC + \beta_{12} Sc + \beta_{13} Reg + \beta_{14}\ln N$$

**Equilibrium:** bisection (80 iterations) → Newton-Raphson refinement  
**Revenue** $= P^* \times Q^*$ · **COGS** $= WC \times Q^*$ · **Net Profit** $= (Rev - COGS - OpEx)(1-\tau)$
""")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption("Cola Market Simulator · Built with Streamlit · "
           "Economic model: log-linear + quadratic + cubic demand & supply · "
           "Equilibrium: bisection + Newton-Raphson")
