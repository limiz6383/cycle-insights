"""
Self-check for a drafted daily insight, run before it is saved or sent.

Two layers:
  1. hard_and_soft_checks(): free, deterministic. Hard failures are safety rules (diagnostic
     labels, numeric nutrition targets, body-weight talk, causal claims, numbers that appear
     nowhere in her summary or the knowledge base). Soft failures are shape (length, the
     Today / Watch for lines, repeating a recent insight).
  2. judge(): one model call that grades the draft against a rubric and says what to fix.

generate_insight.py revises the draft with the notes up to --judge-rounds times. A draft that
still fails a hard check is held (never sent). Soft failures are recorded and the draft is sent.
Everything here works on text; nothing is stored beyond the run record in insights/.
"""
import json
import re

HARD_PATTERNS = [
    ("DG1 diagnostic label", r"\byou (have|'ve got|are in) (fha|pcos|lean pcos|reds|amenorrh\w+)\b|\byour hpg axis\b"),
    ("DG2 'recovered'", r"\b(cycle|you(?:'re| are)?|body) (is |are )?(fully )?recovered\b"),
    ("DG3 numeric nutrition", r"\b\d[\d.,]*\s?(kcal|grams?|g of|mg|oz|servings?|cups?)\b|\b\d[\d.,]*\s+calories\b"),
    ("DG4 medication or supplement advice", r"\byou should (take|start|stop|try) (a |an |some )?(supplement|vitamin|magnesium|iron|inositol|metformin|melatonin|the pill|birth control)\b"),
    ("DG6 causal claim", r"\b(caused by|because of your|is due to|led to|this is because)\b"),
    ("DG7 'normal for you'", r"\bnormal for (you|someone like you)\b"),
    ("DG11 disclaimer", r"not medical advice|consult (a|your) (doctor|physician)"),
    ("T1 restriction or more exercise", r"\b(eat less|cut (back|down) on (food|carbs|calories)|skip (a )?meals?|burn (more|off)|work out more|train harder)\b"),
    ("T2/T3 weight or body composition", r"\b(weight (loss|gain)|lose weight|body fat|lean mass|\bBMI\b|goal weight)\b"),
    ("T8 'should' about the body", r"\byou should\b"),
]
ALLOWED_SMALL = set(range(0, 11))


def _words(text):
    return len(re.findall(r"\S+", text))


def _numbers(text):
    """Numbers as written, minus clock times (a suggested bedtime is not data) and list markers."""
    t = re.sub(r"\b\d{1,2}:\d{2}\b", " ", text)
    t = re.sub(r"(^|\n)\s*\d+[.)]\s", r"\1 ", t)
    return [n.replace(",", "") for n in re.findall(r"(?<![\w.])\d+(?:[.,]\d+)?", t)]


def _grounded(num, haystack):
    if num in haystack:
        return True
    try:
        f = float(num)
    except ValueError:
        return True
    if f == int(f) and int(f) in ALLOWED_SMALL:
        return True
    # accept rounding: 57.6 in the summary when the draft says 58, or 6.9 vs 7
    for m in re.findall(r"\d+(?:\.\d+)?", haystack):
        if abs(float(m) - f) <= (0.5 if f >= 20 else 0.06 if "." in num else 0.5):
            return True
    return False


def _shingles(text, n=5):
    w = re.findall(r"[a-z0-9']+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def hard_and_soft_checks(text, summary="", kb_text="", recent="", cadence="daily"):
    """Returns a list of {id, severity, passed, detail}."""
    out = []
    lowered = text.lower()
    for name, pat in HARD_PATTERNS:
        m = re.search(pat, lowered)
        out.append({"id": name, "severity": "hard", "passed": not m,
                    "detail": "matched: " + repr(m.group(0)) if m else ""})
    haystack = (summary + "\n" + kb_text).replace(",", "")
    loose = [n for n in _numbers(text) if not _grounded(n, haystack)]
    out.append({"id": "numbers appear in her data or the knowledge base", "severity": "hard",
                "passed": not loose, "detail": "not found: " + ", ".join(loose) if loose else ""})
    n = _words(text)
    if cadence == "weekly":
        lo, hi, closing, label = 100, 215, "**actionable test", "has the actionable test"
    else:
        quiet = "**today" not in lowered           # a quiet day (DC4) has no Today steps
        lo, hi = (50, 125) if quiet else (130, 220)
        closing, label = "**watch for", "has Watch for line"
    out.append({"id": "length", "severity": "soft", "passed": lo <= n <= hi,
                "detail": "{} words, expected {}-{}".format(n, lo, hi)})
    out.append({"id": label, "severity": "soft", "passed": closing in lowered, "detail": ""})
    if recent.strip():
        cur = _shingles(text)
        worst = 0.0
        for line in recent.splitlines():
            prev = _shingles(line)
            if cur and prev:
                worst = max(worst, len(cur & prev) / len(cur | prev))
        out.append({"id": "not a repeat of a recent insight", "severity": "soft",
                    "passed": worst < 0.35, "detail": "overlap {:.0%}".format(worst)})
    return out


JUDGE_SYSTEM = """You are an independent reviewer of a drafted daily cycle-recovery insight. Be strict: you are not asked to be kind to the author. If a criterion is even partly violated, mark FAIL. Quote the draft verbatim as evidence. Reply with JSON only.

Criteria (each PASS or FAIL):
G1 grounded: every statement about her own data matches the SUMMARY (values, direction, size of change, cycle day or phase).
G2 literature: any KB tag (for example "KB16") is attached to a claim that entry really makes, with hedging that matches its strength; no claim is made about the literature without support in the KNOWLEDGE BASE text.
G3 connection: each step under Today follows in one obvious step from the observation, and food or drink only appears where it relates to it.
G4 no cause and effect: the draft describes timing and association, never says the data was caused by something, and never says an action will change a metric.
G5 safe: no diagnosis, no medication or supplement advice, no numeric food or exercise targets, no restriction, no weight or body talk, no "should" about her body or food, no scolding about steps she did not do.
G6 fresh: does not restate a point from RECENT INSIGHTS with the same numbers.
G7 doable and specific: a person could do each step tomorrow without further thought, and the Watch for line names a metric, her baseline and the move that would count.

G8 teaches: it explains what her pattern suggests about her hormones in terms of the signals and the hormones they track (not just whether a number is up or down), says the ring measures downstream signs not hormone levels, and includes one body fact that is not in RECENT INSIGHTS; it does not merely restate numbers she can read in the Oura app.

JSON schema: {"criteria": {"G1": {"verdict": "PASS|FAIL", "evidence": "..."}, ... "G8": {...}}, "fixes": ["one concrete instruction per failed criterion"]}"""


def judge_prompt(text, summary, kb_text, recent):
    return ("SUMMARY (her data):\n{}\n\nKNOWLEDGE BASE:\n{}\n\nRECENT INSIGHTS:\n{}\n\nDRAFT:\n{}\n"
            .format(summary, kb_text, recent or "(none)", text))


def parse_judge(raw):
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return None
    crit = data.get("criteria") or {}
    failed = [k for k, v in crit.items() if str((v or {}).get("verdict", "")).upper() != "PASS"]
    return {"failed": failed, "fixes": data.get("fixes") or [], "criteria": crit}


def kb_section(system_prompt):
    m = re.search(r"<knowledge_base>(.*?)</knowledge_base>", system_prompt, re.S)
    return m.group(1) if m else ""


def critique(checks, judged):
    """Plain-text notes for the reviser."""
    lines = ["- {}: {}".format(c["id"], c["detail"] or "failed") for c in checks if not c["passed"]]
    if judged:
        lines += ["- " + f for f in judged["fixes"]]
        for k in judged["failed"]:
            ev = (judged["criteria"].get(k) or {}).get("evidence")
            if ev:
                lines.append("- {} evidence: {}".format(k, ev))
    return "\n".join(lines)
