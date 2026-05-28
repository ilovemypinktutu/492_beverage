"""
Cola Retail Market Simulation
==============================
Demand and supply data-generating functions with log-linear, quadratic,
and cubic terms. Includes a two-phase equilibrium solver (bisection +
Newton-Raphson refinement) and a full financial output report.

Demand factors
--------------
  Log-linear : own price, competitor price, advertising, income, season
  Quadratic  : consumer satisfaction (inverted-U in quality perception)
  Cubic      : time trend (growth -> plateau -> possible decline)
  Linear     : unemployment rate, brand dummy

New factors added vs original log-linear baseline
--------------------------------------------------
  Population density  - log-linear (more people -> more units demanded)
  Age index           - quadratic (young adults & families buy more)
  Health trend index  - linear negative (rising health awareness depresses cola)
  Promo dummy         - linear (in-store promotion boost)
  Temperature (F)     - quadratic (hot weather drives beverage demand, extreme cold dampens)

Supply factors
--------------
  Log-linear : own price, wholesale cost, transport cost
  Quadratic  : employee satisfaction (productivity has diminishing returns)
  Cubic      : upstream market power (nonlinear margin compression)
  Linear     : tax rate, capacity utilisation

New supply factors
------------------
  Energy cost index   - log-linear (refrigeration, production energy)
  Input scarcity      - linear negative (sugar/CO2 supply disruptions)
  Regulatory burden   - linear negative (compliance overhead)
  Store count         - log-linear (more outlets -> more total supply)

Intercepts are calibrated so the baseline scenario clears near $1.80/unit
with ~10,000 units/week -- a plausible small-regional-market volume.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# 1. Market conditions dataclass
# ---------------------------------------------------------------------------

@dataclass
class MarketConditions:
    """All exogenous inputs that define the market environment."""

    # --- Demand-side ---
    own_price: float = 1.80          # $/unit (seed; endogenous at equilibrium)
    competitor_price: float = 1.90   # $/unit
    ad_spend_k: float = 50.0         # $K / week
    local_income_k: float = 65.0     # median household income, $K / year
    unemployment_pct: float = 5.0    # local unemployment rate, %
    consumer_sat: float = 7.0        # 0-10 brand satisfaction score
    season_index: float = 1.0        # 0.5 (winter) - 1.5 (peak summer)
    brand: int = 0                   # 0=independent, 1=regional chain, 2=national chain
    time_months: float = 0.0         # months since launch / baseline

    # New demand factors
    pop_density: float = 3000.0      # people per sq mile
    age_index: float = 35.0          # avg age of local shopper base (years)
    health_trend: float = 0.0        # 0=neutral, positive=health-conscious market
    promo_dummy: int = 0             # 1 if in-store promotion active
    temperature_f: float = 72.0      # average weekly temperature, degF

    # --- Supply-side ---
    wholesale_cost: float = 0.90     # $/unit (cost of goods from bottler)
    tax_rate_pct: float = 8.0        # sales/excise tax, %
    transport_cost_k: float = 20.0   # $K / week
    upstream_power: float = 0.30     # 0-1 bottler bargaining power index
    employee_sat: float = 7.0        # 0-10 employee satisfaction
    capacity_util_pct: float = 75.0  # % of max production/distribution capacity

    # New supply factors
    energy_cost_idx: float = 1.0     # index relative to baseline (1.0 = normal)
    input_scarcity: float = 0.0      # 0=no scarcity, 1=severe shortage
    regulatory_burden: float = 0.0   # composite score 0-1
    store_count: float = 8.0         # number of retail outlets in area

    # --- Financials ---
    fixed_overhead_k: float = 5.0    # $K / week (rent, utilities, admin)


# ---------------------------------------------------------------------------
# 2. Demand function  ln Q_d = f(P, demographics, market conditions)
# ---------------------------------------------------------------------------

def demand(price: float, mc: MarketConditions) -> float:
    """
    Mixed functional form demand model.

    ln Q_d =
      a0                              intercept (calibrated)
      + a1  * ln(P)                   own-price elasticity        [log-linear]
      + a2  * ln(P_comp)              cross-price elasticity       [log-linear]
      + a3  * ln(Adv)                 advertising elasticity       [log-linear]
      + a4  * ln(Income)              income elasticity            [log-linear]
      + a5  * Unemp                   unemployment rate            [linear]
      + a6  * CS  + a7  * CS^2        consumer satisfaction        [quadratic]
      + a8  * T   + a9  * T^2
              + a10 * T^3             time trend                   [cubic]
      + a11 * ln(Season)              seasonality                  [log-linear]
      + brand_effect                  store brand dummy            [categorical]
      + a12 * ln(PopDens)             population density           [log-linear]
      + a13 * Age + a14 * Age^2       shopper age profile          [quadratic]
      + a15 * HealthTrend             health-consciousness         [linear]
      + a16 * Promo                   in-store promotion           [linear]
      + a17 * Temp + a18 * Temp^2     temperature effect           [quadratic]

    Returns quantity demanded (units / week).
    """
    # Calibrated intercept (baseline equilibrium ~$1.80, ~10,000 units)
    a0  =  2.791

    # Log-linear price and market terms
    a1  = -1.60   # own-price elasticity (elastic: -1.6)
    a2  =  0.90   # cross-price elasticity
    a3  =  0.25   # advertising elasticity
    a4  =  0.50   # income elasticity (normal good)
    a5  = -0.030  # unemployment (units: %)

    # Quadratic consumer satisfaction
    # Inverted-U peaks at CS* = -a6/(2*a7) = 0.18/(2*0.012) = 7.5
    a6  =  0.18
    a7  = -0.012

    # Cubic time trend
    # Linear growth -> decelerating -> subtle long-run uptick
    a8  =  0.025
    a9  = -0.0008
    a10 =  0.000004

    # Seasonality
    a11 =  0.40

    # Brand dummies (base = independent)
    brand_effects = {0: 0.0, 1: 0.15, 2: 0.35}

    # New factors
    a12 =  0.30   # population density elasticity
    a13 =  0.040  # age (linear) -- younger markets buy more
    a14 = -0.0007 # age (quadratic) -- peaks ~28.6 yrs, older markets buy less
    a15 = -0.20   # health trend (negative -- conscious market reduces cola)
    a16 =  0.18   # promotion dummy
    a17 =  0.006  # temperature linear
    a18 = -0.000035  # temperature quadratic (very hot or very cold depresses)

    P      = max(price, 0.01)
    P_comp = max(mc.competitor_price, 0.01)
    Adv    = max(mc.ad_spend_k, 0.01)
    Inc    = max(mc.local_income_k, 0.01)
    CS     = mc.consumer_sat
    T      = mc.time_months
    S      = max(mc.season_index, 0.01)
    PopD   = max(mc.pop_density, 1.0)
    Age    = mc.age_index
    Temp   = mc.temperature_f

    ln_qd = (
        a0
        + a1  * math.log(P)
        + a2  * math.log(P_comp)
        + a3  * math.log(Adv)
        + a4  * math.log(Inc)
        + a5  * mc.unemployment_pct
        + a6  * CS  + a7  * CS**2
        + a8  * T   + a9  * T**2 + a10 * T**3
        + a11 * math.log(S)
        + brand_effects.get(mc.brand, 0.0)
        + a12 * math.log(PopD)
        + a13 * Age + a14 * Age**2
        + a15 * mc.health_trend
        + a16 * mc.promo_dummy
        + a17 * Temp + a18 * Temp**2
    )
    return math.exp(ln_qd)


# ---------------------------------------------------------------------------
# 3. Supply function  ln Q_s = f(P, costs, operational factors)
# ---------------------------------------------------------------------------

def supply(price: float, mc: MarketConditions) -> float:
    """
    Mixed functional form supply model.

    ln Q_s =
      b0                                  intercept (calibrated)
      + b1  * ln(P)                       own-price supply elasticity   [log-linear]
      + b2  * ln(WC)                      wholesale cost elasticity     [log-linear]
      + b3  * Tax                         tax rate                      [linear]
      + b4  * ln(Trans)                   transport cost elasticity     [log-linear]
      + b5  * UP + b6 * UP^2 + b7 * UP^3 upstream market power         [cubic]
      + b8  * ES + b9  * ES^2             employee satisfaction         [quadratic]
      + b10 * CapUtil                     capacity utilisation          [linear]
      + b11 * ln(EnergyCost)              energy cost elasticity        [log-linear]
      + b12 * InputScarcity               input scarcity                [linear]
      + b13 * RegBurden                   regulatory burden             [linear]
      + b14 * ln(StoreCount)              store count elasticity        [log-linear]

    Returns quantity supplied (units / week).
    """
    # Calibrated intercept (baseline equilibrium ~$1.80, ~10,000 units)
    b0  =  7.513

    # Price and cost terms
    b1  =  1.20   # own-price supply elasticity
    b2  = -1.40   # wholesale cost elasticity
    b3  = -0.015  # tax rate (units: %)
    b4  = -0.08   # transport cost elasticity

    # Cubic upstream market power
    # b5<0, b6<0 -> accelerating squeeze; b7>0 -> slight relief at near-monopoly
    # (supplier self-limits at extreme power to avoid regulatory scrutiny)
    b5  = -0.50
    b6  = -0.30
    b7  =  0.10

    # Quadratic employee satisfaction
    # Peaks at ES* = -b8/(2*b9) = 0.14/(2*0.008) = 8.75
    b8  =  0.14
    b9  = -0.008

    # Capacity utilisation (linear -- more headroom = more supply)
    b10 =  0.005

    # New supply factors
    b11 = -0.35   # energy cost elasticity (negative)
    b12 = -0.40   # input scarcity (linear, 0-1 scale)
    b13 = -0.25   # regulatory burden (linear, 0-1 scale)
    b14 =  0.20   # store count elasticity

    P   = max(price, 0.01)
    WC  = max(mc.wholesale_cost, 0.01)
    Tr  = max(mc.transport_cost_k, 0.01)
    UP  = mc.upstream_power
    ES  = mc.employee_sat
    EC  = max(mc.energy_cost_idx, 0.01)
    SC  = max(mc.store_count, 1.0)

    ln_qs = (
        b0
        + b1  * math.log(P)
        + b2  * math.log(WC)
        + b3  * mc.tax_rate_pct
        + b4  * math.log(Tr)
        + b5  * UP  + b6  * UP**2  + b7  * UP**3
        + b8  * ES  + b9  * ES**2
        + b10 * mc.capacity_util_pct
        + b11 * math.log(EC)
        + b12 * mc.input_scarcity
        + b13 * mc.regulatory_burden
        + b14 * math.log(SC)
    )
    return math.exp(ln_qs)


def excess_demand(price: float, mc: MarketConditions) -> float:
    return demand(price, mc) - supply(price, mc)


# ---------------------------------------------------------------------------
# 4. Two-phase equilibrium solver: Bisection + Newton-Raphson
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


def find_equilibrium(
    mc: MarketConditions,
    p_low: float = 0.05,
    p_high: float = 50.0,
    bisection_iters: int = 80,
    nr_iters: int = 30,
    nr_tol: float = 1e-10,
) -> EquilibriumResult:
    """
    Two-phase equilibrium solver.

    Phase 1 - Bisection (80 iterations)
    ------------------------------------
    Guarantees convergence from any wide bracket because excess demand is
    monotonically decreasing in price (demand falls, supply rises).
    Precision after 80 steps: (50 - 0.05) / 2^80 ~ 4e-23 dollars.
    No starting-point assumption needed; safe for any parameter combination.

    Phase 2 - Newton-Raphson refinement (up to 30 iterations)
    ----------------------------------------------------------
    Starts from the bisection estimate. Uses a numerical first derivative
    of excess demand:
        f'(P) ~ [f(P + h) - f(P)] / h,  h = P * 1e-6
    Update rule:  P_new = P - f(P) / f'(P)
    Converges quadratically near the root. Clamped to [0.001, 100] to
    prevent divergence. Falls back to bisection result if NR fails to
    tighten within tolerance.

    Returns EquilibriumResult with price, quantity, excess, and solver info.
    """
    # Ensure root is bracketed
    ed_low  = excess_demand(p_low,  mc)
    ed_high = excess_demand(p_high, mc)

    if ed_low < 0:
        p_low  = 1e-4
        ed_low = excess_demand(p_low, mc)
    if ed_high > 0:
        p_high  = 500.0
        ed_high = excess_demand(p_high, mc)

    if ed_low * ed_high > 0:
        p_eq = (p_low + p_high) / 2
        qd, qs = demand(p_eq, mc), supply(p_eq, mc)
        return EquilibriumResult(p_eq, (qd+qs)/2, qd, qs, qd-qs, False, 0, "failed-no-bracket")

    # Phase 1: Bisection
    lo, hi = p_low, p_high
    for _ in range(bisection_iters):
        mid = (lo + hi) / 2.0
        if excess_demand(mid, mc) > 0:
            lo = mid
        else:
            hi = mid
    p_bisect = (lo + hi) / 2.0

    # Phase 2: Newton-Raphson from bisection seed
    p_nr = p_bisect
    nr_count = 0
    nr_converged = False
    for _ in range(nr_iters):
        h = p_nr * 1e-6 + 1e-12
        f_val   = excess_demand(p_nr, mc)
        f_prime = (excess_demand(p_nr + h, mc) - f_val) / h
        if abs(f_prime) < 1e-15:
            break
        p_new = p_nr - f_val / f_prime
        p_new = max(1e-4, min(p_new, 500.0))
        nr_count += 1
        if abs(p_new - p_nr) < nr_tol:
            p_nr = p_new
            nr_converged = True
            break
        p_nr = p_new

    p_eq   = p_nr if nr_converged else p_bisect
    method = "bisection + Newton-Raphson" if nr_converged else "bisection only"

    qd  = demand(p_eq, mc)
    qs  = supply(p_eq, mc)
    q_eq = (qd + qs) / 2.0

    return EquilibriumResult(
        price_eq=p_eq,
        quantity_eq=q_eq,
        quantity_demanded=qd,
        quantity_supplied=qs,
        excess=qd - qs,
        converged=True,
        iterations=bisection_iters + nr_count,
        method=method,
    )


# ---------------------------------------------------------------------------
# 5. Financial calculations
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


def compute_financials(eq: EquilibriumResult, mc: MarketConditions) -> Financials:
    q = eq.quantity_eq
    p = eq.price_eq

    revenue      = p * q
    cogs         = mc.wholesale_cost * q
    gross_profit = revenue - cogs
    gross_margin = (gross_profit / revenue * 100) if revenue > 0 else 0.0

    ad_exp    = mc.ad_spend_k      * 1_000
    trans_exp = mc.transport_cost_k * 1_000
    fixed     = mc.fixed_overhead_k * 1_000
    total_opex = ad_exp + trans_exp + fixed

    ebit       = gross_profit - total_opex
    tax        = max(ebit * mc.tax_rate_pct / 100, 0.0)
    net_profit = ebit - tax
    net_margin = (net_profit / revenue * 100) if revenue > 0 else 0.0

    cm  = p - mc.wholesale_cost     # contribution margin per unit
    bep = total_opex / cm if cm > 0 else float("inf")

    return Financials(
        revenue=revenue,
        cogs=cogs,
        gross_profit=gross_profit,
        gross_margin_pct=gross_margin,
        ad_expense=ad_exp,
        transport_expense=trans_exp,
        fixed_overhead=fixed,
        total_opex=total_opex,
        ebit=ebit,
        tax_amount=tax,
        net_profit=net_profit,
        net_margin_pct=net_margin,
        contribution_margin=cm,
        break_even_units=bep,
    )


# ---------------------------------------------------------------------------
# 6. Price sensitivity sweep
# ---------------------------------------------------------------------------

def price_sensitivity(
    mc: MarketConditions,
    p_min: float = 0.50,
    p_max: float = 4.00,
    steps: int = 15,
) -> list[dict]:
    rows = []
    for i in range(steps + 1):
        p = p_min + (p_max - p_min) * i / steps
        qd  = demand(p, mc)
        qs  = supply(p, mc)
        rev = p * qs
        cgs = mc.wholesale_cost * qs
        opx = (mc.ad_spend_k + mc.transport_cost_k + mc.fixed_overhead_k) * 1_000
        profit = (rev - cgs - opx) * (1 - mc.tax_rate_pct / 100)
        rows.append({"price": p, "Qd": qd, "Qs": qs,
                     "excess": qd - qs, "profit": profit})
    return rows


# ---------------------------------------------------------------------------
# 7. Report printer
# ---------------------------------------------------------------------------

LINE  = "-" * 64
DLINE = "=" * 64

def _fk(val: float) -> str:
    """Format dollar value."""
    sign = "-" if val < 0 else ""
    v = abs(val)
    if v >= 1_000_000:
        return f"{sign}${v/1_000_000:,.2f}M"
    if v >= 1_000:
        return f"{sign}${v/1_000:,.1f}K"
    return f"{sign}${v:,.2f}"


def print_report(mc: MarketConditions, eq: EquilibriumResult, fin: Financials,
                 scenario: str = "") -> None:
    BRANDS = {0: "Independent", 1: "Regional chain", 2: "National chain"}

    print()
    print(DLINE)
    if scenario:
        print(f"  Scenario: {scenario}")
    print("  COLA RETAIL MARKET SIMULATION -- FULL REPORT")
    print(DLINE)

    # --- Market conditions ---
    print("\n  MARKET CONDITIONS")
    print(LINE)
    def row(label, val): print(f"  {label:<34} {val}")
    row("Own price (seed):",         f"${mc.own_price:.2f}/unit")
    row("Competitor price:",         f"${mc.competitor_price:.2f}/unit")
    row("Wholesale cost:",           f"${mc.wholesale_cost:.2f}/unit")
    row("Ad spend:",                 f"{_fk(mc.ad_spend_k*1000)}/week")
    row("Transport cost:",           f"{_fk(mc.transport_cost_k*1000)}/week")
    row("Fixed overhead:",           f"{_fk(mc.fixed_overhead_k*1000)}/week")
    row("Tax rate:",                 f"{mc.tax_rate_pct:.1f}%")
    row("Local income (median):",    f"{_fk(mc.local_income_k*1000)}/yr")
    row("Unemployment rate:",        f"{mc.unemployment_pct:.1f}%")
    row("Population density:",       f"{mc.pop_density:,.0f} people/sq mi")
    row("Consumer satisfaction:",    f"{mc.consumer_sat:.1f}/10")
    row("Employee satisfaction:",    f"{mc.employee_sat:.1f}/10")
    row("Upstream market power:",    f"{mc.upstream_power:.2f}  (0=none, 1=monopoly)")
    row("Season index:",             f"{mc.season_index:.2f}  (1.0=average)")
    row("Temperature:",              f"{mc.temperature_f:.0f} degF")
    row("Shopper age index:",        f"{mc.age_index:.1f} yrs")
    row("Health trend:",             f"{mc.health_trend:+.2f}  (0=neutral)")
    row("In-store promotion:",       "Yes" if mc.promo_dummy else "No")
    row("Brand type:",               BRANDS.get(mc.brand, "Unknown"))
    row("Store count:",              f"{mc.store_count:.0f}")
    row("Energy cost index:",        f"{mc.energy_cost_idx:.2f}  (1.0=baseline)")
    row("Input scarcity:",           f"{mc.input_scarcity:.2f}  (0=none, 1=severe)")
    row("Regulatory burden:",        f"{mc.regulatory_burden:.2f}  (0=none, 1=max)")
    row("Capacity utilisation:",     f"{mc.capacity_util_pct:.1f}%")
    row("Time since baseline:",      f"{mc.time_months:.0f} months")

    # --- Equilibrium ---
    print("\n  EQUILIBRIUM SOLUTION")
    print(LINE)
    status = "CONVERGED" if eq.converged else "DID NOT CONVERGE"
    row("Status:",           status)
    row("Solver method:",    eq.method)
    row("Total iterations:", str(eq.iterations))
    row("Equilibrium price:",    f"${eq.price_eq:.4f}/unit")
    row("Equilibrium quantity:", f"{eq.quantity_eq:,.1f} units/week")
    row("Quantity demanded:",    f"{eq.quantity_demanded:,.1f} units/week")
    row("Quantity supplied:",    f"{eq.quantity_supplied:,.1f} units/week")
    excess_abs   = abs(eq.excess)
    excess_label = "excess demand" if eq.excess > 0 else "excess supply"
    row("Residual excess:",  f"{excess_abs:.4f} units  ({excess_label})")

    # --- Financials ---
    print("\n  WEEKLY FINANCIALS")
    print(LINE)
    row("Revenue:",                  _fk(fin.revenue))
    row("Cost of goods sold:",       _fk(fin.cogs))
    row("Gross profit:",             f"{_fk(fin.gross_profit)}  ({fin.gross_margin_pct:.1f}% margin)")
    print(f"  {'':34} ---")
    row("  Advertising expense:",    _fk(fin.ad_expense))
    row("  Transport expense:",      _fk(fin.transport_expense))
    row("  Fixed overhead:",         _fk(fin.fixed_overhead))
    row("  Total OpEx:",             _fk(fin.total_opex))
    print(f"  {'':34} ---")
    row("EBIT:",                     _fk(fin.ebit))
    row(f"Tax ({mc.tax_rate_pct:.1f}%):", _fk(fin.tax_amount))
    profit_arrow = "+" if fin.net_profit >= 0 else "-"
    row("Net profit:",               f"{profit_arrow} {_fk(fin.net_profit)}  ({fin.net_margin_pct:.1f}% margin)")
    print(f"  {'':34} ---")
    row("Contribution margin/unit:", f"${fin.contribution_margin:.4f}")
    bep_str = (f"{fin.break_even_units:,.0f} units/week"
               if fin.break_even_units != float("inf") else "N/A (negative CM)")
    row("Break-even volume:",        bep_str)
    profitable = "YES" if eq.quantity_eq >= fin.break_even_units else "NO"
    row("Profitable at equilibrium:", profitable)

    # --- Price sensitivity table ---
    print("\n  PRICE SENSITIVITY SWEEP  ($0.50 - $4.00)")
    print(LINE)
    rows = price_sensitivity(mc)
    print(f"  {'Price':>7}  {'Qd':>10}  {'Qs':>10}  {'Excess':>10}  {'Profit':>12}")
    print(f"  {'-'*7}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*12}")
    for r in rows:
        near_eq = abs(r["price"] - eq.price_eq) < (4.0 - 0.5) / 15 / 2
        marker  = "  <- eq" if near_eq else ""
        print(f"  ${r['price']:>6.2f}  {r['Qd']:>10,.0f}  {r['Qs']:>10,.0f}"
              f"  {r['excess']:>+10,.0f}  {_fk(r['profit']):>12}{marker}")

    print(f"\n{DLINE}\n")


# ---------------------------------------------------------------------------
# 8. Helper to run a scenario end-to-end
# ---------------------------------------------------------------------------

def run_scenario(label: str, mc: MarketConditions) -> tuple[EquilibriumResult, Financials]:
    eq  = find_equilibrium(mc)
    fin = compute_financials(eq, mc)
    print_report(mc, eq, fin, scenario=label)
    return eq, fin


# ---------------------------------------------------------------------------
# 9. Main -- four built-in scenarios
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    # -----------------------------------------------------------------------
    # Scenario A: Baseline -- suburban mid-income market
    # -----------------------------------------------------------------------
    baseline = MarketConditions()
    run_scenario("A: Baseline -- suburban mid-income market", baseline)

    # -----------------------------------------------------------------------
    # Scenario B: Dense urban, national chain, hot summer, promotion active
    # -----------------------------------------------------------------------
    urban_summer = MarketConditions(
        competitor_price=2.10,
        ad_spend_k=120.0,
        local_income_k=90.0,
        unemployment_pct=3.5,
        consumer_sat=8.2,
        season_index=1.45,
        brand=2,                   # national chain
        time_months=12.0,
        pop_density=18_000.0,      # dense urban
        age_index=28.0,            # younger demographic
        health_trend=0.3,
        promo_dummy=1,             # active promotion
        temperature_f=95.0,        # hot summer
        wholesale_cost=0.85,
        tax_rate_pct=10.0,
        transport_cost_k=35.0,
        upstream_power=0.15,       # large retailer has power over supplier
        employee_sat=8.0,
        capacity_util_pct=90.0,
        energy_cost_idx=1.2,
        input_scarcity=0.1,
        regulatory_burden=0.2,
        store_count=25,
        fixed_overhead_k=12.0,
    )
    run_scenario("B: Urban summer -- national chain, promotion active", urban_summer)

    # -----------------------------------------------------------------------
    # Scenario C: Rural winter -- near-monopoly supplier, supply squeeze
    # -----------------------------------------------------------------------
    rural_squeeze = MarketConditions(
        own_price=1.60,
        competitor_price=1.55,
        ad_spend_k=12.0,
        local_income_k=42.0,
        unemployment_pct=9.5,
        consumer_sat=5.5,
        season_index=0.75,         # winter
        brand=0,                   # independent
        time_months=24.0,
        pop_density=250.0,         # sparse rural
        age_index=48.0,            # older demographic
        health_trend=0.5,
        promo_dummy=0,
        temperature_f=30.0,        # cold
        wholesale_cost=1.10,
        tax_rate_pct=6.0,
        transport_cost_k=55.0,     # remote -- high transport
        upstream_power=0.85,       # near-monopoly bottler
        employee_sat=5.0,
        capacity_util_pct=50.0,
        energy_cost_idx=1.5,       # high energy costs
        input_scarcity=0.4,
        regulatory_burden=0.1,
        store_count=3,
        fixed_overhead_k=3.0,
    )
    run_scenario("C: Rural winter -- near-monopoly supplier, supply squeeze", rural_squeeze)

    # -----------------------------------------------------------------------
    # Scenario D: Premium suburban -- high income, weak supplier, strong brand
    # -----------------------------------------------------------------------
    premium = MarketConditions(
        own_price=2.50,
        competitor_price=2.20,
        ad_spend_k=200.0,
        local_income_k=110.0,
        unemployment_pct=2.8,
        consumer_sat=9.0,
        season_index=1.3,
        brand=2,                   # national chain
        time_months=36.0,
        pop_density=8_000.0,
        age_index=32.0,
        health_trend=-0.2,         # negative = health-unconscious market (boosts demand)
        promo_dummy=1,
        temperature_f=85.0,
        wholesale_cost=0.75,
        tax_rate_pct=12.0,
        transport_cost_k=18.0,
        upstream_power=0.05,       # retailer dominates supplier
        employee_sat=9.2,
        capacity_util_pct=85.0,
        energy_cost_idx=0.9,       # cheap energy
        input_scarcity=0.0,
        regulatory_burden=0.05,
        store_count=15,
        fixed_overhead_k=8.0,
    )
    run_scenario("D: Premium suburban -- high income, strong brand, low friction", premium)
