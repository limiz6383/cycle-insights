"""
Deterministic rule checkers — string / regex / count operations.
No LLM calls here. Cheap, fast, always-run.

For semantic checks (CF firing correctly, DG1 absence detection, NT2
hallucination pattern), see rules/judge.py — those require LLM-as-judge.
"""
import re


def check_word_count(output_text: str, expected_range: list) -> dict:
    """OF1 / OF5 word count check."""
    words = output_text.split()
    n = len(words)
    low, high = expected_range
    return {
        "rule": "OF1_word_count",
        "passed": low <= n <= high,
        "observed": n,
        "expected_range": expected_range,
        "detail": f"Output is {n} words; expected {low}-{high}.",
    }


def check_bolded_actionable_test(output_text: str) -> dict:
    """OF1 — must end with a bolded **Actionable test for this week:** callout."""
    has_bold = "**Actionable test for this week:**" in output_text
    return {
        "rule": "OF1_bold_actionable_test",
        "passed": has_bold,
        "detail": "Bolded 'Actionable test for this week:' callout present." if has_bold
                  else "Missing required bolded actionable test callout.",
    }


def check_kb_citation_inline(output_text: str) -> dict:
    """OF2 / OF3 — at least one inline KB[N] citation must appear."""
    matches = re.findall(r"KB\d+", output_text)
    return {
        "rule": "OF2_kb_citation_inline",
        "passed": len(matches) >= 1,
        "observed_citations": list(set(matches)),
        "detail": f"Found {len(set(matches))} unique KB citation(s): {sorted(set(matches))}."
                  if matches else "No inline KB[N] citations found.",
    }


def check_banned_phrases(output_text: str, banned: list) -> dict:
    """Scan for any banned phrase (case-insensitive substring match)."""
    lowered = output_text.lower()
    hits = [p for p in banned if p.lower() in lowered]
    return {
        "rule": "banned_phrases",
        "passed": len(hits) == 0,
        "violations": hits,
        "detail": f"Found {len(hits)} banned phrase(s): {hits}." if hits
                  else "No banned phrases detected.",
    }


def check_required_phrases(output_text: str, required: list) -> dict:
    """Scan for required phrases (case-insensitive substring match)."""
    if not required:
        return {"rule": "required_phrases", "passed": True, "detail": "No required phrases specified."}
    lowered = output_text.lower()
    missing = [p for p in required if p.lower() not in lowered]
    return {
        "rule": "required_phrases",
        "passed": len(missing) == 0,
        "missing": missing,
        "detail": f"Missing required phrase(s): {missing}." if missing
                  else "All required phrases present.",
    }


def check_specific_numbers_present(output_text: str, min_count: int = 2) -> dict:
    """OF2 — at least N specific numbers from user data must appear (descriptive observations)."""
    # Match decimals and integers (loosely — captures '~63', '27%', '0.4°C', '32-day', etc.)
    numbers = re.findall(r"~?\d+\.?\d*", output_text)
    return {
        "rule": "OF2_specific_numbers",
        "passed": len(numbers) >= min_count,
        "observed_count": len(numbers),
        "min_expected": min_count,
        "detail": f"Output contains {len(numbers)} numeric tokens; minimum {min_count} expected.",
    }


def run_deterministic_checks(output_text: str, scenario: dict) -> list:
    """
    Run all deterministic checks against one output for one scenario.
    Returns a list of check-result dicts.
    """
    checks = []
    shape = scenario.get("expected_output_shape", {})

    checks.append(check_word_count(output_text, shape.get("word_count_range", [100, 180])))

    if shape.get("must_include_bold_actionable_test", True):
        # For urgent-only escalations (OF4), the bolded actionable test is not required.
        if shape.get("format") != "urgent_only":
            checks.append(check_bolded_actionable_test(output_text))

    if shape.get("must_cite_kb_inline", True):
        checks.append(check_kb_citation_inline(output_text))

    checks.append(check_specific_numbers_present(output_text, min_count=2))
    checks.append(check_banned_phrases(output_text, scenario.get("banned_phrases", [])))
    checks.append(check_required_phrases(output_text, scenario.get("required_phrases", [])))

    return checks
