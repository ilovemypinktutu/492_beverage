
import numpy as np
from sheets.google_sheets import (
    get_current_decisions,
    save_outcome
)

def demand_function(
    price,
    ad_budget,
    competitor_price,
    competitor_ad
):
    base = 1000

    quantity = (
        base
        - 120 * price
        + 0.015 * ad_budget
        + 60 * competitor_price
        - 0.01 * competitor_ad
        + np.random.normal(0, 50)
    )

    return max(quantity, 0)

def cost_function(quantity, ad_budget):

    production_cost = 1.10 * quantity
    total_cost = production_cost + ad_budget

    return total_cost

def run_period(session_id):

    decisions = get_current_decisions(session_id)

    for row in decisions:

        quantity = demand_function(
            row["price"],
            row["ad_budget"],
            row["competitor_price"],
            row["competitor_ad"]
        )

        revenue = row["price"] * quantity

        cost = cost_function(
            quantity,
            row["ad_budget"]
        )

        profit = revenue - cost

        save_outcome(
            session_id=session_id,
            player_name=row["player_name"],
            revenue=revenue,
            cost=cost,
            profit=profit,
            quantity=quantity
        )
