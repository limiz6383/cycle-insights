#!/usr/bin/env python3
"""
Plain stats summary for the last N days, no model involved, so nothing in it can be invented.

  python3 scripts/period_report.py --days 7      # what chat_bot.py sends for /weekly
  python3 scripts/period_report.py --days 30     # ... for /monthly

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

# key -> (short name, unit, divisor, decimals)
SHORT = {
    "temp_deviation": ("skin temp", " °C", 1, 2), "RHR": ("sleeping HR", " bpm", 1, 1),
    "HRV": ("HRV", " ms", 1, 0), "breath_rate": ("breathing rate", "/min", 1, 1),
    "total_sleep_min": ("sleep", "", 1, 0), "efficiency": ("sleep efficiency", "%", 1, 0),
    "sleep_latency_min": ("time to fall asleep", " min", 1, 0), "awake_min": ("awake in bed", " min", 1, 0),
    "sleep_midpoint_hr": ("sleep midpoint", "", 1, 0), "deep_min": ("deep sleep", " min", 1, 0),
    "REM_min": ("REM sleep", " min", 1, 0), "stress_high_sec": ("high-stress time", " min", 60, 0),
    "recovery_high_sec": ("recovery time", " min", 60, 0), "spo2_avg": ("SpO2", "%", 1, 1),
    "steps": ("steps", "", 1, 0), "active_calories": ("active calories", "", 1, 0),
    "high_activity_min": ("high-activity time", " min", 1, 0), "sedentary_min": ("sedentary time", " min", 1, 0),
    "readiness_score": ("readiness", "", 1, 0), "sleep_score": ("sleep score", "", 1, 0),
}
# Each group: headline metrics shown on one line, in this order.
GROUPS = [
    ("Body signals", ["RHR", "HRV", "temp_deviation", "breath_rate"]),
    ("Sleep", ["total_sleep_min", "efficiency", "sleep_midpoint_hr"]),
    ("Stress", ["stress_high_sec", "recovery_high_sec"]),
    ("Activity", ["steps", "active_calories", "sedentary_min"]),
    ("Scores", ["readiness_score", "sleep_score"]),
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


def _val(m, v):
    """A value in its short unit: 6h52, 2:35, 57.6 bpm."""
    if v is None:
        return "--"
    name, unit, div, dec = SHORT.get(m, (m, "", 1, 1))
    if m == "sleep_midpoint_hr":
        return _clock(v)
    if m == "total_sleep_min":
        return "{}h{:02d}".format(int(v // 60), int(round(v % 60)) % 60)
    if m == "sedentary_min":
        return "{:.1f} h".format(v / 60)
    return "{:,.{d}f}{}".format(v / div, unit, d=dec)


def _name(m):
    return SHORT.get(m, (m,))[0]


def build_report(days, sorted_days, n, actions=None):
    cur, prev = sorted_days[-n:], sorted_days[-2 * n:-n]
    older = sorted_days[:-n]
    title = "Your week" if n == 7 else "Your month" if n == 30 else "Last {} days".format(n)
    L = ["{}: {} to {}".format(title, cur[0][5:], cur[-1][5:])]
    nights = [d for d in cur if days[d].get("RHR") is not None or days[d].get("total_sleep_min") is not None]
    ph = {}
    for d in cur:
        k = days[d].get("phase") or "unknown"
        ph[k] = ph.get(k, 0) + 1
    ph_txt = ", ".join("{} {}d".format(k.replace("no_shift", "no rise yet"), v)
                       for k, v in sorted(ph.items(), key=lambda kv: -kv[1]))
    L.append("Cycle (estimated): {}. Data on {} of {} days.".format(ph_txt, len(nights), n))

    def stats(m):
        c = ca._vals(days, cur, m)
        if len(c) < max(3, n // 3):
            return None
        p = ca._vals(days, prev, m)
        o = ca._vals(days, older, m)
        _, sd = ca._mean_sd(o) if len(o) >= 21 else (None, None)
        pm = mean(p) if len(p) >= max(3, n // 3) else None
        z = (mean(c) - pm) / sd if (pm is not None and sd) else None
        return mean(c), pm, z

    moves = []
    for _, ms in GROUPS:
        for m in ms:
            st = stats(m)
            if st and st[2] is not None and abs(st[2]) >= ca.NOTABLE_SD:
                moves.append((abs(st[2]), m, st))
    moves.sort(reverse=True)
    L.append("")
    if moves:
        L.append("What changed")
        for _, m, (c, p, z) in moves[:4]:
            L.append("{} {}: {} (was {})".format("↑" if z > 0 else "↓", _name(m), _val(m, c), _val(m, p)))
        if len(moves) > 4:
            L.append("+ {} smaller moves; ask me.".format(len(moves) - 4))
        if len(set(days[d].get("phase") for d in cur) ^ set(days[d].get("phase") for d in prev)):
            L.append("Your cycle phase differs from last period, so some of this is probably just the cycle.")
    else:
        L.append("What changed: nothing moved by a full SD of your own variation. A steady period.")

    L.append("")
    L.append("Averages")
    for gname, ms in GROUPS:
        parts = []
        for m in ms:
            st = stats(m)
            if st:
                parts.append("{} {}".format(_name(m), _val(m, st[0])))
        if parts:
            L.append("{}: {}".format(gname, " · ".join(parts)))
    mids = ca._vals(days, cur, "sleep_midpoint_hr")
    if len(mids) >= 4:
        L.append("Bedtime consistency: ±{:.0f} min".format(stdev(mids) * 60))

    mine = [a for a in (actions or []) if cur[0] <= a["id"] <= cur[-1]]
    if mine:
        counts = {}
        for a in mine:
            k = {"all": "did them", "some": "did some", "none": "didn't get to them"}.get(a["status"], "no answer")
            counts[k] = counts.get(k, 0) + 1
        L.append("")
        L.append("Steps I suggested: " + ", ".join("{} day{} {}".format(v, "" if v == 1 else "s", k)
                                                    for k, v in counts.items()))
    L.append("")
    L.append("Compared with the {} days before; a move counts when it's 1+ SD of your own usual range. "
             "Ask me about anything here.".format(n))
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
