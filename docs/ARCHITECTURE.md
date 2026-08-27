# Architecture

## Overview

**Client-side MCP.** `tinypilot-mcp` runs on the user's machine next to the MCP host. It does not run on the TinyPilot appliance.

Requires TinyPilot Pro **3.2.0+**. Auth is a persistent API key from **System → Automation** (`Authorization: Bearer <API_KEY>`).

```
┌─────────────────────────────────────────────────────────┐
│  MCP host (Cursor, Claude Desktop, Claude Code, …)      │
│  (user's machine)                                       │
└───────────────────────────┬─────────────────────────────┘
                            │ stdio (JSON-RPC)
┌───────────────────────────▼─────────────────────────────┐
│  tinypilot-mcp (user's machine)                         │
│  ┌─────────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ server.py   │  │ session  │  │ config.py        │  │
│  │ (tools)     │──│ state    │──│ devices.json     │  │
│  └──────┬──────┘  └──────────┘  └──────────────────┘  │
│         │                                               │
│  ┌──────▼──────┐                ┌───────────────┐     │
│  │ client.py   │                │ action_log    │     │
│  └──────┬──────┘                └───────────────┘     │
└─────────┼───────────────────────────────────────────────┘
          │ HTTPS + Bearer API key per device
┌─────────▼───────────────────────────────────────────────┐
│  TinyPilot device A    TinyPilot device B    …          │
│  GET  /api/v1/screenshot                                │
│  GET  /state                                            │
│  POST /api/v1/keystroke | mouseEvent | paste            │
└─────────────────────────────────────────────────────────┘
```

There is **no central TinyPilot fleet API**. Multiple devices = multiple URLs + API keys in local config.

## Module responsibilities

| Module | Responsibility |
|--------|----------------|
| `config.py` | Load/validate `devices.json`; required `api_key` per device; capability flags |
| `client.py` | httpx calls to one device's REST API with Bearer API key |
| `stream_state.py` | Parse `GET /state` (online, resolution) |
| `coords.py` | Pixel ↔ relative coordinate conversion |
| `session.py` | Active device, resolve `device_id`, paste wait |
| `errors.py` | Agent-facing error message strings |
| `action_log.py` | Append-only JSONL audit hook (no paste content, no API keys) |
| `server.py` | FastMCP registration, instructions, tool handlers |
| `tools/annotations.py` | `readOnlyHint`, `destructiveHint`, etc. |

## Session state (in-process)

- `active_device_id` — set by `tinypilot_select_device`
- Config loaded once at startup from `TINYPILOT_DEVICES`

## Tool layers

| Capability | Tools |
|------------|-------|
| `read` | `tinypilot_list_devices`, `tinypilot_get_stream_state`, `tinypilot_capture_screenshot` |
| `input` | `tinypilot_select_device`, `tinypilot_paste_text`, `tinypilot_send_keystroke`, `tinypilot_mouse_event` |

Tools not in configured capabilities are **not registered**.

## Boundaries

**In scope:** Client-side REST primitive wrapper, fleet config, paste timing, stream state, pixel mouse coords, workflow hints in tool layer, local log

**Out of scope:**

- Server-side MCP on the appliance
- tinypilot-connector orchestration
- Composite workflow tools
- CMDB, ITSM, runbooks, admin API
- Host-specific code
- Pre-3.2.0 ephemeral `POST /api/v1/auth`

**Linked separately:** tinypilot-ai-agent-skills (workflow; not bundled)

## Dependencies

- `mcp` — protocol server (FastMCP; `mcp<2`)
- `httpx` — sync HTTP to TinyPilot (paste wait uses `time.sleep`)
- `pydantic` — config + tool input models

No ORM, no web framework, no CLI beyond `tinypilot-mcp` entry point.
