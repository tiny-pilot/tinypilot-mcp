# Agent development guide

Instructions for AI agents working on **tinypilot-mcp**. Read [Architecture](docs/ARCHITECTURE.md) first.

## Product constraints

- **Client-side MCP** — runs on the user's machine; stdio to MCP host; not on the TinyPilot appliance
- **Host-agnostic** — stdio only; no Cursor-specific code
- **Atomic primitives only** — no composite workflow tools (paste+Enter bundles, runbooks)
- **Fleet via local config** — no network discovery, no TinyPilot fleet API
- **Skill is linked, not bundled** — workflow lives in [tinypilot-ai-agent-skills](https://github.com/tiny-pilot/tinypilot-ai-agent-skills)
- **Connector is out of scope** — not part of this offering

## Out of scope (do not add without explicit request)

- Server-side MCP on the appliance or streamable HTTP transport
- CMDB, ITSM, orchestration, admin API tools
- Bundling the skill repo
- Host-specific code paths

## Code conventions

- Python 3.11+; `from __future__ import annotations` in library modules
- Pydantic models for config and tool inputs; flat schemas (no `$ref` / `oneOf`)
- Sync httpx; paste wait blocks intentionally
- Tools: `tinypilot_*` prefix; annotations on every tool; actionable error strings
- Log to **stderr** only — stdout is MCP protocol
- Action log: no paste content, no tokens
- Tests: `pytest` + `pytest-httpx`; mock HTTP, not hardware
- Minimum diff; no new dependencies without good reason

## When changing code

1. Read surrounding code; match existing style
2. Run `pytest -v` before committing
3. One logical commit per change (`feat:`, `fix:`, `docs:`, `test:`, `chore:`)
4. Do not commit secrets, tokens, or real device URLs
5. Do not log to stdout

## Escalate (do not guess) when

- Change requires new tools or dependencies not in `pyproject.toml`
- MCP SDK API differs from existing patterns in `server.py`
- Architectural change beyond REST primitive wrapping
