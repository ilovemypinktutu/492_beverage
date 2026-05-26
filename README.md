
# Streamlit Business Analytics Simulation Game

A multiplayer simultaneous-move classroom business simulation game built with Streamlit.

## Features

- Multiplayer simultaneous decisions
- Instructor dashboard
- Student dashboard
- Google Sheets backend
- Demand simulation engine
- Revenue / cost / profit calculations
- Historical accumulation of game data
- Team-based competition

## Folder Structure

app.py
pages/
simulation/
models/
sheets/

## Setup

### 1. Install Requirements

```bash
pip install -r requirements.txt
```

### 2. Google Sheets API Setup

1. Create a Google Cloud project
2. Enable Google Sheets API
3. Create service account credentials
4. Download credentials JSON
5. Save as:

```text
credentials.json
```

6. Share your Google Sheet with the service account email

---

### 3. Create Google Sheets Tabs

Create:
- sessions
- players
- decisions
- outcomes

---

### 4. Train Initial Models

Optional:

```bash
python train_models.py
```

---

### 5. Run App

```bash
streamlit run app.py
```
