# Cycle Insights — Eval Harness

Automated structural eval for the v3.x system prompt. Replaces the manual within-distribution scoring done during Phase 0 with a programmatic version that can run on every prompt change.

## Structure

```
scripts/eval/
  scenarios/              # One JSON per scenario; oura_summary + context + expected behavior
    01_deep_ha.json
    02_early_recovery_anovulatory.json
    ...
    template.json         # Copy this when adding a new scenario
  rules/                  # Rule checkers
    deterministic.py      # Regex / string / count checks (OF1 word count, OF2 citations and numbers, banned/required phrases)
    judge.py              # LLM-as-judge checks (NT2 hallucination chain, CF1 reframe, DG8 ambiguity, escalation firing)
  prompt_lib.py           # Shared prompt loading + assembly + API call (also used by generate_insight.py)
  run_eval.py             # Main runner — loads scenarios, calls Claude, applies checkers, writes results
  results/                # JSON results per run, timestamped (gitignored)
    2026-06-01T1200_v3.1.json
    ...
  README.md
```

## Running the eval

Run from `scripts/eval/`. The prompt is read from `prompts/<prompt-version>.md` at the repo root, so `prompts/v3.3.md` by default.

```bash
# Check the wiring without an API key: assembles the prompt, makes no API calls
python3 run_eval.py --scenario 01_deep_ha --dry-run

# Single scenario
python3 run_eval.py --scenario 01_deep_ha

# All scenarios, deterministic checks only (no judge calls)
python3 run_eval.py --all --skip-judge

# A prompt saved somewhere else
python3 run_eval.py --all --prompt-file ../../prompts/my_draft.md --prompt-version v3.2-draft
```

A real run needs `pip install anthropic` and `ANTHROPIC_API_KEY` (in the environment or the repo's `.env`). In `--dry-run` every check reports FAIL, because there is no generated output to score; that is expected.

`--prompt-file` takes either a bare prompt or a markdown file like `prompts/v3.3.md`, where the prompt is the first fenced code block. `--prompt-version` is the label written into the results filename.

## Adding a new scenario

1. `cp scenarios/template.json scenarios/NN_short_name.json`
2. Fill in `oura_summary` (paste pre-processed Oura summary in markdown form — see `scripts/preprocess_oura.py` output for the shape)
3. Fill in `user_reported_context` (period dates, symptoms, prior diagnoses if any)
4. Fill in `user_query` (or leave empty for default weekly-insight behavior)
5. Fill in `expected_triggers` — which CFs, ETs, DGs, KBs *should* fire for this data shape
6. Fill in `banned_phrases` — specific phrases that would indicate a rule violation (e.g., from prior v2 failure modes)
7. Run `python3 run_eval.py --scenario NN_short_name`

## Why scenarios are JSON, not Python

Scenarios are *data*, not code. JSON lets you eyeball a scenario in 30 seconds without parsing logic, and loads with the standard library alone. The runner is Python; scenarios are declarative.

## What this harness does NOT do (yet)

- Doesn't cover every rule in the prompt. `rules/deterministic.py` and `rules/judge.py` check only the rules listed above (DG1 is covered indirectly, inside the DG8 ambiguity check).
- Doesn't have a diff view between prompt versions. Compare two results files by hand for now.

These are the next things to fill in. Each is a small concrete unit of work; don't try to do all at once.

## Known limits of this methodology (acknowledge in case study)

- LLM-as-judge can be sycophantic — Claude scoring Claude has a known bias. Mitigate by giving the judge an explicit anti-sycophancy instruction in its system prompt, AND by validating the judge against a small set of human-scored outputs first.
- Scenarios are written by the same person who wrote the prompt. Within-distribution risk persists until external scenarios are added (e.g., from real Oura users, if ever, or by deliberately adversarial scenario design).
- "Pass rate" is a structural compliance metric, not a clinical correctness metric. Clinical correctness requires a credentialed advisor cross-check.
