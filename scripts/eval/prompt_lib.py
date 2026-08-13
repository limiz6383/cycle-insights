"""
Shared prompt assembly + API call for the cycle insights system.

Both `generate_insight.py` (real data, produces an insight you read) and
`run_eval.py` (synthetic scenarios, produces a pass/fail scoreboard) go
through this module, so they are guaranteed to exercise the SAME prompt.
That property is the whole point: an eval that assembles the prompt
differently from production measures a system nobody runs.
"""
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Make ANTHROPIC_API_KEY from .env visible to the SDK. Both entry points
# (generate_insight.py and run_eval.py) come through this module, so loading
# here covers both rather than each remembering to do it.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from config import load_env
except ImportError:  # config.py absent — fall back to real env vars only
    def load_env():
        return None

# Generation model. Thinking is on by default on this model and MAX_TOKENS caps
# thinking + visible text together, so the ceiling is far above the ~180-word
# output — a tight max_tokens truncates the answer mid-sentence.
DEFAULT_MODEL = "claude-opus-5"
DEFAULT_MAX_TOKENS = 8000


def load_prompt(prompt_version="v3.1", prompt_file=None):
    """
    Return the system prompt text.

    With --prompt-file, read it verbatim. Otherwise extract the fenced block
    under '### Full v3 prompt' in pretotype_log.md (v3.1 patches were edited
    in place in the v3 block, so that block IS v3.1).

    Extraction is brittle by design: once you fork v3.2, save prompts to their
    own files under prompts/ and pass --prompt-file instead.
    """
    if prompt_file:
        path = Path(prompt_file)
        if not path.exists():
            sys.exit("Prompt file not found: {}".format(path))
        return path.read_text().strip()

    log_path = REPO_ROOT / "pretotype_log.md"
    if not log_path.exists():
        sys.exit("pretotype_log.md not found at {}".format(log_path))
    text = log_path.read_text()

    marker = "### Full v3 prompt"
    idx = text.find(marker)
    if idx == -1:
        sys.exit("Could not find '{}' in pretotype_log.md".format(marker))
    match = re.search(r"`{3,}\n(.+?)\n`{3,}", text[idx:], re.DOTALL)
    if not match:
        sys.exit("Could not extract fenced prompt block after '{}'.".format(marker))
    return match.group(1).strip()


def _replace_block(text, tag, content):
    """
    Swap the body of the <tag>...</tag> PLACEHOLDER BLOCK, leaving tags in place.

    Anchored to tags that sit alone on their own line. This matters: the UD1
    trust-hierarchy rules mention '<user_reported_context>' and '<oura_summary>'
    inline in prose ("- <user_reported_context> is ground truth for..."). A
    naive `<tag>.*?</tag>` match starts at that prose mention and eats UD1-UD4
    on its way to the closing tag — deleting the very rules this fix restores.
    """
    pattern = re.compile(
        r"^<{tag}>[ \t]*\n(.*?)\n^</{tag}>[ \t]*$".format(tag=re.escape(tag)),
        re.DOTALL | re.MULTILINE,
    )
    matches = pattern.findall(text)
    if len(matches) != 1:
        sys.exit(
            "Expected exactly 1 <{0}> placeholder block on its own lines, found {1}. "
            "The prompt's <user_data> layout changed — update prompt_lib.".format(
                tag, len(matches)
            )
        )
    return pattern.sub(
        lambda m: "<{0}>\n{1}\n</{0}>".format(tag, (content or "").strip()),
        text,
        count=1,
    )


def inject_user_data(system_prompt, oura_summary="", user_reported_context="", user_query=""):
    """
    Fill the three runtime placeholders inside <user_data>.

    IMPORTANT: this replaces only the <oura_summary>, <user_reported_context>,
    and <user_query> sub-blocks. The UD1-UD4 rules (trust hierarchy, coverage
    and sparsity thresholds, empty-query default, out-of-scope handling) stay
    exactly as written in the source prompt.

    The previous implementation in run_eval.py replaced the entire <user_data>
    block with a sentinel that dropped UD1-UD4, so every eval run scored a
    prompt that was missing its own data-handling rules.
    """
    if "<user_data>" not in system_prompt:
        sys.exit("Could not find <user_data> block in the prompt.")
    out = _replace_block(system_prompt, "oura_summary", oura_summary)
    out = _replace_block(out, "user_reported_context", user_reported_context)
    out = _replace_block(out, "user_query", user_query)
    return out


def call_claude(system_prompt, model=DEFAULT_MODEL, max_tokens=DEFAULT_MAX_TOKENS,
                dry_run=False, user_turn=None):
    """
    Run the assembled prompt. Returns (text, usage_dict).

    On dry_run, prints a preview and returns a placeholder without spending
    API budget — use it to eyeball what would actually be sent.
    """
    if user_turn is None:
        user_turn = "Generate this week's insight per <your_job> and <output_format>."

    if dry_run:
        print("=" * 78)
        print("DRY RUN — assembled system prompt is {} chars.".format(len(system_prompt)))
        print("=" * 78)
        marker = system_prompt.find("<user_data>")
        print(system_prompt[marker:marker + 1500] if marker != -1 else system_prompt[:1500])
        print("... [truncated preview]")
        print("=" * 78)
        return "[DRY RUN — no generation]", {}

    load_env()

    try:
        from anthropic import Anthropic
    except ImportError:
        sys.exit("Missing SDK. Install with: pip install anthropic")

    client = Anthropic()  # resolves ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, or an `ant auth login` profile
    if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        print("[note] No API key env var set — relying on a stored `ant auth login` profile.",
              file=sys.stderr)

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_turn}],
    )

    if response.stop_reason == "refusal":
        return "[REFUSED by safety classifier — stop_reason=refusal]", {
            "stop_reason": "refusal",
        }

    text = "".join(b.text for b in response.content if b.type == "text")
    usage = {
        "model": response.model,
        "stop_reason": response.stop_reason,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    if response.stop_reason == "max_tokens":
        print("[warn] Hit max_tokens — output is truncated. Raise --max-tokens.",
              file=sys.stderr)
    return text, usage
