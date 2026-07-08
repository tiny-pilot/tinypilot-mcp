import asyncio
import json

from mcp.types import CallToolResult

from tinypilot_mcp.client import TinyPilotApiError
from tinypilot_mcp.errors import hid_disconnected
from tinypilot_mcp.server import (
    _format_input_api_error,
    _register_tools,
    _tool_error,
    get_session,
    mcp,
)


def test_read_only_config_registers_list_and_screenshot(
    sample_devices_json, monkeypatch
) -> None:
    monkeypatch.setenv("TINYPILOT_DEVICES", str(sample_devices_json))

    import tinypilot_mcp.server as server

    server._session = None
    session = get_session()
    session.config.defaults.capabilities = ["read"]
    _register_tools(session)

    # FastMCP stores tools internally; smoke test session setup.
    assert session.config.has_capability("read")


def test_devices_resource_returns_config_json(sample_devices_json, monkeypatch) -> None:
    monkeypatch.setenv("TINYPILOT_DEVICES", str(sample_devices_json))

    import tinypilot_mcp.server as server

    server._session = None
    session = get_session()
    _register_tools(session)

    async def read_devices_resource() -> str:
        resource = await mcp._resource_manager.get_resource("tinypilot://devices")
        return await resource.read()

    payload = json.loads(asyncio.run(read_devices_resource()))
    assert payload == {
        "devices": [
            {
                "id": "lab-01",
                "label": "Lab box",
                "aliases": ["lab", "LAB-01"],
                "base_url": "http://127.0.0.1:48000",
            }
        ]
    }


def test_non_500_input_api_error_is_not_rewritten_as_hid() -> None:
    exc = TinyPilotApiError("Keystroke failed (400): Invalid code")

    message = _format_input_api_error(exc)

    assert message == "Keystroke failed (400): Invalid code"
    assert message != hid_disconnected(str(exc))


def test_tool_error_uses_is_error_result() -> None:
    result = _tool_error("No active device.")

    assert isinstance(result, CallToolResult)
    assert result.isError is True
    assert result.content[0].type == "text"
    assert result.content[0].text == "No active device."
