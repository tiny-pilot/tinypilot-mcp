from __future__ import annotations

import time

from tinypilot_mcp.client import TinyPilotClient
from tinypilot_mcp.config import AppConfig, DeviceConfig
from tinypilot_mcp.errors import NO_ACTIVE_DEVICE, unknown_device


class Session:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.active_device_id: str | None = None

    def valid_ids(self) -> list[str]:
        return [d.id for d in self.config.devices]

    def resolve_device(self, device_id: str | None) -> DeviceConfig:
        chosen = device_id or self.active_device_id
        if not chosen:
            raise ValueError(NO_ACTIVE_DEVICE)
        device = self.config.device_by_id(chosen)
        if device is None:
            raise ValueError(unknown_device(chosen, self.valid_ids()))
        return device

    def select_device(self, device_id: str) -> DeviceConfig:
        device = self.resolve_device(device_id)
        self.active_device_id = device.id
        return device

    def client(self, device_id: str | None = None) -> TinyPilotClient:
        device = self.resolve_device(device_id)
        return TinyPilotClient(device, self.config.defaults)

    def paste_wait_seconds(self, text: str) -> float:
        ms = (100 * len(text)) + self.config.defaults.paste_wait_buffer_ms
        return ms / 1000.0

    def paste_and_wait(
        self, text: str, *, device_id: str | None = None, language: str = "en-US"
    ) -> None:
        client = self.client(device_id)
        client.paste(text, language=language)
        time.sleep(self.paste_wait_seconds(text))
