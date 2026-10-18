# Methodology

How this system is built, why it's built this way, and what it does not do.

---

## 1. The problem

Oura reports a daily **Readiness** score built largely from resting heart rate, heart-rate variability, and temperature deviation. For most wearers that framing is fine. For a specific population it is actively misleading.

In women with low energy availability — undereating relative to training load, whether deliberate or not — the body suppresses metabolic rate. That suppression produces **low resting heart rate and high HRV**, the same signature Oura reads as excellent recovery (Melin et al. 2019). The metric that looks best is the one that should prompt concern.

Two things compound it:

1. **Oura's own validation says so.** Thigpen et al. 2025 (JMIR, PMID 39889300) cautions that Oura's ovulation detection was not validated for, and should be interpreted with caution in, PCOS and other luteal-phase-deficiency conditions — precisely the population most likely to be looking at these numbers for answers.
2. **Cycle-tracker apps predict from calendar history.** For irregular or absent cycles there is no history to predict from, so they degrade to guessing.

This system reads the same Oura data and reframes it against the endocrinology literature, in software, where the device's defaults cannot.

**Scope:** built by its only user, for herself. Not a product, not a clinical tool, not offered to anyone else.

---

## 2. Why the eval harness is most of the work

An LLM giving physiological guidance to someone with a restriction history can do harm — by validating undereating as "good recovery," by naming a diagnosis it cannot support, by suggesting restriction. The generating prompt is maybe a third of this repository. The rest is the machinery that checks the prompt obeys its own rules.

Two artifacts, deliberately separate:

| | Path | Produces |
|---|---|---|
| **Product** | `generate_insight.py` | One weekly insight from real data |
| **Trust** | `eval/run_eval.py` | Per-rule pass/fail across adversarial scenarios |

Both assemble the prompt through the same module (`eval/prompt_lib.py`). This is load-bearing: an eval that builds the prompt differently from production measures a system nobody runs. That failure had already happened here once — see §6.

---

## 3. Prompt architecture

Eleven named blocks, each earning its place by preventing a specific observed failure:

| Block | Job |
|---|---|
| `role` | Frame and boundaries |
| `user_population` | Who the modeled reader is, and who they are not |
| `your_job` | One insight per run, highest-signal pattern only — not a report |
| `knowledge_base` | 14 curated literature entries (KB1–KB14) |
| `active_counter_framings` | 6 reframes (CF1–CF6) that flip default LLM intuitions |
| `diagnostic_guardrails` | 11 rules (DG1–DG11) bounding what may be claimed |
| `tone` | 10 rules (T1–T10), including banned vocabulary |
| `escalation_triggers` | 12 triggers (ET1–ET12) routing to real-world care |
| `numeric_threshold_rule` | 6 anti-hallucination rules (NT1–NT6) |
| `output_format` | 9 rules (OF1–OF9) on shape, length, citation |
| `user_data` | 4 rules (UD1–UD4): trust hierarchy, coverage, defaults |

**The counter-framings are the core.** CF1 exists because a general-purpose model shown high HRV and low RHR will congratulate the user. In this population that is the wrong reading, so the prompt names the counter-intuitive interpretation explicitly rather than hoping the model infers it.

**The trust hierarchy (UD1) is the second-order design.** User-reported context outranks Oura-derived events, because the ring cannot observe a bleed. Where they conflict, the human wins and the discrepancy is surfaced.

---

## 4. Safety decisions

The most consequential choices were subtractions.

**Lean PCOS was removed as a served population.** The system's guardrails and anti-restriction tone are built for hypothalamic amenorrhea, where the intervention is usually *more* energy availability. Lean PCOS often points the other way. From Oura data alone the two are not reliably separable — and a system that guesses wrong here does real harm. So DG8 forbids resolving the ambiguity: when the data is consistent with both, the output must name both and recommend the discriminating workup (AMH, free testosterone, DHEAS, pelvic ultrasound). Lean PCOS remains in the knowledge base for differential reasoning; it is not a population the system claims to serve.

**No body-composition engagement. No medication recommendations.** (DG4, T3.)

**Nutrition guidance: direction yes, numbers no.** The original design (DG3) fenced off eating entirely. That was over-broad for a single-user tool: the entire knowledge base is about energy availability, so a system forbidden from mentioning fuelling can diagnose a cause it is not allowed to name. The line has been moved to sit where the actual risk is — **behavioural and directional guidance is in scope** ("more carbohydrate around your hardest sessions", "you are under-fuelling relative to this training load"); **numeric targets remain out** (calories, grams, macros, weight). A direction is something to act on; a number is a target to be beaten, and in an ED-adjacent population that difference is the whole risk. Body composition and weight stay out entirely.

**Escalation is a first-class output.** Twelve triggers route to real care rather than continuing to advise: crisis language, acute medical symptoms, active ED behaviors, amenorrhea at 3 and 6 months, cycle-length variability, disclosed low BMI, FHA/PCOS ambiguity, fertility intent, prior labs, psychological stressors, supplements.

---

## 5. Evaluation design

**Deterministic checks first.** Word count, required bolded callout, inline KB citation, banned phrases, numeric density — anything a regex can settle is settled by a regex. Reserving the model for judgments that need one is both cheaper and more reliable.

**LLM-as-judge for semantics**, one rule per call, never compound. Four judges today: NT2b chain-hallucination, CF1 reframe firing, DG8 ambiguity handling, escalation firing. Each judge prompt carries an explicit anti-charity preamble, demands a binary verdict, and requires verbatim quotes as evidence — mitigations against the known leniency bias of a model grading a model. The judge should run on a different model family than the generator; self-preference bias is real and cross-family judging reduces it.

**Retrospective backfill with a hard data cutoff.** `preprocess_oura.py --as-of DATE` rebuilds the summary as it would have looked on that date, dropping later days **and later user-reported period dates**. Without that truncation a retrospective insight can see the cycle it is about to be judged against, and the exercise measures nothing. This is the same hindsight-stripping discipline that makes a backtest honest.

**Real failures become scenarios.** Each generated insight is rated by its user; anything rated wrong, unsafe, or not actionable is flagged as an eval scenario candidate. Scenarios grounded in observed failures beat scenarios invented while writing the prompt — which is exactly why the original eval was void.

---

## 6. Limitations

Stated plainly, because a rigor claim that hides its own holes is worth less than no claim.

**The original 92% pass rate was invalid, twice.** The scenarios were written by the same person who wrote the prompt, so they tested in-distribution by construction. Separately, the harness contained a bug that replaced the entire `<user_data>` block with a placeholder, stripping UD1–UD4 before scoring — so every run measured a prompt missing its own data-handling rules. Both are fixed; the number is not cited anywhere and should not be.

**One rater, unblinded.** Insights are rated by the person who built the system. That is a real bias and no amount of process removes it. Version comparisons are rated blind — both versions generated for the same week, labels stripped, shuffled — which controls part of it, not all.

**The judge is unvalidated until measured against human labels.** Agreement rate between judge verdicts and hand-scored outputs is the number that makes the rest meaningful. Until it exists, judge results are provisional.

**Structural compliance is not clinical correctness.** Every check here asks whether the output followed its rules. Whether the physiological reasoning is *right* requires a credentialed reviewer, and none has been involved.

**Known unfixed prompt findings.** An external review identified an NT2 chain-hallucination pattern (observation + citation composed into an unsourced significance claim), a prompt-injection vector in `<user_query>`, no anti-praise rule, and undefined behavior on out-of-distribution Oura data shapes. These are documented rather than hidden.

**Single-subject data.** Everything here is validated against one person's biometrics. Nothing generalizes without work that has not been done.

**Structural compliance says nothing about input validity — and this bit hard.** For its first fourteen runs the pipeline never requested Oura's `enhanced_tag` endpoint, where the user's own period tags live. With no bleed dates in the summary, the model treated an empty log as an empty uterus and reasoned to an 83-day amenorrhea — a claim carrying escalation triggers — for a user who had bled twice in that window. Every rule in the harness would have scored that output clean: it cited correctly, hedged correctly, handled the FHA/PCOS ambiguity correctly, and stayed in format. It was confidently, dangerously wrong about the one fact that mattered.

Two lessons, both structural. First, **the highest-leverage fix was in the data layer, not the prompt** — no amount of prompt engineering recovers from an input that omits the ground truth. Second, an eval that only measures rule-following will certify nonsense, so the harness needs input-validity checks (is the bleed log present? is its coverage plausible for the window?) alongside the output checks. A rule now exists for the narrower version of this: absence of a log must be reported as a coverage gap, never inferred as absence of the event.

---

## 7. Citation integrity

An audit of the knowledge base found **two fabricated citations** — plausible author/journal/year combinations for papers that do not exist — plus several paraphrases labeled as direct quotes. They were replaced with verified sources and the quote framing corrected.

This is the most useful thing in this repository. Retrieval grounding fails silently: a fabricated citation reads exactly like a real one, and the model will reason confidently from it. Verification has to be mechanical, because a human reading a citation list cannot tell the real ones from the invented ones.

**The control is not yet in place, but its prerequisite mostly is.** Of the 14 knowledge-base entries, **12 now carry PMIDs** for their cited sources (KB1–KB7, KB10–KB14). KB6 is a multi-source table: most of its sources have PMIDs, but O'Donnell 2015 (apparently a conference abstract) and Asarnow 2020 could not be found and are marked unverified inline. KB8 and KB9 are synthesized tables with no single source and are marked `[UNSOURCED]`; they cannot be machine-checked until each row is traced to a citation.

The backfill turned up two more citation errors, which is the argument for the verifier in miniature: the README's Melin 2019 link pointed to PMID 30753098, an unrelated atrial-fibrillation paper (the correct PMID is 30632422), and KB14 was attributed to "Zhang Y" when the paper's first author is Thigpen (Zhang is last author). The planned automated verifier — resolve every PMID against PubMed, fail the build on anything that doesn't return matching metadata — would have caught both. Until it exists, nothing prevents the next one.

---

## 8. Personalization layer (prompt v3.2, extended in v3.3)

**Problem.** The weekly insight read as generic: the summary gave 90-day means and four rolling windows, so the model could say "HRV is lower than your 30-day average" but not whether that is what her own luteal phases usually look like. A luteal HRV dip, a luteal sleeping-HR rise and a luteal temperature rise are all expected in regular cycles (KB15–KB19), so without phase context the model either missed them or mislabelled them as stress.

**Metric audit (what reaches the prompt).** From the Oura v2 endpoints this repo fetches, as of this change; endpoint and field names are from the API as I know it and were not re-checked against a live token:

| Used before | Fetched or available but dropped before | Now used | Still dropped |
|---|---|---|---|
| Readiness score, temperature deviation and trend; sleep score; steps, active calories, medium/high activity minutes; sleeping avg and lowest HR, avg HRV, sleep stage minutes, efficiency, breathing rate; high-stress and recovery seconds; period tags | SpO2 and breathing disturbance index; sleep latency, awake time, restless periods, bed/wake timing; sedentary time; readiness and sleep contributor sub-scores; resilience; cardiovascular age; stress day summary; the within-night HRV and HR series | SpO2 average, breathing disturbance index, sleep latency, awake time, restless periods, sleep midpoint, sedentary minutes | Contributor sub-scores, resilience, cardiovascular age, within-night series, non-period `enhanced_tag` tags (symptoms, mood, alcohol etc. if the user logs them), workouts, VO2 max |

**What was added.** `scripts/cycle_analysis.py` labels each day with cycle day and phase from the user's own period tags plus an estimated temperature shift (3 consecutive days at least 0.15 °C above the prior 6-day mean, which must persist; 0.15 °C is the criterion used in Maijala 2019, KB20, and is a detection setting here, not a clinical threshold). It then produces: the last 7 days against her own baseline and same-phase baseline in her own SDs, a per-cycle table (ovulation estimate, luteal length, luteal-minus-follicular change in temperature, HR, HRV, breathing rate, sleep efficiency), pooled phase means with how many cycles agree on direction, and a 28-day slope. No clinical threshold is introduced. `preprocess_oura.py` appends these sections; older-format summaries still work (PR0).

**Literature added (KB15–KB23).** Every entry was read from the paper's abstract or full text during this change; none comes from memory. The usable evidence is healthy-women cycle physiology: luteal rises in skin temperature (about 0.2–0.3 °C), sleeping HR (about 2–4 bpm) and a lower HRV (KB15–KB19), with HRV tied to progesterone within a person (KB19). The weaker parts are flagged in the entries: HRV phase effects are inconsistent across wearable studies (KB16), breathing rate is a weak cycle signal (KB16, KB23), sleep stages do not vary by phase (KB15), and a temperature shift does not prove ovulation (KB21). All studies enrolled regular cyclers, so phase effects are not norms for women with amenorrhea, FHA or PCOS (PR7).

**Gaps stated, not filled.**
- No verified source was found for an Oura-measurable marker of energy availability beyond the existing KB4/KB6 entries (moderate evidence, not Oura-specific). The prompt does not pretend otherwise.
- No verified wearable study of phase effects in anovulatory, HA or PCOS cycles was found. KB21 is the closest and it is Ava, not Oura.
- Several papers have company-affiliated authors (KB16, KB17, KB20, KB21), noted in the entries.
- Searching was limited to what could be fetched from the build environment; PubMed itself was blocked. Verification of KB15–KB23 comes from publisher and repository pages. PMIDs are given only where seen directly; the rest carry DOIs. `scripts/verify_citations.py` now checks that every entry has a PMID or DOI (offline, run in the tests); `--online` also resolves each one against PubMed and Crossref and compares first author and year. It has not been run online because the build environment is blocked, so run it once from a normal network. It checks that a paper exists and matches the citation, not that the entry paraphrases it correctly.

**Tests.** `tests/` holds a seeded synthetic Oura generator and unit tests: ovulation estimate near the injected day, injected luteal offsets recovered, an anovulatory series gets no shift, an injected HRV crash is flagged in SDs, the `--as-of` slice cannot see later days. No real data is used or stored. Run with `python3 -m unittest discover tests`.

**Not done.** The LLM was not run against this prompt in this change (no API key in the build environment), so insight quality, word range and the new rules are untested beyond `run_eval.py --all --dry-run` assembling the prompt. The eval scenarios still use the old summary format and exercise PR0 only; scenarios with the new sections should be added from real failures, per §5.

**Spotting and other events the API omits.** Oura's public API returned no record for spotting logged in the app (`enhanced_tag`, the older `tag` endpoint and `rest_mode_period` were all empty for a window that contained it; probe: `scripts/probe_oura_tags.py`), so it cannot be fetched. Put the dates in `scripts/user_cycle_log.json` (gitignored; format in `scripts/user_cycle_log.example.json`): `spotting` ranges are listed in the summary as user-reported ground truth and never counted as a cycle start, and `not_a_period` ranges drop tagged days that were not periods. `preprocess_oura.py` reads the file by default, so `scheduled_pull.py` and `backfill.py` pick it up with no extra flags; `--spotting` and `--not-a-period` still work and are merged with it.

**Daily cadence.** The insight is sent daily, and a long one-pattern essay repeated every morning is the failure mode. `generate_insight.py --cadence daily` (the default; `weekly` keeps the long form) changes four things: the summary gets a "Last 3 nights" table with per-night z-scores and a streak line, so one noisy night is not mistaken for a trend; the prompt's `daily_rules` (DC1–DC8) ask for 60–110 words about today, a quiet-day form that says "steady" instead of inventing a pattern, and a **Watch for:** line in place of the weekly test; `recent_insights` passes the last seven sent insights so the model does not repeat itself, and standing clinician flags are limited to once in 14 days unless something new appears; and KB tags appear only when a literature claim is made. `scheduled_pull.py --insight` generates daily (`--weekly` is kept as an alias for the weekly form). Untested against a live model; judge on the first few real days and tighten DC2 if repeats get through.

### 8.x Daily lenses and food ideas (prompt v3.3)

A daily message that only talks about cycle hormones gets stale, so v3.3 adds a `daily_lenses` block. Each day the model picks one lens that the last three nights make interesting: cycle-phase physiology, an alcohol-like night, sleep timing, sleep quality, an illness-like night, breathing and oxygen, stress and recovery, activity and fueling, or a sedentary day. The "Last 3 nights" table now carries every metric Oura detects that has a route to hormones or fueling (skin temperature, sleeping HR, HRV, breathing rate, sleep amount, timing, latency, efficiency, awake time, SpO2, high-stress and recovery time, active calories, high-activity and sedentary minutes).

Dietary content follows direction yes, numbers no (§4). DG3 now allows non-numeric food and lifestyle ideas, but only under rules FL1–FL6, and only ideas anchored in KB entries: eating enough and regularly (KB1, KB2), slightly higher luteal resting energy use (KB22), alcohol (KB24, a WHOOP study of about 21,000 adults), and caffeine timing (KB25, weak athlete evidence). I could not verify nutrition literature on other nutrients (iron, fibre, vitamin D, magnesium, carbohydrate type, blood-sugar effects), so the prompt makes no claims about them and refers questions to a clinician or dietitian. Adding those entries needs sources that have been read, not recalled.

### 8.y Detailed daily steps, chat, and unsourced tables (prompt v3.3)

- **Detailed, actionable daily insight.** DC8 now asks for 140–210 words: what the data shows, what the literature says (or that it is silent), a **Today:** list of two or three concrete steps tied to the observation, then **Watch for:**. Steps may name times of day; they may not carry amounts of food or exercise (DG3).
- **Chat.** `scripts/chat_bot.py` makes the Telegram bot two-way. A new `chat` cadence and `<chat_rules>` block (CH1–CH6) keep every guardrail on. The model sees her Oura summary, the recent insights and the last 12 turns, so a follow-up such as "so is that why?" has context. Messages from any chat other than `TELEGRAM_CHAT_ID` are ignored, and a rating-word reply to an insight is stored as feedback as before. Tests mock the model and Telegram; no real data is used.
- **KB8 and KB9 had no source** for several figures (LH:FSH failure rate, DHEAS percentage, estradiol and AMH cut-offs, treatment positions for PCOS). v3.3 removed the numbers and the unsourced treatment rows; the tables are now qualitative and the prompt tells the model never to quote a number from them. This removes claims rather than checking them, so if you want those figures back they need a source that has been read.

### 8.z Check-ins and follow-through (prompt v3.3)

Each daily insight stores its **Today:** steps. The next time `send_insight.py` runs, it opens the chat with a check-in ("did you get to yesterday's steps?") and three buttons, and holds the new insight until `chat_bot.py` gets an answer (button or typed). If she never answers, the next run releases the held insight first. The answer is stored on the earlier record.

The summary then gets a section, "Suggested actions and what your data did since", built from those records: for each action in the last 28 days, the metrics whose average since the action differs from the 7 days before it by at least 1 SD of her older data, with the cycle phase then and now. This is timing, not evidence of effect, and the prompt says so (DC10, CH8, DG6). It lets slow actions be revisited when a change shows up days or weeks later. Nothing is stored beyond the gitignored `insights/` records.

### 8.w Weekly and monthly summaries

`/weekly` and `/monthly` (also `/weekly_summary`, `/monthly-summary`) reply with a stats report from `scripts/period_report.py`: the last 7 or 30 days against the same number of days before, in original units and in SDs of the metric's older days, the cycle phases covered, sleep-timing regularity, and how many suggested steps she did. The report is computed from her data with no model call, so it cannot invent anything, and it flags when the cycle phase mix differs between the two periods because that alone can move several metrics.
