"""
core/model.py — Multi-product beverage retail market simulator.

Products : Coffee | Soda | Beer
Roles    : Price Setter | Ad Spend Manager | Wholesale Price Setter (Manufacturer)

Demand functional form
----------------------
  ln Qd = a0
    + a1*ln(P) + a_pp*P^2            own price: log-linear + quadratic
    + a2*ln(Pc1) + a3*ln(Pc2)        competitor prices: log-linear
    + a4*ln(Adv) + a_adv2*Adv^2      own ads: log + quadratic (diminishing returns)
    + a5*ln(Ac1) + a6*ln(Ac2)        competitor ads: negative log-linear spillover
    + a7*ln(Income)                   income: log-linear
    + a8*Unemp                        unemployment: linear
    + a9*CS + a10*CS^2                consumer satisfaction: quadratic
    + a11*T + a12*T^2 + a13*T^3      time trend: cubic
    + a14*ln(Season)                  seasonality: log-linear
    + a15*ln(PopDens)                 population density: log-linear
    + a16*Age + a17*Age^2             shopper age: quadratic
    + a18*Temp + a19*Temp^2           temperature: quadratic
    + product_mod                     product-specific modifier

Supply functional form
----------------------
  ln Qs = b0
    + b1*ln(P)                        own price: log-linear
    + b2*ln(WC) + b_wc2*WC^2         wholesale cost: log + quadratic
    + b3*Tax                          tax: linear
    + b4*ln(Trans)                    transport: log-linear
    + b5*UP + b6*UP^2 + b7*UP^3      upstream power: cubic
    + b8*ES + b9*ES^2                 employee satisfaction: quadratic
    + b10*CapUtil                     capacity: linear
    + b11*ln(Energy)                  energy cost: log-linear
    + b14*ln(StoreCount)              store count: log-linear

Profit & interior maxima
------------------------
  Q_sold = min(Qd(P), Qs(P))  — market-clearing quantity at student's price
  Profit = (P - WC)*Q_sold - AdOpEx - TransOpEx - FixedOH  (pre-tax EBIT * (1-tau))

  This creates genuine interior maxima:
    Price setter   : (P-WC)*min(Qd(P),Qs(P)) is concave around equilibrium
    Ad manager     : Qd rises with Adv but a_adv2*Adv^2 makes returns diminishing;
                     profit peaks where marginal revenue from ads = marginal ad cost
    Manufacturer   : (WC-UnitCost)*Qs(WC) has interior max because higher WC
                     reduces Qs via the b2/b_wc2 terms

Calibrated intercepts (bisection-verified, targets in docstring):
  Coffee: Peq~$3.50, Qty~80K,  profit@eq~+$89K
  Soda:   Peq~$1.80, Qty~150K, profit@eq~+$55K
  Beer:   Peq~$3.00, Qty~60K,  profit@eq~+$26K
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Literal

Product = Literal["coffee", "soda", "beer"]
Role    = Literal["price_setter", "ad_manager", "manufacturer"]

# ---------------------------------------------------------------------------
# Calibrated intercepts
# ---------------------------------------------------------------------------
_DEMAND_INTERCEPTS: dict[str, float] = {
    "coffee": 6.775,
    "soda":   6.586,
    "beer":   6.490,
}
_SUPPLY_INTERCEPTS: dict[str, float] = {
    "coffee": 9.331,
    "soda":  10.327,
    "beer":   9.843,
}

# ---------------------------------------------------------------------------
# Product defaults
# ---------------------------------------------------------------------------
PRODUCT_DEFAULTS: dict[str, dict] = {
    "coffee": dict(
        eq_price=3.50, eq_qty=80_000,
        own_price=3.50, wc_default=1.20, ad_default=60.0,
        comp1="soda",  comp2="beer",
        comp1_price=1.80, comp2_price=3.00,
        comp1_ad=50.0,   comp2_ad=40.0,
        tax=8.0, transport=22.0, upstream=0.25,
        esat=7.0, cap_util=75.0, energy=1.0, store_count=10.0,
        health_mod=0.10, stim_mod=0.15, alc_mod=0.0,
    ),
    "soda": dict(
        eq_price=1.80, eq_qty=150_000,
        own_price=1.80, wc_default=0.90, ad_default=50.0,
        comp1="coffee", comp2="beer",
        comp1_price=3.50, comp2_price=3.00,
        comp1_ad=60.0,   comp2_ad=40.0,
        tax=9.0, transport=20.0, upstream=0.30,
        esat=7.0, cap_util=75.0, energy=1.0, store_count=8.0,
        health_mod=-0.12, stim_mod=0.05, alc_mod=0.0,
    ),
    "beer": dict(
        eq_price=3.00, eq_qty=60_000,
        own_price=3.00, wc_default=1.50, ad_default=40.0,
        comp1="coffee", comp2="soda",
        comp1_price=3.50, comp2_price=1.80,
        comp1_ad=60.0,   comp2_ad=50.0,
        tax=12.0, transport=15.0, upstream=0.35,
        esat=7.0, cap_util=70.0, energy=1.1, store_count=6.0,
        health_mod=-0.08, stim_mod=0.0, alc_mod=0.20,
    ),
}

FIXED_DEMOGRAPHICS: dict = dict(
    local_income_k=65.0,
    unemployment_pct=5.0,
    pop_density=3000.0,
    age_index=35.0,
    season_index=1.0,
    temperature_f=72.0,
    consumer_sat=7.0,
    time_months=0.0,
)


# ---------------------------------------------------------------------------
# 1. MarketState
# ---------------------------------------------------------------------------
@dataclass
class MarketState:
    product: str = "soda"

    # Student-controlled
    own_price: float = 1.80
    ad_spend_k: float = 50.0
    wholesale_cost: float = 0.90

    # Competitor variables (student can also adjust)
    comp1_price: float = 3.50
    comp2_price: float = 3.00
    comp1_ad_k: float = 60.0
    comp2_ad_k: float = 40.0
    comp1_wholesale: float = 1.20
    comp2_wholesale: float = 1.50

    # Fixed supply-side (hidden)
    tax_rate_pct: float = 9.0
    transport_cost_k: float = 20.0
    upstream_power: float = 0.30
    employee_sat: float = 7.0
    capacity_util_pct: float = 75.0
    energy_cost_idx: float = 1.0
    store_count: float = 8.0
    fixed_overhead_k: float = 5.0

    # Fixed demographics (hidden)
    local_income_k: float = 65.0
    unemployment_pct: float = 5.0
    pop_density: float = 3000.0
    age_index: float = 35.0
    season_index: float = 1.0
    temperature_f: float = 72.0
    consumer_sat: float = 7.0
    time_months: float = 0.0

    # Product modifiers
    health_mod: float = 0.0
    stim_mod: float = 0.0
    alc_mod: float = 0.0

    @property
    def __dataclass_fields__(self):
        import dataclasses
        return {f.name: f for f in dataclasses.fields(self)}


def make_market_state(product: str, overrides: dict | None = None) -> MarketState:
    d = PRODUCT_DEFAULTS[product]
    ms = MarketState(
        product=product,
        own_price=d["own_price"],
        ad_spend_k=d["ad_default"],
        wholesale_cost=d["wc_default"],
        comp1_price=d["comp1_price"],
        comp2_price=d["comp2_price"],
        comp1_ad_k=d["comp1_ad"],
        comp2_ad_k=d["comp2_ad"],
        comp1_wholesale=PRODUCT_DEFAULTS[d["comp1"]]["wc_default"],
        comp2_wholesale=PRODUCT_DEFAULTS[d["comp2"]]["wc_default"],
        tax_rate_pct=d["tax"],
        transport_cost_k=d["transport"],
        upstream_power=d["upstream"],
        employee_sat=d["esat"],
        capacity_util_pct=d["cap_util"],
        energy_cost_idx=d["energy"],
        store_count=d["store_count"],
        health_mod=d["health_mod"],
        stim_mod=d["stim_mod"],
        alc_mod=d["alc_mod"],
        **FIXED_DEMOGRAPHICS,
    )
    if overrides:
        for k, v in overrides.items():
            setattr(ms, k, v)
    return ms


# ---------------------------------------------------------------------------
# 2. Demand
# ---------------------------------------------------------------------------
def demand(price: float, ms: MarketState) -> float:
    prod = ms.product
    a0   = _DEMAND_INTERCEPTS[prod]

    # Own price: log-linear + quadratic (quadratic creates interior profit max)
    a1   = {"coffee": -1.40, "soda": -1.60, "beer": -1.50}[prod]
    a_pp = {"coffee": -0.04, "soda": -0.10, "beer": -0.06}[prod]

    # Cross-price elasticities (two competitors)
    a2 = {"coffee": 0.30, "soda": 0.60, "beer": 0.45}[prod]
    a3 = {"coffee": 0.25, "soda": 0.40, "beer": 0.35}[prod]

    # Own advertising: log + quadratic diminishing returns
    a4     = {"coffee": 0.30, "soda": 0.25, "beer": 0.28}[prod]
    a_adv2 = {"coffee": -8e-5, "soda": -1e-4, "beer": -9e-5}[prod]

    # Competitor advertising spillover (negative)
    a5 = {"coffee": -0.10, "soda": -0.15, "beer": -0.12}[prod]
    a6 = {"coffee": -0.08, "soda": -0.12, "beer": -0.10}[prod]

    # Demographics
    a7  =  0.50;  a8  = -0.030
    a9  =  0.18;  a10 = -0.012
    a11 =  0.025; a12 = -0.0008; a13 = 4e-6
    a14 =  0.40
    a15 =  0.30
    a16 =  0.040; a17 = -0.0007
    a18 =  0.006; a19 = -3.5e-5

    product_mod = ms.health_mod + ms.stim_mod + ms.alc_mod

    P   = max(price, 0.01)
    Pc1 = max(ms.comp1_price, 0.01)
    Pc2 = max(ms.comp2_price, 0.01)
    Adv = max(ms.ad_spend_k, 0.01)
    Ac1 = max(ms.comp1_ad_k, 0.01)
    Ac2 = max(ms.comp2_ad_k, 0.01)
    Inc = max(ms.local_income_k, 0.01)
    CS  = ms.consumer_sat; T  = ms.time_months
    S   = max(ms.season_index, 0.01)
    D   = max(ms.pop_density, 1.0)
    Age = ms.age_index; Tmp = ms.temperature_f

    ln_qd = (
        a0
        + a1   * math.log(P)   + a_pp   * P**2
        + a2   * math.log(Pc1)
        + a3   * math.log(Pc2)
        + a4   * math.log(Adv) + a_adv2 * Adv**2
        + a5   * math.log(Ac1)
        + a6   * math.log(Ac2)
        + a7   * math.log(Inc)
        + a8   * ms.unemployment_pct
        + a9   * CS  + a10 * CS**2
        + a11  * T   + a12 * T**2  + a13 * T**3
        + a14  * math.log(S)
        + a15  * math.log(D)
        + a16  * Age + a17 * Age**2
        + a18  * Tmp + a19 * Tmp**2
        + product_mod
    )
    return math.exp(ln_qd)


# ---------------------------------------------------------------------------
# 3. Supply
# ---------------------------------------------------------------------------
def supply(price: float, ms: MarketState) -> float:
    prod = ms.product
    b0   = _SUPPLY_INTERCEPTS[prod]

    b1    = {"coffee": 1.10, "soda": 1.20, "beer": 1.05}[prod]
    b2    = {"coffee": -1.30, "soda": -1.40, "beer": -1.20}[prod]
    b_wc2 = {"coffee": -0.05, "soda": -0.08, "beer": -0.04}[prod]

    b3  = -0.018; b4  = -0.08
    b5  = -0.50;  b6  = -0.30; b7 = 0.10
    b8  =  0.14;  b9  = -0.008
    b10 =  0.005; b11 = -0.35; b14 = 0.20

    P   = max(price, 0.01)
    WC  = max(ms.wholesale_cost, 0.01)
    Tr  = max(ms.transport_cost_k, 0.01)
    UP  = ms.upstream_power; ES = ms.employee_sat
    EC  = max(ms.energy_cost_idx, 0.01)
    SC  = max(ms.store_count, 1.0)

    ln_qs = (
        b0
        + b1  * math.log(P)
        + b2  * math.log(WC) + b_wc2 * WC**2
        + b3  * ms.tax_rate_pct
        + b4  * math.log(Tr)
        + b5  * UP + b6 * UP**2 + b7 * UP**3
        + b8  * ES + b9 * ES**2
        + b10 * ms.capacity_util_pct
        + b11 * math.log(EC)
        + b14 * math.log(SC)
    )
    return math.exp(ln_qs)


def excess_demand(price: float, ms: MarketState) -> float:
    return demand(price, ms) - supply(price, ms)


# ---------------------------------------------------------------------------
# 4. Equilibrium solver
# ---------------------------------------------------------------------------
@dataclass
class EquilibriumResult:
    price_eq: float
    quantity_eq: float
    quantity_demanded: float
    quantity_supplied: float
    excess: float
    converged: bool
    iterations: int
    method: str


def find_equilibrium(ms: MarketState,
                     p_low: float = 0.05, p_high: float = 50.0,
                     bisection_iters: int = 80, nr_iters: int = 30,
                     nr_tol: float = 1e-10) -> EquilibriumResult:
    """Bisection (80 iter) + Newton-Raphson refinement."""
    ed_low  = excess_demand(p_low,  ms)
    ed_high = excess_demand(p_high, ms)
    if ed_low < 0:   p_low  = 1e-4;  ed_low  = excess_demand(p_low,  ms)
    if ed_high > 0:  p_high = 500.0; ed_high = excess_demand(p_high, ms)
    if ed_low * ed_high > 0:
        p_eq = (p_low + p_high) / 2
        qd, qs = demand(p_eq, ms), supply(p_eq, ms)
        return EquilibriumResult(p_eq, (qd+qs)/2, qd, qs, qd-qs, False, 0, "failed")

    lo, hi = p_low, p_high
    for _ in range(bisection_iters):
        mid = (lo + hi) / 2.0
        if excess_demand(mid, ms) > 0: lo = mid
        else: hi = mid
    p_b = (lo + hi) / 2.0

    p_nr = p_b; nr_ok = False; nr_n = 0
    for _ in range(nr_iters):
        h  = p_nr * 1e-6 + 1e-12
        fv = excess_demand(p_nr, ms)
        fp = (excess_demand(p_nr + h, ms) - fv) / h
        if abs(fp) < 1e-15: break
        pn = max(1e-4, min(p_nr - fv / fp, 500.0))
        nr_n += 1
        if abs(pn - p_nr) < nr_tol: p_nr = pn; nr_ok = True; break
        p_nr = pn

    p_eq   = p_nr if nr_ok else p_b
    method = "bisection+NR" if nr_ok else "bisection"
    qd, qs = demand(p_eq, ms), supply(p_eq, ms)
    return EquilibriumResult(
        price_eq=p_eq, quantity_eq=(qd+qs)/2,
        quantity_demanded=qd, quantity_supplied=qs,
        excess=qd-qs, converged=True,
        iterations=bisection_iters+nr_n, method=method,
    )


# ---------------------------------------------------------------------------
# 5. Financials  (Q_sold = min(Qd, Qs) — key for interior profit maximum)
# ---------------------------------------------------------------------------
@dataclass
class Financials:
    revenue: float
    cogs: float
    gross_profit: float
    gross_margin_pct: float
    ad_expense: float
    transport_expense: float
    fixed_overhead: float
    total_opex: float
    ebit: float
    tax_amount: float
    net_profit: float
    net_margin_pct: float
    contribution_margin: float
    break_even_units: float
    q_sold: float            # min(Qd, Qs) — actual units transacted
    manufacturer_revenue: float = 0.0
    manufacturer_profit: float  = 0.0


def compute_financials(eq: EquilibriumResult, ms: MarketState) -> Financials:
    # Use market-clearing quantity: min(Qd, Qs) at equilibrium
    q_sold = min(eq.quantity_demanded, eq.quantity_supplied)
    p      = eq.price_eq

    revenue      = p * q_sold
    cogs         = ms.wholesale_cost * q_sold
    gross_profit = revenue - cogs
    gross_margin = (gross_profit / revenue * 100) if revenue > 0 else 0.0

    ad_exp     = ms.ad_spend_k       * 1_000
    trans_exp  = ms.transport_cost_k * 1_000
    fixed      = ms.fixed_overhead_k * 1_000
    total_opex = ad_exp + trans_exp + fixed

    ebit       = gross_profit - total_opex
    tax        = max(ebit * ms.tax_rate_pct / 100, 0.0)
    net_profit = ebit - tax
    net_margin = (net_profit / revenue * 100) if revenue > 0 else 0.0

    cm  = p - ms.wholesale_cost
    bep = total_opex / cm if cm > 0 else float("inf")

    # Manufacturer perspective (earns WC per unit, bears ~40% unit cost + some fixed)
    mfr_unit_cost  = ms.wholesale_cost * 0.40
    mfr_revenue    = ms.wholesale_cost * q_sold
    mfr_profit     = ((mfr_revenue - mfr_unit_cost * q_sold)
                      - ad_exp * 0.5 - fixed * 0.5)

    return Financials(
        revenue=revenue, cogs=cogs,
        gross_profit=gross_profit, gross_margin_pct=gross_margin,
        ad_expense=ad_exp, transport_expense=trans_exp,
        fixed_overhead=fixed, total_opex=total_opex,
        ebit=ebit, tax_amount=tax,
        net_profit=net_profit, net_margin_pct=net_margin,
        contribution_margin=cm, break_even_units=bep,
        q_sold=q_sold,
        manufacturer_revenue=mfr_revenue, manufacturer_profit=mfr_profit,
    )


# ---------------------------------------------------------------------------
# 6. Sensitivity sweeps
# ---------------------------------------------------------------------------
def _profit_at(p: float, ms: MarketState) -> float:
    """Net profit using min(Qd,Qs)."""
    qd   = demand(p, ms)
    qs   = supply(p, ms)
    q    = min(qd, qs)
    opex = (ms.ad_spend_k + ms.transport_cost_k + ms.fixed_overhead_k) * 1000
    return (p * q - ms.wholesale_cost * q - opex) * (1 - ms.tax_rate_pct / 100)


def sweep_price(ms: MarketState, p_min: float = 0.50, p_max: float = 7.00,
                steps: int = 60) -> list[dict]:
    rows = []
    for i in range(steps + 1):
        p   = p_min + (p_max - p_min) * i / steps
        qd  = demand(p, ms)
        qs  = supply(p, ms)
        q   = min(qd, qs)
        opx = (ms.ad_spend_k + ms.transport_cost_k + ms.fixed_overhead_k) * 1000
        pf  = (p * q - ms.wholesale_cost * q - opx) * (1 - ms.tax_rate_pct / 100)
        rows.append(dict(price=p, qd=qd, qs=qs, q_sold=q, excess=qd-qs, profit=pf))
    return rows


def sweep_ad(ms: MarketState, ad_min: float = 1.0, ad_max: float = 300.0,
             steps: int = 60) -> list[dict]:
    import dataclasses
    rows = []
    for i in range(steps + 1):
        adv  = ad_min + (ad_max - ad_min) * i / steps
        ms2  = dataclasses.replace(ms, ad_spend_k=adv)
        eq2  = find_equilibrium(ms2)
        fin2 = compute_financials(eq2, ms2)
        rows.append(dict(ad=adv, profit=fin2.net_profit, qty=fin2.q_sold,
                         price_eq=eq2.price_eq))
    return rows


def sweep_wholesale(ms: MarketState, wc_min: float = 0.20, wc_max: float = 4.50,
                    steps: int = 60) -> list[dict]:
    import dataclasses
    rows = []
    for i in range(steps + 1):
        wc   = wc_min + (wc_max - wc_min) * i / steps
        ms2  = dataclasses.replace(ms, wholesale_cost=wc)
        eq2  = find_equilibrium(ms2)
        fin2 = compute_financials(eq2, ms2)
        mfr_uc = wc * 0.40
        mfr_p  = ((wc - mfr_uc) * fin2.q_sold
                  - ms2.ad_spend_k * 500 - ms2.fixed_overhead_k * 500)
        rows.append(dict(wc=wc, profit=fin2.net_profit, mfr_profit=mfr_p,
                         qty=fin2.q_sold, price_eq=eq2.price_eq))
    return rows
