import json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import checkin  # noqa: E402
from synthetic_oura import make_dump  # noqa: E402


class Checkin(unittest.TestCase):
    def test_extract_steps(self):
        t = "Obs.\n\n**Today:** 1. First. 2. Second.\n\n**Watch for:** x"
        self.assertEqual(checkin.extract_steps(t), "1. First. 2. Second.")
        self.assertEqual(checkin.extract_steps("no steps here"), "")

    def test_classify(self):
        self.assertEqual(checkin.classify("Yes, did them"), "all")
        self.assertEqual(checkin.classify("didn't get to it"), "none")
        self.assertEqual(checkin.classify("some of it"), "some")
        self.assertEqual(checkin.classify("the weather was awful"), "note")

    def test_awaiting_and_release(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / "2030-03-01.json").write_text(json.dumps({"today_steps": "a"}))
            (d / "2030-03-02.json").write_text(json.dumps({"today_steps": "b", "pending_send": True}))
            self.assertEqual(checkin.awaiting_checkin(d, "2030-03-02")[0].stem, "2030-03-01")
            self.assertEqual(checkin.pending_release(d)[0].stem, "2030-03-02")
            checkin.record_followup(d / "2030-03-01.json", "all")
            self.assertIsNone(checkin.awaiting_checkin(d, "2030-03-02"))


class ActionSection(unittest.TestCase):
    def test_summary_lists_actions_and_moves(self):
        dump = make_dump(days=120, ovulatory=False)
        # Sleeping HR drops by ~4 bpm after day 100 (2030-04-11 is day index 100).
        for r in dump["sleep"]["data"][101:]:
            r["average_heart_rate"] = r.get("average_heart_rate", 58) - 4
            r["lowest_heart_rate"] = r.get("lowest_heart_rate", 52) - 4
        with tempfile.TemporaryDirectory() as t:
            src, out, ins = Path(t) / "d.json", Path(t) / "s.md", Path(t) / "ins"
            ins.mkdir()
            src.write_text(json.dumps(dump))
            (ins / "2030-04-11.json").write_text(json.dumps({
                "insight_id": "2030-04-11", "today_steps": "1. Fixed wind-down at 21:30.",
                "followup": {"status": "all", "note": ""}}))
            subprocess.run([sys.executable, str(ROOT / "scripts" / "preprocess_oura.py"),
                            "--input", str(src), "--output", str(out), "--insights-dir", str(ins)],
                           check=True, capture_output=True)
            md = out.read_text()
        self.assertIn("Suggested actions and what your data did since", md)
        self.assertIn("2030-04-11", md)
        self.assertIn("she did them", md)
        self.assertIn("sleeping HR", md.split("Suggested actions")[1].split("##")[0])


if __name__ == "__main__":
    unittest.main()


class PeriodReport(unittest.TestCase):
    def test_weekly_and_monthly_reports(self):
        import period_report as pr
        with tempfile.TemporaryDirectory() as t:
            src = Path(t) / "d.json"
            src.write_text(json.dumps(make_dump(days=130)))
            days, sd, _ = pr.load_days(src, str(Path(t) / "none.json"))
        week = pr.build_report(days, sd, 7)
        month = pr.build_report(days, sd, 30)
        self.assertIn("Weekly summary: " + sd[-7], week)
        self.assertIn("Monthly summary: " + sd[-30], month)
        for text in (week, month):
            self.assertIn("sleeping HR", text)
            self.assertIn("Moved by 1 SD or more", text)
            self.assertLess(len(text), 4000)
