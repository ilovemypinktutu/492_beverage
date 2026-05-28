"""core/export.py — Excel and CSV export for the multi-product simulator."""
from __future__ import annotations
import io
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from core.model import MarketState, EquilibriumResult, Financials, sweep_price, PRODUCT_DEFAULTS

C_NAVY  = "1B3A6B"
C_TEAL  = "0D7377"
C_PROD  = {"coffee": "6F4E37", "soda": "1B3A6B", "beer": "C9A227"}
C_GREY  = "D9E1F2"
C_LIGHT = "EBF3FB"

def _thin():
    s = Side(style="thin", color="B0C4DE")
    return Border(left=s, right=s, top=s, bottom=s)

def _hf(sz=10, bold=True, color="FFFFFF"):
    return Font(name="Arial", size=sz, bold=bold, color=color)

def _cf(sz=10, bold=False, color="111111", italic=False):
    return Font(name="Arial", size=sz, bold=bold, color=color, italic=italic)

def _fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)

def _mhdr(ws, row, c1, c2, text, bg=C_NAVY, fg="FFFFFF", sz=11):
    ws.merge_cells(start_row=row, start_column=c1, end_row=row, end_column=c2)
    c = ws.cell(row=row, column=c1, value=text)
    c.font = Font(name="Arial", size=sz, bold=True, color=fg)
    c.fill = _fill(bg)
    c.alignment = Alignment(horizontal="center", vertical="center")
    return c

def _row(ws, r, label, val, note="", bg=None):
    bg = bg or (C_LIGHT if r % 2 == 0 else "FFFFFF")
    ws.cell(r, 1, label).font  = _cf()
    ws.cell(r, 1).fill = _fill(bg)
    ws.cell(r, 2, val).font    = _cf(color="0000FF")
    ws.cell(r, 2).alignment    = Alignment(horizontal="right")
    ws.cell(r, 2).fill = _fill(bg)
    ws.cell(r, 3, note).font   = _cf(sz=9, italic=True, color="666666")
    ws.cell(r, 3).fill = _fill(bg)
    for col in (1, 2, 3):
        ws.cell(r, col).border = _thin()

def export_xlsx(ms: MarketState, eq: EquilibriumResult,
                fin: Financials, scenario: str = "Simulation") -> bytes:
    wb  = openpyxl.Workbook()
    ws  = wb.active
    ws.title = "Summary"
    ws.sheet_view.showGridLines = False
    for col, w in zip("ABC", [30, 22, 20]):
        ws.column_dimensions[col].width = w

    prod_color = C_PROD.get(ms.product, C_NAVY)
    d = PRODUCT_DEFAULTS[ms.product]

    _mhdr(ws, 1, 1, 3,
          f"{ms.product.title()} Market Simulation  |  {scenario}",
          bg=prod_color, sz=12)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=3)
    ts = ws.cell(row=2, column=1,
                 value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    ts.font = _cf(sz=9, italic=True, color="555555")
    ts.alignment = Alignment(horizontal="center")

    r = 4
    _mhdr(ws, r, 1, 3, "EQUILIBRIUM", bg=C_TEAL); r += 1
    for lbl, val, note in [
        ("Equilibrium price",    f"${eq.price_eq:.4f}", "per unit"),
        ("Equilibrium quantity", f"{eq.quantity_eq:,.0f}", "units/week"),
        ("Quantity demanded",    f"{eq.quantity_demanded:,.0f}", ""),
        ("Quantity supplied",    f"{eq.quantity_supplied:,.0f}", ""),
        ("Solver method",        eq.method, ""),
    ]:
        _row(ws, r, lbl, val, note); r += 1

    r += 1
    _mhdr(ws, r, 1, 3, "WEEKLY FINANCIALS", bg=C_TEAL); r += 1
    for lbl, val, note in [
        ("Revenue",              f"${fin.revenue:,.2f}", ""),
        ("COGS",                 f"${fin.cogs:,.2f}", ""),
        ("Gross profit",         f"${fin.gross_profit:,.2f}", f"{fin.gross_margin_pct:.1f}%"),
        ("Ad expense",           f"${fin.ad_expense:,.2f}", ""),
        ("Transport expense",    f"${fin.transport_expense:,.2f}", ""),
        ("Fixed overhead",       f"${fin.fixed_overhead:,.2f}", ""),
        ("Total OpEx",           f"${fin.total_opex:,.2f}", ""),
        ("EBIT",                 f"${fin.ebit:,.2f}", ""),
        ("Tax",                  f"${fin.tax_amount:,.2f}", f"{ms.tax_rate_pct:.1f}%"),
        ("Net profit",           f"${fin.net_profit:,.2f}", f"{fin.net_margin_pct:.1f}%"),
        ("Contribution margin",  f"${fin.contribution_margin:.4f}", "per unit"),
        ("Break-even volume",
         f"{fin.break_even_units:,.0f}" if fin.break_even_units != float("inf") else "N/A",
         "units/week"),
        ("Manufacturer revenue", f"${fin.manufacturer_revenue:,.2f}", ""),
        ("Manufacturer profit",  f"${fin.manufacturer_profit:,.2f}", ""),
    ]:
        _row(ws, r, lbl, val, note); r += 1

    r += 1
    _mhdr(ws, r, 1, 3, "MARKET STATE (INPUTS)", bg=C_TEAL); r += 1
    for lbl, val, note in [
        ("Product",              ms.product.title(), ""),
        ("Own retail price",     f"${ms.own_price:.2f}", "per unit"),
        ("Own wholesale cost",   f"${ms.wholesale_cost:.2f}", "per unit"),
        ("Own ad spend",         f"${ms.ad_spend_k:.1f}K", "per week"),
        (f"{d['comp1'].title()} price",  f"${ms.comp1_price:.2f}", "competitor 1"),
        (f"{d['comp2'].title()} price",  f"${ms.comp2_price:.2f}", "competitor 2"),
        (f"{d['comp1'].title()} ad",     f"${ms.comp1_ad_k:.1f}K", "competitor 1"),
        (f"{d['comp2'].title()} ad",     f"${ms.comp2_ad_k:.1f}K", "competitor 2"),
        ("Tax rate",             f"{ms.tax_rate_pct:.1f}%", ""),
        ("Transport cost",       f"${ms.transport_cost_k:.1f}K", "per week"),
        ("Upstream power",       f"{ms.upstream_power:.2f}", "0=none 1=monopoly"),
        ("Employee satisfaction",f"{ms.employee_sat:.1f}/10", ""),
        ("Capacity utilisation", f"{ms.capacity_util_pct:.1f}%", ""),
        ("Energy cost index",    f"{ms.energy_cost_idx:.2f}", ""),
        ("Store count",          f"{ms.store_count:.0f}", ""),
    ]:
        _row(ws, r, lbl, val, note); r += 1

    # Sensitivity sheet
    ws2 = wb.create_sheet("Price Sensitivity")
    ws2.sheet_view.showGridLines = False
    hdrs = ["Price ($/unit)", "Qd", "Qs", "Excess", "Net Profit ($)"]
    for i, h in enumerate(hdrs, 1):
        c = ws2.cell(1, i, h)
        c.font = _hf(sz=10, color="111111")
        c.fill = _fill(C_GREY)
        ws2.column_dimensions[get_column_letter(i)].width = 16
    for ri, row_d in enumerate(sweep_price(ms, steps=30), 2):
        rev  = row_d["price"] * row_d["qs"]
        opex = (ms.ad_spend_k + ms.transport_cost_k + ms.fixed_overhead_k) * 1000
        pf   = (rev - ms.wholesale_cost * row_d["qs"] - opex) * (1 - ms.tax_rate_pct / 100)
        for ci, v in enumerate([row_d["price"], round(row_d["qd"]), round(row_d["qs"]),
                                  round(row_d["excess"]), round(pf, 2)], 1):
            ws2.cell(ri, ci, v)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_csv(ms: MarketState, eq: EquilibriumResult,
               fin: Financials, scenario: str = "Simulation") -> str:
    import csv, io as _io
    d = PRODUCT_DEFAULTS[ms.product]
    buf = _io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Beverage Market Simulation", scenario,
                datetime.now().strftime("%Y-%m-%d %H:%M")])
    w.writerow(["product", ms.product])
    w.writerow([])
    w.writerow(["=== EQUILIBRIUM ==="])
    for k, v in [("price_eq", round(eq.price_eq, 6)),
                 ("quantity_eq", round(eq.quantity_eq, 2)),
                 ("quantity_demanded", round(eq.quantity_demanded, 2)),
                 ("quantity_supplied", round(eq.quantity_supplied, 2)),
                 ("excess", round(eq.excess, 6)),
                 ("converged", eq.converged),
                 ("solver_method", eq.method)]:
        w.writerow([k, v])
    w.writerow([])
    w.writerow(["=== FINANCIALS ==="])
    for f in __import__("dataclasses").fields(fin):
        try:
            w.writerow([f.name, round(getattr(fin, f.name), 4)])
        except (TypeError, ValueError):
            w.writerow([f.name, getattr(fin, f.name)])
    w.writerow([])
    w.writerow(["=== MARKET STATE ==="])
    for f in __import__("dataclasses").fields(ms):
        w.writerow([f.name, getattr(ms, f.name)])
    w.writerow([])
    w.writerow(["=== PRICE SENSITIVITY ==="])
    w.writerow(["price", "qd", "qs", "excess", "profit"])
    for r in sweep_price(ms, steps=30):
        rev  = r["price"] * r["qs"]
        opex = (ms.ad_spend_k + ms.transport_cost_k + ms.fixed_overhead_k) * 1000
        pf   = (rev - ms.wholesale_cost * r["qs"] - opex) * (1 - ms.tax_rate_pct / 100)
        w.writerow([round(r["price"], 2), round(r["qd"], 1),
                    round(r["qs"], 1), round(r["excess"], 1), round(pf, 2)])
    return buf.getvalue()
