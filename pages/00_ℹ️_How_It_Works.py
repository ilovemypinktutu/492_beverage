"""
pages/00_ℹ️_How_It_Works.py — Standalone "How the simulation works" page.
Appears in the sidebar between Home and Glossary.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st

st.set_page_config(
    page_title="How It Works",
    page_icon="ℹ️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  [data-testid="stSidebarNav"] { display: none !important; }
  .block-container { padding-top: 1.5rem; max-width: 820px; margin: auto; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar nav ──────────────────────────────────────────────────────────────
PAGE_MAP = {
    ("coffee","price_setter"): ("pages/1_☕_Coffee_Price_Setter.py",  "☕ Coffee — Price Setter"),
    ("coffee","ad_manager"):   ("pages/2_☕_Coffee_Ad_Manager.py",    "☕ Coffee — Ad Manager"),
    ("coffee","manufacturer"): ("pages/3_☕_Coffee_Manufacturer.py",  "☕ Coffee — Manufacturer"),
    ("soda",  "price_setter"): ("pages/4_🥤_Soda_Price_Setter.py",   "🥤 Soda — Price Setter"),
    ("soda",  "ad_manager"):   ("pages/5_🥤_Soda_Ad_Manager.py",     "🥤 Soda — Ad Manager"),
    ("soda",  "manufacturer"): ("pages/6_🥤_Soda_Manufacturer.py",   "🥤 Soda — Manufacturer"),
    ("beer",  "price_setter"): ("pages/7_🍺_Beer_Price_Setter.py",   "🍺 Beer — Price Setter"),
    ("beer",  "ad_manager"):   ("pages/8_🍺_Beer_Ad_Manager.py",     "🍺 Beer — Ad Manager"),
    ("beer",  "manufacturer"): ("pages/9_🍺_Beer_Manufacturer.py",   "🍺 Beer — Manufacturer"),
}
with st.sidebar:
    st.markdown("### 🧃 Navigation")
    st.page_link("app.py",                    label="🏠 Home / Setup")
    st.page_link("pages/00_ℹ️_How_It_Works.py", label="ℹ️ How It Works")
    st.page_link("pages/0_📖_Glossary.py",     label="📖 Glossary")
    cp = st.session_state.get("confirmed_product")
    cr = st.session_state.get("confirmed_role")
    if cp and cr and (cp, cr) in PAGE_MAP:
        path, label = PAGE_MAP[(cp, cr)]
        st.markdown("---")
        st.markdown("**Your simulation:**")
        st.page_link(path, label=f"▶ {label}")

# ── Content ──────────────────────────────────────────────────────────────────
st.title("ℹ️ How the Simulation Works")

st.markdown("""
This simulator places you in a real beverage retail market alongside two competing products.
You control **one decision variable** — your assigned role determines which one.
Every time you move your slider, the market reacts.

---

### Your role

| Role | What you control |
|------|-----------------|
| 🏷️ **Price Setter** | The retail shelf price of your product |
| 📢 **Ad Spend Manager** | Your weekly advertising budget |
| 🏭 **Wholesale Price Setter** | The price you (the manufacturer) charge the retailer |

---

### How demand works

Consumers decide how much to buy based on:

- **Your retail price** — higher price reduces quantity demanded (price-elastic market)
- **Competitor prices** — if competitors raise their prices, some consumers switch to you
- **Advertising** — more ad spend shifts the demand curve outward, but with diminishing returns
- **Demographics** — local income, unemployment rate, population density, and shopper age
- **Environment** — season and temperature affect beverage consumption
- **Consumer satisfaction** — loyal customers buy more; the effect peaks and then diminishes
- **Health trend** — health-conscious markets drink less soda and beer

---

### How supply works

Retailers and distributors decide how much to stock based on:

- **Retail price** — higher prices make supplying more attractive
- **Wholesale cost** — the retailer's cost of goods; higher wholesale cost reduces supply
- **Tax rate and transport cost** — raise operating costs, reducing supply
- **Upstream market power** — a powerful bottler or brewer compresses retailer margins
- **Employee satisfaction** — higher morale improves operational efficiency
- **Energy cost** — refrigeration and logistics costs affect profitability
- **Input scarcity and regulatory burden** — constraints that limit supply

---

### Market equilibrium

The simulator finds the **equilibrium price** — the price at which quantity demanded
exactly equals quantity supplied — using a two-phase numerical algorithm
(bisection followed by Newton-Raphson refinement).

The **quantity sold** is `min(Qd, Qs)` at your chosen price:
- If your price is **below** equilibrium: supply is the binding constraint
- If your price is **above** equilibrium: demand is the binding constraint

---

### Your profit

> **Profit = (Price − Wholesale Cost) × Units Sold − Ad Spend − Transport − Fixed Overhead − Tax**

Breaking that down:
- **(Price − Wholesale Cost)** is your contribution margin per unit
- **× Units Sold** gives your gross profit
- Subtracting **Ad Spend + Transport + Fixed Overhead** gives EBIT
- Subtracting **Tax** gives net profit

Each role has a **profit-maximizing choice** at an interior point within the slider range.
Your goal is to find it by experimenting.

---

### What is correlated mode?

When you move your slider, the model does not hold everything else constant.
Instead, it draws **correlated values** for all other market variables from a
joint statistical distribution conditioned on your choice.

This reflects economic reality:
- When you raise your price, competitors tend to raise theirs too (strategic complementarity)
- When wholesale costs rise, they tend to rise for all products simultaneously (common cost shocks)
- Random demand and supply disturbances are correlated across the market

The result is a realistic competitive environment where your decision has
ripple effects throughout the market — not an artificial ceteris-paribus experiment.

---

### Decision history

Every time you move your slider to a new value, the result is automatically recorded
in the **Decision History** table. You can download the full history as an Excel file
at any time. The history includes your choice, all financial outcomes, the values of
competitor variables generated by the correlated draw, and the current market conditions.
""")
