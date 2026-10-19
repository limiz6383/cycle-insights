#!/usr/bin/env python3
"""
Cycle Insights eval harness — main runner.

Usage:
  python3 run_eval.py --scenario 01_deep_ha --prompt-version v3.3
  python3 run_eval.py --all --prompt-version v3.3
  python3 run_eval.py --scenario 01_deep_ha --dry-run    # don't call API; print prompt only

Requires:
  pip install anthropic    (optional for --dry-run mode)
  ANTHROPIC_API_KEY env var (unless --dry-run)

Scenarios are JSON files in scenarios/ — stdlib only, no extra deps.

The prompt is read from prompts/<prompt-version>.md (prompts/v3.3.md by
default). Override with --prompt-file to test a prompt saved elsewhere.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from prompt_lib import DEFAULT_MAX_TOKENS, DEFAULT_MODEL
from prompt_lib import call_claude as _call_claude
from prompt_lib import inject_user_data, load_prompt
from rules.deterministic import run_deterministic_checks
from rules.judge import run_judge_checks

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = Path(__file__).parent / "scenarios"
RESULTS_DIR = Path(__file__).parent / "results"


def load_scenario(scenario_id: str) -> dict:
    path = SCENARIOS_DIR / f"{scenario_id}.json"
    if not path.exists():
        sys.exit(f"Scenario not found: {path}")
    with open(path) as f:
        return json.load(f)


def load_all_scenarios() -> list:
    paths = sorted(SCENARIOS_DIR.glob("*.json"))
    scenarios = []
    for p in paths:
        if p.name == "template.json":
            continue
        with open(p) as f:
            scenarios.append(json.load(f))
    return scenarios


def load_system_prompt(prompt_version: str = "v3.3", prompt_file: str = None) -> str:
    """Delegates to prompt_lib so the eval loads the same prompt production does."""
    return load_prompt(prompt_version, prompt_file)


def inject_scenario_into_prompt(system_prompt: str, scenario: dict) -> str:
    """
    Fill the three runtime placeholders inside <user_data> with scenario data.

    FIXED: the previous version replaced the whole <user_data> block with a
    one-line sentinel, which silently deleted UD1-UD4 (trust hierarchy,
    coverage/sparsity thresholds, empty-query default, out-of-scope handling).
    Every run before this fix scored a prompt missing its own data rules, so
    any pass rate measured with it is void. Re-baseline from scratch.
    """
    return inject_user_data(
        system_prompt,
        oura_summary=scenario.get("oura_summary", ""),
        user_reported_context=scenario.get("user_reported_context", ""),
        user_query=scenario.get("user_query", ""),
    )


def call_claude(system_prompt: str, dry_run: bool = False) -> str:
    """
    Call Claude API with the assembled prompt. Returns generated text.
    In --dry-run mode, prints the assembled prompt and returns a placeholder.
    """
    text, _usage = _call_claude(
        system_prompt,
        model=DEFAULT_MODEL,
        max_tokens=DEFAULT_MAX_TOKENS,
        dry_run=dry_run,
    )
    return text


def evaluate_scenario(scenario: dict, prompt_version: str, dry_run: bool = False,
                       skip_judge: bool = False, prompt_file: str = None) -> dict:
    """Run one scenario through the prompt + apply deterministic and judge checks."""
    system_prompt_raw = load_system_prompt(prompt_version, prompt_file)
    system_prompt = inject_scenario_into_prompt(system_prompt_raw, scenario)
    output_text = call_claude(system_prompt, dry_run=dry_run)

    deterministic_results = run_deterministic_checks(output_text, scenario)
    deterministic_passed = all(r["passed"] for r in deterministic_results)

    if skip_judge:
        judge_results = []
        judge_passed = None
    else:
        judge_results = run_judge_checks(output_text, scenario, dry_run=dry_run)
        judge_passed = all(r["passed"] for r in judge_results)

    return {
        "scenario_id": scenario["id"],
        "scenario_title": scenario["title"],
        "prompt_version": prompt_version,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "output": output_text,
        "deterministic_checks": deterministic_results,
        "deterministic_passed": deterministic_passed,
        "judge_checks": judge_results,
        "judge_passed": judge_passed,
        "expected_triggers": scenario.get("expected_triggers", {}),
        "notes": scenario.get("notes", ""),
    }


def write_results(results: list, prompt_version: str) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H%M")
    fname = f"{ts}_{prompt_version}.json"
    path = RESULTS_DIR / fname
    with open(path, "w") as f:
        json.dump(
            {
                "prompt_version": prompt_version,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "n_scenarios": len(results),
                "results": results,
            },
            f,
            indent=2,
        )
    return path


def summarize(results: list) -> None:
    print("\n" + "=" * 80)
    print(f"Eval summary — {len(results)} scenario(s)")
    print("=" * 80)
    for r in results:
        det_status = "PASS" if r["deterministic_passed"] else "FAIL"
        if r.get("judge_passed") is None:
            judge_status = "—"
        elif r["judge_passed"]:
            judge_status = "PASS"
        else:
            judge_status = "FAIL"
        print(f"  det:[{det_status}]  judge:[{judge_status}]  {r['scenario_id']} — {r['scenario_title']}")
        if not r["deterministic_passed"]:
            for check in r["deterministic_checks"]:
                if not check["passed"]:
                    print(f"      ✗ {check['rule']}: {check.get('detail', '')}")
        if r.get("judge_passed") is False:
            for check in r["judge_checks"]:
                if not check["passed"]:
                    print(f"      ✗ {check['rule']}: {check.get('detail', '')[:160]}")
    det_pass_n = sum(1 for r in results if r["deterministic_passed"])
    judge_pass_n = sum(1 for r in results if r.get("judge_passed"))
    judge_total = sum(1 for r in results if r.get("judge_passed") is not None)
    print(f"\nDeterministic pass rate: {det_pass_n}/{len(results)}")
    if judge_total:
        print(f"Judge pass rate: {judge_pass_n}/{judge_total}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario", help="Scenario ID to run (e.g., 01_deep_ha)")
    ap.add_argument("--all", action="store_true", help="Run all scenarios")
    ap.add_argument("--prompt-version", default="v3.3", help="Prompt version label (for results filename); also picks prompts/<version>.md")
    ap.add_argument("--prompt-file", default=None,
                    help="Read the system prompt from this file (default: prompts/<prompt-version>.md)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Don't call Claude API; print assembled prompt and skip generation")
    ap.add_argument("--skip-judge", action="store_true",
                    help="Skip LLM-as-judge checks (deterministic only — cheaper, faster)")
    args = ap.parse_args()

    if args.scenario:
        scenarios = [load_scenario(args.scenario)]
    elif args.all:
        scenarios = load_all_scenarios()
    else:
        ap.error("Specify --scenario <id> or --all")

    results = []
    for sc in scenarios:
        print(f"Running scenario: {sc['id']}")
        r = evaluate_scenario(sc, args.prompt_version, dry_run=args.dry_run,
                              skip_judge=args.skip_judge, prompt_file=args.prompt_file)
        results.append(r)

    if not args.dry_run:
        path = write_results(results, args.prompt_version)
        print(f"\nResults written to {path}")
    summarize(results)


if __name__ == "__main__":
    main()
