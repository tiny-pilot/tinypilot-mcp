import pytest
from pytest_httpx import HTTPXMock
from tinypilot_mcp.client import TinyPilotClient, TinyPilotOfflineError
from tinypilot_mcp.config import DeviceConfig, DefaultsConfig
from tinypilot_mcp.token_cache import TokenCache


@pytest.fixture
def device():
    return DeviceConfig(id="lab-01", base_url="http://127.0.0.1:48000")


@pytest.fixture
def defaults():
    return DefaultsConfig(timeout_seconds=5)


def test_auth_and_screenshot(httpx_mock: HTTPXMock, device, defaults):
    httpx_mock.add_response(url="http://127.0.0.1:48000/api/v1/auth", json={"token": "tok"})
    httpx_mock.add_response(
        url="http://127.0.0.1:48000/api/v1/screenshot",
        content=b"jpeg-bytes",
        headers={"Content-Type": "image/jpeg"},
    )
    client = TinyPilotClient(device, defaults, TokenCache())
    data, content_type = client.capture_screenshot()
    assert data == b"jpeg-bytes"
    assert content_type == "image/jpeg"


def test_screenshot_offline_204(httpx_mock: HTTPXMock, device, defaults):
    httpx_mock.add_response(url="http://127.0.0.1:48000/api/v1/auth", json={"token": "tok"})
    httpx_mock.add_response(url="http://127.0.0.1:48000/api/v1/screenshot", status_code=204)
    client = TinyPilotClient(device, defaults, TokenCache())
    with pytest.raises(TinyPilotOfflineError):
        client.capture_screenshot()


def test_403_retries_auth_once(httpx_mock: HTTPXMock, device, defaults):
    httpx_mock.add_response(url="http://127.0.0.1:48000/api/v1/auth", json={"token": "tok1"})
    httpx_mock.add_response(url="http://127.0.0.1:48000/api/v1/auth", json={"token": "tok2"})
    httpx_mock.add_response(url="http://127.0.0.1:48000/api/v1/screenshot", status_code=403)
    httpx_mock.add_response(
        url="http://127.0.0.1:48000/api/v1/screenshot",
        content=b"ok",
        headers={"Content-Type": "image/jpeg"},
    )
    client = TinyPilotClient(device, defaults, TokenCache())
    data, _ = client.capture_screenshot()
    assert data == b"ok"


def test_get_stream_state(httpx_mock: HTTPXMock, device, defaults):
    httpx_mock.add_response(url="http://127.0.0.1:48000/api/v1/auth", json={"token": "tok"})
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
    client = TinyPilotClient(device, defaults, TokenCache())
    state = client.get_stream_state()
    assert state.online is True
    assert state.width == 1920
    assert state.height == 1080
