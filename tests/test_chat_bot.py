import json, sys, tempfile, unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "eval"))
import chat_bot as cb  # noqa: E402

ARGS = Namespace(dry_run=False, summary="/nonexistent", prompt_version="v3.3", model="m")


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

    def test_chat_prompt_fills_every_placeholder(self):
        p = cb.build_chat_prompt("q?", [{"role": "user", "text": "earlier"}], "/nonexistent",
                                 insights_dir=self.tmp.name)
        self.assertIn("Her: earlier", p)
        self.assertIn("\nchat\n", p)
        self.assertNotIn("[Earlier turns of this chat", p)


if __name__ == "__main__":
    unittest.main()
