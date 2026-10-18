#!/usr/bin/env python3
"""
Plain stats summary for the last N days, no model involved, so nothing in it can be invented.

  python3 scripts/period_report.py --days 7      # what chat_bot.py sends for /weekly_summary
  python3 scripts/period_report.py --days 30     # ... for /monthly_summary

Compares the last N days with the N days before them, in the original units and in SDs of the
metric's own older days, and lists the cycle phases covered, sleep-timing regularity, the
steps she was suggested and what she answered. A difference is a description, not a diagnosis.
"""
import argparse
import json
import sys
from pathlib import Path
from statistics import mean, stdev

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_analysis as ca  # noqa: E402
import preprocess_oura as po  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent

REPORT_METRICS = [
    ("Cycle-related", ["temp_deviation", "RHR", "HRV", "breath_rate"]),
    ("Sleep", ["total_sleep_min", "efficiency", "sleep_latency_min", "awake_min", "sleep_midpoint_hr",
               "deep_min", "REM_min"]),
    ("Stress and oxygen", ["stress_high_sec", "recovery_high_sec", "spo2_avg"]),
    ("Activity", ["steps", "active_calories", "high_activity_min", "sedentary_min"]),
    ("Readiness", ["readiness_score", "sleep_score"]),
]


def load_days(data_path, user_log_path=None):
    """Daily metrics with cycle phases, the same way preprocess_oura.py builds them."""
    data = po.load_data(data_path)
    days = po.build_daily(data)
    if not days:
        raise SystemExit("No usable data in {}".format(data_path))
    sd = sorted(days)
    log = po.load_user_log(user_log_path or str(SCRIPTS_DIR / "user_cycle_log.json"))
    tags = po.drop_ranges(po.period_days_from_tags(data), log["not_a_period"])
    cycles = ca.build_cycles(days, po.period_starts(tags), sd[-1])
    ca.label_days(days, cycles, tags)
    return days, sd, cycles


def _clock(v):
    v = v % 24
    return "{:d}:{:02d}".format(int(v), int(round((v - int(v)) * 60)) % 60)


DURATION_OR_CLOCK = {"sleep_midpoint_hr", "total_sleep_min", "deep_min", "REM_min", "awake_min"}


def _label(m):
    label = ca.LABELS.get(m, m)
    return label.split(" (")[0] if m in DURATION_OR_CLOCK else label


def _fmt_val(m, v):
    if v is None:
        return "--"
    if m == "sleep_midpoint_hr":
        return _clock(v)
    if m in ("total_sleep_min", "deep_min", "REM_min", "awake_min"):
        return "{}h{:02d}".format(int(v // 60), int(round(v % 60)) % 60) if v >= 60 else "{:.0f} min".format(v)
    if m in ("steps", "active_calories", "stress_high_sec", "recovery_high_sec"):
        return "{:,.0f}".format(v)
    return "{:.{d}f}".format(v, d=ca._dec(m))


def build_report(days, sorted_days, n, actions=None):
    cur, prev = sorted_days[-n:], sorted_days[-2 * n:-n]
    older = sorted_days[:-n]
    name = "Weekly" if n == 7 else "Monthly" if n == 30 else "{}-day".format(n)
    L = ["{} summary: {} to {}".format(name, cur[0], cur[-1])]
    have = [d for d in cur if any(days[d].get(m) is not None for m in ("RHR", "HRV", "total_sleep_min"))]
    L.append("Nights with data: {} of {}.".format(len(have), n))
    if len(prev) < n // 2:
        L.append("Not enough earlier days for a comparison; showing this period only.")

    phases = {}
    for d in cur:
        phases[days[d].get("phase") or "unknown"] = phases.get(days[d].get("phase") or "unknown", 0) + 1
    L.append("Estimated cycle phases covered: " + ", ".join(
        "{} {} d".format(k, v) for k, v in sorted(phases.items(), key=lambda kv: -kv[1])) + ".")
    if len(set(days[d].get("phase") for d in cur) | set(days[d].get("phase") for d in prev)) > 1 and prev:
        L.append("The phase mix differs from the previous period, so part of any change below may be "
                 "your cycle, not anything new.")

    notable = []
    for title, metrics in REPORT_METRICS:
        lines = []
        for m in metrics:
            c = ca._vals(days, cur, m)
            if len(c) < max(3, n // 3):
                continue
            p = ca._vals(days, prev, m)
            _, sd = ca._mean_sd(ca._vals(days, older, m)) if len(ca._vals(days, older, m)) >= 21 else (None, None)
            cm = mean(c)
            line = "{}: {}".format(_label(m), _fmt_val(m, cm))
            if len(p) >= max(3, n // 3):
                pm = mean(p)
                line += " (before: {}".format(_fmt_val(m, pm))
                if sd:
                    z = (cm - pm) / sd
                    line += ", {:+.1f} SD".format(z)
                    if abs(z) >= ca.NOTABLE_SD:
                        notable.append("{} {} ({:+.1f} SD)".format(
                            _label(m), "up" if z > 0 else "down", z))
                        line += " *"
                line += ")"
            lines.append("- " + line)
        if lines:
            L.append("")
            L.append(title)
            L.extend(lines)

    mids = ca._vals(days, cur, "sleep_midpoint_hr")
    if len(mids) >= 4:
        L.append("")
        L.append("Sleep timing varied by +/-{:.0f} min (SD of your sleep midpoint).".format(stdev(mids) * 60))

    L.append("")
    L.append("Moved by 1 SD or more (*): " + ("; ".join(notable) if notable else "nothing."))

    mine = [a for a in (actions or []) if cur[0] <= a["id"] <= cur[-1]]
    if mine:
        counts = {}
        for a in mine:
            k = {"all": "did them", "some": "did some", "none": "did not get to them"}.get(a["status"], "no answer")
            counts[k] = counts.get(k, 0) + 1
        L.append("")
        L.append("Suggested steps this period: {} day{}; ".format(len(mine), "" if len(mine) == 1 else "s") + ", ".join(
            "{} {}".format(v, k) for k, v in counts.items()) + ".")
    L.append("")
    L.append("Differences are descriptive and do not show cause. Ask me about anything that moved.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--input", default=str(SCRIPTS_DIR / "oura_data.json"))
    ap.add_argument("--insights-dir", default=str(REPO_ROOT / "insights"))
    args = ap.parse_args()
    days, sd, _ = load_days(args.input)
    print(build_report(days, sd, args.days, po.load_actions(args.insights_dir)))


if __name__ == "__main__":
    main()
