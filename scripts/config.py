"""
Minimal .env loader — stdlib only, no python-dotenv dependency.

Reads <repo_root>/.env into os.environ. Real environment variables always win,
so `OURA_TOKEN=x python3 fetch_oura_data.py` still overrides the file.

.env is gitignored. Never commit it: it holds your Oura personal access token,
your Anthropic API key, and your Telegram bot token.
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"

_loaded = False


def load_env(path=None):
    """Populate os.environ from .env. Idempotent; existing vars are not clobbered."""
    global _loaded
    if _loaded and path is None:
        return
    env_file = Path(path) if path else ENV_PATH
    if env_file.exists():
        for raw in env_file.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    if path is None:
        _loaded = True


def require(name, hint=""):
    """Fetch a required env var or exit with an actionable message."""
    load_env()
    value = os.environ.get(name)
    if not value:
        msg = "Missing {} — add it to {}".format(name, ENV_PATH)
        if hint:
            msg += "\n{}".format(hint)
        raise SystemExit(msg)
    return value


def get(name, default=None):
    load_env()
    return os.environ.get(name, default)
