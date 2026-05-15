"""
Shared config — finds the .env file by walking up from this file's location.
Both group-a and group-b import from here via their own thin wrappers.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

def _find_env() -> Path | None:
    """Walk up the directory tree looking for a .env file."""
    current = Path(__file__).resolve().parent
    for _ in range(6):          # max 6 levels up
        candidate = current / ".env"
        if candidate.exists():
            return candidate
        current = current.parent
    return None

_env_path = _find_env()
if _env_path:
    load_dotenv(_env_path)

OPENCODE_API_KEY: str = os.getenv("OPENCODE_API_KEY", "your_api_key_here")
OPENCODE_BASE_URL: str = os.getenv("OPENCODE_BASE_URL", "https://api.minimaxi.chat/v1")
MODEL_NAME: str        = os.getenv("MODEL_NAME", "MiniMax-Text-01")
SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
