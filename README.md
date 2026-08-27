# tinypilot-mcp

Host-agnostic MCP server for the [TinyPilot REST API](https://tinypilotkvm.com/pages/tinypilot-rest-api). Exposes fleet-aware KVM primitives for AI agent builders.

**Client-side:** runs on your machine next to Cursor (or other MCP hosts). Calls TinyPilot devices over the network.

## Requirements

- Python 3.11+
- TinyPilot Pro **3.2.0 or later** with an [Automation License](https://tinypilotkvm.com/pages/automation)
- A persistent API key from **System → Automation** on each device (keys work with WebUI user auth enabled)

## Quick start

```bash
pip install tinypilot-mcp
```

Create a fleet config (edit `base_url`, `api_key`, and device ids):

```bash
curl -sSL https://raw.githubusercontent.com/tiny-pilot/tinypilot-mcp/master/examples/devices.json \
  -o ~/tinypilot-devices.json
chmod 600 ~/tinypilot-devices.json
```

Create an API key on each device under **System → Automation**, set `api_key` in
the config, and keep that file out of git.

Wire it into your MCP host — see [MCP host setup](#mcp-host-setup). Set
`TINYPILOT_DEVICES` to the **absolute path** of your `devices.json`. The server
logs to **stderr** only (stdio MCP transport).

**No global install?** Use `uvx tinypilot-mcp` as the MCP `command` with
`"args": ["tinypilot-mcp"]`.

### Migrating from 0.1.x

1. Upgrade the device to TinyPilot Pro **3.2.0+** and create an API key.
2. `pip install -U tinypilot-mcp` (0.2.0+).
3. Add `"api_key": "..."` to every device in `devices.json`.
4. Restart the MCP server / host.

## MCP host setup

Use `tinypilot-mcp` (after `pip install`) or `uvx` with `args: ["tinypilot-mcp"]`. Set `TINYPILOT_DEVICES` to your config path.

### Cursor

Edit `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project):

```json
{
  "mcpServers": {
    "tinypilot": {
      "command": "tinypilot-mcp",
      "env": {
        "TINYPILOT_DEVICES": "/absolute/path/to/devices.json"
      }
    }
  }
}
```

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the equivalent config path on your OS:

```json
{
  "mcpServers": {
    "tinypilot": {
      "command": "tinypilot-mcp",
      "env": {
        "TINYPILOT_DEVICES": "/absolute/path/to/devices.json"
      }
    }
  }
}
```

### Claude Code

Project scope — create `.mcp.json` in your repo root (shareable via git):

```json
{
  "mcpServers": {
    "tinypilot": {
      "type": "stdio",
      "command": "tinypilot-mcp",
      "env": {
        "TINYPILOT_DEVICES": "/absolute/path/to/devices.json"
      }
    }
  }
}
```

User scope — add the same entry under `mcpServers` in `~/.claude.json`, or run:

```bash
claude mcp add tinypilot --scope user -- tinypilot-mcp
```

Then set `TINYPILOT_DEVICES` in the server env via `claude mcp add-json` or by editing the config file directly.

### VS Code

Edit `.vscode/mcp.json` (workspace) or run **MCP: Open User Configuration**:

```json
{
  "servers": {
    "tinypilot": {
      "type": "stdio",
      "command": "tinypilot-mcp",
      "env": {
        "TINYPILOT_DEVICES": "/absolute/path/to/devices.json"
      }
    }
  }
}
```

Use **Agent mode** in Copilot Chat to invoke MCP tools.

## Tools

All tools use the `tinypilot_` prefix. Input tools accept optional `device_id`; if omitted, the active device from `tinypilot_select_device` is used.

| Tool | Access | Description |
|------|--------|-------------|
| `tinypilot_list_devices` | read | List devices from local config (no network call) |
| `tinypilot_select_device` | input | Set the active device for subsequent calls |
| `tinypilot_get_stream_state` | read | Online status + resolution (text only) — not for reading UI |
| `tinypilot_capture_screenshot` | read | Capture target console; returns JPEG + metadata |
| `tinypilot_paste_text` | input | Paste text; server waits before returning |
| `tinypilot_send_keystroke` | input | Send a single keystroke |
| `tinypilot_mouse_event` | input | Mouse move/click/scroll — relative (0.0–1.0) **or** `pixel_x`/`pixel_y` |

`tinypilot_get_stream_state` uses the unofficial uStreamer `GET /state` endpoint. Use it for **online status and resolution** (e.g. converting `pixel_x`/`pixel_y` for mouse events). Use **`tinypilot_capture_screenshot`** whenever you need to read the UI, find click targets, or verify an action worked — stream state does not show screen content.

For mouse clicks, call `tinypilot_get_stream_state` for resolution, then pass `pixel_x`/`pixel_y` to `tinypilot_mouse_event` — the server converts to relative coords. Mouse responses echo both relative and pixel positions when resolution is known.

## Fleet workflow

There is no TinyPilot fleet API. Multiple devices are configured as URLs in `devices.json`. A typical agent loop:

1. **`tinypilot_list_devices`** — show configured ids, labels, aliases, and active device
2. **`tinypilot_select_device`** — pick the target by `device_id` (required before input)
3. **`tinypilot_get_stream_state`** — check online + resolution (not for reading UI)
4. **`tinypilot_capture_screenshot`** — read screen content; verify before and after each input
5. **Input tools** — paste, keystroke, or mouse (`pixel_x`/`pixel_y` from step 3)

Paste timing is enforced server-side: `tinypilot_paste_text` waits `(100ms × character count) + buffer` before returning. Do not send keystrokes until paste completes.

MCP hosts load **server instructions** at connect time (observe → act → verify, prefer keyboard over mouse). Input tool responses include a verify-next hint. Install the workflow skill below for full guidance.

Screenshots are saved to `{output_dir}/screenshots/{device_id}-{timestamp}.jpg`. Actions are logged to `{output_dir}/actions.jsonl`.

## Capability tiers

Set `defaults.capabilities` in `devices.json` to limit which tools are registered:

| Capability | Tools enabled |
|------------|---------------|
| `read` | `tinypilot_list_devices`, `tinypilot_get_stream_state`, `tinypilot_capture_screenshot` |
| `input` | `tinypilot_select_device`, `tinypilot_paste_text`, `tinypilot_send_keystroke`, `tinypilot_mouse_event` |

Default: `["read", "input"]`. Use `["read"]` for read-only diagnostics — input tools are not registered.

## Workflow skill

Install the companion skill for observe → act → verify guidance:

**[tinypilot-ai-agent-skills](https://github.com/tiny-pilot/tinypilot-ai-agent-skills)**

This MCP server provides execution primitives; the skill teaches agents how to use them safely across a fleet.

## Safety

**Validate on non-production hardware first.** MCP tool annotations (`readOnlyHint`, `destructiveHint`) are hints for hosts, not security guarantees. Agents can send real keystrokes and mouse events to physical targets. Use capability tiers and the workflow skill to limit blast radius.

## Development

From a git checkout:

```bash
git clone https://github.com/tiny-pilot/tinypilot-mcp.git
cd tinypilot-mcp
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pytest -v
```

Published on [PyPI](https://pypi.org/project/tinypilot-mcp/) as `tinypilot-mcp`.

AI agents changing this repo: read [AGENTS.md](AGENTS.md).

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [AGENTS.md](AGENTS.md) — scope and conventions for AI agents

## License

MIT — see [LICENSE](LICENSE).
