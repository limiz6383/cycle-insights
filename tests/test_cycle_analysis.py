"""Synthetic-data tests for the personalization layer. Run: python3 -m unittest discover tests"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import cycle_analysis as ca  # noqa: E402
import preprocess_oura as po  # noqa: E402
from synthetic_oura import make_dump  # noqa: E402


def analyse(dump, as_of=None):
    days = po.build_daily(dump)
    sd = sorted(days)
    tags = po.period_days_from_tags(dump)
    starts = po.period_starts(tags)
    if as_of:
        sd = [d for d in sd if d <= as_of]
        starts = [s for s in starts if s <= as_of]
        tags = [t for t in tags if t <= as_of]
        days = {d: days[d] for d in sd}
    cycles = ca.build_cycles(days, starts, sd[-1])
    ca.label_days(days, cycles, tags)
    return days, sd, cycles


class CycleAnalysisTests(unittest.TestCase):
    def test_ovulation_estimated_near_truth(self):
        _, _, cycles = analyse(make_dump(days=120))
        done = [c for c in cycles if c["complete"]]
        found = [c for c in done if c["ovulation_est"]]
        self.assertGreaterEqual(len(found), len(done) - 1)   # noise may hide one shift
        # true ovulation is cycle day 14; the shift detector may lag by a few days
        for c in found:
            off = (ca._d(c["ovulation_est"]) - ca._d(c["start"])).days + 1
            self.assertTrue(12 <= off <= 18, off)

    def test_phase_deltas_match_injected_offsets(self):
        days, sd, cycles = analyse(make_dump(days=150))
        rows = ca.per_cycle_table(days, cycles)
        summ = ca.phase_summary(days, cycles, rows)
        self.assertAlmostEqual(summ["temp_deviation"]["mean_delta"], 0.30, delta=0.08)
        self.assertAlmostEqual(summ["RHR"]["mean_delta"], 2.5, delta=1.0)
        self.assertAlmostEqual(summ["HRV"]["mean_delta"], -5.0, delta=3.0)

    def test_anovulatory_has_no_shift_and_flat_deltas(self):
        days, sd, cycles = analyse(make_dump(days=120, ovulatory=False))
        self.assertTrue(all(c["ovulation_est"] is None for c in cycles))
        self.assertEqual(ca.per_cycle_table(days, cycles), [])
        self.assertIn("no_shift", {days[d].get("phase") for d in sd})

    def test_recent_vs_baseline_flags_injected_change(self):
        dump = make_dump(days=100)
        for r in dump["sleep"]["data"][-7:]:
            r["average_hrv"] = 40      # synthetic HRV crash in the last week
        days, sd, _ = analyse(dump)
        cmp_, _ = ca.recent_vs_baseline(days, sd, ["HRV", "RHR"])
        self.assertLess(cmp_["HRV"]["z"], -2)
        self.assertLess(abs(cmp_["RHR"]["z"]), 2)

    def test_as_of_slice_cannot_see_future(self):
        dump = make_dump(days=150)
        cut = "2030-03-01"
        days, sd, cycles = analyse(dump, as_of=cut)
        self.assertLessEqual(sd[-1], cut)
        self.assertTrue(all(c["end"] <= cut for c in cycles))

    def test_short_spike_in_flat_curve_is_not_a_shift(self):
        dump = make_dump(days=60, ovulatory=False, seed=3)
        for r in dump["daily_readiness"]["data"][12:15]:
            r["temperature_deviation"] = 0.45      # 3-day spike, then flat again
        days, sd, cycles = analyse(dump)
        self.assertTrue(all(c["ovulation_est"] is None for c in cycles))

    def test_long_cycle_is_labelled_and_midcycle_window_start_is_not(self):
        days, sd, cycles = analyse(make_dump(days=100, cycle_len=70, ovulation_day=55))
        self.assertTrue(any(c["length_days"] == 70 for c in cycles))
        late = {k: v for k, v in days.items() if k >= "2030-01-20"}
        c2 = ca.build_cycles(late, ["2030-01-01"], max(late))
        self.assertEqual(c2, [])

    def test_not_a_period_ranges_drop_phantom_cycle_starts(self):
        dump = make_dump(days=120)
        tags = po.period_days_from_tags(dump)
        kept = po.drop_ranges(tags, "2030-02-26:2030-03-01")
        self.assertEqual(len(po.period_starts(tags)) - 1, len(po.period_starts(kept)))
        dump["enhanced_tag"]["data"].append({"tag_type_code": "spotting", "start_day": "2030-02-10"})
        self.assertNotIn("2030-02-10", po.period_days_from_tags(dump))

    def test_spotting_is_listed_but_not_a_cycle_start(self):
        with tempfile.TemporaryDirectory() as t:
            src, out = Path(t) / "d.json", Path(t) / "s.md"
            src.write_text(json.dumps(make_dump(days=100)))
            subprocess.run([sys.executable, str(ROOT / "scripts" / "preprocess_oura.py"),
                            "--input", str(src), "--output", str(out),
                            "--spotting", "2030-02-10:2030-02-12"], check=True, capture_output=True)
            md = out.read_text()
        self.assertIn("User-reported spotting", md)
        self.assertIn("2030-02-10 to 2030-02-12 (3 days with data)", md)
        self.assertIn("Cycle lengths (from user-reported periods): [28, 28, 28]", md)

    def test_user_log_file_supplies_spotting(self):
        with tempfile.TemporaryDirectory() as t:
            src, out, log = Path(t) / "d.json", Path(t) / "s.md", Path(t) / "log.json"
            src.write_text(json.dumps(make_dump(days=100)))
            log.write_text(json.dumps({"spotting": ["2030-02-10:2030-02-12"]}))
            subprocess.run([sys.executable, str(ROOT / "scripts" / "preprocess_oura.py"),
                            "--input", str(src), "--output", str(out),
                            "--user-log", str(log)], check=True, capture_output=True)
            self.assertIn("2030-02-10 to 2030-02-12", out.read_text())

    def test_last_nights_flags_a_streak_not_a_single_night(self):
        dump = make_dump(days=100, ovulatory=False)
        for r in dump["sleep"]["data"][-3:]:
            r["average_hrv"] = 30                  # three low nights in a row
        days, sd, _ = analyse(dump)
        rows, streaks = ca.last_nights(days, sd)
        self.assertEqual(len(rows), 3)
        self.assertEqual(streaks.get("HRV"), "below")
        dump = make_dump(days=100, ovulatory=False)
        dump["sleep"]["data"][-2]["average_hrv"] = 30   # one low night only
        days, sd, _ = analyse(dump)
        self.assertNotIn("HRV", ca.last_nights(days, sd)[1])

    def test_prompt_gets_cadence_and_recent_insights(self):
        sys.path.insert(0, str(ROOT / "scripts" / "eval"))
        import prompt_lib
        base = prompt_lib.load_prompt("v3.2")
        out = prompt_lib.inject_user_data(base, oura_summary="x", recent_insights="[2030-01-01] steady",
                                          cadence="daily")
        self.assertIn("[2030-01-01] steady", out)
        self.assertRegex(out, r"<cadence>\ndaily\n</cadence>")
        self.assertIn("UD4", out)
        old = prompt_lib.load_prompt("v3.1")      # older prompts have neither block
        prompt_lib.inject_user_data(old, oura_summary="x", cadence="daily")

    def test_end_to_end_summary_has_sections_and_no_real_dates(self):
        with tempfile.TemporaryDirectory() as t:
            src, out = Path(t) / "d.json", Path(t) / "s.md"
            src.write_text(json.dumps(make_dump(days=120)))
            subprocess.run([sys.executable, str(ROOT / "scripts" / "preprocess_oura.py"),
                            "--input", str(src), "--output", str(out)], check=True, capture_output=True)
            md = out.read_text()
        for h in ("## Where you are in the cycle", "## Last 7 days vs your own baseline",
                  "## Per-cycle detail", "## Phase means"):
            self.assertIn(h, md)
        self.assertIn("2030-", md)   # synthetic epoch, not a real period


if __name__ == "__main__":
    unittest.main()
