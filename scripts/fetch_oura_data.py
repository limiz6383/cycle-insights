#!/usr/bin/env python3
"""
Fetch last 90 days of Oura data for the cycle insights pretotype.

Setup (2 min):
  1. Go to https://cloud.ouraring.com/personal-access-tokens
  2. Log in with your Oura account, click "Create New Personal Access Token"
  3. Copy the token

Run:
  OURA_TOKEN=paste_your_token_here python3 fetch_oura_data.py

Outputs:
  oura_data.json  — raw API responses for all relevant endpoints

Uses Python stdlib only — no pip installs needed.
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from config import load_env
    load_env()  # pick up OURA_TOKEN from .env
except ImportError:
    pass

_ap = argparse.ArgumentParser(description="Fetch Oura data.")
_ap.add_argument("--days", type=int, default=180,
                 help="How many days back to fetch (default 180). Backfill needs "
                      "180+: 90 days of runway before the first insight, then the "
                      "weeks you actually want insights for.")
_ap.add_argument("--output", default="oura_data.json")
_args = _ap.parse_args()

TOKEN = os.environ.get("OURA_TOKEN")
if not TOKEN:
    sys.exit(
        "Missing OURA_TOKEN env var.\n"
        "Get one at https://cloud.ouraring.com/personal-access-tokens\n"
        "Then add it to .env as OURA_TOKEN=... (or pass it inline)."
    )

END = date.today()
START = END - timedelta(days=_args.days)
BASE = "https://api.ouraring.com/v2/usercollection"

# Relevant endpoints for cycle insight synthesis
ENDPOINTS = [
    "daily_readiness",      # RHR, HRV components, temperature deviation
    "daily_sleep",          # sleep score, total sleep duration
    "daily_activity",       # steps, active calories, sedentary time
    "daily_spo2",           # blood oxygen
    "daily_stress",         # stress score (newer Oura feature)
    "daily_cardiovascular_age",
    "sleep",                # detailed sleep stages (deep, REM, light, awake)
    "enhanced_tag",         # USER-LOGGED period tags — the ground truth for cycle starts.
                            # Without this the pipeline has no bleed dates at all and the
                            # model infers amenorrhea from silence. Do not drop.
    "daily_resilience",     # longer-horizon load/recovery balance
]


def fetch(endpoint):
    qs = urllib.parse.urlencode({
        "start_date": START.isoformat(),
        "end_date": END.isoformat(),
    })
    url = f"{BASE}/{endpoint}?{qs}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


data = {
    "_meta": {
        "fetched_at": END.isoformat(),
        "date_range": {"start": START.isoformat(), "end": END.isoformat()},
    }
}

for ep in ENDPOINTS:
    print(f"Fetching {ep}...", end=" ", flush=True)
    try:
        data[ep] = fetch(ep)
        count = len(data[ep].get("data", []))
        print(f"ok ({count} records)")
    except Exception as e:
        print(f"FAILED: {e}")
        data[ep] = {"error": str(e)}

out = _args.output
with open(out, "w") as f:
    json.dump(data, f, indent=2, default=str)

size_kb = os.path.getsize(out) / 1024
print(f"\nWrote {out} ({size_kb:.1f} KB)")
print(f"Date range: {START} to {END}")
print("\nNext: paste oura_data.json contents into Claude with your system prompt.")
