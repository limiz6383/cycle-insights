#!/usr/bin/env python3
"""
Push a generated insight to Telegram, and record the message_id so replies
can be traced back to the insight they're rating.

That message_id is the whole feedback mechanism: you reply to the weekly
message, poll_feedback.py reads `reply_to_message.message_id`, and knows
which week's JSON record to write your rating into.

Setup (one time):
  1. Message @BotFather in Telegram, /newbot, copy the token
  2. Put TELEGRAM_BOT_TOKEN=... in <repo_root>/.env
  3. Send your new bot any message ("hi")
  4. python3 send_insight.py --discover-chat-id   → prints your chat id
  5. Put TELEGRAM_CHAT_ID=... in .env

Usage:
  python3 send_insight.py --discover-chat-id
  python3 send_insight.py                      # sends the most recent insight
  python3 send_insight.py --insight 2026-08-09 # sends a specific one
  python3 send_insight.py --dry-run
"""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import REPO_ROOT, get, require  # noqa: E402
import checkin  # noqa: E402

INSIGHTS_DIR = REPO_ROOT / "insights"
API = "https://api.telegram.org/bot{token}/{method}"
TELEGRAM_MAX = 4096


def api_call(method, params, token=None):
    token = token or require(
        "TELEGRAM_BOT_TOKEN", "Get one from @BotFather in Telegram (/newbot)."
    )
    url = API.format(token=token, method=method)
    data = urllib.parse.urlencode(params).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            return json.loads(body)
        except ValueError:
            raise SystemExit("Telegram HTTP {}: {}".format(e.code, body[:300]))


def discover_chat_id():
    """Print chat ids from recent updates so you can find yours."""
    res = api_call("getUpdates", {"limit": 20})
    if not res.get("ok"):
        raise SystemExit("Telegram error: {}".format(res.get("description")))
    seen = {}
    for upd in res.get("result", []):
        msg = upd.get("message") or upd.get("channel_post") or {}
        chat = msg.get("chat") or {}
        if chat.get("id"):
            who = chat.get("username") or chat.get("first_name") or chat.get("title") or "?"
            seen[chat["id"]] = who
    if not seen:
        raise SystemExit(
            "No messages found. Send your bot a message in Telegram first, then re-run.\n"
            "(If you set a webhook on this bot, getUpdates returns nothing — delete it.)"
        )
    print("Chat ids seen (add the right one to .env as TELEGRAM_CHAT_ID):")
    for cid, who in seen.items():
        print("  {}  ({})".format(cid, who))


def latest_insight():
    if not INSIGHTS_DIR.exists():
        raise SystemExit("No insights/ directory. Run generate_insight.py first.")
    files = sorted(INSIGHTS_DIR.glob("*.json"))
    if not files:
        raise SystemExit("No insight records in {}.".format(INSIGHTS_DIR))
    return files[-1]


def format_message(record):
    """
    Plain-ish text with the actionable test emphasized.

    The prompt emits '**Actionable test for this week:**' (OF1). Telegram's
    legacy Markdown uses single asterisks, so convert. If the body contains
    stray _ or [ the API rejects the parse — send_message falls back to plain.
    """
    body = record.get("insight_text", "").strip().replace("**", "*")
    header = "*Cycle insight — {}*".format(record.get("insight_id", "?"))
    footer = "_prompt {} · data {}_".format(
        record.get("prompt_version", "?"), record.get("data_range", "?")
    )
    prompt_back = (
        "Reply to this message to log feedback.\n"
        "Start with one of: useful / wrong / unsafe / obvious / not_actionable — "
        "then say what it got right or missed."
    )
    text = "{}\n\n{}\n\n{}\n\n{}".format(header, body, footer, prompt_back)
    if len(text) > TELEGRAM_MAX:
        text = text[: TELEGRAM_MAX - 20] + "\n…[truncated]"
    return text


def send_message(text, chat_id, dry_run=False, reply_markup=None):
    if dry_run:
        print("--- DRY RUN, would send to chat {} ---\n{}".format(chat_id, text))
        return None
    params = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        params["reply_markup"] = reply_markup
    res = api_call("sendMessage", params)
    if not res.get("ok"):
        # Almost always a Markdown parse error from an underscore or bracket
        # in the insight body. Resend as plain text rather than lose the week.
        print("[warn] Markdown send failed ({}); retrying as plain text.".format(
            res.get("description")), file=sys.stderr)
        params.pop("parse_mode")
        res = api_call("sendMessage", params)
        if not res.get("ok"):
            raise SystemExit("Telegram error: {}".format(res.get("description")))
    return res["result"]["message_id"]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--insight", default=None,
                    help="Insight id (e.g. 2026-08-09). Default: most recent.")
    ap.add_argument("--discover-chat-id", action="store_true",
                    help="Print chat ids from recent bot messages, then exit.")
    ap.add_argument("--dry-run", action="store_true", help="Print, don't send.")
    ap.add_argument("--no-checkin", action="store_true",
                    help="Send the insight now even if yesterday's steps are unconfirmed.")
    args = ap.parse_args()

    if args.discover_chat_id:
        discover_chat_id()
        return

    path = INSIGHTS_DIR / "{}.json".format(args.insight) if args.insight else latest_insight()
    if not path.exists():
        raise SystemExit("No insight record at {}".format(path))
    record = json.loads(path.read_text())

    chat_id = require("TELEGRAM_CHAT_ID",
                      "Run: python3 send_insight.py --discover-chat-id")
    send_or_checkin(path, chat_id, dry_run=args.dry_run, skip_checkin=args.no_checkin)


def deliver_insight(path, chat_id, dry_run=False):
    """Send the insight in `path` and store the Telegram linkage on its record."""
    record = json.loads(path.read_text())
    message_id = send_message(format_message(record), chat_id, dry_run=dry_run)
    if message_id is not None:
        # Linkage for poll_feedback.py / chat_bot.py — without this a reply can't be
        # traced back to the insight it rates.
        record["telegram"] = {"chat_id": str(chat_id), "message_id": message_id}
        record.pop("pending_send", None)
        path.write_text(json.dumps(record, indent=2))
        print("Sent {} (telegram message_id {}).".format(path.stem, message_id))
    return message_id


def send_or_checkin(path, chat_id, dry_run=False, skip_checkin=False):
    """
    Open the chat with a check-in on yesterday's steps when there is one; the insight is
    held (pending_send) until she answers in chat_bot.py. A still-held older insight is
    released first so nothing stays unsent for more than a day.
    """
    held = checkin.pending_release(INSIGHTS_DIR)
    if held and held[0] != path and not dry_run:
        deliver_insight(held[0], chat_id)
    waiting = None if skip_checkin else checkin.awaiting_checkin(INSIGHTS_DIR, path.stem)
    if not waiting:
        return deliver_insight(path, chat_id, dry_run=dry_run)
    prev_path, prev = waiting
    mid = send_message(checkin.checkin_text(prev), chat_id, dry_run=dry_run,
                       reply_markup=checkin.checkin_markup(prev_path.stem))
    if mid is not None and not dry_run:
        record = json.loads(path.read_text())
        record["pending_send"] = True
        path.write_text(json.dumps(record, indent=2))
        prev["checkin"] = {"message_id": mid}
        checkin.write(prev_path, prev)
        print("Sent check-in for {}; holding {} until you answer.".format(prev_path.stem, path.stem))
    return mid


if __name__ == "__main__":
    main()
