from __future__ import annotations


class TokenCache:
    def __init__(self) -> None:
        self._tokens: dict[str, str] = {}

    def get(self, device_id: str) -> str | None:
        return self._tokens.get(device_id)

    def set(self, device_id: str, token: str) -> None:
        self._tokens[device_id] = token

    def clear(self, device_id: str) -> None:
        self._tokens.pop(device_id, None)
