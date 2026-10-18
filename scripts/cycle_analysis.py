"""
Personal-baseline and cycle-phase analysis of the daily Oura table.

preprocess_oura.py builds one record per day; this module turns that table into
the numbers the prompt actually needs to say something specific:

  - where each day sits in the cycle (day number, phase),
  - the user's own baseline for each metric, in the same phase when possible,
  - how the last 7 days compare with that baseline, in the user's own SDs,
  - per-cycle luteal-vs-follicular deltas, with an estimated ovulation day.

Everything is descriptive arithmetic on the user's own data. Nothing here
interprets a number clinically and nothing introduces a threshold from the
literature; the only fixed numbers are the detection settings below, which are
labelled as such in the output. Interpretation stays in the prompt, where it
must come from the knowledge base.

Phases are ESTIMATES. Menses come from the user's own period tags; the
ovulation day is inferred from a sustained rise in nocturnal skin temperature,
which marks a temperature shift, not ovulation itself (see KB21).

Stdlib only.
"""
from datetime import date, datetime, timedelta
from statistics import mean, pstdev, stdev

# Detection settings (descriptive, not clinical thresholds).
MENSES_DAYS = 5          # cycle days 1-5 labelled "menstrual" when no per-day tags
SHIFT_RISE_C = 0.15      # a day is "elevated" if >= this above the prior-6-day mean
SHIFT_RUN_DAYS = 3       # consecutive elevated days that define a shift (3-over-6)
SHIFT_BASE_DAYS = 6
MIN_BASELINE_DAYS = 21   # fewer baseline days than this -> no baseline claim
NOTABLE_SD = 1.0         # |delta| in SDs above which a change is called out
MAX_PRESHIFT_DAYS = 16   # open cycle with no shift before this many days: provisional follicular
MAX_CYCLE_DAYS = 120     # a gap longer than this is not treated as one cycle (a missed log, not a cycle)

# Metrics grouped by what they describe. "dir" is the direction of the typical
# luteal-vs-follicular change in healthy regular cycles (KB15-KB19); it is only
# used to label whether the user's own change points the same way.
PHASE_METRICS = {
    "temp_deviation": {"label": "skin temp deviation (°C)", "dir": +1, "dec": 2},
    "RHR": {"label": "sleeping HR (bpm)", "dir": +1, "dec": 1},
    "lowest_HR": {"label": "lowest sleeping HR (bpm)", "dir": +1, "dec": 1},
    "HRV": {"label": "HRV rMSSD (ms)", "dir": -1, "dec": 1},
    "breath_rate": {"label": "breathing rate (/min)", "dir": +1, "dec": 2},
    "efficiency": {"label": "sleep efficiency (%)", "dir": -1, "dec": 1},
    "total_sleep_min": {"label": "total sleep (min)", "dir": 0, "dec": 0},
    "deep_min": {"label": "deep sleep (min)", "dir": 0, "dec": 0},
    "REM_min": {"label": "REM sleep (min)", "dir": 0, "dec": 0},
    "sleep_latency_min": {"label": "sleep latency (min)", "dir": 0, "dec": 1},
    "stress_high_sec": {"label": "high-stress time (s)", "dir": 0, "dec": 0},
    "readiness_score": {"label": "readiness score", "dir": 0, "dec": 1},
}

# Metrics checked against the user's own baseline, grouped by domain so the
# prompt can see which domains were examined.
DOMAINS = {
    "autonomic / cardiac": ["RHR", "lowest_HR", "HRV"],
    "temperature": ["temp_deviation"],
    "respiratory / oxygen": ["breath_rate", "spo2_avg", "breathing_disturbance_index"],
    "sleep": ["total_sleep_min", "efficiency", "deep_min", "REM_min",
              "sleep_latency_min", "awake_min", "restless_periods", "sleep_midpoint_hr"],
    "load / stress": ["steps", "active_calories", "high_activity_min",
                      "sedentary_min", "stress_high_sec", "recovery_high_sec"],
    "oura scores": ["readiness_score", "sleep_score"],
}

LABELS = dict((k, v["label"]) for k, v in PHASE_METRICS.items())
LABELS.update({
    "spo2_avg": "SpO2 average (%)",
    "breathing_disturbance_index": "breathing disturbance index",
    "awake_min": "awake time in bed (min)",
    "restless_periods": "restless periods",
    "sleep_midpoint_hr": "sleep midpoint (clock hr; >24 = after midnight)",
    "steps": "steps",
    "active_calories": "active calories",
    "high_activity_min": "high-activity min",
    "sedentary_min": "sedentary min",
    "recovery_high_sec": "recovery time (s)",
    "sleep_score": "sleep score",
})


def _d(s):
    return datetime.fromisoformat(s).date()


def _vals(days, dates, metric):
    return [days[x].get(metric) for x in dates if days[x].get(metric) is not None]


def _mean_sd(vals):
    if not vals:
        return None, None
    return mean(vals), (stdev(vals) if len(vals) > 1 else None)


def _r(v, dec=2):
    return None if v is None else round(v, dec)


# --------------------------------------------------------------------------
# Cycle structure
# --------------------------------------------------------------------------

def find_temperature_shift(days, start, end):
    """
    First sustained skin-temperature shift in [start, end] (ISO dates).

    A day is elevated when its temperature deviation is >= SHIFT_RISE_C above
    the mean of the preceding SHIFT_BASE_DAYS days; SHIFT_RUN_DAYS elevated days
    in a row make a shift. Returns the first elevated day, or None. Needs the
    preceding days to have data, so a shift in the first week of a cycle (still
    menses) is not looked for.
    """
    dates = [x for x in sorted(days) if start <= x <= end]
    series = [(x, days[x].get("temp_deviation")) for x in dates]
    for i in range(SHIFT_BASE_DAYS, len(series) - SHIFT_RUN_DAYS + 1):
        base = [t for _, t in series[i - SHIFT_BASE_DAYS:i] if t is not None]
        if len(base) < SHIFT_BASE_DAYS - 1:
            continue
        ref = mean(base)
        run = series[i:i + SHIFT_RUN_DAYS]
        if all(t is not None and t >= ref + SHIFT_RISE_C for _, t in run):
            # require consecutive calendar days, not a gap-bridged run
            if (_d(run[-1][0]) - _d(run[0][0])).days != SHIFT_RUN_DAYS - 1:
                continue
            # Persistence: the days 4-7 of the shift must still sit above the
            # pre-shift reference (when at least 3 of them exist), so a 2-3 day
            # spike in an otherwise flat curve (illness, alcohol, a bad night)
            # is not read as a shift. With fewer later days the shift is
            # provisional and accepted on the run alone.
            later = [t for _, t in series[i + SHIFT_RUN_DAYS:i + 7] if t is not None]
            if len(later) >= 3 and mean(later) < ref + SHIFT_RISE_C:
                continue
            return series[i][0]
    return None


def build_cycles(days, period_starts, last_day):
    """
    One dict per cycle, from each period start to the day before the next (the
    current cycle runs to last_day). Adds an ovulation estimate (the day before
    the temperature shift), luteal length, and whether the cycle is complete.
    """
    cycles = []
    starts = sorted(period_starts)
    for i, s in enumerate(starts):
        complete = i + 1 < len(starts)
        end_d = _d(starts[i + 1]) - timedelta(days=1) if complete else _d(last_day)
        length = (end_d - _d(s)).days + 1
        if length > MAX_CYCLE_DAYS or length < 1:
            continue
        end = end_d.isoformat()
        seen = [x for x in days if s <= x <= end]
        if not seen or _d(min(seen)) > _d(s) + timedelta(days=7):
            continue  # the window starts mid-cycle: no honest baseline for this cycle
        shift = find_temperature_shift(days, s, end)
        ov = (_d(shift) - timedelta(days=1)).isoformat() if shift else None
        luteal_len = None
        if ov and complete:
            luteal_len = (end_d - _d(ov)).days
        cycles.append({
            "start": s, "end": end, "length_days": length if complete else None,
            "days_so_far": length, "complete": complete,
            "shift_day": shift, "ovulation_est": ov, "luteal_len": luteal_len,
        })
    return cycles


def label_days(days, cycles, period_days=None):
    """
    Annotate days[...]['cycle_day'] and days[...]['phase'].

    Phases: menstrual (tagged bleed days, else cycle days 1..MENSES_DAYS),
    follicular, luteal (day after estimated ovulation to cycle end), and
    'no_shift' for the non-menstrual days of a cycle with no detected shift.
    Mutates and returns days.
    """
    tagged = set(period_days or [])
    for c in cycles:
        s, e = _d(c["start"]), _d(c["end"])
        ov = _d(c["ovulation_est"]) if c["ovulation_est"] else None
        d = s
        while d <= e:
            key = d.isoformat()
            if key in days:
                cd = (d - s).days + 1
                days[key]["cycle_day"] = cd
                menses = key in tagged if tagged else cd <= MENSES_DAYS
                if menses and (ov is None or d <= ov):
                    phase = "menstrual"
                elif ov is None:
                    # An open cycle with no shift yet is provisionally follicular;
                    # a completed one (or an open one past MAX_PRESHIFT_DAYS) is not.
                    pre = (not c["complete"]) and c["days_so_far"] < MAX_PRESHIFT_DAYS
                    phase = "follicular" if pre else "no_shift"
                elif d <= ov:
                    phase = "follicular"
                else:
                    phase = "luteal"
                days[key]["phase"] = phase
            d += timedelta(days=1)
    return days


# --------------------------------------------------------------------------
# Personal baseline and recent comparison
# --------------------------------------------------------------------------

def recent_vs_baseline(days, sorted_days, metrics, recent_n=7):
    """
    For each metric: mean of the last recent_n days against the baseline formed
    by all earlier days, and (when the current phase is known) against earlier
    days in the same phase. Differences are also expressed in the baseline's own
    daily SD. Returns {metric: dict} for metrics with enough data.
    """
    recent = sorted_days[-recent_n:]
    earlier = sorted_days[:-recent_n]
    cur_phase = days[sorted_days[-1]].get("phase")
    # A cycle with no shift yet is provisionally follicular, so its baseline is
    # the follicular days of earlier cycles (the cycle's own days are excluded
    # by the hold-out), not a pool of every phase.
    base_phase = "follicular" if cur_phase == "no_shift" else cur_phase
    same = [x for x in earlier if base_phase and days[x].get("phase") == base_phase]
    out = {}
    for m in metrics:
        rv = _vals(days, recent, m)
        bv = _vals(days, earlier, m)
        if len(rv) < 3 or len(bv) < MIN_BASELINE_DAYS:
            continue
        rm = mean(rv)
        bm, bs = _mean_sd(bv)
        sv = _vals(days, same, m)
        row = {"recent": rm, "base_mean": bm, "base_sd": bs, "n_recent": len(rv),
               "n_base": len(bv), "delta": rm - bm,
               "z": ((rm - bm) / bs) if bs else None}
        if len(sv) >= 7:
            sm, ss = _mean_sd(sv)
            row.update({"phase_mean": sm, "phase_sd": ss, "n_phase": len(sv),
                        "phase_delta": rm - sm,
                        "phase_z": ((rm - sm) / ss) if ss else None})
        out[m] = row
    return out, cur_phase


NIGHT_METRICS = ["temp_deviation", "RHR", "HRV", "breath_rate", "total_sleep_min", "readiness_score"]


def last_nights(days, sorted_days, n=3, hold_out=7):
    """
    The last n nights, each metric as a value and a z-score against the user's
    baseline: same-phase earlier days when the phase is known and there are 7+,
    else all days older than the last hold_out. Single nights are noisy, so the
    table also reports how many of the n nights sit on the same side of the
    baseline by at least 1 SD (a streak is a pattern, one night is not).
    Returns (rows, streaks).
    """
    older = sorted_days[:-hold_out] if len(sorted_days) > hold_out + MIN_BASELINE_DAYS else []
    if not older:
        return [], {}
    out = []
    pool_all = {}
    for m in NIGHT_METRICS:
        pool_all[m] = _mean_sd(_vals(days, older, m))
    for day in sorted_days[-n:]:
        ph = days[day].get("phase")
        bph = "follicular" if ph == "no_shift" else ph
        same = [x for x in older if bph and days[x].get("phase") == bph]
        row = {"day": day, "cycle_day": days[day].get("cycle_day"), "phase": ph, "cells": {}}
        for m in NIGHT_METRICS:
            v = days[day].get(m)
            if v is None:
                continue
            sv = _vals(days, same, m)
            mu, sd = _mean_sd(sv) if len(sv) >= 7 else pool_all[m]
            z = (v - mu) / sd if sd else None
            row["cells"][m] = (v, z, "same-phase" if len(sv) >= 7 else "all-days")
        out.append(row)
    streaks = {}
    for m in NIGHT_METRICS:
        zs = [r["cells"][m][1] for r in out if m in r["cells"] and r["cells"][m][1] is not None]
        if len(zs) == n:
            if all(z >= NOTABLE_SD for z in zs):
                streaks[m] = "above"
            elif all(z <= -NOTABLE_SD for z in zs):
                streaks[m] = "below"
    return out, streaks


def slope_per_week(days, sorted_days, metric, n=28):
    """Least-squares slope of the last n days, per 7 days. None if <14 points."""
    pts = [(i, days[x].get(metric)) for i, x in enumerate(sorted_days[-n:])
           if days[x].get(metric) is not None]
    if len(pts) < 14:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    mx, my = mean(xs), mean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    return 7 * sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else None


# --------------------------------------------------------------------------
# Per-phase comparison
# --------------------------------------------------------------------------

def phase_dates(days, cycles, phase, only_complete=False):
    sel = set(c["start"] for c in cycles if c["complete"] or not only_complete)
    out = []
    for c in cycles:
        if c["start"] not in sel:
            continue
        out.append([x for x in sorted(days)
                    if c["start"] <= x <= c["end"] and days[x].get("phase") == phase])
    return out


def per_cycle_table(days, cycles):
    """
    One row per cycle with an estimated ovulation: luteal-minus-follicular
    change in each phase metric, using each cycle's own follicular days
    (post-menses) and luteal days. Early luteal days are skipped (first 2 days
    after ovulation) so the transition does not blur the contrast.
    """
    rows = []
    for c in cycles:
        if not c["ovulation_est"]:
            continue
        ov = _d(c["ovulation_est"])
        fol = [x for x in sorted(days) if c["start"] <= x <= c["end"]
               and days[x].get("phase") == "follicular"]
        lut = [x for x in sorted(days) if c["start"] <= x <= c["end"]
               and days[x].get("phase") == "luteal" and _d(x) > ov + timedelta(days=2)]
        if len(fol) < 3 or len(lut) < 3:
            continue
        deltas = {}
        for m in PHASE_METRICS:
            fv, lv = _vals(days, fol, m), _vals(days, lut, m)
            if len(fv) >= 3 and len(lv) >= 3:
                deltas[m] = mean(lv) - mean(fv)
        rows.append({"cycle": c, "n_fol": len(fol), "n_lut": len(lut), "deltas": deltas})
    return rows


def phase_summary(days, cycles, rows):
    """
    Pooled per-metric means by phase plus the average of the per-cycle luteal -
    follicular deltas and how many cycles agree on the sign of the change.
    """
    out = {}
    for m, meta in PHASE_METRICS.items():
        means = {}
        for ph in ("menstrual", "follicular", "luteal", "no_shift"):
            v = [days[x].get(m) for x in days
                 if days[x].get("phase") == ph and days[x].get(m) is not None]
            if len(v) >= 5:
                means[ph] = (mean(v), len(v))
        ds = [r["deltas"][m] for r in rows if m in r["deltas"]]
        if not means and not ds:
            continue
        entry = {"means": means, "n_cycles": len(ds)}
        if ds:
            entry["mean_delta"] = mean(ds)
            entry["same_sign"] = max(sum(1 for d in ds if d > 0), sum(1 for d in ds if d < 0))
        out[m] = entry
    return out


def direction_label(m, entry, all_sd):
    """
    Compare the user's mean luteal-minus-follicular change with the direction
    typical of healthy regular cycles. 'flat' means smaller than 0.5 daily SD.
    """
    want = PHASE_METRICS[m]["dir"]
    d = entry.get("mean_delta")
    if d is None or not want:
        return ""
    sd = all_sd.get(m)
    if sd and abs(d) < 0.5 * sd:
        return "flat"
    return "same direction as typical" if d * want > 0 else "opposite to typical"


def overall_sd(days, sorted_days, metric):
    v = _vals(days, sorted_days, metric)
    return stdev(v) if len(v) > 1 else None


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def _fmt(v, dec=1, sign=False):
    if v is None:
        return "--"
    s = "{:+.{d}f}" if sign else "{:.{d}f}"
    return s.format(v, d=dec)


def _dec(m):
    return PHASE_METRICS.get(m, {}).get("dec", 1)


def render_markdown(days, sorted_days, cycles, period_source=""):
    """The 'Personalization' sections appended to oura_summary.md."""
    L = []
    last = sorted_days[-1]
    cur = days[last]

    L.append("## Where you are in the cycle (ESTIMATED)")
    if not cycles:
        L.append("- No period starts available, so no phase labels. Comparisons below use "
                 "the whole window as baseline only.")
    else:
        c = cycles[-1]
        ph = cur.get("phase")
        L.append("- Latest data day: {} | cycle day {} | phase: {}".format(
            last, cur.get("cycle_day", "--"), ph or "unknown"))
        if c["ovulation_est"]:
            since = (_d(last) - _d(c["ovulation_est"])).days
            L.append("- Temperature shift began {}; ovulation estimated {} ({} days before the "
                     "latest data day). This marks a temperature shift, not confirmed "
                     "ovulation.".format(c["shift_day"], c["ovulation_est"], since))
        elif c["days_so_far"] >= MAX_PRESHIFT_DAYS:
            L.append("- No sustained temperature shift yet in this cycle after {} days "
                     "(settings: {} consecutive days >= {:.2f}°C above the prior {}-day "
                     "mean).".format(c["days_so_far"], SHIFT_RUN_DAYS, SHIFT_RISE_C, SHIFT_BASE_DAYS))
        else:
            L.append("- Cycle day {} so far; too early to expect a shift.".format(c["days_so_far"]))
        L.append("- Phase labels: menstrual = tagged bleed days (or cycle days 1-{}), luteal = day "
                 "after the estimated ovulation to the next period; 'no_shift' = non-menstrual "
                 "days of a cycle with no detected shift.".format(MENSES_DAYS))
    L.append("")

    nights, streaks = last_nights(days, sorted_days)
    L.append("## Last 3 nights (single nights are noisy; a streak is a pattern)")
    if not nights:
        L.append("- Not enough earlier data for a nightly comparison.")
    else:
        L.append("Each cell: value (change in SD vs your baseline; baseline = same phase when 7+ earlier "
                 "days exist, else all earlier days).")
        L.append("")
        L.append("| night | cycle day / phase | " + " | ".join(LABELS.get(m, m) for m in NIGHT_METRICS) + " |")
        L.append("|---|---|" + "---|" * len(NIGHT_METRICS))
        for r in nights:
            cells = []
            for m in NIGHT_METRICS:
                c = r["cells"].get(m)
                cells.append("--" if not c else "{} ({} SD)".format(_fmt(c[0], _dec(m)), _fmt(c[1], 1, True)))
            L.append("| {} | {} / {} | {} |".format(r["day"], r["cycle_day"] or "--",
                                                    r["phase"] or "--", " | ".join(cells)))
        if streaks:
            L.append("")
            L.append("- Streaks (all {} nights >= {:.0f} SD on one side): {}".format(
                len(nights), NOTABLE_SD, "; ".join("{} {}".format(LABELS.get(m, m), d)
                                                   for m, d in streaks.items())))
        else:
            L.append("")
            L.append("- No metric has been >= {:.0f} SD on the same side for all {} nights.".format(
                NOTABLE_SD, len(nights)))
    L.append("")

    metrics = [m for ms in DOMAINS.values() for m in ms]
    cmp_, cur_phase = recent_vs_baseline(days, sorted_days, metrics)
    L.append("## Last 7 days vs your own baseline")
    if not cmp_:
        L.append("- Not enough earlier data ({}+ days) for a personal baseline.".format(MIN_BASELINE_DAYS))
    else:
        L.append("Baseline = all earlier days in the window. Phase baseline = earlier days in the "
                 "same phase as the latest day ({}). SDs are the baseline's own day-to-day SD; "
                 "'notable' = |change| >= {:.0f} SD.".format(cur_phase or "unknown", NOTABLE_SD))
        L.append("")
        L.append("| domain | metric | last 7d | baseline (mean ± SD) | change | change in SD | "
                 "same-phase baseline | vs same phase | 28d slope /wk |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        for dom, ms in DOMAINS.items():
            for m in ms:
                r = cmp_.get(m)
                if not r:
                    continue
                dec = _dec(m)
                z = r["z"]
                flag = " **notable**" if z is not None and abs(z) >= NOTABLE_SD else ""
                ph_cell = "--"
                ph_delta = "--"
                if "phase_mean" in r:
                    ph_cell = "{} ± {} (n={})".format(_fmt(r["phase_mean"], dec),
                                                       _fmt(r["phase_sd"], dec), r["n_phase"])
                    pz = r.get("phase_z")
                    ph_delta = "{} ({} SD)".format(_fmt(r["phase_delta"], dec, True),
                                                   _fmt(pz, 1, True))
                L.append("| {} | {} | {} | {} ± {} | {} | {}{} | {} | {} | {} |".format(
                    dom, LABELS.get(m, m), _fmt(r["recent"], dec),
                    _fmt(r["base_mean"], dec), _fmt(r["base_sd"], dec),
                    _fmt(r["delta"], dec, True), _fmt(z, 1, True), flag,
                    ph_cell, ph_delta,
                    _fmt(slope_per_week(days, sorted_days, m), dec, True)))
    L.append("")

    rows = per_cycle_table(days, cycles)
    L.append("## Per-cycle detail (luteal vs follicular, your own cycles)")
    if not rows:
        L.append("- No cycle with both an estimated ovulation and enough follicular and luteal "
                 "days yet. Per-phase comparisons need at least one such cycle.")
    else:
        L.append("Deltas are luteal minus follicular (luteal days start 3 days after the "
                 "estimated ovulation; follicular = after menses to ovulation).")
        L.append("")
        cols = ["temp_deviation", "RHR", "HRV", "breath_rate", "efficiency"]
        L.append("| cycle start | length | ovulation est. (cycle day) | luteal length | " +
                 " | ".join("Δ " + LABELS[m] for m in cols) + " |")
        L.append("|---|---|---|---|" + "---|" * len(cols))
        for r in rows:
            c = r["cycle"]
            L.append("| {} | {} | {} (day {}) | {} | {} |".format(
                c["start"], c["length_days"] if c["complete"] else "{} (open)".format(c["days_so_far"]),
                c["ovulation_est"], (_d(c["ovulation_est"]) - _d(c["start"])).days + 1, c["luteal_len"] if c["luteal_len"] is not None else "--",
                " | ".join(_fmt(r["deltas"].get(m), _dec(m), True) for m in cols)))
    L.append("")

    summ = phase_summary(days, cycles, rows)
    L.append("## Phase means (pooled across cycles in the window)")
    if not summ:
        L.append("- Not enough phase-labelled days.")
    else:
        L.append("| metric | menstrual | follicular | luteal | no_shift | mean luteal−follicular "
                 "| cycles agreeing on sign | vs typical healthy direction |")
        L.append("|---|---|---|---|---|---|---|---|")
        all_sd = dict((m, overall_sd(days, sorted_days, m)) for m in PHASE_METRICS)
        for m, e in summ.items():
            dec = _dec(m)
            cells = []
            for ph in ("menstrual", "follicular", "luteal", "no_shift"):
                v = e["means"].get(ph)
                cells.append("{} (n={})".format(_fmt(v[0], dec), v[1]) if v else "--")
            n = e["n_cycles"]
            agree = "{}/{}".format(e["same_sign"], n) if n else "--"
            L.append("| {} | {} | {} | {} | {} |".format(
                LABELS[m], " | ".join(cells),
                _fmt(e.get("mean_delta"), dec, True), agree,
                direction_label(m, e, all_sd) or "n/a"))
    L.append("")
    return "\n".join(L)
