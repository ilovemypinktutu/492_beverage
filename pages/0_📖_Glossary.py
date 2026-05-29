"""
pages/0_📖_Glossary.py — Market conditions glossary page.
Always visible in the sidebar.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st

st.set_page_config(
    page_title="Glossary — Market Conditions",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Keep auto-nav hidden; show our own sidebar links
st.markdown("""
<style>
  [data-testid="stSidebarNav"] { display: none !important; }
  .gt { font-size:1rem; font-weight:700; color:#1B3A6B; margin-bottom:2px; }
  .gd { font-size:0.87rem; color:#333; line-height:1.55; margin-bottom:1.1rem; }
  .ge { font-size:0.8rem; color:#666; font-style:italic; }
  .cat { font-size:0.72rem; font-weight:700; text-transform:uppercase;
         letter-spacing:.06em; color:#888; margin:1.4rem 0 0.4rem; }
  .block-container { padding-top:1.5rem; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🧃 Navigation")
    st.page_link("app.py",                       label="🏠 Home / Setup")
    st.page_link("pages/00_ℹ️_How_It_Works.py", label="ℹ️ How It Works")
    st.page_link("pages/0_📖_Glossary.py",       label="📖 Glossary")
    confirmed_product = st.session_state.get("confirmed_product")
    confirmed_role    = st.session_state.get("confirmed_role")
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
    if confirmed_product and confirmed_role:
        key = (confirmed_product, confirmed_role)
        if key in PAGE_MAP:
            path, label = PAGE_MAP[key]
            st.markdown("---")
            st.markdown("**Your simulation:**")
            st.page_link(path, label=f"▶ {label}")

st.title("📖 Market Conditions Glossary")
st.caption("Definitions of every market condition used in the simulation.")

search = st.text_input("🔍 Search terms", placeholder="e.g. price, advertising, demand…",
                       label_visibility="collapsed")
q = search.strip().lower()

GLOSSARY = [
    # ── Demand-side ──────────────────────────────────────────────────────────
    ("Demand-side", [
        ("Retail Price",
         "The price at which the product is sold to consumers at the point of sale. "
         "Higher prices generally reduce the quantity consumers wish to buy. "
         "This is the choice variable for the Price Setter role.",
         "e.g. $1.80/can of soda"),

        ("Competitor Prices",
         "The retail prices charged by the two other beverage products in the market. "
         "When a competitor raises its price, some consumers switch to your product, "
         "increasing your demand (substitution effect). Each product has two competitors.",
         "e.g. if Soda costs $1.80 and Coffee rises to $4.50, some coffee buyers switch to soda"),

        ("Advertising Spend",
         "The weekly budget spent on marketing and promotions for a product. "
         "Higher ad spend increases brand awareness and shifts the demand curve outward — "
         "more units are demanded at every price. Returns are diminishing: doubling the budget "
         "less than doubles demand. This is the choice variable for the Ad Manager role.",
         "e.g. $50K/week in regional TV and digital ads"),

        ("Competitor Ad Spend",
         "The advertising budgets of the two competing products. "
         "Heavy competitor advertising pulls consumers toward rival products, "
         "reducing demand for your product. This negative spillover is captured "
         "in the demand function.",
         "e.g. a beer campaign during a sports season reduces soda demand"),

        ("Local Income",
         "The median household income in the market area, measured in thousands of dollars "
         "per year. Higher incomes generally increase spending on all normal goods. "
         "Coffee has a higher income elasticity than soda because it is more of a "
         "premium product.",
         "e.g. $65K/year median income in a suburban market"),

        ("Unemployment Rate",
         "The percentage of the local workforce that is unemployed and seeking work. "
         "Higher unemployment reduces disposable income and consumer confidence, "
         "depressing demand for beverages — especially premium products like coffee.",
         "e.g. 5% unemployment in baseline scenario"),

        ("Population Density",
         "The number of people per square mile in the market area. "
         "Denser areas support higher total sales volumes. "
         "A downtown urban market with 15,000 people/sq mi sells far more "
         "units than a rural area with 300/sq mi.",
         "e.g. 3,000 people/sq mile in a suburban area"),

        ("Shopper Age Index",
         "The average age of the primary consumer base in the market area (years). "
         "Younger shoppers (late 20s) buy the most beverages; demand declines for "
         "older demographics. Soda skews younger; coffee spans a broader age range; "
         "beer peaks in early adulthood.",
         "e.g. 35-year average in a mixed suburban neighborhood"),

        ("Season Index",
         "A multiplier reflecting seasonal demand patterns. "
         "1.0 = average week; 1.5 = peak summer demand; 0.5 = winter trough. "
         "Cold beverages (soda, beer) have stronger seasonality than coffee.",
         "e.g. 1.45 during a hot July week"),

        ("Temperature",
         "The average weekly outdoor temperature in degrees Fahrenheit. "
         "Warm weather strongly increases cold-beverage demand (soda, beer) and "
         "moderately reduces hot-beverage demand (coffee). Extreme cold also depresses "
         "all outdoor-consumption beverages.",
         "e.g. 95°F in summer vs 30°F in winter"),

        ("Consumer Satisfaction",
         "A 0–10 score reflecting existing consumer loyalty and brand satisfaction. "
         "Higher satisfaction drives repeat purchases and positive word-of-mouth, "
         "boosting demand. The relationship is quadratic — gains diminish beyond ~7.5.",
         "e.g. 7.0 = solid brand loyalty; 9.0 = strong brand advocates"),

        ("Health Trend",
         "A market-level index of health-consciousness among consumers. "
         "Positive values indicate a health-aware market that reduces sugary beverage "
         "consumption (hurts soda, moderately hurts beer). Negative values indicate "
         "a market less concerned with health. Coffee benefits mildly from positive "
         "health trends (perceived as functional).",
         "e.g. +0.5 in a fitness-oriented urban market; -0.2 in a price-driven rural area"),

        ("In-Store Promotion",
         "A binary indicator (on/off) for whether the product has active in-store "
         "promotions such as end-cap displays, coupons, or multi-buy deals. "
         "Promotions provide a direct short-term boost to demand.",
         "e.g. a 'Buy 2 Get 1 Free' soda deal at checkout"),

        ("Time Since Baseline",
         "The number of months since the simulation baseline. Captures secular trends "
         "such as brand building, market penetration, or market fatigue. "
         "The effect is cubic: rapid early growth, deceleration, then a modest long-run uptick.",
         "e.g. month 0 = launch; month 24 = established brand"),
    ]),

    # ── Supply-side ──────────────────────────────────────────────────────────
    ("Supply-side", [
        ("Wholesale Cost",
         "The price the manufacturer charges the retailer per unit — the retailer's "
         "cost of goods. Higher wholesale costs reduce the retailer's margin and "
         "their willingness to stock the product, shifting the supply curve left. "
         "This is the choice variable for the Manufacturer role.",
         "e.g. $0.90/can = manufacturer's price to grocery retailer"),

        ("Tax Rate",
         "The combined sales and excise tax rate applied to the product, as a percentage. "
         "Excise taxes on beverages (especially alcohol and sugary drinks) directly "
         "increase costs, reducing the quantity suppliers are willing to bring to market.",
         "e.g. 12% excise tax on beer; 9% sales tax on soda"),

        ("Transport Cost",
         "The weekly logistics cost of moving product from the distribution center "
         "to retail outlets, in thousands of dollars. Higher transport costs reduce "
         "supply. Remote markets pay more; urban markets with nearby warehouses pay less.",
         "e.g. $20K/week for a regional suburban distribution network"),

        ("Upstream Market Power",
         "An index from 0 to 1 measuring the bargaining strength of the upstream supplier "
         "(bottler, brewer, roaster) relative to the retailer. "
         "0 = retailer has full power; 1 = supplier monopoly. "
         "High upstream power squeezes margins non-linearly: mild at first, then severe.",
         "e.g. 0.85 = a major brewer who controls exclusive regional distribution rights"),

        ("Employee Satisfaction",
         "A 0–10 score reflecting workforce morale and engagement at the retail/distribution "
         "level. Higher satisfaction improves operational efficiency and reduces errors, "
         "increasing effective supply. The relationship is quadratic — gains peak near 8.75.",
         "e.g. 7.0 = average workforce; 9.0 = highly motivated, low-turnover staff"),

        ("Capacity Utilisation",
         "The percentage of production and distribution capacity currently in use. "
         "Higher utilisation means the supply chain is running closer to its maximum, "
         "increasing quantity supplied. Low utilisation suggests idle inventory or "
         "underused facilities.",
         "e.g. 75% = three-quarters of warehouse and delivery capacity in active use"),

        ("Energy Cost Index",
         "An index measuring the cost of energy (electricity, refrigeration, fuel) "
         "relative to a baseline of 1.0. Higher energy costs raise operating expenses "
         "for refrigeration, production, and delivery, reducing supply. "
         "Particularly important for cold-chain products like beer.",
         "e.g. 1.5 = energy costs 50% above baseline, as in a cold-winter supply squeeze"),

        ("Input Scarcity",
         "A 0–1 score measuring how constrained the supply of key raw materials is. "
         "0 = no scarcity; 1 = severe shortage. "
         "For coffee this reflects coffee-bean harvests; for beer, hops and grain; "
         "for soda, sugar and CO₂ supply. High scarcity reduces supply.",
         "e.g. 0.4 = moderate CO₂ shortage affecting canned-beverage supply"),

        ("Regulatory Burden",
         "A 0–1 composite score measuring compliance costs: labeling requirements, "
         "health inspections, import/export restrictions, alcohol licensing, etc. "
         "Higher regulatory burden increases fixed and variable costs, reducing supply.",
         "e.g. 0.3 = moderate local health-code requirements; 0.8 = strict alcohol licensing"),

        ("Store Count",
         "The number of retail outlets in the market area actively stocking the product. "
         "More stores distribute more total supply to consumers. "
         "A national-chain rollout doubles store count and dramatically increases "
         "total quantity supplied.",
         "e.g. 8 stores = small regional market; 25 stores = large urban network"),
    ]),

    # ── Financial outcomes ───────────────────────────────────────────────────
    ("Financial Outcomes", [
        ("Revenue",
         "Total weekly sales revenue: Equilibrium Price × Units Sold. "
         "This is the top line — what consumers pay before any costs are deducted.",
         "e.g. $1.80 × 150,000 units = $270,000/week"),

        ("Cost of Goods Sold (COGS)",
         "The direct cost of the units sold: Wholesale Cost × Units Sold. "
         "This is the retailer's payment to the manufacturer for each unit.",
         "e.g. $0.90 × 150,000 = $135,000/week"),

        ("Gross Profit",
         "Revenue minus COGS. Represents the contribution before operating expenses. "
         "Gross Profit = (Price − Wholesale Cost) × Units Sold = "
         "Contribution Margin × Units Sold.",
         "e.g. $270K − $135K = $135K gross profit"),

        ("Operating Expenses (OpEx)",
         "Fixed and semi-fixed weekly costs not tied to individual units: "
         "advertising spend + transport cost + fixed overhead (rent, utilities, admin). "
         "These must be covered by gross profit for the firm to break even.",
         "e.g. $50K ad + $20K transport + $5K overhead = $75K OpEx/week"),

        ("EBIT",
         "Earnings Before Interest and Tax: Gross Profit − OpEx. "
         "The operating profit before financing costs and taxes.",
         "e.g. $135K − $75K = $60K EBIT"),

        ("Net Profit",
         "EBIT multiplied by (1 − tax rate). The bottom-line profit after all costs. "
         "This is the primary outcome to maximise as you adjust your choice variable.",
         "e.g. $60K × (1 − 0.09) = $54.6K net profit"),

        ("Break-Even Volume",
         "The minimum weekly units sold needed to cover all fixed costs: "
         "OpEx ÷ Contribution Margin. Below this volume the firm loses money; "
         "above it every additional unit adds to profit.",
         "e.g. $75K ÷ $0.90 CM = 83,333 units/week break-even"),

        ("Contribution Margin",
         "The profit contribution of each unit sold: Price − Wholesale Cost. "
         "Every unit sold above break-even volume adds one contribution margin "
         "to net profit.",
         "e.g. $1.80 − $0.90 = $0.90/unit contribution margin"),
    ]),

    # ── Market structure ────────────────────────────────────────────────────
    ("Market Structure & Equilibrium", [
        ("Market Equilibrium",
         "The price at which quantity demanded equals quantity supplied. "
         "At equilibrium there is no excess demand (shortage) or excess supply (surplus). "
         "The simulator solves for this price using a two-phase numerical algorithm.",
         "e.g. P* = $1.80 for soda with default parameters"),

        ("Excess Demand",
         "Quantity demanded minus quantity supplied at a given price. "
         "Positive excess demand means consumers want more than is available — "
         "a shortage. This occurs when the price is set below equilibrium.",
         "e.g. if price = $1.50 and Qd = 180K but Qs = 130K, excess demand = 50K"),

        ("Excess Supply",
         "The amount by which quantity supplied exceeds quantity demanded. "
         "A surplus — unsold inventory accumulates. Occurs when price is set "
         "above equilibrium.",
         "e.g. if price = $2.20 and Qs = 200K but Qd = 90K, excess supply = 110K"),

        ("Substitution Effect",
         "When a competitor raises its price, some consumers switch to your product, "
         "increasing your demand. Measured by the cross-price elasticity. "
         "All three beverages are substitutes for each other to some degree.",
         "e.g. a beer price increase shifts some consumers to soda"),

        ("Upstream Market Power",
         "The degree to which your supplier (manufacturer or bottler) can dictate "
         "terms to your business. High upstream power compresses retailer margins, "
         "reduces supply, and limits your pricing flexibility.",
         "e.g. a dominant regional brewer who is the only source of a popular beer brand"),

        ("Price Elasticity of Demand",
         "How sensitive quantity demanded is to a 1% change in price. "
         "Elastic demand (|ε| > 1) means a 1% price rise reduces quantity by more "
         "than 1% — typical for price-sensitive beverages like soda. "
         "Inelastic demand (|ε| < 1) means consumers are less price-sensitive.",
         "Soda elasticity ≈ −1.6; Coffee ≈ −1.4; Beer ≈ −1.5"),

        ("Correlated Market Simulation",
         "When you set your choice variable (e.g. coffee price), the simulator "
         "automatically draws correlated values for all other choice variables "
         "(competitor prices, ad spends, wholesale costs) from a joint distribution. "
         "This reflects the reality that market variables do not move independently — "
         "a commodity-cost shock raises wholesale costs across all products simultaneously.",
         "e.g. a sugar-price spike raises wholesale costs for both soda and beer together"),
    ]),
]

def render_entry(term, defn, example):
    match = (not q or q in term.lower() or q in defn.lower()
             or (example and q in example.lower()))
    if match:
        st.markdown(f'<div class="gt">{term}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="gd">{defn}</div>', unsafe_allow_html=True)
        if example:
            st.markdown(f'<div class="ge">Example: {example}</div>',
                        unsafe_allow_html=True)
        st.markdown("")

any_shown = False
for category, entries in GLOSSARY:
    visible = [e for e in entries
               if not q or q in e[0].lower() or q in e[1].lower()
               or (len(e) > 2 and q in e[2].lower())]
    if visible:
        any_shown = True
        st.markdown(f'<div class="cat">{category}</div>', unsafe_allow_html=True)
        for entry in visible:
            term, defn, *rest = entry
            example = rest[0] if rest else ""
            render_entry(term, defn, example)

if not any_shown:
    st.caption("No matching terms. Try a shorter keyword.")
