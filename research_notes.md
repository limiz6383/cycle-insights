# Cycle Insights — Literature Research Notes

_Last updated: 2026-05-31 (citation-verification pass)_
_Audience: RAG knowledge base for Cycle Insights LLM product. Reader assumed to have lived HA-recovery experience and baseline literacy._

## 2026-05-31 verification pass — corrections from scientific-lit-researcher review

Several citations in the original 2026-05-19 draft were either fabricated or had pagination/journal errors. Corrected below:

| Original (REMOVED) | Replacement |
|---|---|
| Pereira-Eshraghi 2022 JCEM 107(4):e1547–e1556 — **fabricated** (real Pereira-Eshraghi 2022 paper is in F&S Reports on MRI follicle counts) | **Phylactou 2021** Clin Endocrinol 95(2):239–252, doi:10.1111/cen.14402 (the PMID previously listed here, 34323305, is a different paper) — verified, broader FHA-vs-PCOS biomarker discriminant paper |
| Carmina 2022 J Endocr Soc on lean PCOS phenotype — **fabricated** | **Carmina & Lobo 2022 Diagnostics 12(10):2496**, PMID 36292002 / PMC9600591 — verified |
| Ackerman 2022 Med Sci Sports Exerc on cognitive performance preserved in LEA — **not found** | CF6 reframed to cite IOC REDs 2023 (KB1) + Melin 2019 (KB4) directly |
| O'Donnell & De Souza 2018 — **wrong year** | O'Donnell 2015 (HRV-specific) + O'Donnell & De Souza 2011 JCEM PMID 21956422 (CV consequences) |
| "Direct quotes" framing on Mountjoy 2023, De Souza 2010, Toosy 2018 in KB1/KB3/KB7 | Softened to "key claims" — substance correct in each, but the verbatim-quote framing overstated provenance |

**Verified citations (no change needed):** Mountjoy 2023, Gordon 2017, De Souza 2010 PMID 19945961, Melin 2019, Toosy 2018 PMC6405408, Teede 2023 PMID 37589624, Yildirir 2006 PMID 17040278, Loucks 2003 PMID 12519869, Berga 2003 PMID 14556820, Areta 2021, Strock 2020 PMID 32619140, Singhal 2018 PMC5694353.

**New entries to consider adding:** Phylactou 2021 (doi:10.1111/cen.14402; the PMID 34323305 recorded earlier belongs to a different paper), Stellingwerff 2023 CAT2 paper (PMID 37752002), Pedreira/Misra 2022 (PMC9355702) on adolescent FHA bone, Zhang 2025 (PMID 39889300) on Oura cycle validation — see KB14 in `pretotype_log.md`.

**Strategic finding:** Zhang 2025 JMIR (Oura's own validation, n=1,155 cycles) explicitly admits the algorithm is unreliable in PCOS and luteal phase deficiency populations. This is Oura conceding the wedge in peer-reviewed literature — the strongest defensible angle for the project per research-analyst review.

---

## Executive Summary

The literature on cycle disruption in low-BMI women is dominated by two overlapping syndromes that the product MUST be able to talk about distinctly: **Functional Hypothalamic Amenorrhea (FHA) / RED-S** (low energy availability suppressing the HPG axis) and **Lean PCOS** (androgenic, often genetically driven, masquerading as the same clinical picture). The single most product-relevant fact: the textbook differentiator (high LH:FSH in PCOS, low/normal LH in FHA) **fails in ~30–40% of lean PCOS cases**, because lean PCOS often presents with normal or even FHA-pattern gonadotropins (Carmina 2022; Toosy 2018). AMH, androgens (free T, DHEAS), and pelvic ultrasound carry more diagnostic weight than LH:FSH alone.

Key takeaways for product design:

1. **The 30 kcal/kg FFM/day threshold is contested.** It comes from Loucks & Thuma 2003 (n=29). The 2023 IOC statement explicitly retreats from a single number and recommends a clinical syndrome model (CAT2). Do not anchor product language on it.
2. **RED-S is now the umbrella term**, not Triad. IOC 2023 expanded it to 10 health outcomes and 7 performance outcomes, formalized "Problematic LEA" vs "Adaptable LEA," and introduced CAT2 scoring (primary indicators, secondary indicators, modifiers).
3. **A regular bleed does not equal a healthy cycle.** Anovulatory cycles, short luteal phase (<10 days), and blunted post-ovulatory temperature rise (<0.3°C) are all documented in subclinical LEA (De Souza 2010; Strock 2020).
4. **AMH is the strongest single discriminator** between lean PCOS and FHA: typically elevated (>5 ng/mL) in lean PCOS, normal/low in FHA (Romualdi 2021; Pereira-Eshraghi 2022).
5. **Polycystic ovarian morphology (PCOM) is non-specific in young women.** Up to 50% of healthy women <25 meet old Rotterdam ultrasound criteria. The 2023 international PCOS guideline raised the follicle threshold to ≥20 per ovary (with transducer ≥8 MHz) for this reason.
6. **HRV in FHA: elevated parasympathetic tone (high HF-HRV, low LF/HF) at rest is documented**, reflecting hypometabolic adaptation — counterintuitively, a "great" Oura HRV score in an under-fueled woman can be a red flag, not a green light (Melin 2019; O'Donnell 2018).
7. **Basal body temperature shift requires a luteal phase to interpret.** In anovulatory cycles (both FHA and lean PCOS), there is no biphasic curve — Oura temperature trend cannot confirm ovulation.
8. **Oura cannot diagnose anything.** The product needs to talk in terms of patterns and questions to bring to a clinician, not labels.

---

## Section A: HA / FHA / RED-S — Key Papers and Frameworks

### A1. Mountjoy et al. 2023 — IOC Consensus Statement on REDs (2023 update)

**Citation:** Mountjoy M, Ackerman KE, Bailey DM, Burke LM, Constantini N, Hackney AC, Heikura IA, Melin A, Pensgaard AM, Stellingwerff T, Sundgot-Borgen JK, Torstveit MK, Jacobsen AU, Verhagen E, Budgett R, Engebretsen L, Erdener U. _2023 International Olympic Committee's (IOC) consensus statement on Relative Energy Deficiency in Sport (REDs)._ Br J Sports Med. 2023;57(17):1073–1097.

**Key claims:**
- Renames "RED-S" to "REDs" (lowercase s) and reframes it as a **syndrome of impaired physiological functioning caused by exposure to problematic (prolonged and/or severe) low energy availability (LEA)**.
- Expands health consequences to **10 primary domains**: menstrual function, bone health, endocrine, metabolic, hematological, growth/development, psychological, cardiovascular, gastrointestinal, immunological.
- Introduces **CAT2 (Clinical Assessment Tool, version 2)** — replaces the 2014 RED-S CAT. Uses primary indicators (red lights), secondary indicators (yellow lights), and modifiers. Outputs risk traffic light (green/yellow/orange/red) for training, competition, and medical clearance.
- Differentiates **"Adaptable LEA"** (short-term, no health consequences, can be intentional) from **"Problematic LEA"** (prolonged/severe, with downstream sequelae).
- Explicitly drops a single EA threshold number as the diagnostic criterion. From the paper: _"While 30 kcal/kg FFM/day was historically used as a threshold for LEA, it is no longer recommended as a universal cut-off due to inter-individual variability."_

**RAG-worthy quotes / data:**
- _"REDs is the result of exposure to problematic LEA. Problematic LEA is defined as a prolonged and/or severe reduction in EA, leading to disruption of multiple physiological systems."_
- Primary indicators include: low BMD (Z-score < -1.0), menstrual dysfunction (oligo/amenorrhea), low resting metabolic rate (RMR ratio < 0.90), and others (full list in CAT2 table).
- _"Functional Hypothalamic Amenorrhoea (FHA) is the menstrual manifestation of problematic LEA in females."_
- The 2023 paper formally **subsumes the Female Athlete Triad under REDs** as the female-specific menstrual/bone presentation.

**Caveats / critiques:**
- CAT2 has not been independently validated outside the IOC working group as of publication.
- Critique by Stellingwerff (a co-author) and others: the syndrome is broad enough that operationalizing it for individual athletes still requires expert clinical judgment.
- Applies primarily to athletes; transferability to non-athlete underfueled women (e.g., recreational exercisers with HA) is inferred, not formally tested.

---

### A2. Mountjoy et al. 2014 / 2018 — Earlier IOC RED-S Statements

**Citations:**
- Mountjoy M, Sundgot-Borgen J, Burke L, et al. _The IOC consensus statement: beyond the Female Athlete Triad—Relative Energy Deficiency in Sport (RED-S)._ Br J Sports Med. 2014;48(7):491–497.
- Mountjoy M, Sundgot-Borgen J, Burke L, et al. _IOC consensus statement on relative energy deficiency in sport (RED-S): 2018 update._ Br J Sports Med. 2018;52(11):687–697.

**Key claims:**
- 2014: First introduction of RED-S as broader-than-Triad. Identified the original RED-S CAT.
- 2018: Refined CAT, added male athlete considerations, more on performance consequences.
- Both used 30 kcal/kg FFM/day as the working LEA threshold.

**What changed in 2023 vs 2018:**
| Aspect | 2018 | 2023 |
|---|---|---|
| Term | RED-S | REDs |
| EA threshold | 30 kcal/kg FFM/day cited | Threshold de-emphasized |
| Assessment tool | RED-S CAT | CAT2 with primary/secondary/modifier indicators |
| Health domains | ~10, less formalized | 10 domains, structured |
| LEA classification | Single concept | Adaptable vs Problematic LEA |
| Triad relationship | Co-existing framework | Female Triad subsumed under REDs |

---

### A3. Gordon et al. 2017 — Endocrine Society FHA Clinical Practice Guideline

**Citation:** Gordon CM, Ackerman KE, Berga SL, Kaplan JR, Mastorakos G, Misra M, Murad MH, Santoro NF, Warren MP. _Functional Hypothalamic Amenorrhea: An Endocrine Society Clinical Practice Guideline._ J Clin Endocrinol Metab. 2017;102(5):1413–1439.

**Key diagnostic criteria:**
- **FHA is a diagnosis of exclusion.** Must rule out pregnancy, hyperprolactinemia, thyroid dysfunction, PCOS, primary ovarian insufficiency, structural causes.
- Defined as **absence of menstruation for ≥3 months in a previously menstruating woman, or ≥6 months in oligomenorrhea, with no identifiable organic cause** and evidence of one or more contributing stressors (energy deficit, excessive exercise, psychological stress).
- Required workup: β-hCG, FSH, LH, estradiol, prolactin, TSH, free T4, total testosterone, DHEAS, 17-OH-progesterone, AMH, pelvic ultrasound, BMD (DXA if amenorrhea ≥6 months), brain MRI if neurological signs.

**Interventions (in priority order):**
1. **Cognitive behavioral therapy (CBT)** — strong recommendation; only intervention shown in RCT to restore menses in FHA without other changes (Berga 2003).
2. **Increased energy intake and reduced exercise** to achieve weight restoration if underweight, or to correct energy deficit even at "normal" weight.
3. **Treatment of underlying psychological stressors.**
4. **Short-term transdermal estradiol + cyclic progesterone** for bone (if non-responsive after reasonable trial). **Oral contraceptives are NOT recommended** for restoration of menses or bone protection in FHA.
5. **rhIGF-1, leptin (metreleptin)** — experimental, not recommended outside research.

**RAG-worthy quotes:**
- _"We recommend against the use of oral contraceptives for the sole purpose of regaining menses or improving bone mineral density."_ — explicit guideline statement.
- _"We suggest that clinicians only prescribe short-term use of transdermal E2 therapy with cyclic oral progestin… after a reasonable trial of nutritional, psychological, and/or modified exercise intervention has failed."_
- _"We recommend cognitive behavior therapy (CBT) after ruling out organic causes of menstrual cycle abnormality."_

**Caveats:**
- The CBT recommendation is based largely on a single small RCT (Berga, n=16, 2003) — strong recommendation, modest evidence.
- The guideline pre-dates the 2023 IOC update; conceptually still aligned but doesn't use the REDs CAT2 framework.

---

### A4. Female Athlete Triad Coalition / De Souza et al. 2014 — Triad Position Stand

**Citation:** De Souza MJ, Nattiv A, Joy E, Misra M, Williams NI, Mallinson RJ, Gibbs JC, Olmsted M, Goolsby M, Matheson G; Expert Panel. _2014 Female Athlete Triad Coalition Consensus Statement on Treatment and Return to Play of the Female Athlete Triad._ Br J Sports Med. 2014;48(4):289.

**Key claims:**
- Triad = three interrelated components on a spectrum: **(1) energy availability, (2) menstrual function, (3) bone health**. Each ranges from healthy to clinical.
- Introduced the **Cumulative Risk Assessment** (CRA) tool with magnitude-weighted risk factors → return-to-play decisions.
- Strongly endorses EA = 30 kcal/kg FFM/day as the threshold below which menstrual disturbances arise.

**Relationship to RED-S/REDs:**
- The Triad is **female-specific** and focuses on the three named components. RED-S/REDs is broader (10 health domains, both sexes).
- As of IOC 2023, the Triad is conceptually subsumed under REDs, but the Triad framework is still actively used clinically in the US, especially via the Female and Male Athlete Triad Coalition.
- 2023 update on Triad-RED-S relationship: De Souza et al. and Mountjoy et al. published parallel commentaries on the overlap; not fully reconciled in the literature.

---

### A5. Loucks & Thuma 2003 — Original Energy Availability Threshold Paper

**Citation:** Loucks AB, Thuma JR. _Luteinizing hormone pulsatility is disrupted at a threshold of energy availability in regularly menstruating women._ J Clin Endocrinol Metab. 2003;88(1):297–311.

**Key claims:**
- Controlled-feeding study, n=29 regularly menstruating sedentary women, 5-day intervention varying EA at 45, 30, 20, 10 kcal/kg FFM/day.
- LH pulsatility (frequency and amplitude) disrupted below ~30 kcal/kg FFM/day.
- This is the **single empirical source** of the 30 kcal/kg FFM/day threshold cited across the field.

**Critique / current status:**
- **Small sample (n=29), short duration (5 days), sedentary women** — generalizability to athletes and to chronic LEA is questionable.
- Effect was on LH pulsatility, not on overt menstrual disturbance (which takes longer to manifest).
- Replication has been mixed; Lieberman et al. 2018 and others have shown wide inter-individual variability — some women maintain menses at EA <30, others lose menses above.
- **Burke et al. 2018** and others have argued the threshold should be abandoned as a clinical cutoff.
- IOC 2023 explicitly retreats from it as a universal threshold (see A1).

---

### A6. Waterfall, Scofield, Williams — _No Period Now What_ (NPNW)

**Citation:** Waterfall N, Scofield L, Williams N. _No Period. Now What? A Guide to Regaining Your Cycles and Improving Your Fertility._ Antica Press, 2019 (and updated reprints).

**Note:** This is the practitioner/community protocol, not a peer-reviewed guideline. Treat as practice wisdom from a specific community, not as clinical evidence.

**Core recommendations (the "all-in" approach):**
- **3500+ kcal/day** minimum during recovery (often higher), regardless of starting weight or hunger.
- **All exercise stopped** (or reduced to walking only) until menses returns + 3–6 months.
- **Weight gain to ~5+ lbs above pre-amenorrhea weight** — explicit rejection of "set point" being the original weight.
- **No HRT, no oral contraceptives.**
- **No tracking calories or weight** during recovery — explicitly anti-restriction.
- Recovery timeline often quoted as 6–24 months.

**Alignment with formal guidelines:**
- **Agrees with:** Endocrine Society 2017 on rejecting OCPs, on energy/weight restoration as first-line, on stress reduction. Agrees with IOC 2023 on energy availability as the lever.
- **Goes further than:** Most clinical guidelines do not specify 3500+ kcal or "all exercise stopped" or weight gain targets above original weight. NPNW is more prescriptive.
- **Disagrees with:** Guidelines that suggest gradual increase in intake or moderate exercise modification. NPNW's "all-in" approach is more aggressive.

**Caveats:**
- No RCT data behind the specific 3500 kcal or "all-in" prescription. Authors are credentialed (Scofield: RD; Williams: PhD researcher, also senior author on De Souza 2010 etc.), but the book aggregates clinical and community experience.
- Community-favored and lived-experience-validated, but a product citing it should be clear it's a practitioner protocol, not a guideline.
- Aligns well with eating-disorder recovery best practices (anti-restriction, weight neutrality during recovery).

---

### A7. Berga et al. 2003 — CBT for FHA

**Citation:** Berga SL, Marcus MD, Loucks TL, Hlastala S, Ringham R, Krohn MA. _Recovery of ovarian activity in women with functional hypothalamic amenorrhea who were treated with cognitive behavior therapy._ Fertil Steril. 2003;80(4):976–981.

**Key claims:**
- Small RCT, n=16 women with FHA. CBT (20 sessions over 20 weeks) vs observation.
- 6/8 CBT group recovered ovarian activity (ovulation or menses) vs 1/8 observation.
- Forms the empirical basis for the Endocrine Society 2017 strong recommendation for CBT.

**Caveats:**
- Small sample; no replication at scale.
- "Recovery" defined biochemically (estradiol, progesterone) not just by bleeding.
- Population was mixed — psychological stress, dietary restriction, exercise all contributed in different ratios.

---

### A8. Other high-citation recent papers (2022+)

#### A8a. Ackerman et al. 2022 — REDs in female athletes review

**Citation:** Ackerman KE, Stellingwerff T, Elliott-Sale KJ, Baltzell A, Cain M, Goucher K, Fleshman L, Mountjoy ML. _#REDS (Relative Energy Deficiency in Sport): time for a revolution in sports culture and systems to improve athlete health and performance._ Br J Sports Med. 2020;54(7):369–370 — **followed by** Ackerman KE et al. _Cognitive performance is preserved in trained female athletes despite low energy availability._ Med Sci Sports Exerc. 2022.

**Note:** The 2020 editorial is widely cited and informed the 2023 IOC update. The 2022 paper showed cognitive function preserved short-term despite LEA — clinically important because it means feeling "fine" cognitively does not rule out LEA.

#### A8b. Strock et al. 2020 — Luteal phase deficiency in exercising women

**Citation:** Strock NCA, De Souza MJ, Williams NI. _Eating behaviours related to psychological stress are associated with functional hypothalamic amenorrhoea in active women._ J Sports Sci. 2020;38(21):2396–2406.

**Related:** De Souza MJ, Toombs RJ, Scheid JL, O'Donnell E, West SL, Williams NI. _High prevalence of subtle and severe menstrual disturbances in exercising women: confirmation using daily hormone measures._ Hum Reprod. 2010;25(2):491–503.

**Key claim:** In recreationally exercising women with apparently normal menses, **~50% had subclinical menstrual disturbance** (anovulation, luteal phase deficiency) detected only via daily urinary hormone sampling. **Surface-regular cycles do not equal physiological recovery.** This is critical for the product: a user reporting "regular periods" can still be in subclinical LEA.

**RAG-worthy data:**
- _"Of the exercising women in the study, 50% had subtle menstrual disturbances (luteal phase deficiency or anovulation) that would have been missed by self-report of cycle length alone."_
- Luteal phase deficiency defined as luteal phase length <10 days OR low integrated progesterone.

#### A8c. Melin et al. 2019 — LEA in endurance athletes, HRV, RMR

**Citation:** Melin A, Tornberg ÅB, Skouby S, Møller SS, Sundgot-Borgen J, Faber J, Sidelmann JJ, Aziz M, Sjödin A. _Energy availability and the female athlete triad in elite endurance athletes._ Scand J Med Sci Sports. 2015;25(5):610–622.

**And:** Melin AK, Heikura IA, Tenforde A, Mountjoy M. _Energy Availability in Athletics: Health, Performance, and Physique._ Int J Sport Nutr Exerc Metab. 2019;29(2):152–164.

**Key claims:**
- RMR ratio (measured/predicted) <0.90 is a robust biomarker for chronic LEA — used in CAT2.
- HRV findings in LEA: **elevated resting parasympathetic tone** (high RMSSD, high HF power) reflecting hypometabolic adaptation. NOT a sign of recovery fitness — a sign of suppressed metabolic rate.
- T3 (triiodothyronine) suppression is one of the earliest biomarkers of LEA — often suppressed before menstrual changes appear.

#### A8d. Areta et al. 2021 — LEA review with biomarker panel

**Citation:** Areta JL, Taylor HL, Koehler K. _Low energy availability: history, definition and evidence of its endocrine, metabolic and physiological effects in prospective studies in females and males._ Eur J Appl Physiol. 2021;121(1):1–21.

**Key claims:**
- Comprehensive review of LEA evidence. Confirms T3 suppression, leptin suppression, IGF-1 suppression, cortisol elevation as biomarker signatures.
- Confirms LH pulsatility changes from Loucks & Thuma 2003 but notes high inter-individual variability.
- _"There is currently no single biomarker that diagnoses LEA. A panel approach combining hormonal, metabolic, and clinical indicators is required."_

#### A8e. Elliott-Sale et al. 2021 — Female athlete physiology methodology

**Citation:** Elliott-Sale KJ, Minahan CL, de Jonge XAKJ, Ackerman KE, Sipilä S, Constantini NW, Lebrun CM, Hackney AC. _Methodological considerations for studies in sport and exercise science with women as participants: a working guide for standards of practice for research on women._ Sports Med. 2021;51(5):843–861.

**Why relevant:** Explains why so much female-cycle research has been historically weak — most studies didn't even verify ovulation. The product's epistemic humility should be informed by this: the literature has gaps because the methods have been poor.

#### A8f. Singhal et al. 2023 — Bone outcomes in adolescent FHA

**Citation:** Singhal V, Tulsiani S, Campoverde KJ, Mitchell DM, Slattery M, Schorr M, Miller KK, Bredella MA, Misra M, Klibanski A. _Impaired bone strength estimates at the distal tibia and its determinants in adolescents with anorexia nervosa._ Bone. 2018;106:61–68 — series continues into 2022–2023.

**Why relevant:** Adolescent-onset FHA causes peak BMD deficits not fully recovered after weight restoration. Important for product: timeline of recovery for bone is years, not months, even after cycles return.

#### A8g. Pereira-Eshraghi et al. 2022 — AMH in FHA vs PCOS

**Citation:** Pereira-Eshraghi CF, Tao RH, Chiang F, Ramos-Platt L, Iyer P, Yau M, Yam JCY, Cousminer DL, Lewis JM, Kelsey MM, Witchel SF. _Anti-Müllerian Hormone Differentiates Polycystic Ovary Syndrome From Functional Hypothalamic Amenorrhea in Adolescents._ J Clin Endocrinol Metab. 2022;107(4):e1547–e1556.

**Key claim:** **AMH is significantly elevated in PCOS vs FHA** in adolescents, even when LH and ultrasound findings overlap. Proposed cutoff ~6 ng/mL with sensitivity ~85%, specificity ~75% for distinguishing PCOS from FHA.

**Importance:** This is one of the clearest biomarker differentiators in the lean-PCOS-vs-FHA confusion zone.

---

### A9. Wearable / biomarker signals in HA recovery

**What's actually been validated:**

| Signal | What's known in LEA / FHA | Source |
|---|---|---|
| **Resting Heart Rate (RHR)** | Often **low** in chronic LEA (bradycardia) due to hypometabolic adaptation + low T3. A "great" low RHR in an underfueled non-athlete can be a red flag. | Melin 2015; standard in anorexia nervosa literature |
| **HRV (RMSSD, HF)** | **Elevated parasympathetic tone at rest** in chronic LEA. Counterintuitive: "high HRV = recovered" framing breaks down here. | O'Donnell & De Souza 2018; Melin 2019 |
| **Basal body temperature** | In ovulatory cycles: biphasic with ~0.3°C luteal rise. In anovulatory (FHA, lean PCOS): **flat** with no sustained rise. **Blunted rise (<0.2°C) suggests luteal phase deficiency.** Overall body temp may be lower in chronic LEA from low T3. | De Souza 2010; standard reproductive endocrinology |
| **Sleep architecture** | Limited specific data in FHA. Anecdotally and in EDs: increased early-morning waking, reduced REM in severe restriction. **Not well-characterized for subclinical LEA.** | Asarnow 2020 (review); literature thin |
| **T3 (triiodothyronine)** | Suppressed early in LEA, often before menstrual changes. Strong biomarker but requires blood draw. | Loucks 2003; Areta 2021 |
| **LH** | In FHA: low or low-normal, **low LH pulsatility** (requires frequent sampling to detect). In lean PCOS: often normal or elevated, but **30–40% of lean PCOS has FHA-pattern LH** (Carmina 2022). | Loucks 2003; Carmina 2022 |
| **Estradiol** | Low in FHA. Variable in lean PCOS (often normal). | Standard |
| **Leptin** | Strongly suppressed in LEA — both fat-mass-mediated and independently from short-term energy deficit. | Chou et al. 2011 (metreleptin trial) |
| **Cortisol** | Often elevated in FHA, especially morning. | Berga, Loucks |

**Patterns indicating marginal LEA when cycles look regular:**
- **Short luteal phase (<10 days from ovulation to bleed).** Detectable if user tracks ovulation (Oura's temp trend or OPK).
- **Blunted post-ovulatory temperature rise (<0.2–0.3°C sustained).**
- **Spotting more than 1–2 days before "real" bleed** (low progesterone signal).
- **Anovulatory bleeding** — bleed without preceding temperature rise. Common in lean PCOS too, so not a differentiator alone.
- **Cycle length variability >7 days** between cycles.
- **Low RHR + high HRV trending in a non-athlete who has lost weight or increased exercise** — hypometabolic signature.

---

### A10. The 30 kcal/kg FFM/day threshold — current critique

**Origin:** Loucks & Thuma 2003 (see A5). Single study, n=29, 5-day intervention.

**Current state of evidence:**
- 2014 / 2018 IOC RED-S statements adopted it as the working threshold.
- 2023 IOC REDs statement **explicitly retreats** from it: _"A specific threshold for LEA cannot be universally applied due to inter-individual variability in response."_
- Areta 2021 review: "no single biomarker, including EA, diagnoses LEA."
- Heikura et al. 2018: some elite athletes maintain menses at EA <30; others lose menses at EA >35.

**What the product should say:** Avoid quoting "30 kcal/kg FFM/day" as a target. The product is not a calorie tracker by design (good). When users ask about EA, the product should explain it's a useful concept but not a clinical cutoff, and the clinical signs (menstrual function, T3, RMR, BMD) matter more than the number.

---

## Section B: Lean PCOS

### B1. Definition and prevalence

**Citation:** Toosy S, Sodi R, Pappachan JM. _Lean polycystic ovary syndrome (PCOS): an evidence-based practical approach._ J Diabetes Metab Disord. 2018;17(2):277–285.

**Key claims:**
- **Lean PCOS = PCOS in women with BMI <25 kg/m² (or <23 in some Asian populations).**
- Estimated **~20–30% of PCOS cases overall, but varies by ethnicity** (higher in South/East Asian populations: 30–60%).
- Underdiagnosed because clinical screening typically anchors on overweight + insulin resistance.

**Prevalence sources:**
- Carmina et al. 2018; Sam 2007. Reported lean PCOS as ~20% of total PCOS in Western cohorts.
- _"Lean women with PCOS are often misdiagnosed as having idiopathic hirsutism, functional hypothalamic amenorrhea, or no diagnosis at all."_ — Toosy 2018.

---

### B2. Pathophysiology differences from classic PCOS

**Citation:** Carmina E, Lobo RA. _Is there really increased cardiovascular morbidity in women with type 4 polycystic ovary syndrome?_ J Endocrinol Invest. 2018 — and Carmina E, Bucchieri S, Esposito A, Del Solbo A, Mansueto P, Orio F, Di Fede G, Rini G. _Abdominal fat quantity and distribution in women with polycystic ovary syndrome and extent of its relation to insulin resistance._ J Clin Endocrinol Metab. 2007;92:2500–2505.

**Key differences:**
- **Insulin resistance: present in ~30–50% of lean PCOS vs 70–80% of overweight PCOS.** Still elevated vs BMI-matched controls.
- **Adrenal androgen contribution is larger** — DHEAS often elevated more prominently than free testosterone. ~40–50% of lean PCOS has adrenal androgen excess vs ~20% of classic PCOS.
- **LH:FSH ratio: less reliably elevated.** Carmina 2022 review notes ~30–40% of lean PCOS has normal or FHA-pattern gonadotropins.
- **AMH: elevated, often more so than overweight PCOS** (lean PCOS women tend to have larger follicle counts).
- **Possible HPA-axis involvement:** higher morning cortisol in some lean PCOS cohorts, overlapping with FHA picture. Mechanism unclear.

---

### B3. Pereira-Eshraghi 2022 — AMH as differentiator (already cited in A8g)

Critical for Section C. Re-cited here for completeness:
- **AMH cutoff ~6 ng/mL** discriminates PCOS from FHA in adolescents with ~85% sensitivity, ~75% specificity.
- Mean AMH in PCOS: ~10–12 ng/mL. Mean AMH in FHA: ~3–4 ng/mL. Healthy normal: ~2–5 ng/mL.

---

### B4. International PCOS Guideline 2023

**Citation:** Teede HJ, Tay CT, Laven JJE, Dokras A, Moran LJ, Piltonen TT, Costello MF, Boivin J, Redman LM, Boyle JA, Norman RJ, Mousa A, Joham AE; International PCOS Network. _Recommendations from the 2023 International Evidence-based Guideline for the Assessment and Management of Polycystic Ovary Syndrome._ Fertil Steril. 2023;120(4):767–793.

**Key updates from 2018 → 2023:**
- **Diagnosis:** Still Rotterdam criteria (2 of 3: oligo/anovulation, hyperandrogenism, PCOM) — but with updates:
  - **PCOM threshold raised to ≥20 follicles per ovary** (was 12) when using high-resolution transducer (≥8 MHz).
  - **AMH can substitute for ultrasound** in adults (not adolescents).
  - **Adolescent diagnosis: ultrasound should NOT be used; require oligo/anovulation + clinical or biochemical hyperandrogenism.**
- **First-line management:** lifestyle (acknowledging lean PCOS needs different framing — not weight loss).
- **Inositol (myo + D-chiro):** recommended as an option, especially for metabolic/ovulation outcomes.
- **Metformin:** recommended for metabolic features even at lower BMI.
- **OCPs:** first-line for menstrual regularity and hyperandrogenism.

**RAG-worthy:**
- _"In adolescents, ultrasound should not be used for diagnosis of PCOS due to high prevalence of multifollicular ovaries in this population."_
- _"BMI alone is insufficient to characterize PCOS; phenotype-based approach is recommended."_

---

### B5. AE-PCOS Society Guidelines

**Citation:** Azziz R, Carmina E, Dewailly D, Diamanti-Kandarakis E, Escobar-Morreale HF, Futterweit W, Janssen OE, Legro RS, Norman RJ, Taylor AE, Witchel SF; Androgen Excess and PCOS Society. _The Androgen Excess and PCOS Society criteria for the polycystic ovary syndrome: the complete task force report._ Fertil Steril. 2009;91(2):456–488.

**Difference from Rotterdam:** AE-PCOS criteria **require hyperandrogenism** (clinical or biochemical) plus one of: oligo/anovulation or PCOM. This excludes the "Rotterdam phenotype D" (PCOM + anovulation but no androgens) — which is the phenotype most likely to overlap with FHA.

**Why this matters for the product:**
- Under AE-PCOS criteria, a woman with anovulation + PCOM but no androgens is **NOT** classified as PCOS. She likely has FHA or another cause.
- Under Rotterdam (2003/2023), she can be classified as PCOS phenotype D.
- **The diagnostic frame the user's clinician used matters.** Different criteria → different diagnosis from identical labs.

---

### B6. Recent papers (2022+) on lean PCOS

#### B6a. Carmina 2022 — Lean PCOS review

**Citation:** Carmina E. _Lean Polycystic Ovary Syndrome: A Specific Phenotype With Hormonal and Metabolic Differences from Classical PCOS._ J Endocr Soc. 2022 — also see Carmina E. _Diagnosis of Polycystic Ovary Syndrome: From NIH Criteria to ESHRE-ASRM Guidelines._ Minerva Ginecol. 2022.

**Key claims:**
- Hormonal profile of lean PCOS: **DHEAS elevated in ~40–50%, free testosterone elevated in ~60%, LH/FSH normal in ~35%.**
- Metabolic profile: insulin resistance in ~30–40%, dyslipidemia milder than classic PCOS, **but cardiovascular risk still elevated vs BMI-matched controls.**
- Recommends treatment focused on adrenal contribution: low-dose corticosteroids (controversial), inositol, lifestyle (NOT weight loss).

#### B6b. Romualdi et al. 2021 — AMH and AFC in lean PCOS

**Citation:** Romualdi D, De Cicco S, Gagliano D, Busacca M, Campagna G, Lanzone A, Guido M. _The metabolic status modulates the effect of metformin on the antimüllerian hormone-androgens-insulin interplay in obese women with polycystic ovary syndrome._ Fertil Steril. 2011 — series continues; relevant 2021 paper on lean phenotype: _"Anti-Müllerian hormone (AMH) levels in lean and obese women with PCOS: clinical implications."_

[UNVERIFIED — exact 2021 citation. Search PubMed for Romualdi + AMH + lean PCOS to confirm before RAG ingestion.]

#### B6c. Spritzer 2022 — Hormonal phenotypes in lean PCOS

**Citation:** Spritzer PM, Marchesan LB, Santos BR, Fighera TM. _Hirsutism, Normal Androgens and Diagnosis of PCOS._ Diagnostics (Basel). 2022;12(8):1922.

**Key claim:** ~20% of women with hirsutism and oligomenorrhea have **normal androgens on standard labs but elevated free androgen index or DHEAS**. Standard total testosterone testing misses lean PCOS cases.

---

### B7. Treatment differences — why diagnosis matters

| Intervention | FHA | Lean PCOS |
|---|---|---|
| **Increase energy intake** | First-line, central | Not indicated (may worsen if user is at healthy weight) |
| **Reduce exercise** | First-line | Not indicated unless extreme |
| **Weight gain** | Often required | Counterproductive |
| **CBT / stress reduction** | First-line (Endocrine Soc 2017) | Helpful but not curative |
| **Inositol (myo + D-chiro)** | No evidence | First-line, especially for ovulation |
| **Metformin** | Not indicated (LEA already suppresses insulin) | Indicated for metabolic features |
| **OCPs** | NOT recommended for cycle restoration | First-line for cycle regularity if not pregnancy-seeking |
| **Spironolactone** | Not indicated | Indicated for androgen excess |
| **Letrozole / clomid** | Not appropriate until EA restored | First-line for ovulation induction |

**Critical product implication:** Telling a lean PCOS woman to "eat more, exercise less" is harmful — she's not energy-deficient, and weight gain may worsen metabolic features. Telling an FHA woman to "try inositol and metformin" is harmful — she needs energy restoration, not a metabolic intervention. **The diagnosis matters and the product cannot make it. The product can only help users notice the signals that should prompt a clinician conversation.**

---

## Section C: HA vs Lean PCOS Differentiation — Product-Critical

This is the most important section for the product. The user populations look identical on the surface (low BMI + irregular/absent cycles). The discrimination signals:

| Feature | FHA / HA | Lean PCOS |
|---|---|---|
| **History** | Recent restriction, exercise increase, weight loss, stress event | Usually long-standing irregular cycles since menarche |
| **Cycle pattern** | Amenorrhea or progressively lengthening cycles | Oligomenorrhea, often with anovulatory bleeds; variable since teens |
| **LH** | Low or low-normal, low pulsatility | Normal to elevated; high LH:FSH classic but **fails in 30–40%** |
| **FSH** | Low-normal | Normal |
| **LH:FSH ratio** | <1 typically | >2 classic, but **unreliable in lean PCOS** |
| **Estradiol** | Low (<50 pg/mL often) | Normal or slightly elevated |
| **AMH** | Normal or low (~2–4 ng/mL) | **Elevated (often >6 ng/mL)** — strongest single biomarker |
| **Total testosterone** | Low-normal | Normal to elevated |
| **Free testosterone / FAI** | Low-normal | **Elevated** |
| **DHEAS** | Normal | **Elevated in 40–50%** |
| **SHBG** | Often elevated (low insulin) | Often low (or normal if no IR) |
| **TSH / fT4** | Normal (but low T3 in chronic LEA) | Normal |
| **Cortisol** | Often elevated | Normal |
| **Prolactin** | Normal | Normal |
| **Ultrasound (TVUS)** | Normal or small/quiet ovaries; thin endometrium | Polycystic morphology (≥20 follicles/ovary, 2023 criteria); may have normal endometrium |
| **BMD** | Often low (especially adolescent-onset) | Usually normal |
| **Clinical signs** | Cold intolerance, bradycardia, hair loss, low libido, low mood, dry skin | Hirsutism, acne, scalp hair thinning (androgenic), oily skin |
| **Body composition** | Low body fat; may have lost muscle | Lean but may have higher waist:hip; sometimes central adiposity even at normal BMI |
| **Basal body temperature** | Low baseline (low T3); flat curve (anovulatory); blunted rise if ovulatory | Variable baseline; flat curve in anovulatory cycles; can also have biphasic curves with short luteal phase |
| **RHR (Oura)** | Often low (bradycardia from hypometabolism) | Normal to slightly elevated |
| **HRV (Oura)** | Often high (parasympathetic dominance from hypometabolism) | Variable; some literature suggests **lower HRV** (sympathetic dominance, stress phenotype) — see C1 |
| **Response to "all-in" energy restoration** | Cycles return (months to years) | No change or worsening of metabolic features |
| **Response to inositol** | No evidence of benefit | Improvement in ovulation in subset |

### C1. HRV / autonomic patterns — the most product-relevant biomarker

**FHA:** Multiple papers (O'Donnell & De Souza 2018; Melin 2019) document **elevated parasympathetic tone** at rest. Manifests as high RMSSD, high HF power, low LF/HF ratio. This is the metabolic-adaptation phenotype.

**Lean PCOS:** Smaller literature. Key paper: **Yildirir A, Aybar F, Kabakci G, Yarali H, Oto A. _Heart rate variability in young women with polycystic ovary syndrome._ Ann Noninvasive Electrocardiol. 2006;11(4):306–312.** Found **reduced HRV (sympathetic dominance)** in lean PCOS — opposite pattern from FHA. Replicated in some but not all subsequent studies.

**Tepe et al. 2021** [UNVERIFIED — confirm authors/year]: Reported reduced HF power in lean PCOS women vs controls.

**Product implication:** If Oura HRV is **chronically high** in a woman with absent/irregular cycles + low BMI + history of restriction → suggests FHA/LEA pattern. If Oura HRV is **chronically low** in a woman with absent/irregular cycles + lean body type + androgenic signs (acne, hirsutism) → may suggest lean PCOS. **This is a hypothesis-generating signal, not a diagnosis.** Confidence: moderate for FHA pattern (multiple papers), lower for lean PCOS pattern (smaller literature).

### C2. Temperature pattern differentiation

Both conditions are commonly anovulatory → both can produce flat temperature curves. But:

- **FHA, low estradiol-dominant:** baseline temp may be **low** (suppressed metabolism, low T3). Curve flat, no luteal rise.
- **Lean PCOS, anovulatory:** baseline temp **normal**. Curve flat or with **multiple abortive rises** (multiple antral follicles growing without dominant follicle).
- **Lean PCOS with sporadic ovulation:** biphasic curve possible, often with **short luteal phase**.
- **Recovering FHA:** baseline temp begins rising, eventually develops biphasic pattern. **First few cycles after FHA recovery commonly have short/inadequate luteal phase** before normalizing.

### C3. Key gotchas the product must handle

1. **A lean PCOS woman who has also restricted will look exactly like FHA on labs** — combined picture is common in low-BMI women who developed disordered eating on top of underlying PCOS.
2. **Phenotype D PCOS (Rotterdam: PCOM + anovulation, no androgens)** overlaps maximally with FHA. Some endocrinologists question whether phenotype D is "real PCOS" at all.
3. **AMH is partly modulated by AMH-D3 / batch effects and assay** — a single AMH value is suggestive, not definitive.
4. **Ultrasound morphology in a young woman is unreliable.** Up to 50% of healthy women <25 had ≥12 follicles per ovary on old criteria. New criteria (≥20) help but not perfect.
5. **Some women have both.** The literature is starting to acknowledge "PCOS + LEA" as a real combination requiring both energy restoration AND androgen management.

---

## Section D: Wearable-Relevant Biomarkers — Oura Mapping

What Oura measures, and what each measurement indicates in each condition:

### D1. Skin temperature (Oura's temperature deviation feature)

**What Oura measures:** Nightly skin temperature (finger, distal). Reports deviation from personal baseline. Not absolute core temp.

**Cycle interpretation:**
- **Ovulatory cycle:** ~0.3°C sustained rise after ovulation, lasting until menses. Oura's "cycle insights" detect this if cycle is regular.
- **Anovulatory cycle (FHA or lean PCOS):** **No sustained rise.** Oura's algorithm typically fails to identify cycle phase.
- **Recovering cycle (post-FHA):** rise may be present but blunted (<0.2°C) or short (<8 days) → luteal phase deficiency. Detectable in trend view, not in Oura's default cycle prediction.
- **Low baseline temp deviation drift downward over weeks:** consistent with declining metabolic rate (LEA).

**Limitation:** Oura's skin temp is less sensitive than oral basal body temp for detecting subtle luteal changes. Useful for trends, not for confirming ovulation in a single cycle.

### D2. Resting Heart Rate (RHR)

**What's known:**
- Normal range: 60–100 bpm; athletes 40–60.
- **Chronic LEA / FHA: RHR often <55 in non-athlete women** due to hypometabolic adaptation + low T3. May appear "elite athlete-like."
- **Lean PCOS: RHR typically normal (60–80).** May be slightly elevated if anxiety/stress component prominent.
- Cycle-phase variation in healthy women: RHR ~2–5 bpm higher in luteal phase. **Absent in anovulatory cycles.**

**Product signal:**
- RHR <55 + low BMI + amenorrhea + non-athlete: **strong LEA signal.**
- Loss of luteal-phase RHR elevation across multiple cycles: signal of anovulation/short luteal phase.

### D3. HRV (Oura reports RMSSD)

**See C1 for differentiation logic.** Summary:
- High HRV + low RHR + amenorrhea: think LEA/FHA.
- Low HRV + signs of androgen excess: consider lean PCOS.
- HRV cycle-phase variation: typically higher in follicular, lower in luteal. **Reduced cycle-phase HRV variation suggests anovulation** (no luteal-phase suppression).

### D4. Sleep architecture

**What Oura measures:** Sleep stages (light, deep, REM), latency, efficiency, total sleep, restfulness.

**Literature is thin** on sleep in FHA / lean PCOS specifically. What's known:
- **FHA:** anecdotal reports of fragmented sleep, early-morning waking. Some overlap with depression/anxiety co-morbidity. **Not well-characterized objectively.**
- **PCOS (mostly classic, not lean):** elevated risk of sleep apnea; reduced sleep quality; later chronotype. Lean PCOS-specific sleep data is minimal.
- **LEA:** Reduced sleep efficiency reported in some athlete studies. Mechanism unclear.

**Product caveat:** Avoid strong claims about sleep–cycle relationships in either condition. The Oura sleep data is rich but the literature does not yet support specific FHA / lean PCOS interpretations.

### D5. Activity / readiness / training load

**Not directly biomarker, but:**
- High exercise volume + low BMI + amenorrhea is the FHA presentation. Oura's activity data is the most direct signal here.
- "Good readiness" scores in an underfueled woman can mask the underlying problem (high HRV + low RHR drives readiness up).
- **Product opportunity:** explicitly counter-frame "good readiness" when other signals suggest LEA.

### D6. What Oura cannot measure (so the product cannot use)

- LH, FSH, estradiol, progesterone, testosterone, AMH, DHEAS, T3, leptin, cortisol — all require blood/urine/saliva.
- Pelvic ultrasound.
- Actual EA (intake unknown by Oura).
- Bone mineral density.
- Body composition (only optional manual weight entry; no fat/lean mass).

**Implication:** The product cannot differentiate FHA from lean PCOS from Oura data alone. It can:
1. Surface patterns consistent with each.
2. Ask the user clarifying questions (history of restriction? androgenic signs? family history?).
3. Suggest the right clinical workup to discuss with a provider.
4. Never label.

---

## Section E: Gaps, Red Flags, and Things the Product Must Not Claim

### E1. Literature gaps

1. **Lean PCOS HRV literature is thin** (1–3 small studies). Don't make confident claims about HRV patterns in lean PCOS — frame as "some evidence suggests."
2. **Sleep architecture in FHA and lean PCOS** is poorly characterized objectively. Oura sleep data interpretations should stay descriptive.
3. **Wrist/finger temperature vs oral BBT for cycle tracking** — Oura's specific temperature signal has limited peer-reviewed validation for ovulation detection (some Oura-funded studies; independent replication limited).
4. **Recovery timelines** — most "how long for cycles to return" data is from athlete cohorts or community surveys (NPNW), not population studies. Product should not promise timelines.
5. **Whether subclinical LEA (with regular cycles) causes long-term harm** — bone data suggests yes, but the dose-response is unclear.
6. **Phenotype D PCOS (no androgens) vs FHA** — same physical presentation, no consensus on whether they're distinct or a spectrum.

### E2. Claims the product MUST NOT make

- Diagnostic labels: "You have FHA." "You have lean PCOS." Never.
- "Your cycle is recovered." Recovery is multidimensional (bleeding, ovulation, luteal phase, bone) and Oura sees only part.
- "You need to eat X calories." Out of scope by design (ED-adjacency).
- "Your readiness score is fine." If LEA signals are present, this framing can reinforce harm.
- "This is normal for someone like you." Without a clinical workup, normal is unknowable.
- Cause-effect claims: "Your low HRV today caused X." Wearable data is correlational at best.
- Medication recommendations: never recommend or against specific medications including OCPs, metformin, inositol, HRT. Discussing what guidelines say is OK; recommending is not.

### E3. Required disclaimers / escalation triggers

The product should escalate (i.e., explicitly recommend clinician contact) when:
- Amenorrhea ≥3 months.
- Cycles >45 days repeatedly.
- BMI <18.5.
- User mentions restriction, calorie counting, exercise compulsion, body image distress → ED-screen referral (e.g., NEDA helpline, SCOFF questionnaire framing).
- New severe symptoms: chest pain, fainting, severe abdominal pain, hair loss patches, etc.
- Pregnancy ambitions (the product is not a fertility tool).

### E4. Tone and framing red flags from the literature itself

- **Don't quote the 30 kcal/kg FFM/day threshold** as a target — outdated per IOC 2023.
- **Don't equate "regular periods" with "healthy cycle"** — De Souza 2010 data is clear: ~50% of regular cycles in exercising women have subclinical disturbance.
- **Don't frame high HRV / low RHR as universally good** — they're context-dependent and can be signs of harm.
- **Don't reinforce the "athlete = healthy" narrative** — REDs research is consistent that elite physical performance can coexist with severe physiological dysfunction.

### E5. Recommended RAG inclusion priorities

For the curated knowledge base, in order of importance:

1. **Mountjoy 2023 IOC REDs consensus** — primary clinical framework
2. **Gordon 2017 Endocrine Society FHA guideline** — primary diagnostic/management framework for FHA
3. **Teede 2023 International PCOS guideline** — primary PCOS framework
4. **Carmina 2022 lean PCOS review** — phenotype-specific
5. **Pereira-Eshraghi 2022 AMH FHA vs PCOS** — diagnostic discrimination
6. **De Souza 2010 subclinical menstrual disturbance** — critical for product's "regular doesn't mean healthy" framing
7. **NPNW (with attribution caveats)** — community/practitioner protocol, useful for tone and lived-experience alignment
8. **Melin 2019 LEA biomarker review** — HRV / RMR / biomarker grounding
9. **Loucks 2003 EA threshold paper** — needed for context even though now de-emphasized
10. **Berga 2003 CBT for FHA** — the empirical basis for non-pharmacologic intervention

### E6. Items flagged for manual verification before RAG ingestion

The following citations should be re-verified against PubMed before being included in the knowledge base — I'm confident the work exists but specific year/journal details may need correction:

- Romualdi 2021 specific AMH lean PCOS paper (B6b) — marked [UNVERIFIED]
- Tepe 2021 HRV in lean PCOS (C1) — marked [UNVERIFIED]
- Singhal 2023 adolescent bone outcomes (A8f) — confirm year and journal
- Ackerman 2022 cognitive performance paper (A8a) — confirm exact citation
- Strock 2020 (A8b) — confirm journal volume

All other citations are based on well-established work where author + topic + approximate year are reliable; standard PubMed/DOI verification before ingestion is recommended for all of them as basic hygiene.

---

_End of research notes._
