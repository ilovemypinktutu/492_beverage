# 🧃 Beverage Market Simulator

Interactive retail market economics simulator for students.
Three products × three roles = **9 distinct simulation pages**.

---

## Repository structure

```
cola_market_sim2/
│
├── app.py                        ← Landing page: product & role selection
│
├── pages/
│   ├── 1_☕_Coffee_Price_Setter.py
│   ├── 2_☕_Coffee_Ad_Manager.py
│   ├── 3_☕_Coffee_Manufacturer.py
│   ├── 4_🥤_Soda_Price_Setter.py
│   ├── 5_🥤_Soda_Ad_Manager.py
│   ├── 6_🥤_Soda_Manufacturer.py
│   ├── 7_🍺_Beer_Price_Setter.py
│   ├── 8_🍺_Beer_Ad_Manager.py
│   └── 9_🍺_Beer_Manufacturer.py
│
├── core/
│   ├── __init__.py
│   ├── model.py          ← Demand, supply, equilibrium solver, financials
│   ├── ui.py             ← All Streamlit UI components and chart builders
│   ├── export.py         ← Excel (.xlsx) and CSV export
│   └── page_runner.py    ← Shared page renderer (all 9 pages call this)
│
├── requirements.txt
├── .streamlit/config.toml
└── README.md
```

---

## Quick start (local)

```bash
git clone https://github.com/<your-org>/beverage_market_sim.git
cd beverage_market_sim
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

---

## Deploy to Streamlit Community Cloud

1. Push repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app.
3. Select repo, set main file to `app.py`. Click **Deploy**.

---

## Roles & products

| | ☕ Coffee | 🥤 Soda | 🍺 Beer |
|---|---|---|---|
| 🏷️ Price Setter | Page 1 | Page 4 | Page 7 |
| 📢 Ad Manager | Page 2 | Page 5 | Page 8 |
| 🏭 Manufacturer | Page 3 | Page 6 | Page 9 |

### What each role controls
- **Price Setter** — Retail shelf price. Profit = (P−WC)×Q−OpEx, interior max due to demand quadratic.
- **Ad Manager** — Weekly ad budget. Demand rises with spend but with diminishing returns (a_adv2·Adv²), creating a genuine interior optimum.
- **Manufacturer** — Wholesale price charged to retailer. Higher WC earns more margin but shrinks Qs via supply function quadratic (b_wc2·WC²), giving an interior optimum.

### What students can adjust (sidebar)
All roles can see and adjust:
- Competitor 1 and Competitor 2 **retail prices**
- All three products' **ad spends**
- All three products' **wholesale costs**

No demographic or supply-chain parameters are visible to students.

---

## Economic model

### Demand (mixed nonlinear)
```
ln Qd = a0
  + a1·ln(P) + a_pp·P²              own price: log + quadratic
  + a2·ln(Pc1) + a3·ln(Pc2)         competitor prices
  + a4·ln(Adv) + a_adv2·Adv²        own ads: diminishing returns
  + a5·ln(Ac1) + a6·ln(Ac2)         competitor ad spillover
  + a7·ln(Income) + a8·Unemp        income & unemployment
  + a9·CS + a10·CS²                 consumer satisfaction (quadratic)
  + a11·T + a12·T² + a13·T³         time trend (cubic)
  + a14·ln(Season)                   seasonality
  + a15·ln(PopDens)                  population density
  + a16·Age + a17·Age²               shopper age (quadratic)
  + a18·Temp + a19·Temp²             temperature (quadratic)
  + product_mod                      product-specific modifier
```

### Supply (mixed nonlinear)
```
ln Qs = b0
  + b1·ln(P)                         own price
  + b2·ln(WC) + b_wc2·WC²           wholesale cost: log + quadratic
  + b3·Tax + b4·ln(Trans)            tax and transport
  + b5·UP + b6·UP² + b7·UP³         upstream power (cubic)
  + b8·ES + b9·ES²                   employee satisfaction (quadratic)
  + b10·CapUtil + b11·ln(Energy)     capacity and energy
  + b14·ln(StoreCount)               store count
```

### Profit & interior maxima
```
Q_sold  = min(Qd(P), Qs(P))
Revenue = P × Q_sold
COGS    = WC × Q_sold
OpEx    = Ad spend + Transport + Fixed overhead
EBIT    = Revenue − COGS − OpEx
Net Profit = EBIT × (1 − tax_rate)
```

Each role's profit function has a genuine interior maximum within the slider range.

### Equilibrium solver
Bisection (80 iterations, precision ~10⁻²³) followed by Newton-Raphson refinement (tolerance 10⁻¹⁰).
