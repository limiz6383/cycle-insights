#!/usr/bin/env python3
"""
Unattended Oura pull — what launchd/cron runs so you don't have to.

Default (daily): fetch the last --days of Oura data, then rebuild
oura_summary.md. Nothing else: no Anthropic call, no Telegram message.

  python3 scheduled_pull.py                 # fetch + preprocess
  python3 scheduled_pull.py --weekly        # ... + generate_insight.py
  python3 scheduled_pull.py --weekly --send # ... + send_insight.py

Why local, not GitHub Actions: this repo is public, so Actions logs are
public, and generate_insight.py prints the insight to stdout. Running here
keeps oura_data.json, the summary, and insights/ on your own disk, where
send_insight.py and poll_feedback.py already expect them.

The fresh dump is fetched to a temp file and only replaces oura_data.json if
the endpoints the summary depends on came back. An expired token or an Oura
outage therefore leaves yesterday's good data in place instead of a file of
error stubs.

Every run appends to <repo_root>/logs/scheduled_pull.log (gitignored).
Exit code is non-zero if any step failed, so launchd/cron can surface it.

Uses Python stdlib only.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS.parent
LOG_DIR = REPO_ROOT / "logs"
RAW = SCRIPTS / "oura_data.json"
SUMMARY = SCRIPTS / "oura_summary.md"

# A dump missing either of these is worse than yesterday's dump: no readiness
# means no RHR/HRV/temperature, and no enhanced_tag means no bleed dates (the
# phantom-amenorrhea failure in METHODOLOGY.md §6).
REQUIRED_ENDPOINTS = ["daily_readiness", "enhanced_tag"]


def log(msg):
    line = "[{}] {}".format(datetime.now().isoformat(timespec="seconds"), msg)
    print(line, flush=True)
    LOG_DIR.mkdir(exist_ok=True)
    with (LOG_DIR / "scheduled_pull.log").open("a") as fh:
        fh.write(line + "\n")


def run(step, args):
    """Run one pipeline script from scripts/. Returns True on success."""
    log("{}: {}".format(step, " ".join(args)))
    proc = subprocess.run([sys.executable] + args, cwd=SCRIPTS,
                          capture_output=True, text=True)
    # Script output goes to the log file only on failure: on success it's
    # either record counts (noise) or the insight itself (personal).
    if proc.returncode != 0:
        log("{} FAILED (exit {}):\n{}{}".format(step, proc.returncode,
                                               proc.stdout, proc.stderr))
        return False
    log("{} ok".format(step))
    return True


def fetch(days):
    tmp = SCRIPTS / "oura_data.json.tmp"
    if not run("fetch", ["fetch_oura_data.py", "--days", str(days), "--output", tmp.name]):
        tmp.unlink(missing_ok=True)
        return False
    data = json.loads(tmp.read_text())
    failed = [ep for ep in REQUIRED_ENDPOINTS if "error" in data.get(ep, {"error": "missing"})]
    if failed:
        log("fetch incomplete ({} errored: {}); keeping previous {}".format(
            ", ".join(failed), data.get(failed[0], {}).get("error"), RAW.name))
        tmp.unlink()
        return False
    os.replace(tmp, RAW)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=180,
                    help="Days of history to pull (default 180, same as fetch_oura_data.py).")
    ap.add_argument("--weekly", action="store_true",
                    help="Also generate this week's insight (calls the Anthropic API).")
    ap.add_argument("--send", action="store_true",
                    help="With --weekly: also push the insight to Telegram.")
    args = ap.parse_args()
    if args.send and not args.weekly:
        ap.error("--send needs --weekly")

    ok = fetch(args.days) and run("preprocess", ["preprocess_oura.py",
                                                 "--input", RAW.name,
                                                 "--output", SUMMARY.name])
    if ok and args.weekly:
        ok = run("generate", ["generate_insight.py"])
    if ok and args.send:
        ok = run("send", ["send_insight.py"])

    log("done" if ok else "stopped on failure")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
