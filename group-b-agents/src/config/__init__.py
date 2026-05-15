# Re-export from shared root config so agents can do: from src.config import MODEL_NAME
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
from shared_config import OPENCODE_API_KEY, OPENCODE_BASE_URL, MODEL_NAME, SLACK_WEBHOOK_URL

__all__ = ["OPENCODE_API_KEY", "OPENCODE_BASE_URL", "MODEL_NAME", "SLACK_WEBHOOK_URL"]
