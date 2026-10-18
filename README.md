# Cycle Insights

A weekly cycle-recovery insight generated from Oura ring data, plus the adversarial eval harness that checks it obeys its own safety rules.

Built by its only user, for herself.

---

## The problem

Oura's Readiness score is built largely from resting heart rate, HRV, and temperature deviation. For most wearers that's fine. In women with low energy availability it inverts: metabolic suppression produces **low RHR and high HRV** — the exact signature Oura reads as excellent recovery ([Melin et al. 2019](https://pubmed.ncbi.nlm.nih.gov/30632422/)). The number that looks best is the one that should prompt concern.

Oura's own validation agrees. [Thigpen et al. 2025](https://pubmed.ncbi.nlm.nih.gov/39889300/) (JMIR) cautions that its ovulation detection was not validated for, and should be interpreted with caution in, PCOS and other luteal-phase-deficiency conditions — precisely the people most likely to be reading these numbers for answers.

Cycle-tracker apps don't fill the gap either: they predict from calendar history, so for irregular or absent cycles they degrade to guessing.

This reads the same data and reframes it against the endocrinology literature, in software, where the device's defaults can't.

## Why most of this repo is the eval harness

An LLM giving physiological guidance to someone with a restriction history can cause harm — by validating undereating as "good recovery," by naming a diagnosis it can't support, by suggesting restriction. The generating prompt is maybe a third of the work here. The rest checks that it follows its own rules.

| | Entry point | Produces |
|---|---|---|
| **Product** | `scripts/generate_insight.py` | One insight from real data |
| **Trust** | `scripts/eval/run_eval.py` | Per-rule pass/fail across adversarial scenarios |

Both assemble the prompt through `scripts/eval/prompt_lib.py`. That's deliberate: an eval that builds the prompt differently from production measures a system nobody runs.

## What's here

```
scripts/
  fetch_oura_data.py      Pull raw Oura data (incl. user-tagged period days)
  preprocess_oura.py      → the summary the prompt consumes; --as-of gives a
                            no-lookahead historical slice
  generate_insight.py     Product path: real data → one insight
  backfill.py             Retrospective weekly insights over historical data
  send_insight.py         Push to Telegram, record the message id
  poll_feedback.py        Replies (or --rate) → structured feedback records
  scheduled_pull.py       Unattended fetch + preprocess (optionally the weekly
                            insight), for launchd/cron
  config.py               .env loader, stdlib only
  eval/
    prompt_lib.py         Shared prompt assembly + API call
    run_eval.py           Scenario runner
    rules/deterministic.py  Word count, citation format, banned phrases
    rules/judge.py          LLM-as-judge: NT2b, CF1, DG8, escalation
    scenarios/            One JSON per scenario

scheduling/               launchd job template for scheduled_pull.py

research_notes.md         The curated literature behind the knowledge base
METHODOLOGY.md            Design, eval methodology, and limitations
```

## Quickstart

```bash
cp .env.example .env          # OURA_TOKEN, ANTHROPIC_API_KEY
python3 -m pip install --user anthropic

cd scripts
python3 fetch_oura_data.py --days 180
python3 preprocess_oura.py
python3 generate_insight.py
```

### Automatic pull

`scripts/scheduled_pull.py` does the fetch and preprocess steps unattended, so `oura_data.json` and `oura_summary.md` are always fresh. It only replaces the old dump when readiness and period tags both came back, so an expired token leaves yesterday's data in place. Logs go to `logs/scheduled_pull.log`.

It runs on your own machine, not GitHub Actions: this repo is public, so Actions logs would be too, and the generated insight is printed to stdout.

macOS (daily at 08:00; runs on wake if the Mac was asleep):

```bash
REPO="$(pwd)"; PY="$(command -v python3)"; mkdir -p logs
sed -e "s|__REPO__|$REPO|g" -e "s|__PYTHON__|$PY|g" \
    scheduling/com.cycleinsights.oura-pull.plist \
    > ~/Library/LaunchAgents/com.cycleinsights.oura-pull.plist
launchctl load ~/Library/LaunchAgents/com.cycleinsights.oura-pull.plist
launchctl start com.cycleinsights.oura-pull     # run once now to check
tail logs/scheduled_pull.log
```

Linux (cron): `0 8 * * * cd /path/to/cycle-insights/scripts && python3 scheduled_pull.py`

To automate the weekly insight as well, add a second job with `--weekly` (generates via the Anthropic API) or `--weekly --send` (also pushes to Telegram). Neither is scheduled by default.

The system prompt is published at [`prompts/v3.1.md`](prompts/v3.1.md) — all eleven blocks, with placeholders where runtime data is injected. Pass it with `--prompt-file`, or point that flag at your own.

Not published: the development log it was extracted from, and every generated insight. Both contain real biometric output.

## Status

Working end to end; **actively wrong in places, and documented as such.**

The most recent finding: for its first fourteen runs the pipeline never requested Oura's `enhanced_tag` endpoint, where user-logged period days live. With no bleed dates in the summary, the model treated an empty log as an empty uterus and reasoned to prolonged amenorrhea even though periods had been logged in the app. Every rule in the harness would have scored that output clean.

Two lessons, both in [METHODOLOGY.md](METHODOLOGY.md) §6: the highest-leverage fix was in the data layer rather than the prompt, and an eval that only measures rule-following will happily certify nonsense.

Other known gaps, stated in full in §6–7:

- The original 92% structural pass rate is **void** — self-authored scenarios, plus a harness bug that stripped four prompt rules before scoring. Don't cite it.
- 4 of 14 knowledge-base entries carry a machine-resolvable identifier, so the citation verifier can't yet protect the other 10.
- One rater, unblinded. The LLM judge is unvalidated against human labels.
- Structural compliance is not clinical correctness. No credentialed reviewer has been involved.

## Not medical advice

This is a personal tool built for one person. It does not diagnose, and it is designed to refuse to: where the data is consistent with both hypothalamic amenorrhea and lean PCOS — conditions that call for opposite interventions — it must name both and point at the workup that would distinguish them, never pick one. Twelve escalation triggers route to real clinical care rather than continuing to advise.

Nothing here has been reviewed by a clinician. Don't use it as though it has been.
