NO_ACTIVE_DEVICE = (
    "No active device. Call tinypilot_list_devices, then tinypilot_select_device "
    "with a device_id before sending input."
)


def unknown_device(device_id: str, valid_ids: list[str]) -> str:
    ids = ", ".join(valid_ids) if valid_ids else "(none configured)"
    return (
        f"device_id '{device_id}' not in config. "
        f"Valid ids: {ids}. Call tinypilot_list_devices."
    )


def video_offline(device_id: str) -> str:
    return (
        f"Video stream offline for device '{device_id}'. "
        "Target may be powered off or HDMI disconnected. "
        "Call tinypilot_capture_screenshot after recovery; do not send input until online."
    )


def hid_disconnected(detail: str) -> str:
    return (
        f"Could not forward input to target: {detail}. "
        "Verify USB cable and target power."
    )


def invalid_api_key(device_id: str) -> str:
    return (
        f"API key rejected for device '{device_id}' (HTTP 403). "
        "Check api_key in devices.json, or create/revoke keys under "
        "System → Automation (TinyPilot Pro 3.2.0+)."
    )
