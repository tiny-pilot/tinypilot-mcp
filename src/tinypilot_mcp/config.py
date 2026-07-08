from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Capability = Literal["read", "input"]


class DeviceConfig(BaseModel):
    id: str
    base_url: str
    label: str = ""
    aliases: list[str] = Field(default_factory=list)
    verify_ssl: bool | None = None
    timeout_seconds: float | None = None


class DefaultsConfig(BaseModel):
    verify_ssl: bool = True
    timeout_seconds: float = 30.0
    paste_wait_buffer_ms: int = 1000
    capabilities: list[Capability] = Field(default_factory=lambda: ["read", "input"])

    @field_validator("capabilities")
    @classmethod
    def non_empty(cls, v: list[Capability]) -> list[Capability]:
        if not v:
            raise ValueError("capabilities must not be empty")
        return v


class AppConfig(BaseModel):
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    devices: list[DeviceConfig]
    output_dir: Path = Path("data")
    action_log: Path | None = None

    def device_by_id(self, device_id: str) -> DeviceConfig | None:
        return next((d for d in self.devices if d.id == device_id), None)

    def has_capability(self, cap: Capability) -> bool:
        return cap in self.defaults.capabilities


def load_config(path: Path | None = None) -> AppConfig:
    if path is None:
        env = os.environ.get("TINYPILOT_DEVICES")
        if not env:
            raise FileNotFoundError(
                "No config path provided and TINYPILOT_DEVICES is not set"
            )
        path = Path(env)
    raw = json.loads(path.read_text())
    cfg = AppConfig.model_validate(raw)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    if cfg.action_log is None:
        cfg.action_log = cfg.output_dir / "actions.jsonl"
    return cfg
