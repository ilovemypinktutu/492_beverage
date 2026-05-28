# 🥤 Cola Retail Market Simulator

An interactive market-economics simulator for students, built with **Python + Streamlit**.

Students set a **retail price** and instantly see the resulting market equilibrium,
supply & demand curves, revenue, costs, and profit — all grounded in a rigorous
log-linear + quadratic + cubic demand/supply model.

---

## 📁 Repository Structure

```
cola_market_sim/
│
├── app.py                  ← Streamlit entry point (run this)
│
├── core/
│   ├── __init__.py
│   ├── model.py            ← All economics: demand, supply, equilibrium solver, financials
│   └── export.py           ← Excel (.xlsx) and CSV export utilities
│
├── requirements.txt        ← Python dependencies
├── .streamlit/
│   └── config.toml         ← Streamlit theme configuration
└── README.md
```

---

## 🚀 Quick Start (local)

```bash
# 1. Clone the repo
git clone https://github.com/<your-org>/cola_market_sim.git
cd cola_market_sim

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## ☁️ Deploy to Streamlit Community Cloud (free)

1. Push this repo to GitHub (public or private).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app** → select your repo → set **Main file path** to `app.py`.
4. Click **Deploy**. Done — shareable URL generated automatically.

No additional configuration needed; Streamlit Cloud reads `requirements.txt` automatically.

---

## 🎓 Student Instructions

1. **Open the app** at the shared Streamlit URL (or locally).
2. **Drag the price slider** (top of main panel) to your chosen retail price.
3. Watch the **equilibrium metrics** update in real time.
4. **Read the alert** — it tells you whether your price is above or below
   the market-clearing equilibrium and what that means economically.
5. Explore the **three chart tabs**:
   - *Supply & Demand* — classic textbook curve with your price marked
   - *Profit Curve* — see how profit varies across the price range
   - *Cost Breakdown* — pie chart of where revenue goes
6. Adjust **market conditions** in the left sidebar to model different scenarios
   (competitor pricing, local demographics, upstream power, etc.).
7. **Export** your scenario as Excel or CSV for your assignment.

---

## 📐 Economic Model

### Demand function (18 parameters)

| Term | Variable | Form |
|------|----------|------|
| Own price | P | log-linear |
| Competitor price | P_comp | log-linear |
| Advertising spend | Adv | log-linear |
| Local income | Inc | log-linear |
| Unemployment rate | U | linear |
| Consumer satisfaction | CS | **quadratic** (peaks ~7.5) |
| Time trend | T | **cubic** (growth → plateau → uptick) |
| Season index | S | log-linear |
| Brand type | — | dummy |
| Population density | D | log-linear |
| Shopper age | Age | **quadratic** (peaks ~29 yrs) |
| Health trend | H | linear |
| Promotion dummy | Promo | linear |
| Temperature | Temp | **quadratic** |

### Supply function (14 parameters)

| Term | Variable | Form |
|------|----------|------|
| Own price | P | log-linear |
| Wholesale cost | WC | log-linear |
| Tax rate | τ | linear |
| Transport cost | Trans | log-linear |
| Upstream market power | UP | **cubic** (accelerating compression) |
| Employee satisfaction | ES | **quadratic** (peaks ~8.75) |
| Capacity utilisation | Cap | linear |
| Energy cost index | EC | log-linear |
| Input scarcity | Sc | linear |
| Regulatory burden | Reg | linear |
| Store count | N | log-linear |

### Equilibrium solver

Two-phase numerical solver:
1. **Bisection** — 80 iterations, bracket `[$0.05, $50]`, precision ~10⁻²³.
2. **Newton-Raphson** — refines from bisection seed using numerical derivative,
   convergence tolerance 10⁻¹⁰. Falls back to bisection result if NR diverges.

### Financial model

```
Revenue       = P* × Q*
COGS          = wholesale_cost × Q*
Gross Profit  = Revenue − COGS
OpEx          = Ad spend + Transport + Fixed overhead
EBIT          = Gross Profit − OpEx
Tax           = max(EBIT, 0) × tax_rate
Net Profit    = EBIT − Tax
Break-even    = OpEx / (P* − wholesale_cost)
```

---

## 🛠 Extending the Model

- **Add new factors**: edit `core/model.py` — `demand()` and `supply()` functions.
  Add a parameter to `MarketConditions` and a slider in `app.py`.
- **Change coefficient values**: all α and β parameters are annotated at the top
  of each function body.
- **Add a new page**: create `pages/my_page.py` — Streamlit automatically
  shows it in the sidebar nav.

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `streamlit` | Web UI framework |
| `plotly` | Interactive charts |
| `pandas` | Data tables |
| `openpyxl` | Excel export |

---

## 📄 License

MIT — free to use, modify, and distribute for educational purposes.
