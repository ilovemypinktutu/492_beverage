"""
pages/A_How_It_Works.py — Standalone "How the simulation works" page.
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
    st.page_link("app.py",                    label="🏠 Home / Setup")
    st.page_link("pages/A_How_It_Works.py", label="ℹ️ How It Works")
    st.page_link("pages/B_Glossary.py",     label="📖 Glossary")
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

In correlated mode, moving your slider does not hold everything else constant.
Instead, other market variables are drawn from a **structured distribution**
conditioned on your choice, following specific economic logic for each role.

**If you are a Manufacturer (wholesale price setter):**
- A higher wholesale price causes the retailer's own retail price to rise
  (the retailer passes the cost through to consumers)
- Competitor retail prices are held at their background noise levels —
  your wholesale decision does not structurally affect them
- A higher wholesale price also generates a **negative supply shock**:
  the retailer becomes more reluctant to stock your product, adding friction
  beyond the model's supply curve

**If you are an Ad Spend Manager:**
- Higher ad spend causes the retailer's own retail price to rise
  (advertising supports a premium positioning)
- Competitor prices are held at background noise — your ad decision
  does not structurally affect them
- Higher ad spend also generates a **positive demand shock**:
  advertising creates awareness and buzz beyond what the model's ad-spend term captures,
  so the net effect on equilibrium quantity is ambiguous —
  the price increase reduces demand while the shock boosts it

**If you are a Price Setter:**
- When you raise your price, **competitor prices rise too** (strategic complementarity:
  competitors respond to your pricing signal)
- Your own wholesale cost co-moves with your retail price (reflecting common cost shocks)
- A higher price also generates a **positive demand shock** (a quality-signaling effect:
  consumers partly interpret a higher price as a signal of higher quality)

**In all roles**, a pure random (iid) component is added on top of the structural
effects above. This residual noise is uncorrelated with your choice and represents
unpredictable market disturbances.

### What is experiment mode?

Experiment mode removes all structural correlations.
Only the **pure random iid component** of demand and supply disturbances remains —
uncorrelated with your decision and with everything else in the model.

This is useful when you want to isolate the direct causal effect of your choice
variable without any correlated market responses clouding the results.
In experiment mode the market behaves as a ceteris-paribus laboratory:
everything except your choice variable stays fixed at its sidebar value,
plus a small random shock to demand and supply each period.

| | Correlated mode | Experiment mode |
|---|---|---|
| Other choice vars | Drawn from structured distribution | Fixed at sidebar values |
| Demand/supply shocks | Correlated with your choice | Pure iid (uncorrelated) |
| Competitor prices | Respond to your decision (role-specific) | Fixed |
| Realism | High | Low (controlled experiment) |
| Learning objective | How markets respond to decisions | Pure causal effect |

---

### Decision history

Every time you move your slider to a new value, the result is automatically recorded
in the **Decision History** table. You can download the full history as an Excel file
at any time. The history includes your choice, all financial outcomes, the values of
competitor variables generated by the correlated draw, and the current market conditions.
""")
