
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

SHEET_NAME = "business_simulation"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json",
    scope
)

client = gspread.authorize(creds)

sheet = client.open(SHEET_NAME)

sessions_ws = sheet.worksheet("sessions")
players_ws = sheet.worksheet("players")
decisions_ws = sheet.worksheet("decisions")
outcomes_ws = sheet.worksheet("outcomes")

def add_session(session_id, num_periods):

    sessions_ws.append_row([
        session_id,
        num_periods,
        datetime.now().isoformat()
    ])

def get_sessions():

    return sessions_ws.get_all_records()

def add_player(session_id, player_name, team_name, role):

    players_ws.append_row([
        session_id,
        player_name,
        team_name,
        role
    ])

def submit_decision(
    session_id,
    player_name,
    decisions
):

    decisions_ws.append_row([
        session_id,
        player_name,
        decisions["price"],
        decisions["ad_budget"],
        decisions["competitor_price"],
        decisions["competitor_ad"],
        datetime.now().isoformat()
    ])

def get_current_decisions(session_id):

    rows = decisions_ws.get_all_records()

    results = []

    for r in rows:
        if r["session_id"] == session_id:

            results.append({
                "player_name": r["player_name"],
                "price": float(r["price"]),
                "ad_budget": float(r["ad_budget"]),
                "competitor_price": float(r["competitor_price"]),
                "competitor_ad": float(r["competitor_ad"])
            })

    return results

def all_players_submitted(session_id):

    players = players_ws.get_all_records()
    decisions = decisions_ws.get_all_records()

    player_count = len([
        p for p in players
        if p["session_id"] == session_id
    ])

    decision_count = len([
        d for d in decisions
        if d["session_id"] == session_id
    ])

    return decision_count >= player_count

def save_outcome(
    session_id,
    player_name,
    revenue,
    cost,
    profit,
    quantity
):

    outcomes_ws.append_row([
        session_id,
        player_name,
        revenue,
        cost,
        profit,
        quantity,
        datetime.now().isoformat()
    ])

def get_outcomes(session_id):

    rows = outcomes_ws.get_all_records()

    return [
        r for r in rows
        if r["session_id"] == session_id
    ]

def get_player_history(session_id, player_name):

    rows = outcomes_ws.get_all_records()

    return [
        r for r in rows
        if r["session_id"] == session_id
        and r["player_name"] == player_name
    ]
