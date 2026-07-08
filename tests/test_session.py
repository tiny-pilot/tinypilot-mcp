import pytest
from tinypilot_mcp.config import load_config
from tinypilot_mcp.session import Session

def test_select_and_resolve(sample_devices_json):
    cfg = load_config(sample_devices_json)
    session = Session(cfg)
    d = session.select_device("lab-01")
    assert d.id == "lab-01"
    assert session.client().device_id == "lab-01"

def test_resolve_without_select_raises(sample_devices_json):
    cfg = load_config(sample_devices_json)
    session = Session(cfg)
    with pytest.raises(ValueError, match="No active device"):
        session.client()
