# Design: TinyPilot REST API key auth (Pro 3.2.0+)

**Date:** 2026-08-27  
**Status:** Approved for implementation planning  
**Package:** `tinypilot-mcp`  
**Breaking change:** Yes (v0.2.0)

## Context

As of TinyPilot Pro **3.2.0**, the public REST API no longer issues ephemeral tokens via `POST /api/v1/auth`. That endpoint returns `410 Gone` with `EPHEMERAL_TOKEN_DEPRECATED`. Clients must use a persistent API key created under **System → Automation**, sent as:

```http
Authorization: Bearer <API_KEY>
```

Keys work while web interface user authentication is enabled. An Automation License is still required. Protected REST endpoints with an API key are limited to:

- `GET /api/v1/screenshot`
- `POST /api/v1/keystroke`
- `POST /api/v1/mouseEvent`
- `POST /api/v1/paste`

Status endpoints available without an API key include `GET /state` (already used by MCP for online/resolution).

Adoption of `tinypilot-mcp` is early (~single-digit active users; PyPI ~24 downloads/month). This is treated as a **one-time re-architecture**: API-key only (no dual-mode legacy `/auth`).

## Decision

**Approach A — API-key only.**

- Require `api_key` per device in `devices.json`.
- Delete ephemeral token fetch and `TokenCache`.
- No OS keychain, vault, or env-override in this pass.
- Document clearly: **requires TinyPilot Pro 3.2.0 or later**.

## Config

`DeviceConfig` gains a required field:

```json
{
  "id": "lab-01",
  "base_url": "https://tinypilot.example",
  "api_key": "YOUR_API_KEY",
  "label": "Lab",
  "aliases": ["lab"]
}
```

- Missing `api_key` → config validation error at startup (fail fast).
- Examples use the placeholder `YOUR_API_KEY` only.
- README: keep `devices.json` outside git; prefer `chmod 600` on the file.
- Action log / tool output: never log the API key (same rule as today’s “no tokens”).

## Client behavior

| Before (≤0.1.0) | After (0.2.0+) |
|-----------------|----------------|
| `POST /api/v1/auth` → cache token | Use `device.api_key` as Bearer |
| On 403, refresh token and retry once | On 403, fail with actionable message (invalid/revoked key or license) |
| `token_cache.py` | **Delete** |

Protected calls keep the same paths and JSON bodies. Screenshot `204` → offline error unchanged. Paste wait timing unchanged.

`GET /state` may continue to send the Bearer header (harmless with a valid key). No new status tools in this change.

## Docs / messaging

Update README, ARCHITECTURE, and examples to state:

> As of TinyPilot Pro **3.2.0**, `tinypilot-mcp` authenticates with a persistent API key from **System → Automation**. Ephemeral `POST /api/v1/auth` tokens are not supported. This package requires TinyPilot Pro 3.2.0 or later.

Also:

- Remove “password-protected WebUI blocks REST API” (obsolete as of 3.2.0).
- Migration: upgrade package → add `api_key` per device → restart MCP host / server process.
- Architecture diagram: config-held API key instead of `/api/v1/auth` + token cache.

## Tests

- Assert `Authorization: Bearer <api_key>` on screenshot/keystroke/etc.
- Remove tests that mock `/api/v1/auth` and 403 token refresh.
- Add: 403 → error string mentions API key / license.
- Add: config without `api_key` fails validation.

## Out of scope

- Dual-mode / legacy `/auth` for pre-3.2.0 firmware
- Env var or keychain secret backends
- New MCP tools or Web UI API endpoints
- Changes to Proxmox demo playbooks (operators must put keys in local `devices.json`)

## Rollout

1. Implement + `pytest -v` in this repo.
2. Bump package version to **0.2.0** (breaking).
3. Ponytail pass on the diff (expect net deletion: `TokenCache`, auth retry).
4. Publish to PyPI when ready (separate explicit step).
5. Existing installs keep working on 0.1.0 until users upgrade the package; devices already on Pro 3.2.0 are already broken against 0.1.0 auth.

## Success criteria

- Fresh install with `api_key` set talks to a Pro 3.2.0+ device without calling `/api/v1/auth`.
- Docs state the 3.2.0 requirement prominently.
- No token cache module; no speculative auth abstraction.
