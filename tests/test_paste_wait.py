from tinypilot_mcp.config import load_config
from tinypilot_mcp.session import Session

def test_paste_wait_seconds(sample_devices_json):
    cfg = load_config(sample_devices_json)
    session = Session(cfg)
    # 5 chars -> 500ms + 1000ms buffer = 1.5s
    assert session.paste_wait_seconds("hello") == 1.5
