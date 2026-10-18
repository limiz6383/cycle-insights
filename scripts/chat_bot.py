#!/usr/bin/env python3
"""
Two-way Telegram chat on top of the same prompt, data and guardrails as the daily insight.

  python3 scripts/chat_bot.py              # run until stopped (Ctrl-C)
  python3 scripts/chat_bot.py --once       # handle what is waiting, then exit
  python3 scripts/chat_bot.py --dry-run    # print replies instead of sending/calling the model

What it does with each message from your chat (anything from another chat is ignored):
  - A reply to an insight that starts with a rating word (useful, wrong, unsafe, obvious,
    not_actionable) is stored as feedback on that insight, exactly as poll_feedback.py does.
  - A tap on a check-in button (or a typed answer while one is open) records whether you did
    yesterday's steps and then releases the insight that was held behind it.
  - /help lists these commands; /insight shows the latest insight.
  - Anything else is a question. It goes to the model with prompt v3.3 in "chat" cadence:
    your Oura summary (scripts/oura_summary.md, refreshed by scheduled_pull.py), the recent
    insights, and the last few turns of this conversation.

Only one program should read Telegram updates at a time. While this is running, do not run
poll_feedback.py; it shares the same update cursor and this script already handles feedback.

Privacy: the conversation is kept in .chat_history.jsonl and every raw update in
.telegram_raw.jsonl; both are gitignored. Nothing here is committed.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "eval"))
from config import REPO_ROOT, get, require  # noqa: E402
from send_insight import api_call, deliver_insight, send_message, TELEGRAM_MAX  # noqa: E402
import checkin  # noqa: E402
import poll_feedback as pf  # noqa: E402
from prompt_lib import DEFAULT_MODEL, call_claude, inject_user_data, load_prompt  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
HISTORY_PATH = REPO_ROOT / ".chat_history.jsonl"
HISTORY_TURNS = 12          # messages (both sides) passed back to the model
CHAT_MAX_TOKENS = 700
HELP = ("Ask me anything about your data, your cycle or what to try next. "
        "Reply to an insight with useful / wrong / unsafe / obvious / not_actionable "
        "and a note to rate it. /insight shows the latest insight.")


def load_history(path=None):
    path = path or HISTORY_PATH
    if not Path(path).exists():
        return []
    rows = []
    for line in Path(path).read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def append_history(role, text, path=None):
    path = path or HISTORY_PATH
    with Path(path).open("a") as fh:
        fh.write(json.dumps({"t": int(time.time()), "role": role, "text": text}) + "\n")


def format_conversation(rows, n=HISTORY_TURNS):
    return "\n".join("{}: {}".format("Her" if r["role"] == "user" else "You", r["text"])
                     for r in rows[-n:])


def recent_insight_text(n=3, insights_dir=None):
    d = Path(insights_dir or pf.INSIGHTS_DIR)
    if not d.is_dir():
        return ""
    out = []
    for f in sorted(d.glob("*.json"), reverse=True)[:n]:
        rec = json.loads(f.read_text())
        out.append("[{}] {}{}".format(rec.get("insight_id", f.stem), rec.get("insight_text", ""),
                                      checkin.followup_tag(rec)))
    return "\n".join(out)


def build_chat_prompt(question, history, summary_path, context="", prompt_version="v3.3",
                      insights_dir=None):
    summary = Path(summary_path).read_text().strip() if Path(summary_path).exists() else ""
    return inject_user_data(
        load_prompt(prompt_version),
        oura_summary=summary,
        user_reported_context=context,
        user_query=question,
        recent_insights=recent_insight_text(insights_dir=insights_dir),
        cadence="chat",
        conversation=format_conversation(history),
    )


def answer(question, history, args):
    """Ask the model. Returns the reply text; never raises into the polling loop."""
    system = build_chat_prompt(question, history, args.summary, prompt_version=args.prompt_version)
    try:
        text, _ = call_claude(system, model=args.model, max_tokens=CHAT_MAX_TOKENS,
                              dry_run=args.dry_run,
                              user_turn="Reply to her latest message per <chat_rules>.")
    except BaseException as e:  # SystemExit from a missing key as well
        print("[warn] model call failed: {}".format(e), file=sys.stderr)
        return "I couldn't reach the model just now. Please try again in a few minutes."
    return text.strip()[: TELEGRAM_MAX - 50]


def latest_insight_message():
    files = sorted(pf.INSIGHTS_DIR.glob("*.json")) if pf.INSIGHTS_DIR.exists() else []
    if not files:
        return "There is no insight yet."
    rec = json.loads(files[-1].read_text())
    return "[{}]\n{}".format(rec.get("insight_id"), rec.get("insight_text", ""))[: TELEGRAM_MAX - 50]


def resolve_checkin(prev_id, status, note, chat_id, args, insights_dir=None):
    """Store her answer on yesterday's record and release the insight held behind it."""
    d = Path(insights_dir or pf.INSIGHTS_DIR)
    prev = d / "{}.json".format(prev_id)
    if not prev.exists():
        return False
    if not args.dry_run:
        checkin.record_followup(prev, status, note)
    held = checkin.pending_release(d)
    if held:
        deliver_insight(held[0], chat_id, dry_run=args.dry_run)
    return True


def open_checkin(insights_dir=None):
    """The record whose check-in is open (insight held behind it), or None."""
    d = Path(insights_dir or pf.INSIGHTS_DIR)
    held = checkin.pending_release(d)
    if not held:
        return None
    waiting = checkin.awaiting_checkin(d, held[0].stem)
    return waiting[0] if waiting else None


def handle_callback(cb_query, allowed_chat_id, args):
    """A tap on a check-in button: callback_data is ci:<insight id>:<status>."""
    chat_id = str(((cb_query.get("message") or {}).get("chat") or {}).get("id", ""))
    data = cb_query.get("data") or ""
    if chat_id != str(allowed_chat_id) or not data.startswith("ci:"):
        return "ignored"
    _, prev_id, status = data.split(":", 2)
    if status not in ("all", "some", "none"):
        return "ignored"
    if not args.dry_run:
        api_call("answerCallbackQuery", {"callback_query_id": cb_query["id"], "text": "Noted"})
    return "checkin" if resolve_checkin(prev_id, status, "", chat_id, args) else "ignored"


def handle_message(msg, allowed_chat_id, args, index=None, reply=None):
    """
    Route one Telegram message. Returns a short tag ('ignored', 'feedback', 'command',
    'chat') so callers and tests can see what happened. `reply(text)` sends the response.
    """
    chat_id = str((msg.get("chat") or {}).get("id", ""))
    text = (msg.get("text") or "").strip()
    if chat_id != str(allowed_chat_id) or not text:
        return "ignored"
    reply = reply or (lambda t: send_message(t, chat_id, dry_run=args.dry_run))

    replied_to = (msg.get("reply_to_message") or {}).get("message_id")
    index = pf.index_by_message_id() if index is None else index
    if replied_to in index:
        rating, note = pf.parse_reply(text)
        if rating:
            pf.apply_feedback(index[replied_to], rating, note, dry_run=args.dry_run)
            reply("Noted: {}.".format(rating))
            return "feedback"

    if text.startswith("/"):
        cmd = text.split()[0].lower().split("@")[0]
        if cmd in ("/start", "/help"):
            reply(HELP)
        elif cmd == "/insight":
            reply(latest_insight_message())
        else:
            reply(HELP)
        return "command"

    waiting = open_checkin()
    if waiting is not None:                      # typed answer to the check-in
        status = checkin.classify(text)
        resolve_checkin(waiting.stem, status, text if status == "note" else "", chat_id, args)
        reply("Thanks, noted. Here is today's insight." if status != "note"
              else "Thanks, noted. Here is today's insight; ask me anything after it.")
        return "checkin"

    history = load_history()
    if not args.dry_run:
        append_history("user", text)
    out = answer(text, history, args)
    if not args.dry_run:
        append_history("assistant", out)
    reply(out)
    return "chat"


def poll_once(args, state, allowed_chat_id, timeout=25):
    res = api_call("getUpdates", {"offset": state["last_update_id"] + 1, "limit": 20,
                                  "timeout": timeout})
    if not res.get("ok"):
        raise SystemExit("Telegram error: {}".format(res.get("description")))
    updates = res.get("result", [])
    if updates and not args.dry_run:
        with pf.RAW_LOG.open("a") as fh:       # log before acknowledging, as poll_feedback does
            for u in updates:
                fh.write(json.dumps(u) + "\n")
    for u in updates:
        state["last_update_id"] = max(state["last_update_id"], u["update_id"])
        if u.get("callback_query"):
            print("[{}] update {}: {}".format(time.strftime("%H:%M:%S"), u["update_id"],
                                              handle_callback(u["callback_query"], allowed_chat_id, args)))
            if not args.dry_run:
                pf.save_state(state)
            continue
        msg = u.get("message")
        if not msg:
            continue
        if (msg.get("text") or "").strip() and str((msg.get("chat") or {}).get("id")) == str(allowed_chat_id):
            api_call("sendChatAction", {"chat_id": allowed_chat_id, "action": "typing"})
        tag = handle_message(msg, allowed_chat_id, args)
        print("[{}] update {}: {}".format(time.strftime("%H:%M:%S"), u["update_id"], tag))
        if not args.dry_run:
            pf.save_state(state)               # persist per update so a crash never replays a reply
    return len(updates)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--summary", default=str(SCRIPTS_DIR / "oura_summary.md"))
    ap.add_argument("--prompt-version", default="v3.3")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--once", action="store_true", help="Handle waiting messages and exit.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Do not call the model, send, or write state; print what would happen.")
    args = ap.parse_args()

    require("TELEGRAM_BOT_TOKEN")
    allowed = require("TELEGRAM_CHAT_ID", "Run: python3 send_insight.py --discover-chat-id")
    state = pf.load_state()
    print("Chat bot running. Ctrl-C to stop.")
    try:
        while True:
            try:
                poll_once(args, state, allowed, timeout=0 if args.once else 25)
            except (OSError, ValueError) as e:     # network blips: wait and keep going
                print("[warn] {}; retrying in 10s".format(e), file=sys.stderr)
                time.sleep(10)
            if args.once:
                break
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
