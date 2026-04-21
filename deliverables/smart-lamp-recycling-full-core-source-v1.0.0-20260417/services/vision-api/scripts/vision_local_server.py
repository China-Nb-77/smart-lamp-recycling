from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))
os.environ.setdefault("AI_LIGHT_AGENT_MODE", "real")

from image_quote_system.serving.api import serve_api


if __name__ == "__main__":
    serve_api("127.0.0.1", 8000, REPO_ROOT / "configs")
