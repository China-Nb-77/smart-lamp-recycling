from __future__ import annotations

import json
import os
import sys
from pathlib import Path



def main() -> None:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    openapi_dir = root / "backend" / "openapi"
    openapi_dir.mkdir(parents=True, exist_ok=True)
    sqlite_path = (openapi_dir / "openapi.db").resolve().as_posix()
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{sqlite_path}")
    os.environ.setdefault("AI_LIGHT_WORKFLOW_MODE", "mock")
    os.environ.setdefault("AI_LIGHT_PAYMENT_MODE", "mock")

    from backend.app.main import create_app

    target = openapi_dir / "openapi.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    schema = create_app().openapi()
    target.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
