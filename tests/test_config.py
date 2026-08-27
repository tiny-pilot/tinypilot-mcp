import os
import pytest
from tinypilot_mcp.config import load_config, AppConfig

def test_load_config_from_path(sample_devices_json):
    cfg = load_config(sample_devices_json)
    assert len(cfg.devices) == 1
    assert cfg.devices[0].id == "lab-01"
    assert "read" in cfg.defaults.capabilities

def test_load_config_from_env(sample_devices_json, monkeypatch):
    monkeypatch.setenv("TINYPILOT_DEVICES", str(sample_devices_json))
    cfg = load_config()
    assert cfg.devices[0].base_url == "http://127.0.0.1:48000"

def test_missing_config_raises(monkeypatch):
    monkeypatch.delenv("TINYPILOT_DEVICES", raising=False)
    with pytest.raises(FileNotFoundError):
        load_config()


def test_load_config_requires_api_key(tmp_path):
    path = tmp_path / "devices.json"
    path.write_text(
        """
{
  "defaults": {"capabilities": ["read"]},
  "devices": [{"id": "lab-01", "base_url": "http://127.0.0.1:48000"}],
  "output_dir": "data"
}
""".strip()
    )
    with pytest.raises(Exception):
        load_config(path)


def test_load_config_exposes_api_key(sample_devices_json):
    cfg = load_config(sample_devices_json)
    assert cfg.devices[0].api_key == "test-api-key"
