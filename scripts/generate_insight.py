#!/usr/bin/env python3
"""
Generate one cycle-recovery insight from YOUR real Oura data.

This is the product path — the thing that produces an insight you actually
read. `eval/run_eval.py` is the trust path: same prompt, synthetic adversarial
scenarios, pass/fail per rule. Both assemble the prompt via eval/prompt_lib.py.

Usage:
  python3 generate_insight.py --dry-run
  python3 generate_insight.py
  python3 generate_insight.py --context-file my_context.md --query "Should I add a run this week?"

  # Retrospective (backfill) — see --as-of note below
  python3 preprocess_oura.py --input oura_data.json --output /tmp/s.md \
      --as-of 2030-01-10 --period-dates 2030-01-03,2030-02-01
  python3 generate_insight.py --summary /tmp/s.md --as-of 2030-01-10

Writes two files per run into --out-dir:
  <date>.md    the insight, human-readable
  <date>.json  the insight plus metadata and EMPTY FEEDBACK FIELDS for you
               to fill in. Rated failures become eval scenarios later.

Requires: pip install anthropic, and ANTHROPIC_API_KEY (or `ant auth login`).
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "eval"))
import checkin  # noqa: E402
import self_check  # noqa: E402
from prompt_lib import (  # noqa: E402
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    call_claude,
    inject_user_data,
    load_prompt,
)

SCRIPTS_DIR = Path(__file__).resolve().parent


def read_optional(path, label):
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        sys.exit("{} file not found: {}".format(label, p))
    return p.read_text().strip()


def recent_insights(out_dir, label, n=7):
    """
    The last n insights already written to out_dir before `label`, newest first,
    so the model can avoid repeating itself. Only the insight text is passed on
    (the header lines are dropped). Missing folder or no files -> "".
    """
    d = Path(out_dir)
    if not d.is_dir():
        return ""
    files = sorted((f for f in d.glob("*.md") if f.stem < label), reverse=True)[:n]
    chunks = []
    for f in files:
        body = [ln for ln in f.read_text().splitlines()
                if ln.strip() and not ln.startswith("#") and not ln.startswith("_Prompt")]
        tag = ""
        jf = f.with_suffix(".json")
        if jf.exists():
            tag = checkin.followup_tag(json.loads(jf.read_text()))
        chunks.append("[{}] {}{}".format(f.stem, " ".join(body), tag))
    return "\n".join(chunks)


def self_review(text, system_prompt, oura_summary, label, args, user_turn):
    """
    Check the draft, ask a reviewer pass what is wrong, and revise with those notes, up to
    --judge-rounds times. Returns (text, log, held). held=True means a safety check still
    fails: the record is saved but marked so send_insight.py will not send it.
    """
    kb = self_check.kb_section(system_prompt)
    recent = recent_insights(args.out_dir, label)
    log = []
    for rnd in range(args.judge_rounds + 1):
        checks = self_check.hard_and_soft_checks(text, oura_summary, kb, recent, args.cadence)
        judged = None
        try:
            raw, _ = call_claude(self_check.JUDGE_SYSTEM, model=args.model, max_tokens=1200,
                                 user_turn=self_check.judge_prompt(text, oura_summary, kb, recent))
            judged = self_check.parse_judge(raw)
        except BaseException as e:               # a reviewer outage must not block the insight
            print("[warn] reviewer call failed: {}".format(e), file=sys.stderr)
        failed_checks = [c for c in checks if not c["passed"]]
        failed_judge = (judged or {}).get("failed", [])
        hard = [c for c in failed_checks if c["severity"] == "hard"] + \
               [{"id": k} for k in failed_judge if k in ("G1", "G4", "G5")]
        log.append({"round": rnd, "failed_checks": [c["id"] for c in failed_checks],
                    "failed_judge": failed_judge, "hard_failures": [h["id"] for h in hard],
                    "reviewed": judged is not None})
        print("[self-check round {}] failed checks: {}; reviewer: {}".format(
            rnd, [c["id"] for c in failed_checks] or "none",
            failed_judge if judged else "unavailable"), file=sys.stderr)
        if not failed_checks and not failed_judge:
            return text, log, False
        if rnd == args.judge_rounds:
            return text, log, bool(hard)
        notes = self_check.critique(checks, judged)
        text, _ = call_claude(
            system_prompt, model=args.model, max_tokens=args.max_tokens,
            user_turn=("{}\n\nYour previous draft:\n{}\n\nA reviewer found these problems:\n{}\n\n"
                       "Rewrite the insight so every problem is fixed, keeping the same rules. "
                       "Output only the corrected insight.").format(user_turn or "Generate the insight.",
                                                                    text, notes))
    return text, log, False


def summary_range(summary_text):
    """Pull the '_Generated from X to Y_' line so the record says what it saw."""
    for line in summary_text.splitlines():
        if line.startswith("_Generated from"):
            return line.strip("_ ").replace("Generated from ", "")
    return "unknown"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--summary", default=str(SCRIPTS_DIR / "oura_summary.md"),
                    help="Pre-processed Oura summary (default: scripts/oura_summary.md)")
    ap.add_argument("--context-file", default=None,
                    help="File with user-reported context: period dates, symptoms, "
                         "training changes, stress events, supplements.")
    ap.add_argument("--context", default="",
                    help="Inline user-reported context (overrides --context-file).")
    ap.add_argument("--query", default="",
                    help="Specific question. Empty = default weekly insight (UD3).")
    ap.add_argument("--cadence", choices=["daily", "weekly"], default="daily",
                    help="daily (default): short, today-focused, avoids repeating recent insights; "
                         "weekly: the longer one-pattern insight.")
    ap.add_argument("--prompt-version", default="v3.3", help="Label recorded in the run record; also picks prompts/<version>.md.")
    ap.add_argument("--prompt-file", default=None,
                    help="Read the system prompt from this file (default: prompts/<prompt-version>.md).")
    ap.add_argument("--no-judge", action="store_true",
                    help="Skip the self-check (checks + model reviewer + revision) before saving.")
    ap.add_argument("--judge-rounds", type=int, default=2,
                    help="Revise a draft that fails the self-check up to this many times (default 2).")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    ap.add_argument("--as-of", default=None,
                    help="Label this insight with a past date (backfill runs). Does NOT "
                         "slice the data — pass an --as-of summary from preprocess_oura.py.")
    ap.add_argument("--out-dir", default=str(SCRIPTS_DIR.parent / "insights"))
    ap.add_argument("--dry-run", action="store_true",
                    help="Assemble and preview the prompt; make no API call.")
    ap.add_argument("--no-write", action="store_true", help="Print only; write no files.")
    args = ap.parse_args()

    summary_path = Path(args.summary)
    if not summary_path.exists():
        sys.exit("Oura summary not found: {}\nRun preprocess_oura.py first.".format(summary_path))
    oura_summary = summary_path.read_text().strip()
    context = args.context.strip() or read_optional(args.context_file, "Context")

    label = args.as_of or date.today().isoformat()
    system_prompt = inject_user_data(
        load_prompt(args.prompt_version, args.prompt_file),
        oura_summary=oura_summary,
        user_reported_context=context,
        user_query=args.query,
        recent_insights=recent_insights(args.out_dir, label),
        cadence=args.cadence,
    )

    user_turn = ("Generate today's insight per <your_job>, <daily_rules> and <output_format>."
                 if args.cadence == "daily" else None)
    text, usage = call_claude(
        system_prompt, model=args.model, max_tokens=args.max_tokens, dry_run=args.dry_run,
        user_turn=user_turn,
    )

    judge_log, held = [], False
    if not (args.dry_run or args.no_judge):
        text, judge_log, held = self_review(text, system_prompt, oura_summary, label, args,
                                            user_turn)

    print("\n" + "=" * 78)
    print("INSIGHT — {}  (prompt {}, data {})".format(
        label, args.prompt_version, summary_range(oura_summary)))
    print("=" * 78 + "\n")
    print(text)
    print()
    if usage:
        print("[{} | in {} / out {} tokens | stop={}]".format(
            usage.get("model"), usage.get("input_tokens"),
            usage.get("output_tokens"), usage.get("stop_reason")))

    if args.dry_run or args.no_write:
        return

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "{}.md".format(label)).write_text(
        "# Cycle insight — {}\n\n"
        "_Prompt {} · data {} · model {}_\n\n{}\n".format(
            label, args.prompt_version, summary_range(oura_summary),
            usage.get("model", args.model), text)
    )

    # Feedback fields start empty ON PURPOSE. You fill them in after living with
    # the insight for a week. Anything you mark wrong/unsafe becomes an eval
    # scenario — that is how the harness gets grounded in real failures instead
    # of scenarios you invented while writing the prompt.
    record = {
        "insight_id": label,
        "generated_at": date.today().isoformat(),
        "as_of": args.as_of,
        "prompt_version": args.prompt_version,
        "cadence": args.cadence,
        "data_range": summary_range(oura_summary),
        "query": args.query,
        "user_reported_context": context,
        "insight_text": text,
        "self_check": judge_log,
        "held": held,
        "today_steps": checkin.extract_steps(text),
        "usage": usage,
        "feedback": {
            "rating": None,          # useful | wrong | unsafe | not_actionable | obvious
            "acted_on": None,        # true | false
            "what_was_wrong": "",
            "what_it_missed": "",
            "promote_to_scenario": False,
        },
    }
    (out_dir / "{}.json".format(label)).write_text(json.dumps(record, indent=2))
    print("\nWrote {}/{}.md and .json".format(out_dir, label))
    if held:
        print("HELD: a safety check still fails after {} revision(s); this insight will not be sent. "
              "Run again or look at the 'self_check' field in the .json.".format(args.judge_rounds))
    print("→ Fill in the `feedback` block after you've lived with it for a week.")


if __name__ == "__main__":
    main()
