# Agent Turn Capture — Memory Roadmap P8

**Status:** Implemented  
**Date:** 2026-07-23  
**Module:** `src/core/session_capture.py`  
**CLI:** `superai capture config|start|turn|end|stream`  
**MCP:** `superai_capture`  
**Depends on:** P3 session memory, P2 cognify (optional on end), P7 dataset id  
**Coordination:** Memory track only — does not touch AGY scorecard modules.

## What it does

Captures agent/CLI **turns into the session buffer** (not always permanent):

| Hook | Stored kind | Content |
|------|-------------|---------|
| `user_prompt` | `user` | User text (secrets redacted) |
| `tool_result` | `tool` | Tool name + summary + paths (redacted) |
| `assistant_final` | `assistant` | Answer summary (truncated) |
| `precompact` | `snapshot` | Forced session snapshot (pinned) |
| `session_end` | (end) | Status ended; promote/cognify per level |

## Capture levels

| Level | Buffer | On session_end |
|-------|--------|----------------|
| `off` | No | No side effects |
| `session` (default) | Yes | End only (no auto-promote) |
| `session+promote` | Yes | Promote pinned / high-importance |
| `full-cognify` | Yes | Promote + cognify (mock by default) |

Set via `--level`, `SUPERAI_CAPTURE_LEVEL`, or MCP `level`.

Aliases: `on`→session, `promote`→session+promote, `full`/`cognify`→full-cognify.

## Privacy & storage

| Rule | Detail |
|------|--------|
| **Secrets** | All captures run through `secrets.redact_text` (API keys, tokens, passwords) |
| **Storage path** | Session DB: `~/.superai/memory/sessions.sqlite` (or `SUPERAI_SESSION_DSN`) |
| **Permanent data** | Only after promote (level promote/cognify or explicit `memory-session promote`) |
| **Palace path** | `~/.superai/memory/` palace backend after promote |
| **Never** | Raw credentials, full secret-bearing tool dumps |

See `superai capture config` for live paths and level.

## CLI

```powershell
superai capture config

superai capture start --id demo1 --level session --dataset superai
superai capture turn user_prompt "What is Cloud SQL?" -s demo1
superai capture turn tool_result "found docs" -s demo1 --tool search
superai capture turn assistant_final "Cloud SQL is managed Postgres" -s demo1
superai capture turn precompact "compacting" -s demo1
superai capture end -s demo1 --level session+promote

# Offline E2E stream
superai capture stream "[{`"hook`":`"user_prompt`",`"content`":`"hi`"},{`"hook`":`"assistant_final`",`"content`":`"hello`"}]" --level session
```

## MCP

Tool **`superai_capture`**:

- `action=config|start|turn|end|stream`
- `session_id`, `hook`, `content`, `tool`, `level`, `dataset_id`
- `turns` (array) for stream
- `install_hooks=true` registers process tool post-hooks

## Library / agent integration

```python
from core.session_capture import SessionCapture, process_turn_stream, install_tool_capture_hooks

cap = SessionCapture.start(title="agent-run", level="session", source="agent-tui")
install_tool_capture_hooks(cap)  # optional: core.hooks post-tool

cap.user_prompt("...")
cap.tool_result("bash", {"ok": True, "summary": "done", "path": "x.py"})
cap.assistant_final("...")
cap.precompact()
cap.session_end()

# Or batch:
process_turn_stream([...], level="session+promote", auto_end=True)
```

Optional later: Claude Code / Grok host hooks call MCP `superai_capture` (not required for P8 DoD).

## Safety

- Respects capture `off` toggle (DoD)
- Mock cognify on `full-cognify` by default
- Permission: capture writes session only; promote/cognify follow P3 rules

## Tests

`tests/test_session_capture_p8.py` — level aliases, config, off toggle, E2E turn stream, secret redaction, promote/cognify levels, tool hook install, precompact pin.

## Honest limits

- Host IDE hooks (Claude/Grok native) are **optional later**; SuperAI CLI/MCP/agent API is the P8 surface.
- Tool hook install is process-local via `core.hooks` (not multi-process).
- Summaries truncate long tool/assistant text; full logs are not mirrored.
