from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StreamState:
    online: bool
    width: int
    height: int
    captured_fps: int | None = None


def parse_stream_state(payload: dict) -> StreamState:
    if not payload.get("ok"):
        raise ValueError("Stream state response missing ok=true")
    source = payload.get("result", {}).get("source", {})
    resolution = source.get("resolution", {})
    width = resolution.get("width")
    height = resolution.get("height")
    if width is None or height is None:
        raise ValueError("Stream state missing source.resolution width/height")
    fps = source.get("captured_fps")
    return StreamState(
        online=bool(source.get("online")),
        width=int(width),
        height=int(height),
        captured_fps=int(fps) if fps is not None else None,
    )
