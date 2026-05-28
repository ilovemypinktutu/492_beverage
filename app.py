"""
app.py — Beverage Market Simulator landing page.
Students select their assigned product and role; the app routes them to
the correct simulation page.
"""
import streamlit as st

st.set_page_config(
    page_title="Beverage Market Simulator",
    page_icon="🧃",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  .block-container { padding-top: 2rem; max-width: 860px; margin: auto; }
  .title { font-size: 2.4rem; font-weight: 800; text-align: center;
           background: linear-gradient(90deg,#6F4E37,#1B3A6B,#C9A227);
           -webkit-background-clip:text; -webkit-text-fill-color:transparent;
           margin-bottom: 0.2rem; }
  .subtitle { text-align:center; color:#555; font-size:1rem; margin-bottom:2rem; }
  .card {
    border: 1.5px solid #E0E8F0; border-radius: 14px;
    padding: 1.4rem 1.6rem; cursor: pointer;
    transition: box-shadow .15s, border-color .15s;
    background: #FAFCFF;
  }
  .card:hover { box-shadow: 0 4px 18px rgba(0,0,0,.10); border-color: #9BB8D4; }
  .card-title { font-size: 1.15rem; font-weight: 700; margin-bottom: 4px; }
  .card-sub   { font-size: 0.82rem; color: #666; }
  .prod-coffee { border-left: 5px solid #6F4E37; }
  .prod-soda   { border-left: 5px solid #1B3A6B; }
  .prod-beer   { border-left: 5px solid #C9A227; }
  .role-ps  { border-left: 5px solid #E74C3C; }
  .role-ad  { border-left: 5px solid #27AE60; }
  .role-mfr { border-left: 5px solid #8E44AD; }
  .step { font-size:0.78rem; font-weight:700; text-transform:uppercase;
          letter-spacing:.06em; color:#888; margin-bottom:0.4rem; }
  .go-btn {
    background: linear-gradient(90deg,#1B3A6B,#0D7377);
    color:white; border:none; border-radius:10px;
    padding: 0.7rem 2rem; font-size:1.1rem; font-weight:700;
    cursor:pointer; width:100%; margin-top:1rem;
  }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">🧃 Beverage Market Simulator</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">An interactive market economics tool. '
            'Select your assigned product and role to begin.</div>', unsafe_allow_html=True)

# ── Step 1: Product ─────────────────────────────────────────────────────────
st.markdown('<div class="step">Step 1 — Choose your assigned product</div>',
            unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
product_info = {
    "coffee": ("☕", "Coffee", "#6F4E37",
                "Competitors: Soda & Beer",
                "Premium positioning, caffeine appeal, health-conscious sensitivity"),
    "soda":   ("🥤", "Soda",   "#1B3A6B",
                "Competitors: Coffee & Beer",
                "High volume, price-elastic, strong ad sensitivity"),
    "beer":   ("🍺", "Beer",   "#C9A227",
                "Competitors: Coffee & Soda",
                "Alcohol premium, lower health perception, moderate volume"),
}
for col, (prod_key, (emoji, label, color, comps, desc)) in zip(
        [col1, col2, col3], product_info.items()):
    with col:
        selected = st.session_state.get("product") == prod_key
        border   = f"3px solid {color}" if selected else f"1.5px solid #E0E8F0"
        bg       = f"{color}12" if selected else "#FAFCFF"
        if st.button(f"{emoji}  {label}", key=f"btn_prod_{prod_key}",
                     use_container_width=True):
            st.session_state["product"] = prod_key
        st.caption(f"{comps}  \n{desc}")

product = st.session_state.get("product")

# ── Step 2: Role ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="step">Step 2 — Choose your assigned role</div>',
            unsafe_allow_html=True)

role_info = {
    "price_setter": (
        "🏷️", "Price Setter",
        "You control the retail shelf price.",
        "Explore how price affects demand, supply, and your profit margin. "
        "Find the price that maximizes profit."
    ),
    "ad_manager": (
        "📢", "Ad Spend Manager",
        "You control the advertising budget.",
        "Advertising boosts demand but has diminishing returns. "
        "Find the optimal weekly spend."
    ),
    "manufacturer": (
        "🏭", "Wholesale Price Setter",
        "You are the manufacturer selling to the retailer.",
        "Set the wholesale price to balance your margin against the volume "
        "the retailer is willing to supply."
    ),
}

rc1, rc2, rc3 = st.columns(3)
for col, (role_key, (emoji, label, tagline, desc)) in zip(
        [rc1, rc2, rc3], role_info.items()):
    with col:
        selected = st.session_state.get("role") == role_key
        if st.button(f"{emoji}  {label}", key=f"btn_role_{role_key}",
                     use_container_width=True):
            st.session_state["role"] = role_key
        st.caption(f"**{tagline}**  \n{desc}")

role = st.session_state.get("role")

# ── Step 3: Launch ───────────────────────────────────────────────────────────
st.markdown("---")

PAGE_MAP = {
    ("coffee", "price_setter"): "pages/1_☕_Coffee_Price_Setter.py",
    ("coffee", "ad_manager"):   "pages/2_☕_Coffee_Ad_Manager.py",
    ("coffee", "manufacturer"): "pages/3_☕_Coffee_Manufacturer.py",
    ("soda",   "price_setter"): "pages/4_🥤_Soda_Price_Setter.py",
    ("soda",   "ad_manager"):   "pages/5_🥤_Soda_Ad_Manager.py",
    ("soda",   "manufacturer"): "pages/6_🥤_Soda_Manufacturer.py",
    ("beer",   "price_setter"): "pages/7_🍺_Beer_Price_Setter.py",
    ("beer",   "ad_manager"):   "pages/8_🍺_Beer_Ad_Manager.py",
    ("beer",   "manufacturer"): "pages/9_🍺_Beer_Manufacturer.py",
}

if product and role:
    prod_emoji = product_info[product][0]
    role_emoji = role_info[role][0]
    prod_label = product_info[product][1]
    role_label = role_info[role][1]
    color      = product_info[product][2]

    st.success(
        f"**Ready to launch:** {prod_emoji} {prod_label} — {role_emoji} {role_label}  \n"
        f"Use the **sidebar navigation** (left) to open your simulation page, "
        f"or click the button below."
    )

    target_page = PAGE_MAP.get((product, role))
    if target_page:
        page_name = target_page.replace("pages/", "").replace(".py", "").replace("_", " ").strip()
        # Number prefix stripped for display
        import re
        page_name = re.sub(r"^\d+\s+", "", page_name)
        st.markdown(
            f"➡️ Open **{page_name}** from the sidebar to begin your simulation.",
            unsafe_allow_html=False
        )
    # Store choices so pages can verify/welcome the student
    st.session_state["confirmed_product"] = product
    st.session_state["confirmed_role"]    = role
else:
    if not product:
        st.info("👆 Select your product above to continue.")
    elif not role:
        st.info("👆 Select your role above to continue.")

# ── Legend ───────────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("ℹ️ How the simulation works"):
    st.markdown("""
Each product market has its own **demand** and **supply** function.

- **Demand** depends on: your retail price, competitor prices, your ad spend,
  competitor ad spends, local income, unemployment, population, season, temperature,
  and product-specific factors (caffeine appeal for coffee, alcohol premium for beer, etc.)
- **Supply** depends on: your retail price, wholesale cost, tax, transport cost,
  upstream market power, employee satisfaction, energy cost, and store count.

The market **equilibrium price and quantity** are solved numerically using a
bisection + Newton-Raphson algorithm.

**Your profit** = Revenue − COGS − Ad spend − Transport − Overhead − Tax.
Each role faces a **different profit landscape** with a genuine interior maximum —
finding it is the learning objective.
""")
