import pytest

@pytest.fixture
def sample_devices_json(tmp_path):
    path = tmp_path / "devices.json"
    path.write_text(
        """
{
  "defaults": {"verify_ssl": true, "timeout_seconds": 5, "capabilities": ["read", "input"]},
  "devices": [
    {
      "id": "lab-01",
      "base_url": "http://127.0.0.1:48000",
      "label": "Lab box",
      "aliases": ["lab", "LAB-01"]
    }
  ],
  "output_dir": "data"
}
""".strip()
    )
    return path
