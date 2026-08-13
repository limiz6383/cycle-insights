# Cycle Insights — Eval Harness

Automated structural eval for the v3.x system prompt. Replaces the manual within-distribution scoring done during Phase 0 with a programmatic version that can run on every prompt change.

## Structure

```
scripts/eval/
  scenarios/              # One YAML per scenario; oura_summary + context + expected behavior
    01_deep_ha.yaml
    02_early_recovery.yaml
    ...
    template.yaml         # Copy this when adding a new scenario
  rules/                  # Rule checkers
    deterministic.py      # Regex / string / count checks (OF1 word count, DG3 banned phrases, etc.)
    judge.py              # LLM-as-judge checks (CF firing, DG1 absence, NT2 hallucination detection)
  run_eval.py             # Main runner — loads scenarios, calls Claude, applies checkers, writes results
  results/                # JSON results per run, timestamped
    2026-06-01T1200_v3.2.json
    ...
  README.md
```

## Running the eval

```bash
# Single scenario
python3 run_eval.py --scenario 01_deep_ha --prompt-version v3.2

# All scenarios
python3 run_eval.py --all --prompt-version v3.2

# Compare two prompt versions
python3 run_eval.py --diff v3.1 v3.2
```

## Adding a new scenario

1. `cp scenarios/template.yaml scenarios/NN_short_name.yaml`
2. Fill in `oura_summary` (paste pre-processed Oura summary in markdown form — see `scripts/preprocess_oura.py` output for the shape)
3. Fill in `user_reported_context` (period dates, symptoms, prior diagnoses if any)
4. Fill in `user_query` (or leave empty for default weekly-insight behavior)
5. Fill in `expected_triggers` — which CFs, ETs, DGs, KBs *should* fire for this data shape
6. Fill in `banned_phrases` — specific phrases that would indicate a rule violation (e.g., from prior v2 failure modes)
7. Run `python3 run_eval.py --scenario NN_short_name`

## Why scenarios are YAML, not Python

Scenarios are *data*, not code. YAML lets you eyeball a scenario in 30 seconds without parsing logic. The runner is Python; scenarios are declarative.

## What this harness does NOT do (yet)

- Doesn't call the real Claude API in this skeleton — `call_claude()` is a placeholder. Wire it up in the first eval session by reading `ANTHROPIC_API_KEY` from env.
- Doesn't yet have all rule checkers implemented — only OF1 word count + DG3 banned phrases + KB citation presence are stubbed in `rules/deterministic.py`. The harder rules (CF firing, NT2 hallucination, DG1 absence) need `rules/judge.py` (LLM-as-judge) implementations.
- Doesn't have a diff view between prompt versions — `--diff` flag is reserved but unimplemented.

These are the next things to fill in. Each is a small concrete unit of work; don't try to do all at once.

## Known limits of this methodology (acknowledge in case study)

- LLM-as-judge can be sycophantic — Claude scoring Claude has a known bias. Mitigate by giving the judge an explicit anti-sycophancy instruction in its system prompt, AND by validating the judge against a small set of human-scored outputs first.
- Scenarios are written by the same person who wrote the prompt. Within-distribution risk persists until external scenarios are added (e.g., from real Oura users, if ever, or by deliberately adversarial scenario design).
- "Pass rate" is a structural compliance metric, not a clinical correctness metric. Clinical correctness requires a credentialed advisor cross-check.
