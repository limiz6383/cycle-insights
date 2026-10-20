import json, sys, unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "eval"))
import generate_insight as gi  # noqa: E402
import self_check as sc  # noqa: E402

SUMMARY = "sleeping HR 57.6 bpm baseline 59.8 +- 1.1; cycle day 20; sleep midpoint 2.6 h"
FILLER = " ".join(["Your sleep midpoint moved later and your sleeping HR sits under baseline."] * 11)
GOOD = ("Cycle day 20: your sleeping HR is 57.6 bpm against 59.8 usually. This pattern is consistent "
        "with progesterone not having risen yet (KB26), though the ring only measures downstream signs. " + FILLER +
        "\n\n**Today:** 1. Start a wind-down at 21:30. 2. Keep screens out of the last hour.\n\n"
        "**Watch for:** sleeping HR back near 59.8 over two nights.")


def ok(checks):
    return [c["id"] for c in checks if not c["passed"]]


class Checks(unittest.TestCase):
    def test_clean_draft_passes(self):
        self.assertEqual(ok(sc.hard_and_soft_checks(GOOD, SUMMARY)), [])

    def test_hard_failures(self):
        bad = GOOD.replace("Start a wind-down", "Eat 300 calories more, you should skip a meal, because of your stress this is because")
        failed = ok(sc.hard_and_soft_checks(bad, SUMMARY))
        for k in ("DG3 numeric nutrition", "DG6 causal claim", "T8 'should' about the body"):
            self.assertIn(k, failed)

    def test_invented_number_is_flagged_but_clock_times_are_not(self):
        failed = ok(sc.hard_and_soft_checks(GOOD.replace("57.6", "63.4"), SUMMARY))
        self.assertIn("numbers appear in her data or the knowledge base", failed)
        self.assertEqual(ok(sc.hard_and_soft_checks(GOOD, SUMMARY)), [])   # 21:30 is fine

    def test_repeat_of_recent_insight_is_flagged(self):
        self.assertIn("not a repeat of a recent insight",
                      ok(sc.hard_and_soft_checks(GOOD, SUMMARY, recent="[x] " + GOOD)))

    def test_parse_judge(self):
        j = sc.parse_judge('noise {"criteria": {"G1": {"verdict": "PASS"}, "G3": {"verdict": "FAIL", '
                           '"evidence": "q"}}, "fixes": ["tie step 2 to the bedtime"]} ')
        self.assertEqual(j["failed"], ["G3"])


class Loop(unittest.TestCase):
    ARGS = Namespace(judge_rounds=2, out_dir="/nonexistent", cadence="daily", model="m", max_tokens=500)
    PASS = json.dumps({"criteria": {k: {"verdict": "PASS"} for k in ("G1", "G2", "G3", "G4", "G5", "G6", "G7")}, "fixes": []})

    def run_loop(self, replies):
        with mock.patch.object(gi, "call_claude", side_effect=[(r, {}) for r in replies]):
            return gi.self_review(self.draft, "<knowledge_base>kb</knowledge_base>",
                                  SUMMARY, "2030-01-01", self.ARGS, "go")

    def test_soft_failure_is_revised_and_then_passes(self):
        self.draft = GOOD
        fail = json.dumps({"criteria": {"G3": {"verdict": "FAIL", "evidence": "step 2"}}, "fixes": ["tie step 2"]})
        text, log, held = self.run_loop([fail, GOOD + " ", self.PASS])
        self.assertFalse(held)
        self.assertEqual([r["failed_judge"] for r in log], [["G3"], []])

    def test_persistent_hard_failure_is_held(self):
        self.draft = GOOD.replace("Start a wind-down", "Eat 300 calories more")
        text, log, held = self.run_loop([self.PASS, self.draft, self.PASS, self.draft, self.PASS])
        self.assertTrue(held)

    def test_reviewer_outage_does_not_block_a_clean_draft(self):
        self.draft = GOOD
        with mock.patch.object(gi, "call_claude", side_effect=RuntimeError("down")):
            text, log, held = gi.self_review(GOOD, "<knowledge_base>kb</knowledge_base>", SUMMARY,
                                             "2030-01-01", self.ARGS, "go")
        self.assertFalse(held)
        self.assertFalse(log[0]["reviewed"])


if __name__ == "__main__":
    unittest.main()
