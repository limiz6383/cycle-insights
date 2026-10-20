import json, sys, tempfile, unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "eval"))
import chat_bot as cb  # noqa: E402

ARGS = Namespace(dry_run=False, summary="/nonexistent", prompt_version="v3.4", model="m")


def msg(text, chat=111, reply_to=None):
    m = {"chat": {"id": chat}, "text": text}
    if reply_to:
        m["reply_to_message"] = {"message_id": reply_to}
    return m


class ChatBot(unittest.TestCase):
    def setUp(self):
        self.sent = []
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(cb, "HISTORY_PATH", Path(self.tmp.name) / "h.jsonl")
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def handle(self, m, index=None):
        return cb.handle_message(m, 111, ARGS, index={} if index is None else index,
                                 reply=self.sent.append)

    def test_other_chats_and_empty_text_are_ignored(self):
        self.assertEqual(self.handle(msg("hi", chat=999)), "ignored")
        self.assertEqual(self.handle(msg("   ")), "ignored")
        self.assertEqual(self.sent, [])

    def test_commands(self):
        self.assertEqual(self.handle(msg("/help")), "command")
        self.assertIn("Ask me anything", self.sent[0])

    def test_summary_commands_use_the_stats_report_not_the_model(self):
        with mock.patch.object(cb, "summary_message", return_value="STATS") as sm, \
                mock.patch.object(cb, "call_claude") as model:
            self.assertEqual(self.handle(msg("/weekly")), "command")
            self.assertEqual(self.handle(msg("/monthly@mybot")), "command")
        self.assertEqual([c[0][0] for c in sm.call_args_list], [7, 30])
        self.assertEqual(self.sent, ["STATS", "STATS"])
        model.assert_not_called()

    def test_default_replies_carry_the_quick_buttons(self):
        with mock.patch.object(cb, "send_message") as sm:
            cb.handle_message(msg("/help"), 111, ARGS, index={})
        self.assertEqual(sm.call_args[1]["reply_markup"], cb.KEYBOARD)
        self.assertIn("/weekly", cb.KEYBOARD)

    def test_summary_message_without_data(self):
        self.assertIn("don't have your Oura data", cb.summary_message(7, data_path="/nonexistent.json"))

    def test_rating_reply_is_stored_as_feedback(self):
        p = Path(self.tmp.name) / "i.json"
        p.write_text(json.dumps({"insight_id": "x", "feedback": {}}))
        self.assertEqual(self.handle(msg("wrong, too vague", reply_to=5), index={5: p}), "feedback")
        fb = json.loads(p.read_text())["feedback"]
        self.assertEqual(fb["rating"], "wrong")
        self.assertTrue(fb["promote_to_scenario"])

    def test_question_goes_to_model_and_history_is_kept(self):
        with mock.patch.object(cb, "call_claude", return_value=("Because your HRV fell.", {})) as m:
            self.assertEqual(self.handle(msg("why is my HRV low?")), "chat")
        self.assertEqual(self.sent, ["Because your HRV fell."])
        self.assertIn("why is my HRV low?", m.call_args[0][0])
        self.assertEqual([r["role"] for r in cb.load_history()], ["user", "assistant"])

    def test_second_turn_sees_the_first(self):
        with mock.patch.object(cb, "call_claude", return_value=("ok", {})) as m:
            self.handle(msg("I had two drinks last night"))
            self.handle(msg("so is that why?"))
        self.assertIn("I had two drinks last night", m.call_args[0][0])

    def test_model_failure_gets_a_plain_reply(self):
        with mock.patch.object(cb, "call_claude", side_effect=SystemExit("no key")):
            self.handle(msg("hello?"))
        self.assertIn("couldn't reach the model", self.sent[0])

    def _two_records(self):
        d = Path(self.tmp.name) / "ins"
        d.mkdir()
        (d / "2030-03-01.json").write_text(json.dumps({"insight_id": "2030-03-01", "today_steps": "a"}))
        (d / "2030-03-02.json").write_text(json.dumps(
            {"insight_id": "2030-03-02", "insight_text": "new", "pending_send": True}))
        return d

    def test_button_tap_stores_answer_and_releases_held_insight(self):
        d = self._two_records()
        with mock.patch.object(cb.pf, "INSIGHTS_DIR", d), \
                mock.patch.object(cb, "api_call", return_value={"ok": True}), \
                mock.patch.object(cb, "deliver_insight") as dl:
            tag = cb.handle_callback({"id": "1", "data": "ci:2030-03-01:some",
                                      "message": {"chat": {"id": 111}}}, 111, ARGS)
        self.assertEqual(tag, "checkin")
        self.assertEqual(json.loads((d / "2030-03-01.json").read_text())["followup"]["status"], "some")
        self.assertEqual(dl.call_args[0][0].stem, "2030-03-02")

    def test_typed_answer_while_checkin_open(self):
        d = self._two_records()
        with mock.patch.object(cb.pf, "INSIGHTS_DIR", d), mock.patch.object(cb, "deliver_insight") as dl:
            self.assertEqual(self.handle(msg("yes, did them")), "checkin")
        self.assertEqual(json.loads((d / "2030-03-01.json").read_text())["followup"]["status"], "all")
        self.assertTrue(dl.called)

    def test_wrong_chat_callback_is_ignored(self):
        self.assertEqual(cb.handle_callback({"id": "1", "data": "ci:x:all",
                                             "message": {"chat": {"id": 5}}}, 111, ARGS), "ignored")

    def test_chat_prompt_fills_every_placeholder(self):
        p = cb.build_chat_prompt("q?", [{"role": "user", "text": "earlier"}], "/nonexistent",
                                 insights_dir=self.tmp.name)
        self.assertIn("Her: earlier", p)
        self.assertIn("\nchat\n", p)
        self.assertNotIn("[Earlier turns of this chat", p)


if __name__ == "__main__":
    unittest.main()
