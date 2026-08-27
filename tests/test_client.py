import pytest
from pytest_httpx import HTTPXMock
from tinypilot_mcp.client import TinyPilotApiError, TinyPilotClient, TinyPilotOfflineError
from tinypilot_mcp.config import DeviceConfig, DefaultsConfig


@pytest.fixture
def device():
    return DeviceConfig(
        id="lab-01",
        base_url="http://127.0.0.1:48000",
        api_key="test-api-key",
    )


@pytest.fixture
def defaults():
    return DefaultsConfig(timeout_seconds=5)


def test_screenshot_sends_bearer_api_key(httpx_mock: HTTPXMock, device, defaults):
    httpx_mock.add_response(
        url="http://127.0.0.1:48000/api/v1/screenshot",
        content=b"jpeg-bytes",
        headers={"Content-Type": "image/jpeg"},
    )
    client = TinyPilotClient(device, defaults)
    data, content_type = client.capture_screenshot()
    assert data == b"jpeg-bytes"
    assert content_type == "image/jpeg"
    req = httpx_mock.get_request()
    assert req.headers["Authorization"] == "Bearer test-api-key"


def test_screenshot_offline_204(httpx_mock: HTTPXMock, device, defaults):
    httpx_mock.add_response(
        url="http://127.0.0.1:48000/api/v1/screenshot", status_code=204
    )
    client = TinyPilotClient(device, defaults)
    with pytest.raises(TinyPilotOfflineError):
        client.capture_screenshot()


def test_403_raises_api_key_error(httpx_mock: HTTPXMock, device, defaults):
    httpx_mock.add_response(
        url="http://127.0.0.1:48000/api/v1/screenshot", status_code=403
    )
    client = TinyPilotClient(device, defaults)
    with pytest.raises(TinyPilotApiError, match="API key"):
        client.capture_screenshot()


def test_get_stream_state(httpx_mock: HTTPXMock, device, defaults):
    httpx_mock.add_response(
        url="http://127.0.0.1:48000/state",
        json={
            "ok": True,
            "result": {
                "source": {
                    "online": True,
                    "resolution": {"width": 1920, "height": 1080},
                    "captured_fps": 30,
                }
            },
        },
    )
    client = TinyPilotClient(device, defaults)
    state = client.get_stream_state()
    assert state.online is True
    assert state.width == 1920
    assert state.height == 1080
