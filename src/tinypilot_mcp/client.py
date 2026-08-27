from __future__ import annotations

import httpx

from tinypilot_mcp.config import DefaultsConfig, DeviceConfig
from tinypilot_mcp.errors import invalid_api_key
from tinypilot_mcp.stream_state import StreamState, parse_stream_state


class TinyPilotApiError(Exception):
    pass


class TinyPilotOfflineError(TinyPilotApiError):
    pass


class TinyPilotClient:
    def __init__(self, device: DeviceConfig, defaults: DefaultsConfig) -> None:
        self._device = device
        self._verify = (
            device.verify_ssl if device.verify_ssl is not None else defaults.verify_ssl
        )
        self._timeout = (
            device.timeout_seconds
            if device.timeout_seconds is not None
            else defaults.timeout_seconds
        )

    @property
    def device_id(self) -> str:
        return self._device.id

    def _base(self) -> str:
        return self._device.base_url.rstrip("/")

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
    ) -> httpx.Response:
        url = f"{self._base()}{path}"
        headers = {"Authorization": f"Bearer {self._device.api_key}"}
        kwargs = {
            "headers": headers,
            "timeout": self._timeout,
            "verify": self._verify,
        }
        if method == "GET":
            return httpx.get(url, **kwargs)
        return httpx.post(url, json=json, **kwargs)

    def _raise_for_status(self, r: httpx.Response, action: str) -> None:
        if r.status_code == 403:
            raise TinyPilotApiError(invalid_api_key(self._device.id))
        if r.status_code >= 400:
            raise TinyPilotApiError(f"{action} failed ({r.status_code}): {r.text}")

    def get_stream_state(self) -> StreamState:
        """Fetch uStreamer state from GET /state."""
        r = self._request("GET", "/state")
        self._raise_for_status(r, "Stream state")
        try:
            return parse_stream_state(r.json())
        except ValueError as exc:
            raise TinyPilotApiError(f"Stream state parse failed: {exc}") from exc

    def capture_screenshot(self) -> tuple[bytes, str]:
        r = self._request("GET", "/api/v1/screenshot")
        if r.status_code == 204:
            raise TinyPilotOfflineError("video offline")
        self._raise_for_status(r, "Screenshot")
        return r.content, r.headers.get("Content-Type", "image/jpeg")

    def send_keystroke(self, payload: dict) -> None:
        r = self._request("POST", "/api/v1/keystroke", json=payload)
        self._raise_for_status(r, "Keystroke")

    def mouse_event(self, payload: dict) -> None:
        r = self._request("POST", "/api/v1/mouseEvent", json=payload)
        self._raise_for_status(r, "Mouse event")

    def paste(self, text: str, language: str = "en-US") -> None:
        r = self._request(
            "POST", "/api/v1/paste", json={"text": text, "language": language}
        )
        self._raise_for_status(r, "Paste")
