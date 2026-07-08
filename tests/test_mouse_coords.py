from unittest.mock import MagicMock

import pytest

from tinypilot_mcp.client import TinyPilotApiError
from tinypilot_mcp.server import MouseInput, _resolve_mouse_coords
from tinypilot_mcp.stream_state import StreamState


def test_resolve_mouse_coords_from_pixel() -> None:
    client = MagicMock()
    client.get_stream_state.return_value = StreamState(
        online=True, width=1024, height=768, captured_fps=60
    )
    mouse_input = MouseInput(pixel_x=512, pixel_y=384, buttons=1)

    rel_x, rel_y, state = _resolve_mouse_coords(client, mouse_input)

    assert rel_x == pytest.approx(0.5)
    assert rel_y == pytest.approx(0.5)
    assert state is not None
    assert state.width == 1024


def test_resolve_mouse_coords_from_relative() -> None:
    client = MagicMock()
    client.get_stream_state.return_value = StreamState(
        online=True, width=1024, height=768
    )
    mouse_input = MouseInput(relativeX=0.25, relativeY=0.75, buttons=0)

    rel_x, rel_y, state = _resolve_mouse_coords(client, mouse_input)

    assert rel_x == 0.25
    assert rel_y == 0.75
    assert state is not None


def test_resolve_mouse_coords_rejects_both() -> None:
    client = MagicMock()
    mouse_input = MouseInput(
        relativeX=0.1, relativeY=0.2, pixel_x=10, pixel_y=20, buttons=1
    )

    with pytest.raises(ValueError, match="not both"):
        _resolve_mouse_coords(client, mouse_input)


def test_resolve_mouse_coords_relative_without_state() -> None:
    client = MagicMock()
    client.get_stream_state.side_effect = TinyPilotApiError("Stream state failed (404)")
    mouse_input = MouseInput(relativeX=0.1, relativeY=0.2, buttons=0)

    rel_x, rel_y, state = _resolve_mouse_coords(client, mouse_input)

    assert rel_x == 0.1
    assert rel_y == 0.2
    assert state is None
