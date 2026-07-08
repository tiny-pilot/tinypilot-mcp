from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def log_action(
    path: Path,
    *,
    device_id: str | None,
    tool: str,
    success: bool,
    detail: str = "",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "device_id": device_id,
        "tool": tool,
        "success": success,
        "detail": detail,
    }
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")
