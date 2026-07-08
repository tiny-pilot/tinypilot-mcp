import pytest

from tinypilot_mcp.stream_state import parse_stream_state


def test_parse_stream_state() -> None:
    state = parse_stream_state(
        {
            "ok": True,
            "result": {
                "source": {
                    "online": True,
                    "resolution": {"width": 1024, "height": 768},
                    "captured_fps": 60,
                }
            },
        }
    )
    assert state.online is True
    assert state.width == 1024
    assert state.height == 768
    assert state.captured_fps == 60


def test_parse_stream_state_missing_resolution() -> None:
    with pytest.raises(ValueError, match="resolution"):
        parse_stream_state({"ok": True, "result": {"source": {"online": True}}})
