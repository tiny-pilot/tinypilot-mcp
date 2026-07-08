from __future__ import annotations

import httpx

from tinypilot_mcp.config import DefaultsConfig, DeviceConfig
from tinypilot_mcp.stream_state import StreamState, parse_stream_state
from tinypilot_mcp.token_cache import TokenCache


class TinyPilotApiError(Exception):
    pass


class TinyPilotOfflineError(TinyPilotApiError):
    pass


class TinyPilotClient:
    def __init__(
        self,
        device: DeviceConfig,
        defaults: DefaultsConfig,
        token_cache: TokenCache,
    ) -> None:
        self._device = device
        self._defaults = defaults
        self._token_cache = token_cache
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

    def _fetch_token(self) -> str:
        r = httpx.post(
            f"{self._base()}/api/v1/auth",
            timeout=self._timeout,
            verify=self._verify,
        )
        if r.status_code >= 400:
            raise TinyPilotApiError(f"Auth failed ({r.status_code}): {r.text}")
        token = r.json().get("token")
        if not token:
            raise TinyPilotApiError("Auth response missing token")
        return token

    def _token(self, *, force_refresh: bool = False) -> str:
        if force_refresh:
            self._token_cache.clear(self._device.id)
        cached = self._token_cache.get(self._device.id)
        if cached:
            return cached
        token = self._fetch_token()
        self._token_cache.set(self._device.id, token)
        return token

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
    ) -> httpx.Response:
        url = f"{self._base()}{path}"
        last: httpx.Response | None = None
        for attempt in range(2):
            headers = {"Authorization": f"Bearer {self._token(force_refresh=attempt == 1)}"}
            kwargs = {
                "headers": headers,
                "timeout": self._timeout,
                "verify": self._verify,
            }
            if method == "GET":
                last = httpx.get(url, **kwargs)
            else:
                last = httpx.post(url, json=json, **kwargs)
            if last.status_code != 403:
                return last
        assert last is not None
        return last

    def get_stream_state(self) -> StreamState:
        """Fetch uStreamer state from GET /state (unofficial TinyPilot endpoint)."""
        r = self._request("GET", "/state")
        if r.status_code >= 400:
            raise TinyPilotApiError(f"Stream state failed ({r.status_code}): {r.text}")
        try:
            return parse_stream_state(r.json())
        except ValueError as exc:
            raise TinyPilotApiError(f"Stream state parse failed: {exc}") from exc

    def capture_screenshot(self) -> tuple[bytes, str]:
        r = self._request("GET", "/api/v1/screenshot")
        if r.status_code == 204:
            raise TinyPilotOfflineError("video offline")
        if r.status_code >= 400:
            raise TinyPilotApiError(f"Screenshot failed ({r.status_code}): {r.text}")
        return r.content, r.headers.get("Content-Type", "image/jpeg")

    def send_keystroke(self, payload: dict) -> None:
        r = self._request("POST", "/api/v1/keystroke", json=payload)
        if r.status_code >= 400:
            raise TinyPilotApiError(f"Keystroke failed ({r.status_code}): {r.text}")

    def mouse_event(self, payload: dict) -> None:
        r = self._request("POST", "/api/v1/mouseEvent", json=payload)
        if r.status_code >= 400:
            raise TinyPilotApiError(f"Mouse event failed ({r.status_code}): {r.text}")

    def paste(self, text: str, language: str = "en-US") -> None:
        r = self._request("POST", "/api/v1/paste", json={"text": text, "language": language})
        if r.status_code >= 400:
            raise TinyPilotApiError(f"Paste failed ({r.status_code}): {r.text}")
