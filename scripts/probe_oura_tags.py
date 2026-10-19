#!/usr/bin/env python3
"""
Show which tag records Oura's API returns for a date window, to find where the
app's spotting entries live.

Prints only record kinds and dates (never the token). Tries the endpoints that
can hold user-logged entries: enhanced_tag, the older tag endpoint, and
rest_mode_period. Anything that errors is reported, not hidden.

  python3 probe_oura_tags.py --start 2026-08-20 --end 2026-09-05
"""
import argparse
import collections
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load_env  # noqa: E402

BASE = "https://api.ouraring.com/v2/usercollection"
ENDPOINTS = ["enhanced_tag", "tag", "rest_mode_period"]


def get(endpoint, start, end, token):
    qs = urllib.parse.urlencode({"start_date": start, "end_date": end})
    req = urllib.request.Request("{}/{}?{}".format(BASE, endpoint, qs),
                                 headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    args = ap.parse_args()
    load_env()
    token = os.environ.get("OURA_TOKEN")
    if not token:
        sys.exit("Missing OURA_TOKEN in .env")
    for ep in ENDPOINTS:
        try:
            data = get(ep, args.start, args.end, token)
        except urllib.error.HTTPError as e:
            print("{}: HTTP {} {}".format(ep, e.code, e.reason))
            continue
        except Exception as e:  # noqa: BLE001 - report anything
            print("{}: {}".format(ep, e))
            continue
        recs = data.get("data", [])
        kinds = collections.Counter(r.get("tag_type_code") or r.get("tags") and "tags" or "other"
                                    for r in recs)
        print("{}: {} records {}".format(ep, len(recs), dict(kinds)))
        for r in recs:
            print("   ", r.get("start_day") or r.get("day"), r.get("end_day"),
                  r.get("tag_type_code"), r.get("custom_name"), r.get("tags"))


if __name__ == "__main__":
    main()
