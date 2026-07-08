from __future__ import annotations

import base64
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, Field

from tinypilot_mcp.action_log import log_action
from tinypilot_mcp.client import TinyPilotApiError, TinyPilotClient, TinyPilotOfflineError
from tinypilot_mcp.config import load_config
from tinypilot_mcp.coords import format_coord_summary, pixel_to_relative
from tinypilot_mcp.errors import hid_disconnected, video_offline
from tinypilot_mcp.session import Session
from tinypilot_mcp.stream_state import StreamState
from tinypilot_mcp.tools.annotations import READ_ONLY, SELECT, WRITE

WORKFLOW_INSTRUCTIONS = """\
TinyPilot KVM automation. Use screenshot → act → verify on every step.

1. tinypilot_list_devices, then tinypilot_select_device before any input.
2. Use tinypilot_get_stream_state only for online status and resolution (coordinate conversion). Screenshot whenever you need to read or verify screen content.
3. Prefer paste/keystroke over mouse; use mouse only when keyboard cannot reach the target.
4. One input tool per step. Screenshot to verify before the next input.
5. If an action fails or looks wrong, screenshot and reassess — do not repeat the same input blindly.

Install tinypilot-ai-agent-skills for full workflow guidance.
"""

VERIFY_NEXT = (
    "Next: call tinypilot_capture_screenshot to verify before sending more input."
)

mcp = FastMCP("tinypilot", instructions=WORKFLOW_INSTRUCTIONS)
_session: Session | None = None


def get_session() -> Session:
    global _session
    if _session is None:
        _session = Session(load_config())
    return _session


class SelectDeviceInput(BaseModel):
    device_id: str = Field(description="Device id from tinypilot_list_devices")


class DeviceOverride(BaseModel):
    device_id: str | None = Field(
        default=None,
        description=(
            "Target device id. Uses active device from tinypilot_select_device if omitted."
        ),
    )


class PasteInput(DeviceOverride):
    text: str = Field(description="Text to paste as keystrokes")
    language: str = Field(
        default="en-US",
        description="Keyboard language: en-US, en-GB, or de-DE",
    )


class KeystrokeInput(DeviceOverride):
    code: str = Field(description="KeyboardEvent.code value, e.g. Enter, Delete")
    key: str | None = Field(default=None, description="KeyboardEvent.key value")
    ctrlLeft: bool = False
    altLeft: bool = False
    shiftLeft: bool = False
    metaLeft: bool = False


class MouseInput(DeviceOverride):
    relativeX: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Relative X in 0.0-1.0. Omit if using pixel_x/pixel_y.",
    )
    relativeY: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Relative Y in 0.0-1.0. Omit if using pixel_x/pixel_y.",
    )
    pixel_x: int | None = Field(
        default=None,
        ge=0,
        description="Pixel X from stream resolution (tinypilot_get_stream_state). Use with pixel_y.",
    )
    pixel_y: int | None = Field(
        default=None,
        ge=0,
        description="Pixel Y from stream resolution (tinypilot_get_stream_state). Use with pixel_x.",
    )
    buttons: int = Field(description="MouseEvent.buttons bitmask")
    verticalWheelDelta: int = 0
    horizontalWheelDelta: int = 0


def _format_stream_state(state: StreamState, device_id: str) -> str:
    fps = f" captured_fps={state.captured_fps}" if state.captured_fps is not None else ""
    return (
        f"device_id={device_id} online={str(state.online).lower()} "
        f"resolution={state.width}x{state.height}{fps} "
        "(from GET /state — unofficial, may change between TinyPilot versions)"
    )


def _resolve_mouse_coords(
    client: TinyPilotClient, mouse_input: MouseInput
) -> tuple[float, float, StreamState | None]:
    has_relative = mouse_input.relativeX is not None and mouse_input.relativeY is not None
    has_pixel = mouse_input.pixel_x is not None and mouse_input.pixel_y is not None
    if has_relative and has_pixel:
        raise ValueError(
            "Provide either relativeX/relativeY or pixel_x/pixel_y, not both."
        )
    if not has_relative and not has_pixel:
        raise ValueError(
            "Missing coordinates. Provide relativeX/relativeY (0.0-1.0) or "
            "pixel_x/pixel_y from tinypilot_get_stream_state."
        )

    if has_pixel:
        assert mouse_input.pixel_x is not None and mouse_input.pixel_y is not None
        state = client.get_stream_state()
        rel_x, rel_y = pixel_to_relative(
            mouse_input.pixel_x, mouse_input.pixel_y, state.width, state.height
        )
        return rel_x, rel_y, state

    assert mouse_input.relativeX is not None and mouse_input.relativeY is not None
    try:
        state = client.get_stream_state()
    except TinyPilotApiError:
        state = None
    return mouse_input.relativeX, mouse_input.relativeY, state


def _tool_error(message: str) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=message)],
        isError=True,
    )


def _is_hid_error(message: str) -> bool:
    lowered = message.lower()
    return "(500)" in message or "hid" in lowered


def _format_input_api_error(exc: TinyPilotApiError) -> str:
    message = str(exc)
    return hid_disconnected(message) if _is_hid_error(message) else message


def _register_tools(session: Session) -> None:
    caps = session.config.defaults.capabilities

    @mcp.resource(
        "tinypilot://devices",
        name="tinypilot_devices",
        description="Configured TinyPilot fleet from local config.",
        mime_type="application/json",
    )
    def tinypilot_devices_resource() -> dict[str, list[dict[str, object]]]:
        return {
            "devices": [
                {
                    "id": device.id,
                    "label": device.label,
                    "aliases": device.aliases,
                    "base_url": device.base_url,
                }
                for device in session.config.devices
            ]
        }

    @mcp.tool(name="tinypilot_list_devices", annotations=READ_ONLY)
    def tinypilot_list_devices() -> str:
        """List configured devices from local config. Call before tinypilot_select_device."""
        lines = []
        active = session.active_device_id
        for device in session.config.devices:
            mark = " (active)" if device.id == active else ""
            aliases = f" aliases={device.aliases}" if device.aliases else ""
            lines.append(
                f"- {device.id}{mark}: {device.label or device.id} @ {device.base_url}{aliases}"
            )
        log_action(
            session.config.action_log,
            device_id=active,
            tool="tinypilot_list_devices",
            success=True,
        )
        return "\n".join(lines) if lines else "No devices configured."

    if "input" in caps:

        @mcp.tool(name="tinypilot_select_device", annotations=SELECT)
        def tinypilot_select_device(input: SelectDeviceInput):
            """Set active device for subsequent calls. Required before any input tool."""
            try:
                device = session.select_device(input.device_id)
            except ValueError as exc:
                log_action(
                    session.config.action_log,
                    device_id=input.device_id,
                    tool="tinypilot_select_device",
                    success=False,
                    detail=str(exc),
                )
                return _tool_error(str(exc))
            message = f"Active device: {device.id} ({device.label or device.id}) @ {device.base_url}"
            log_action(
                session.config.action_log,
                device_id=device.id,
                tool="tinypilot_select_device",
                success=True,
            )
            return (
                f"{message} Next: call tinypilot_capture_screenshot to observe the console."
            )

    if "read" in caps:

        @mcp.tool(name="tinypilot_get_stream_state", annotations=READ_ONLY)
        def tinypilot_get_stream_state(input: DeviceOverride | None = None):
            """Online status and resolution via GET /state (text only, no JPEG).

            Use for: is video online? what is width×height (for pixel_x/y conversion)?
            Do not use for: reading UI, finding click targets, or verifying input worked —
            use tinypilot_capture_screenshot for those.
            """
            device_id = input.device_id if input else None
            try:
                client = session.client(device_id)
                state = client.get_stream_state()
            except ValueError as exc:
                message = str(exc)
                log_action(
                    session.config.action_log,
                    device_id=device_id,
                    tool="tinypilot_get_stream_state",
                    success=False,
                    detail=message,
                )
                return _tool_error(message)
            except TinyPilotApiError as exc:
                message = str(exc)
                log_action(
                    session.config.action_log,
                    device_id=device_id or session.active_device_id,
                    tool="tinypilot_get_stream_state",
                    success=False,
                    detail=message,
                )
                return _tool_error(message)

            resolved_id = client.device_id
            message = _format_stream_state(state, resolved_id)
            log_action(
                session.config.action_log,
                device_id=resolved_id,
                tool="tinypilot_get_stream_state",
                success=True,
            )
            return message

        @mcp.tool(name="tinypilot_capture_screenshot", annotations=READ_ONLY)
        def tinypilot_capture_screenshot(input: DeviceOverride | None = None):
            """Capture the target console (JPEG + metadata).

            Use to read UI content, decide what to click, and verify each input worked.
            Call before and after every input tool. get_stream_state does not replace this.
            """
            device_id = input.device_id if input else None
            try:
                client = session.client(device_id)
                data, content_type = client.capture_screenshot()
            except ValueError as exc:
                message = str(exc)
                log_action(
                    session.config.action_log,
                    device_id=device_id,
                    tool="tinypilot_capture_screenshot",
                    success=False,
                    detail=message,
                )
                return _tool_error(message)
            except TinyPilotOfflineError:
                resolved_id = device_id or session.active_device_id or "unknown"
                message = video_offline(resolved_id)
                log_action(
                    session.config.action_log,
                    device_id=resolved_id,
                    tool="tinypilot_capture_screenshot",
                    success=False,
                    detail=message,
                )
                return _tool_error(message)
            except TinyPilotApiError as exc:
                message = str(exc)
                log_action(
                    session.config.action_log,
                    device_id=device_id or session.active_device_id,
                    tool="tinypilot_capture_screenshot",
                    success=False,
                    detail=message,
                )
                return _tool_error(message)

            resolved_id = client.device_id
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            output_dir = session.config.output_dir / "screenshots"
            output_dir.mkdir(parents=True, exist_ok=True)
            path = output_dir / f"{resolved_id}-{timestamp}.jpg"
            path.write_bytes(data)
            log_action(
                session.config.action_log,
                device_id=resolved_id,
                tool="tinypilot_capture_screenshot",
                success=True,
                detail=str(path),
            )
            metadata = (
                f"device_id={resolved_id} path={path} captured_at={timestamp} online=true "
                "Review screen state before calling an input tool."
            )
            try:
                state = client.get_stream_state()
                metadata += f" resolution={state.width}x{state.height}"
            except TinyPilotApiError:
                pass
            encoded = base64.standard_b64encode(data).decode("ascii")
            return [
                {"type": "text", "text": metadata},
                {"type": "image", "data": encoded, "mimeType": content_type},
            ]

    if "input" in caps:

        @mcp.tool(name="tinypilot_paste_text", annotations=WRITE)
        def tinypilot_paste_text(input: PasteInput):
            """Paste text as keystrokes. Server waits (100ms × len + buffer) before returning.

            Prefer paste over mouse for text entry. One paste per step; screenshot to verify
            before follow-up keystrokes.
            """
            resolved_id: str | None = None
            try:
                client = session.client(input.device_id)
                resolved_id = client.device_id
                session.paste_and_wait(
                    input.text,
                    device_id=input.device_id,
                    language=input.language,
                )
            except ValueError as exc:
                message = str(exc)
                log_action(
                    session.config.action_log,
                    device_id=input.device_id,
                    tool="tinypilot_paste_text",
                    success=False,
                    detail=message,
                )
                return _tool_error(message)
            except TinyPilotApiError as exc:
                message = _format_input_api_error(exc)
                log_action(
                    session.config.action_log,
                    device_id=resolved_id or input.device_id or session.active_device_id,
                    tool="tinypilot_paste_text",
                    success=False,
                    detail=message,
                )
                return _tool_error(message)
            log_action(
                session.config.action_log,
                device_id=resolved_id,
                tool="tinypilot_paste_text",
                success=True,
                detail=f"len={len(input.text)}",
            )
            return (
                f"Pasted {len(input.text)} characters to {resolved_id}. "
                f"Safe to send next input. {VERIFY_NEXT}"
            )

        @mcp.tool(name="tinypilot_send_keystroke", annotations=WRITE)
        def tinypilot_send_keystroke(input: KeystrokeInput):
            """Send one keystroke (KeyboardEvent.code). Use metaLeft for Win/Cmd.

            One keystroke per step; screenshot to verify before the next input.
            """
            payload = input.model_dump(exclude={"device_id"}, exclude_none=True)
            resolved_id: str | None = None
            try:
                client = session.client(input.device_id)
                resolved_id = client.device_id
                client.send_keystroke(payload)
            except ValueError as exc:
                message = str(exc)
                log_action(
                    session.config.action_log,
                    device_id=input.device_id,
                    tool="tinypilot_send_keystroke",
                    success=False,
                    detail=message,
                )
                return _tool_error(message)
            except TinyPilotApiError as exc:
                message = _format_input_api_error(exc)
                log_action(
                    session.config.action_log,
                    device_id=resolved_id or input.device_id or session.active_device_id,
                    tool="tinypilot_send_keystroke",
                    success=False,
                    detail=message,
                )
                return _tool_error(message)
            log_action(
                session.config.action_log,
                device_id=resolved_id,
                tool="tinypilot_send_keystroke",
                success=True,
            )
            return f"Keystroke sent to {resolved_id}. {VERIFY_NEXT}"

        @mcp.tool(name="tinypilot_mouse_event", annotations=WRITE)
        def tinypilot_mouse_event(input: MouseInput):
            """Mouse move, click, or scroll. Fallback when keyboard/paste cannot reach the target.

            Provide relativeX/Y (0.0-1.0) or pixel_x/y from get_stream_state. Clicks: buttons
            0 → 1 → 0. Screenshot after each event to verify.
            """
            resolved_id: str | None = None
            try:
                client = session.client(input.device_id)
                resolved_id = client.device_id
                rel_x, rel_y, state = _resolve_mouse_coords(client, input)
                payload = {
                    "relativeX": rel_x,
                    "relativeY": rel_y,
                    "buttons": input.buttons,
                    "verticalWheelDelta": input.verticalWheelDelta,
                    "horizontalWheelDelta": input.horizontalWheelDelta,
                }
                client.mouse_event(payload)
            except ValueError as exc:
                message = str(exc)
                log_action(
                    session.config.action_log,
                    device_id=input.device_id,
                    tool="tinypilot_mouse_event",
                    success=False,
                    detail=message,
                )
                return _tool_error(message)
            except TinyPilotApiError as exc:
                message = _format_input_api_error(exc)
                log_action(
                    session.config.action_log,
                    device_id=resolved_id or input.device_id or session.active_device_id,
                    tool="tinypilot_mouse_event",
                    success=False,
                    detail=message,
                )
                return _tool_error(message)
            log_action(
                session.config.action_log,
                device_id=resolved_id,
                tool="tinypilot_mouse_event",
                success=True,
            )
            width = state.width if state else None
            height = state.height if state else None
            coords = format_coord_summary(rel_x, rel_y, width, height)
            return f"Mouse event sent to {resolved_id}. {coords} {VERIFY_NEXT}"


def run() -> None:
    session = get_session()
    _register_tools(session)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run()
