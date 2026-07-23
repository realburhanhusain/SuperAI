# Memory Phase 9+ — OTEL, multi-client, managed cloud, host hooks

**Status:** Implemented (offline-first honesty)  
**Date:** 2026-07-23  
**Track:** Grok memory — disjoint from AGY scorecard hardening  

Phase 9+ is the **roadmap backlog** after Cognee gaps 1–8: observability, multi-language clients, optional managed cloud, and host IDE capture adapters.

## Components

| Area | Module | CLI | MCP |
|------|--------|-----|-----|
| OTEL spans | `core.memory_otel` | `superai otel status\|list\|demo` | `superai_memory_otel` |
| Managed cloud | `core.memory_cloud` | `superai cloud status\|configure\|dry-sync` | `superai_memory_cloud` |
| Host hooks | `core.host_hooks` | `superai host-hook emit\|install-snippet` | `superai_host_hook` |
| Multi-client | `docs/clients/MEMORY_API_CONTRACT.md` + thin clients | — | same MCP tools |

## OTEL (mock-first)

| Mode (`SUPERAI_MEMORY_OTEL`) | Behavior |
|------------------------------|----------|
| `off` / `0` | Disabled |
| `mock` / default | In-process ring buffer + JSONL under `~/.superai/memory/otel_spans.jsonl` |
| `sdk` / `otlp` | Best-effort real OpenTelemetry tracer if package installed; else mock |

**Never** records free-text memory content — only op names, counts, strategy, dataset_id, timings.

```powershell
$env:SUPERAI_MEMORY_OTEL="mock"
superai otel demo
superai otel list
superai --json otel status
```

Recall attaches `otel_mode` when enabled via `instrument_report`.

## Managed cloud (honest)

Does **not** provision cloud. Provides:

- Local config (`~/.superai/memory/cloud_config.json`)
- Health probe (fail soft offline)
- **Dry-run sync** — builds dataset export zip + plan, **no network write**

```powershell
superai cloud status
superai cloud configure --api-base https://example.com/memory --enable
superai cloud dry-sync --dataset superai
```

Token: env `SUPERAI_MEMORY_CLOUD_TOKEN` only (never printed). DSN passwords redacted in status.

## Host hooks

Maps Claude/Grok-style events → P8 `SessionCapture`.

```powershell
superai host-hook emit start --session demo9
superai host-hook emit user_prompt -c "hello" --session demo9
superai host-hook emit session_end --session demo9
superai host-hook install-snippet --host claude
```

Install snippets are **manual** — SuperAI does not rewrite host `settings.json`.

## Multi-language clients

| Client | Path |
|--------|------|
| Contract | `docs/clients/MEMORY_API_CONTRACT.md` |
| Python | `clients/python/superai_memory_client.py` |
| TypeScript | `clients/typescript/superaiMemoryClient.ts` |

Both default to `superai --json …` subprocess — no direct DB access.

## Tests

`tests/test_phase9_memory.py` — OTEL, cloud local/dry-sync, host hooks, client import.

## Non-goals

- Real multi-region SaaS control plane  
- Auto-install host hooks  
- Mandatory OpenTelemetry dependency  
- Live network tests in CI  

## Related

- P1–P8 roadmap: `docs/MEMORY_ROADMAP_COGNEE_GAPS.md`  
- Capture: `docs/SESSION_CAPTURE.md`  
- Offline eval: `docs/MEMORY_EVAL.md`  
