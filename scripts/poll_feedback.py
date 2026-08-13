#!/usr/bin/env python3
"""
Pull Telegram replies into the feedback block of each insight record.

A reply carries `reply_to_message.message_id`, which send_insight.py stored on
the record. That is the join key: reply -> the exact insight it rates.

Reply format (first word is the rating, the rest is free text):
    wrong — told me to add intensity, but I'd just had a 3-week gap
    useful, the HRV reframe matched how I actually felt
    unsafe: suggested cutting evening carbs

Bare text with no leading keyword is stored as a note with rating=null.
Anything rated wrong / unsafe / not_actionable is flagged
promote_to_scenario=true — those are your eval scenarios.

Usage:
  python3 poll_feedback.py            # fetch new replies, write them in
  python3 poll_feedback.py --list     # show all recorded feedback
  python3 poll_feedback.py --dry-run
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import REPO_ROOT, require  # noqa: E402
from send_insight import api_call  # noqa: E402

INSIGHTS_DIR = REPO_ROOT / "insights"
STATE_PATH = REPO_ROOT / ".telegram_state.json"
# Every update is appended here BEFORE it is matched or acknowledged.
# Acknowledging an update deletes it from Telegram permanently, so an update
# we can't match (malformed reply, reply to the wrong message, reply that
# arrives before the insight was sent) would otherwise be destroyed with no
# record. This log is the safety net: nothing is lost, even when matching fails.
RAW_LOG = REPO_ROOT / ".telegram_raw.jsonl"

RATINGS = {"useful", "wrong", "unsafe", "obvious", "not_actionable"}
# Ratings that indicate a failure worth turning into an eval scenario.
FAILURE_RATINGS = {"wrong", "unsafe", "not_actionable"}


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"last_update_id": 0}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2))


def index_by_message_id():
    """message_id -> insight json path, for records that were actually sent."""
    index = {}
    if not INSIGHTS_DIR.exists():
        return index
    for path in INSIGHTS_DIR.glob("*.json"):
        tg = json.loads(path.read_text()).get("telegram") or {}
        if tg.get("message_id"):
            index[tg["message_id"]] = path
    return index


def parse_reply(text):
    """Split a reply into (rating, note). Rating is None if no keyword leads."""
    stripped = text.strip()
    if not stripped:
        return None, ""
    first = stripped.split()[0].lower().strip(".,:;—-!")
    if first in RATINGS:
        note = stripped[len(stripped.split()[0]):].lstrip(" .,:;—-")
        return first, note.strip()
    return None, stripped


def apply_feedback(path, rating, note, dry_run=False):
    record = json.loads(path.read_text())
    fb = record.setdefault("feedback", {})
    existing = fb.get("what_was_wrong") or ""
    fb["rating"] = rating or fb.get("rating")
    # Append rather than overwrite — you may reply more than once about a week.
    fb["what_was_wrong"] = (existing + "\n" + note).strip() if existing else note
    fb["promote_to_scenario"] = bool(rating in FAILURE_RATINGS) or fb.get(
        "promote_to_scenario", False
    )
    if not dry_run:
        path.write_text(json.dumps(record, indent=2))
    return fb


def list_feedback():
    rows = []
    for path in sorted(INSIGHTS_DIR.glob("*.json")):
        rec = json.loads(path.read_text())
        fb = rec.get("feedback") or {}
        rows.append((rec.get("insight_id"), fb.get("rating"),
                     bool(fb.get("promote_to_scenario")),
                     (fb.get("what_was_wrong") or "").replace("\n", " ")[:60]))
    if not rows:
        print("No insight records yet.")
        return
    print("{:<12} {:<14} {:<9} {}".format("insight", "rating", "scenario?", "note"))
    print("-" * 78)
    for insight_id, rating, promote, note in rows:
        print("{:<12} {:<14} {:<9} {}".format(
            insight_id or "?", rating or "—", "yes" if promote else "", note))
    n_scenarios = sum(1 for r in rows if r[2])
    print("\n{} of {} rated as failures → eval scenario candidates.".format(
        n_scenarios, len(rows)))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="Show recorded feedback and exit.")
    ap.add_argument("--dry-run", action="store_true", help="Parse replies, write nothing.")
    ap.add_argument("--rate", default=None, metavar="RATING",
                    help="Record feedback from the terminal instead of Telegram. One of: "
                         + ", ".join(sorted(RATINGS)))
    ap.add_argument("--note", default="", help="Free-text note to go with --rate.")
    ap.add_argument("--insight", default=None,
                    help="Insight id for --rate (default: most recent).")
    args = ap.parse_args()

    if args.list:
        list_feedback()
        return

    if args.rate:
        if args.rate not in RATINGS:
            raise SystemExit("--rate must be one of: {}".format(", ".join(sorted(RATINGS))))
        if args.insight:
            path = INSIGHTS_DIR / "{}.json".format(args.insight)
        else:
            files = sorted(INSIGHTS_DIR.glob("*.json"))
            if not files:
                raise SystemExit("No insight records yet.")
            path = files[-1]
        if not path.exists():
            raise SystemExit("No insight record at {}".format(path))
        fb = apply_feedback(path, args.rate, args.note, dry_run=args.dry_run)
        print("{}  rating={}  scenario_candidate={}".format(
            path.stem, fb["rating"], fb["promote_to_scenario"]))
        if args.dry_run:
            print("(dry run — nothing written)")
        return

    require("TELEGRAM_BOT_TOKEN")
    state = load_state()
    index = index_by_message_id()
    if not index:
        raise SystemExit("No sent insights found. Run send_insight.py first.")

    # offset = last seen + 1 acknowledges prior updates so they aren't re-served.
    res = api_call("getUpdates", {"offset": state["last_update_id"] + 1, "limit": 100})
    if not res.get("ok"):
        raise SystemExit("Telegram error: {}".format(res.get("description")))

    updates = res.get("result", [])

    # Persist raw updates BEFORE acknowledging any of them. Telegram deletes
    # acknowledged updates, so this write is what makes an unmatched reply
    # recoverable instead of gone.
    if updates and not args.dry_run:
        with RAW_LOG.open("a") as fh:
            for upd in updates:
                fh.write(json.dumps(upd) + "\n")

    matched, unmatched = 0, []
    for upd in updates:
        state["last_update_id"] = max(state["last_update_id"], upd["update_id"])
        msg = upd.get("message") or {}
        replied_to = (msg.get("reply_to_message") or {}).get("message_id")
        if not replied_to or replied_to not in index:
            unmatched.append((upd["update_id"], (msg.get("text") or "")[:70]))
            continue
        rating, note = parse_reply(msg.get("text", ""))
        path = index[replied_to]
        apply_feedback(path, rating, note, dry_run=args.dry_run)
        matched += 1
        print("{}  rating={}  note={}".format(
            path.stem, rating or "—", (note[:60] + "…") if len(note) > 60 else note))

    if not args.dry_run:
        save_state(state)

    print("\n{} update(s) fetched, {} matched a sent insight.".format(len(updates), matched))
    for update_id, text in unmatched:
        print("  unmatched update {}: {!r}".format(update_id, text))
    if unmatched:
        print("  (saved to {} — nothing lost; record it with --rate)".format(RAW_LOG.name))
        print("  Replies must be a true REPLY to the bot's insight message; a plain new"
              " message carries no reply_to_message and can't be linked.")


if __name__ == "__main__":
    main()
