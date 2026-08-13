# Methodology

How this system is built, why it's built this way, and what it does not do.

---

## 1. The problem

Oura reports a daily **Readiness** score built largely from resting heart rate, heart-rate variability, and temperature deviation. For most wearers that framing is fine. For a specific population it is actively misleading.

In women with low energy availability — undereating relative to training load, whether deliberate or not — the body suppresses metabolic rate. That suppression produces **low resting heart rate and high HRV**, the same signature Oura reads as excellent recovery (Melin et al. 2019). The metric that looks best is the one that should prompt concern.

Two things compound it:

1. **Oura's own validation says so.** Zhang et al. 2025 (JMIR, PMID 39889300) reports that Oura's cycle and ovulation detection is unreliable in PCOS and luteal-phase-deficiency populations — precisely the population most likely to be looking at these numbers for answers.
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

**The control is not yet in place.** Of the 14 knowledge-base entries, **4 carry a machine-resolvable identifier** (KB5, KB12, KB13, KB14 — all PMIDs). The other 10 cite author, year, and journal in prose, which is enough for a human to look up and not enough for a script to check. So the planned automated verifier — resolve every PMID against PubMed, fail the build on anything that doesn't return matching metadata — currently cannot run against 10 of the 14 entries it exists to protect.

Backfilling identifiers for all 14 is a prerequisite, not a nice-to-have. Until that lands, the audit that caught the two fabrications was a one-time manual pass, and nothing prevents a third from being introduced by the next edit.
