"""
Daily check-in: before a new insight is sent, ask whether yesterday's steps were done.

Flow (send_insight.py + chat_bot.py):
  1. generate_insight.py stores the insight's **Today:** steps on its record (`today_steps`).
  2. send_insight.py: if the newest earlier record has steps and no `followup`, send a
     check-in message with three buttons instead of the insight, and mark the new record
     `pending_send`. Otherwise send the insight as usual.
  3. chat_bot.py: a button tap, or a typed answer while a check-in is open, stores
     `followup` on the earlier record and then sends the held insight.
  4. If she never answers, the next send_insight run releases the held insight first.
The followup is shown to the model with the recent insights, so the new insight and the chat
can build on what she did or didn't do.
"""
import json
import re
from pathlib import Path

STEPS = re.compile(r"\*\*Today:?\*\*:?\s*(.*?)(?=\*\*Watch for|\Z)", re.S | re.I)
BUTTONS = [("Did them", "all"), ("Did some", "some"), ("Didn't get to it", "none")]
STATUS_WORDS = {
    "all": ("yes", "yep", "yeah", "did", "done", "all", "did them", "i did"),
    "none": ("no", "nope", "didn't", "didnt", "did not", "not today", "skipped", "none"),
    "some": ("some", "partly", "partially", "half", "a bit", "one of"),
}


def extract_steps(text):
    m = STEPS.search(text or "")
    return re.sub(r"\n{3,}", "\n\n", m.group(1).strip()) if m else ""


def read(path):
    return json.loads(Path(path).read_text())


def write(path, rec):
    Path(path).write_text(json.dumps(rec, indent=2))


def records(insights_dir):
    d = Path(insights_dir)
    return sorted(d.glob("*.json")) if d.is_dir() else []


def awaiting_checkin(insights_dir, before_id):
    """Newest record before `before_id` that has steps and no followup, or None."""
    for p in reversed([p for p in records(insights_dir) if p.stem < before_id]):
        rec = read(p)
        if rec.get("today_steps") and not rec.get("followup"):
            return p, rec
        if rec.get("followup"):
            return None
    return None


def pending_release(insights_dir):
    """Record whose insight is being held behind a check-in, or None."""
    for p in reversed(records(insights_dir)):
        rec = read(p)
        if rec.get("pending_send"):
            return p, rec
    return None


def checkin_text(rec):
    return ("Before today's insight: did you get to yesterday's steps?\n\n{}".format(
        rec["today_steps"]))


def checkin_markup(record_id):
    return json.dumps({"inline_keyboard": [[
        {"text": label, "callback_data": "ci:{}:{}".format(record_id, status)}
        for label, status in BUTTONS]]})


def classify(text):
    t = (text or "").strip().lower().strip(".!")
    for status in ("none", "some", "all"):          # "didn't" before "did"
        if any(t == w or t.startswith(w + " ") or t.startswith(w + ",") for w in STATUS_WORDS[status]):
            return status
    return "note"


def record_followup(path, status, note=""):
    rec = read(path)
    rec["followup"] = {"status": status, "note": note}
    write(path, rec)
    return rec


def followup_tag(rec):
    fu = rec.get("followup")
    if not fu:
        return ""
    label = {"all": "she did the steps", "some": "she did some of the steps",
             "none": "she did not get to the steps", "note": "her reply to the steps"}[fu["status"]]
    return " [follow-up: {}{}]".format(label, ": " + fu["note"] if fu.get("note") else "")
