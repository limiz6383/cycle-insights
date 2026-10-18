#!/usr/bin/env python3
"""
Generate retrospective weekly insights over historical Oura data.

For each target date it rebuilds the summary AS OF that date (no lookahead —
days and period dates after the cutoff are dropped), then generates an insight
labelled with that date. The point is a rated eval set derived from real data
in an afternoon, instead of waiting one real week per data point.

Resumable: an insight that already exists in insights/ is skipped, so a run
interrupted halfway costs nothing to restart.

Usage:
  python3 backfill.py --dry-run                    # show target dates, no API calls
  python3 backfill.py                              # generate all missing
  python3 backfill.py --limit 3                    # just the first 3
  python3 backfill.py --period-dates 2026-01-03,2026-02-01
"""
import argparse
import json
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS.parent
INSIGHTS_DIR = REPO_ROOT / "insights"


def data_range(raw_path):
    """Earliest and latest day present in the raw dump."""
    data = json.loads(Path(raw_path).read_text())
    days = set()
    for key, block in data.items():
        if isinstance(block, dict):
            for rec in block.get("data") or []:
                if rec.get("day"):
                    days.add(rec["day"])
    if not days:
        sys.exit("No dated records found in {}".format(raw_path))
    return min(days), max(days)


def target_dates(first_day, last_day, window, step_days):
    """Weekly cutoffs, starting once `window` days of runway exist."""
    start = date.fromisoformat(first_day) + timedelta(days=window)
    end = date.fromisoformat(last_day)
    out, cur = [], start
    while cur <= end:
        out.append(cur.isoformat())
        cur += timedelta(days=step_days)
    return out


def run(cmd):
    proc = subprocess.run(cmd, cwd=str(SCRIPTS), capture_output=True, text=True)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout).strip().splitlines()[-1:] or ["unknown error"]
    return True, proc.stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default=str(SCRIPTS / "oura_data.json"))
    ap.add_argument("--window", type=int, default=90,
                    help="Days of history each insight sees (default 90, matching a live run).")
    ap.add_argument("--step-days", type=int, default=7, help="Spacing between insights.")
    ap.add_argument("--period-dates", default="",
                    help="Comma-separated period start dates. Each run keeps only those "
                         "on or before its cutoff — no lookahead.")
    ap.add_argument("--limit", type=int, default=None, help="Only generate the first N missing.")
    ap.add_argument("--dry-run", action="store_true", help="List target dates, make no API calls.")
    args = ap.parse_args()

    first_day, last_day = data_range(args.input)
    targets = target_dates(first_day, last_day, args.window, args.step_days)
    INSIGHTS_DIR.mkdir(exist_ok=True)
    existing = {p.stem for p in INSIGHTS_DIR.glob("*.json")}
    todo = [d for d in targets if d not in existing]
    if args.limit:
        todo = todo[: args.limit]

    print("Data:      {} → {}".format(first_day, last_day))
    print("Targets:   {} weekly cutoffs (window {}d)".format(len(targets), args.window))
    print("Existing:  {} skipped".format(len(targets) - len([d for d in targets if d not in existing])))
    print("To generate: {}\n".format(len(todo)))
    if args.dry_run:
        for d in todo:
            print("  " + d)
        print("\n(dry run — no API calls, est. ${:.2f} if run)".format(0.21 * len(todo)))
        return

    ok, failed = 0, []
    for i, cutoff in enumerate(todo, 1):
        print("[{}/{}] {} ".format(i, len(todo), cutoff), end="", flush=True)
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            summary_path = tmp.name
        pre = [sys.executable, "preprocess_oura.py", "--input", args.input,
               "--output", summary_path, "--as-of", cutoff, "--window", str(args.window)]
        if args.period_dates:
            pre += ["--period-dates", args.period_dates]
        good, err = run(pre)
        if not good:
            print("preprocess failed: {}".format(err))
            failed.append((cutoff, "preprocess"))
            continue

        good, err = run([sys.executable, "generate_insight.py",
                         "--summary", summary_path, "--as-of", cutoff])
        Path(summary_path).unlink(missing_ok=True)
        if not good:
            print("generate failed: {}".format(err))
            failed.append((cutoff, "generate"))
            continue
        print("ok")
        ok += 1

    print("\n{} generated, {} failed.".format(ok, len(failed)))
    for cutoff, stage in failed:
        print("  {} ({})".format(cutoff, stage))
    print("\nNext: rate them —")
    print("  python3 poll_feedback.py --rate <useful|wrong|unsafe|obvious|not_actionable> "
          "--note '...' --insight <date>")


if __name__ == "__main__":
    main()
