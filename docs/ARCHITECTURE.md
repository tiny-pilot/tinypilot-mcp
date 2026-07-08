# Architecture

## Overview

**Client-side MCP.** `tinypilot-mcp` runs on the user's machine next to the MCP host. It does not run on the TinyPilot appliance.

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
│  ┌──────▼──────┐  ┌──────────────┐  ┌───────────────┐   │
│  │ client.py   │  │ token_cache  │  │ action_log    │   │
│  └──────┬──────┘  └──────────────┘  └───────────────┘   │
└─────────┼───────────────────────────────────────────────┘
          │ HTTPS per device
┌─────────▼───────────────────────────────────────────────┐
│  TinyPilot device A    TinyPilot device B    …          │
│  POST /api/v1/auth     (independent REST endpoints)     │
│  GET  /api/v1/screenshot                                │
│  GET  /state (unofficial)                                 │
│  POST /api/v1/keystroke | mouseEvent | paste            │
└─────────────────────────────────────────────────────────┘
```

There is **no central TinyPilot fleet API**. Multiple devices = multiple URLs in local config.

## Module responsibilities

| Module | Responsibility |
|--------|----------------|
| `config.py` | Load/validate `devices.json`; capability flags |
| `token_cache.py` | In-memory bearer tokens per `device_id` |
| `client.py` | httpx calls to one device's REST API; 403 retry |
| `stream_state.py` | Parse `GET /state` (online, resolution) |
| `coords.py` | Pixel ↔ relative coordinate conversion |
| `session.py` | Active device, resolve `device_id`, paste wait |
| `errors.py` | Agent-facing error message strings |
| `action_log.py` | Append-only JSONL audit hook |
| `server.py` | FastMCP registration, instructions, tool handlers |
| `tools/annotations.py` | `readOnlyHint`, `destructiveHint`, etc. |

## Session state (in-process)

- `active_device_id` — set by `tinypilot_select_device`
- `token_cache[device_id]` — until TinyPilot restart or 403
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

**Linked separately:** tinypilot-ai-agent-skills (workflow; not bundled)

## Dependencies

- `mcp` — protocol server (FastMCP)
- `httpx` — sync HTTP to TinyPilot (simple; paste wait uses `time.sleep`)
- `pydantic` — config + tool input models

No ORM, no web framework, no CLI beyond `tinypilot-mcp` entry point.
