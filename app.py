"""
app.py — Beverage Market Simulator landing page.
"""
import streamlit as st

INSTRUCTOR_PASSWORD = "econ2025"

st.set_page_config(
    page_title="Beverage Market Simulator",
    page_icon="🧃",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  [data-testid="stSidebarNav"] { display: none !important; }
  .block-container { padding-top: 1.8rem; max-width: 880px; margin: auto; }
  .title {
    font-size: 2.3rem; font-weight: 800; text-align: center;
    background: linear-gradient(90deg,#6F4E37,#1B3A6B,#C9A227);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
  }
  .subtitle { text-align:center; color:#555; font-size:1rem; margin-bottom:1.8rem; }
  .step { font-size:0.78rem; font-weight:700; text-transform:uppercase;
          letter-spacing:.06em; color:#888; margin-bottom:0.5rem; }
  .lock-box { background:#F8F4FF; border:1px solid #C5A8F5; border-radius:10px;
              padding:0.8rem 1.1rem; margin-top:1rem; }
  .lock-box p { margin:0; font-size:0.85rem; color:#5A3A9A; }
</style>
""", unsafe_allow_html=True)

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

# ── Sidebar ─────────────────────────────────────────────────────────────────
# Item 2: Do NOT show "Your simulation:" link on the front page.
# Item 1: "How the simulation works" moved here.
with st.sidebar:
    st.markdown("### 🧃 Navigation")
    st.page_link("app.py",                       label="🏠 Home / Setup")
    st.page_link("pages/00_How_It_Works.py", label="ℹ️ How It Works")
    st.page_link("pages/0_Glossary.py",       label="📖 Glossary")


# ── Main ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="title">🧃 Beverage Market Simulator</div>',
            unsafe_allow_html=True)
st.markdown('<div class="subtitle">Select your assigned product and role to unlock '
            'your simulation page.</div>', unsafe_allow_html=True)

product_info = {
    "coffee": ("☕", "Coffee", "#6F4E37",
               "Competitors: Soda & Beer",
               "Premium positioning · caffeine appeal · health-trend sensitive"),
    "soda":   ("🥤", "Soda",   "#1B3A6B",
               "Competitors: Coffee & Beer",
               "High volume · price-elastic · strong ad sensitivity"),
    "beer":   ("🍺", "Beer",   "#C9A227",
               "Competitors: Coffee & Soda",
               "Alcohol premium · moderate volume · excise-tax exposed"),
}
role_info = {
    "price_setter": ("🏷️", "Price Setter",
                     "Control the retail shelf price.",
                     "Find the price that maximizes weekly profit."),
    "ad_manager":   ("📢", "Ad Spend Manager",
                     "Control the weekly advertising budget.",
                     "Ad spend boosts demand but has diminishing returns."),
    "manufacturer": ("🏭", "Wholesale Price Setter",
                     "You are the manufacturer; set the price to the retailer.",
                     "Balance your margin per unit against total volume."),
}

# ── Step 1 ───────────────────────────────────────────────────────────────────
st.markdown('<div class="step">Step 1 — Choose your assigned product</div>',
            unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
for col, (pk, (emoji, label, color, comps, desc)) in zip(
        [c1, c2, c3], product_info.items()):
    with col:
        active = st.session_state.get("product") == pk
        border = f"border: 2.5px solid {color};" if active else "border: 1.5px solid #E0E8F0;"
        bg     = f"background:{color}18;" if active else "background:#FAFCFF;"
        st.markdown(
            f'<div style="{border}{bg}border-radius:12px;padding:0.8rem 1rem;'
            f'margin-bottom:0.5rem">'
            f'<div style="font-size:1.05rem;font-weight:700">{emoji} {label}</div>'
            f'<div style="font-size:0.78rem;color:#666">{comps}</div>'
            f'<div style="font-size:0.74rem;color:#888;margin-top:2px">{desc}</div>'
            f'</div>', unsafe_allow_html=True)
        if st.button(f"Select {label}", key=f"btn_prod_{pk}",
                     use_container_width=True,
                     type="primary" if active else "secondary"):
            st.session_state["product"] = pk
            st.rerun()

product = st.session_state.get("product")

# ── Step 2 ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="step">Step 2 — Choose your assigned role</div>',
            unsafe_allow_html=True)
r1, r2, r3 = st.columns(3)
for col, (rk, (emoji, label, tagline, desc)) in zip(
        [r1, r2, r3], role_info.items()):
    with col:
        active = st.session_state.get("role") == rk
        border = "border: 2.5px solid #1B3A6B;" if active else "border: 1.5px solid #E0E8F0;"
        bg     = "background:#1B3A6B18;" if active else "background:#FAFCFF;"
        st.markdown(
            f'<div style="{border}{bg}border-radius:12px;padding:0.8rem 1rem;'
            f'margin-bottom:0.5rem">'
            f'<div style="font-size:1.05rem;font-weight:700">{emoji} {label}</div>'
            f'<div style="font-size:0.78rem;color:#555;font-style:italic">{tagline}</div>'
            f'<div style="font-size:0.74rem;color:#888;margin-top:2px">{desc}</div>'
            f'</div>', unsafe_allow_html=True)
        if st.button(f"Select {label}", key=f"btn_role_{rk}",
                     use_container_width=True,
                     type="primary" if active else "secondary"):
            st.session_state["role"] = rk
            st.rerun()

role = st.session_state.get("role")

# ── Step 3 — Experiment mode (password-protected) ────────────────────────────
st.markdown("---")
st.markdown('<div class="step">Step 3 — Simulation mode</div>',
            unsafe_allow_html=True)

with st.expander("🔒 Instructor: Configure experiment mode", expanded=False):
    pw = st.text_input("Instructor password", type="password", key="instr_pw")
    if pw == INSTRUCTOR_PASSWORD:
        st.success("✅ Access granted")
        exp_on = st.toggle(
            "Experiment mode (free-play)",
            value=st.session_state.get("experiment_mode", False),
            key="exp_toggle_inner",
            help=(
                "ON = students control ALL choice variables freely (free-play).\n"
                "OFF = when student sets their choice variable, all OTHER choice "
                "variables are drawn from a conditional correlated distribution."
            ),
        )
        st.session_state["experiment_mode"] = exp_on
        st.session_state["instructor_unlocked"] = True
        mode_label_instr = "🔬 Experiment (free-play)" if exp_on else "📊 Correlated simulation"
        st.info(f"Active mode: **{mode_label_instr}**")
    elif pw:
        st.error("Incorrect password.")

exp_mode  = st.session_state.get("experiment_mode", False)
mode_label = "🔬 Free-play experiment" if exp_mode else "📊 Correlated simulation"

st.markdown(
    f'<div style="background:#F4F8FF;border:1px solid #C0D4F0;border-radius:10px;'
    f'padding:0.7rem 1rem;font-size:0.88rem">'
    f'<strong>Active simulation mode:</strong> {mode_label}</div>',
    unsafe_allow_html=True,
)
st.caption(
    "**Correlated mode**: when you set your choice variable, the model draws "
    "correlated values for all other choice variables automatically.  \n"
    "**Free-play mode**: you can adjust every variable manually and see exact effects."
)

# ── Step 4 — Launch ──────────────────────────────────────────────────────────
st.markdown("---")

if product and role:
    pe = product_info[product][0]
    re = role_info[role][0]
    pl = product_info[product][1]
    rl = role_info[role][1]

    st.session_state["confirmed_product"] = product
    st.session_state["confirmed_role"]    = role

    key = (product, role)
    page_path, page_label = PAGE_MAP[key]

    st.success(
        f"✅ **{pe} {pl} · {re} {rl}** — {mode_label}  \n"
        f"Your simulation page is now unlocked in the sidebar. "
        f"Click **▶ {page_label}** to begin."
    )
    st.page_link(page_path, label=f"▶ Open {page_label}", icon="🚀")

elif not product:
    st.info("👆 Select your product in Step 1 to continue.")
else:
    st.info("👆 Select your role in Step 2 to continue.")
