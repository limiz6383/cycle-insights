#!/usr/bin/env python3
"""
Pre-process raw Oura data dump into the <oura_summary> format
required by the v3 cycle insights prompt (Block 11).

Reads `oura_data.json` (output of fetch_oura_data.py) and produces
a markdown summary with:
  - Coverage notes
  - User-reported and auto-detected cycle markers
  - 90-day stats per metric
  - Rolling-window comparisons (last_7d, last_30d, prior_30d, oldest_30d)
  - Day-by-day table

Usage:
  python3 preprocess_oura.py
  python3 preprocess_oura.py --input oura_data.json --output oura_summary.md
  python3 preprocess_oura.py --period-dates 2030-01-03,2030-02-01

Uses Python stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from statistics import mean, stdev

import cycle_analysis


METRICS = [
    "RHR", "lowest_HR", "HRV",
    "temp_deviation", "temp_trend",
    "total_sleep_min", "REM_min", "deep_min", "light_min", "efficiency", "breath_rate",
    "sleep_score", "readiness_score",
    "steps", "active_calories", "high_activity_min", "med_activity_min",
    "stress_high_sec", "recovery_high_sec",
    # Previously fetched or available but never summarised:
    "sleep_latency_min", "awake_min", "restless_periods", "sleep_midpoint_hr",
    "spo2_avg", "breathing_disturbance_index", "sedentary_min",
]


def load_actions(insights_dir):
    """Suggested steps (and her answers) from saved insight records. Missing folder -> []."""
    out = []
    d = Path(insights_dir)
    if not d.is_dir():
        return out
    for f in sorted(d.glob("*.json")):
        try:
            rec = json.loads(f.read_text())
        except ValueError:
            continue
        if rec.get("today_steps"):
            out.append({"id": rec.get("insight_id", f.stem), "steps": rec["today_steps"],
                        "status": (rec.get("followup") or {}).get("status")})
    return out


def load_data(path):
    with open(path) as f:
        return json.load(f)


def _sleep_midpoint_hr(rec):
    """Clock hour (local, from the record's own timestamps) at the midpoint of the main sleep.
    Hours before noon are shifted by +24 so a midnight crossing doesn't split the average."""
    try:
        a = datetime.fromisoformat(rec["bedtime_start"])
        b = datetime.fromisoformat(rec["bedtime_end"])
    except (KeyError, TypeError, ValueError):
        return None
    mid = a + (b - a) / 2
    hr = mid.hour + mid.minute / 60
    return round(hr + 24 if hr < 12 else hr, 2)


def build_daily(data):
    """Per-day records keyed by ISO date string."""
    days = {}

    for r in data.get("daily_readiness", {}).get("data", []) or []:
        d = days.setdefault(r["day"], {})
        d["readiness_score"] = r.get("score")
        d["temp_deviation"] = r.get("temperature_deviation")
        d["temp_trend"] = r.get("temperature_trend_deviation")

    for r in data.get("daily_sleep", {}).get("data", []) or []:
        days.setdefault(r["day"], {})["sleep_score"] = r.get("score")

    for r in data.get("daily_activity", {}).get("data", []) or []:
        d = days.setdefault(r["day"], {})
        d["steps"] = r.get("steps")
        d["active_calories"] = r.get("active_calories")
        d["high_activity_min"] = round((r.get("high_activity_time") or 0) / 60, 1)
        d["med_activity_min"] = round((r.get("medium_activity_time") or 0) / 60, 1)
        if r.get("sedentary_time") is not None:
            d["sedentary_min"] = round(r["sedentary_time"] / 60)

    sleep_by_day = defaultdict(list)
    for r in data.get("sleep", {}).get("data", []) or []:
        sleep_by_day[r["day"]].append(r)
    for day, recs in sleep_by_day.items():
        main = max(recs, key=lambda r: r.get("total_sleep_duration") or 0)
        d = days.setdefault(day, {})
        d["RHR"] = round(main["average_heart_rate"], 1) if main.get("average_heart_rate") is not None else None
        d["lowest_HR"] = main.get("lowest_heart_rate")
        d["HRV"] = main.get("average_hrv")
        d["total_sleep_min"] = round((main.get("total_sleep_duration") or 0) / 60)
        d["REM_min"] = round((main.get("rem_sleep_duration") or 0) / 60)
        d["deep_min"] = round((main.get("deep_sleep_duration") or 0) / 60)
        d["light_min"] = round((main.get("light_sleep_duration") or 0) / 60)
        d["efficiency"] = main.get("efficiency")
        d["breath_rate"] = round(main["average_breath"], 2) if main.get("average_breath") is not None else None
        if main.get("latency") is not None:
            d["sleep_latency_min"] = round(main["latency"] / 60, 1)
        if main.get("awake_time") is not None:
            d["awake_min"] = round(main["awake_time"] / 60)
        d["restless_periods"] = main.get("restless_periods")
        d["sleep_midpoint_hr"] = _sleep_midpoint_hr(main)

    for r in data.get("daily_spo2", {}).get("data", []) or []:
        d = days.setdefault(r["day"], {})
        pct = r.get("spo2_percentage")
        d["spo2_avg"] = pct.get("average") if isinstance(pct, dict) else None
        d["breathing_disturbance_index"] = r.get("breathing_disturbance_index")

    for r in data.get("daily_stress", {}).get("data", []) or []:
        d = days.setdefault(r["day"], {})
        d["stress_high_sec"] = r.get("stress_high")
        d["recovery_high_sec"] = r.get("recovery_high")

    return days


def period_days_from_tags(data):
    """
    Every day the user tagged a period in the Oura app, sorted.

    These are user-reported ground truth under UD1 — the ring cannot observe a
    bleed, the user tagged it. Reading them from the dump instead of asking the
    user to retype dates removes the failure that produced the worst output in
    an early backfill: with no bleed dates supplied, the model inferred
    amenorrhea from an empty log even though periods had been logged.
    """
    days = set()
    for rec in (data.get("enhanced_tag") or {}).get("data") or []:
        code = (rec.get("tag_type_code") or "")
        name = (rec.get("custom_name") or "")
        label = (code + " " + name).lower()
        if "spot" in label:
            continue  # spotting is not a cycle start
        if "period" in label or "menstru" in label:
            if rec.get("start_day"):
                days.add(rec["start_day"])
    return sorted(days)


def load_user_log(path):
    """
    Local, gitignored JSON for things Oura's API does not return, e.g.
    {"spotting": ["2030-02-10:2030-02-12"], "not_a_period": ["2030-03-01:2030-03-02"]}.
    Missing file is fine. Returns comma-joined range strings for each key.
    """
    p = Path(path)
    if not p.exists():
        return {"spotting": "", "not_a_period": ""}
    try:
        raw = json.loads(p.read_text())
    except ValueError as e:
        sys.exit("{} is not valid JSON: {}".format(p, e))
    return dict((k, ",".join(raw.get(k, []))) for k in ("spotting", "not_a_period"))


def drop_ranges(day_list, spec):
    """Remove days inside any 'START:END' range in the comma-separated spec."""
    ranges = []
    for part in (spec or "").split(","):
        if part.strip():
            a, _, b = part.strip().partition(":")
            ranges.append((a, b or a))
    return [d for d in day_list if not any(a <= d <= b for a, b in ranges)]


def period_starts(period_days, max_gap_days=2):
    """
    Collapse consecutive tagged days into episodes; return each episode's first day.

    A bleed spans several tagged days; only the first is a cycle start. Days
    within max_gap_days of each other are treated as one episode, so a single
    untagged day mid-bleed doesn't split it into two phantom cycles.
    """
    if not period_days:
        return []
    starts, prev = [period_days[0]], datetime.fromisoformat(period_days[0]).date()
    for day in period_days[1:]:
        cur = datetime.fromisoformat(day).date()
        if (cur - prev).days > max_gap_days:
            starts.append(day)
        prev = cur
    return starts


def stats_block(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return {"n": 0}
    if len(vals) == 1:
        return {"n": 1, "mean": round(vals[0], 2), "min": vals[0], "max": vals[0], "std": None}
    return {
        "n": len(vals),
        "mean": round(mean(vals), 2),
        "min": round(min(vals), 2),
        "max": round(max(vals), 2),
        "std": round(stdev(vals), 2),
    }


def compute_stats(days, sorted_days):
    windows = {
        "last_7d": sorted_days[-7:],
        "last_30d": sorted_days[-30:],
        "prior_30d": sorted_days[-60:-30] if len(sorted_days) >= 60 else [],
        "oldest_30d": sorted_days[:30],
    }
    out = {"overall_90d": {}}
    for m in METRICS:
        out["overall_90d"][m] = stats_block([days[d].get(m) for d in sorted_days])
    for w_name, w_days in windows.items():
        out[w_name] = {}
        for m in METRICS:
            out[w_name][m] = stats_block([days[d].get(m) for d in w_days])
    return out


def detect_cycles(days, sorted_days, user_periods=None):
    """
    Detect sustained luteal temperature rises as proxy for ovulatory cycles.
    Returns: dict with user_reported_periods, auto-detected luteal rises,
             cycle lengths (from user periods), biphasic_pattern_present flag.
    """
    out = {
        "user_reported_periods": user_periods or [],
        "auto_detected_luteal_rises": [],
        "cycle_lengths_days": [],
        "biphasic_pattern_present": False,
    }

    # Sustained rise: >=7 consecutive days with temp_deviation >= 0.15°C
    in_rise = False
    rise_start = None
    rise_days = 0
    for day in sorted_days:
        td = days[day].get("temp_deviation")
        if td is None:
            continue
        if td >= 0.15:
            if not in_rise:
                in_rise = True
                rise_start = day
                rise_days = 1
            else:
                rise_days += 1
        else:
            if in_rise and rise_days >= 7:
                out["auto_detected_luteal_rises"].append({
                    "start": rise_start,
                    "end_estimate": day,
                    "length_days": rise_days,
                })
            in_rise = False
            rise_start = None
            rise_days = 0
    if in_rise and rise_days >= 7:
        out["auto_detected_luteal_rises"].append({
            "start": rise_start,
            "end_estimate": "ongoing",
            "length_days": rise_days,
        })

    if out["auto_detected_luteal_rises"]:
        out["biphasic_pattern_present"] = True

    if user_periods and len(user_periods) >= 2:
        sorted_periods = sorted(user_periods)
        for i in range(len(sorted_periods) - 1):
            d0 = datetime.fromisoformat(sorted_periods[i]).date()
            d1 = datetime.fromisoformat(sorted_periods[i + 1]).date()
            out["cycle_lengths_days"].append((d1 - d0).days)

    return out


def newest_night_gap(days, sorted_days):
    """
    A note when the newest day has a sleep score or temperature but no detailed sleep record,
    so HRV, sleeping HR and sleep stages are blank. Empty string when nothing is missing.
    """
    last = sorted_days[-1]
    d = days[last]
    if d.get("HRV") is None and d.get("RHR") is None and (
            d.get("sleep_score") is not None or d.get("readiness_score") is not None):
        return ("The newest night ({}) has a sleep score or readiness score but no detailed "
                "sleep record, so its HRV, sleeping HR and sleep stages are missing. Oura may "
                "not have finished processing it when the data was pulled; use the last complete "
                "night and say so.".format(last))
    return ""


def coverage_notes(data, sorted_days):
    endpoints_present = [
        k for k in data.keys()
        if k != "_meta" and isinstance(data[k], dict) and data[k].get("data")
    ]
    endpoints_missing = [
        k for k in data.keys()
        if k != "_meta" and isinstance(data[k], dict) and "error" in data[k]
    ]
    start = sorted_days[0]
    end = sorted_days[-1]
    span_days = (datetime.fromisoformat(end).date() - datetime.fromisoformat(start).date()).days + 1
    gap_days = span_days - len(sorted_days)
    return {
        "date_range": f"{start} to {end}",
        "span_days": span_days,
        "days_with_data": len(sorted_days),
        "gap_days": gap_days,
        "coverage_pct": round(100 * len(sorted_days) / span_days, 1),
        "endpoints_present": endpoints_present,
        "endpoints_missing": endpoints_missing,
    }


def fmt(v):
    if v is None:
        return "--"
    return str(v)


def to_markdown(days, sorted_days, all_stats, cycle_info, coverage):
    lines = []
    lines.append("# Oura Summary — Pre-processed for v3 prompt")
    lines.append(f"_Generated from {coverage['date_range']}_")
    lines.append("")

    lines.append("## Coverage")
    lines.append(f"- Date range: {coverage['date_range']}")
    lines.append(
        f"- Span: {coverage['span_days']} days, {coverage['days_with_data']} days with data "
        f"({coverage['coverage_pct']}% coverage)"
    )
    lines.append(f"- Gap days: {coverage['gap_days']}")
    lines.append(f"- Endpoints present: {', '.join(coverage['endpoints_present'])}")
    if coverage["endpoints_missing"]:
        lines.append(f"- Endpoints missing: {', '.join(coverage['endpoints_missing'])}")
    if coverage.get("newest_night_gap"):
        lines.append(f"- **Data gap:** {coverage['newest_night_gap']}")
    lines.append("")

    lines.append("## Cycle markers")
    if cycle_info["user_reported_periods"]:
        lines.append(f"- User-reported period start dates: {', '.join(cycle_info['user_reported_periods'])}")
        lines.append(f"- Period source: {cycle_info.get('period_source', 'unspecified')}")
    else:
        lines.append("- User-reported periods: NONE AVAILABLE — absence of a log is NOT evidence of absence of a bleed. Do not infer amenorrhea from this.")
    if cycle_info.get("spotting_days"):
        sp = cycle_info["spotting_days"]
        lines.append("- User-reported spotting (NOT a period start, not in Oura's API; ground truth under UD1): "
                     "{} to {} ({} days with data)".format(sp[0], sp[-1], len(sp)))
    lines.append(f"- Biphasic temperature pattern detected: {cycle_info['biphasic_pattern_present']}")
    if cycle_info["auto_detected_luteal_rises"]:
        lines.append("- Auto-detected luteal rises (ESTIMATED — not user-confirmed):")
        for r in cycle_info["auto_detected_luteal_rises"]:
            lines.append(
                f"    - start: {r['start']}, end estimate: {r['end_estimate']}, "
                f"length: {r['length_days']} days"
            )
    if cycle_info["cycle_lengths_days"]:
        lines.append(f"- Cycle lengths (from user-reported periods): {cycle_info['cycle_lengths_days']} days")
    lines.append("")

    lines.append("## 90-day stats per metric")
    lines.append("| metric | mean | min | max | std | n |")
    lines.append("|---|---|---|---|---|---|")
    for m in METRICS:
        s = all_stats["overall_90d"].get(m, {})
        if s.get("n"):
            lines.append(
                f"| {m} | {fmt(s.get('mean'))} | {fmt(s.get('min'))} | "
                f"{fmt(s.get('max'))} | {fmt(s.get('std'))} | {s['n']} |"
            )
    lines.append("")

    lines.append("## Rolling-window comparison (means)")
    lines.append("| metric | last_7d | last_30d | prior_30d | oldest_30d |")
    lines.append("|---|---|---|---|---|")
    for m in METRICS:
        cells = []
        for w in ["last_7d", "last_30d", "prior_30d", "oldest_30d"]:
            s = all_stats[w].get(m, {})
            cells.append(fmt(s.get("mean")))
        lines.append(f"| {m} | " + " | ".join(cells) + " |")
    lines.append("")

    lines.append("## Day-by-day table")
    cols = ["date"] + METRICS
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "---|" * len(cols))
    for day in sorted_days:
        d = days[day]
        row = [day] + [fmt(d.get(m)) for m in METRICS]
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="oura_data.json",
                    help="Path to raw Oura JSON dump (default: oura_data.json)")
    ap.add_argument("--output", default="oura_summary.md",
                    help="Path to write the markdown summary (default: oura_summary.md)")
    ap.add_argument("--period-dates", default="",
                    help="Comma-separated user-reported period start dates (YYYY-MM-DD). "
                         "If omitted, only auto-detected luteal rises will appear.")
    ap.add_argument("--not-a-period", default="",
                    help="Comma-separated YYYY-MM-DD:YYYY-MM-DD ranges whose tagged days are NOT "
                         "periods (e.g. anovulatory bleeding logged as a period). Those days are "
                         "removed before cycle starts are derived, so they don't create phantom cycles.")
    ap.add_argument("--spotting", default="",
                    help="Comma-separated YYYY-MM-DD:YYYY-MM-DD ranges of spotting the user "
                         "reports that Oura's API does not return. Listed as user-reported "
                         "spotting (NOT a cycle start) and flagged on those days.")
    ap.add_argument("--user-log", default=str(Path(__file__).resolve().parent / "user_cycle_log.json"),
                    help="Local gitignored JSON with 'spotting' and 'not_a_period' range lists "
                         "(see user_cycle_log.example.json). Merged with the flags above.")
    ap.add_argument("--insights-dir", default=str(Path(__file__).resolve().parent.parent / "insights"),
                    help="Folder of past insight records; their suggested steps and answers are "
                         "compared with the data that followed.")
    ap.add_argument("--as-of", default=None,
                    help="Build the summary as it would have looked on this date (YYYY-MM-DD). "
                         "Drops all days AFTER it and all period dates after it, so a "
                         "retrospective insight can't see the future it's being judged against. "
                         "Required for honest backfill.")
    ap.add_argument("--window", type=int, default=None,
                    help="Keep only the last N days ending at --as-of (default: all prior days). "
                         "Use 90 to match what a live weekly run would have had.")
    args = ap.parse_args()

    log = load_user_log(args.user_log)
    args.spotting = ",".join(x for x in (args.spotting, log["spotting"]) if x)
    args.not_a_period = ",".join(x for x in (args.not_a_period, log["not_a_period"]) if x)

    data = load_data(args.input)
    days = build_daily(data)
    if not days:
        sys.exit("No usable data in input.")
    sorted_days = sorted(days.keys())

    # Period starts come from the user's own Oura tags by default. --period-dates
    # still overrides, for scenarios or for dates logged outside the app.
    if args.period_dates.strip():
        user_periods = [p.strip() for p in args.period_dates.split(",") if p.strip()]
        period_source = "--period-dates flag"
    else:
        tagged = period_days_from_tags(data)
        tagged = drop_ranges(tagged, args.not_a_period)
        user_periods = period_starts(tagged)
        period_source = "Oura period tags ({} tagged days)".format(len(tagged))

    # --- no-lookahead slice -------------------------------------------------
    # Everything downstream (rolling windows, cycle detection, coverage) is
    # computed from sorted_days, so truncating here is sufficient. Period dates
    # are truncated too: a period start you hadn't bled yet is future knowledge.
    if args.as_of:
        cutoff = args.as_of.strip()
        try:
            datetime.fromisoformat(cutoff)
        except ValueError:
            sys.exit("--as-of must be YYYY-MM-DD, got: {}".format(cutoff))
        sorted_days = [d for d in sorted_days if d <= cutoff]
        user_periods = [p for p in user_periods if p <= cutoff]
        if not sorted_days:
            sys.exit("No data on or before {}.".format(cutoff))
        days = {d: days[d] for d in sorted_days}
    if args.window:
        sorted_days = sorted_days[-args.window:]
        days = {d: days[d] for d in sorted_days}
    tagged_days = [] if args.period_dates.strip() else \
        [d for d in drop_ranges(period_days_from_tags(data), args.not_a_period)
         if not args.as_of or d <= args.as_of.strip()]
    spot_days = [d for d in sorted_days if drop_ranges([d], args.spotting) == []] if args.spotting.strip() else []
    for d in spot_days:
        days[d]["spotting"] = True
    cycle_info_spot = spot_days
    cycles = cycle_analysis.build_cycles(days, user_periods, sorted_days[-1])
    cycle_analysis.label_days(days, cycles, tagged_days)
    all_stats = compute_stats(days, sorted_days)
    cycle_info = detect_cycles(days, sorted_days, user_periods)
    cycle_info["period_source"] = period_source
    cycle_info["spotting_days"] = cycle_info_spot
    coverage = coverage_notes(data, sorted_days)
    coverage["newest_night_gap"] = newest_night_gap(days, sorted_days)

    md = to_markdown(days, sorted_days, all_stats, cycle_info, coverage)
    md += "\n" + cycle_analysis.render_markdown(days, sorted_days, cycles,
                                                actions=load_actions(args.insights_dir))
    with open(args.output, "w") as f:
        f.write(md)
    print(f"Wrote {args.output} ({len(md.splitlines())} lines, {len(sorted_days)} days)")


if __name__ == "__main__":
    main()
