import os
from pathlib import Path


def _load_env_file(path: str = ".env") -> None:
    env_path = Path(__file__).resolve().parent / path
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got {value!r}") from None


_load_env_file()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_TOKEN", ""))
TELEGRAM_TOKEN = TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
PROXYCHECK_API_KEY = os.getenv("PROXYCHECK_API_KEY", "")

HONEYPOT_HOST = os.getenv("HONEYPOT_HOST", "0.0.0.0")
HONEYPOT_PORT = _get_int("HONEYPOT_PORT", 2222)

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = _get_int("API_PORT", 8000)

DB_PATH = os.getenv("DB_PATH", "honeypot.db")
