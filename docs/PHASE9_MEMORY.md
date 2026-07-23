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

## Residual follow-ups (non-host)

Shipped = vertical slice works offline. These are **product depth** items still open
(not host-gated smoke; not “phase unbuilt”). Track here rather than only in chat.

| ID | Area | Residual | Suggested direction |
|----|------|----------|---------------------|
| **P9-R1** | OTEL coverage | Spans are light: recall uses `instrument_report`; cognify / ingest / capture / dataset not fully span-wrapped | Add `memory_span` / `instrument_report` on those hot paths; keep content redaction |
| **P9-R2** | OTEL SDK path | `SUPERAI_MEMORY_OTEL=sdk` is best-effort if `opentelemetry` is installed; no exporter/endpoint UX | Document env for OTLP endpoint when SDK present; optional `otel configure` later |
| **P9-R3** | Cloud push | `cloud dry-sync` only builds export + plan (`network_write: false`) | Define push protocol + auth; real upload behind explicit `--apply` + reachability |
| **P9-R4** | Multi-client HTTP | Thin clients default to `superai --json` subprocess | Optional HTTP JSON client when `SUPERAI_HTTP_BASE` / web surface is stable |
| **P9-R5** | Client packaging | Python/TS clients live under `clients/` only | Optional publish as installable packages (pip/npm) with version pin to CLI |
| **P9-R6** | Host-hook install | `host-hook install-snippet` prints MCP/hooks JSON only | Keep manual by design; optional guided checklist CLI (still no silent rewrite of host config) |
| **P9-R7** | Eval × P9 | `memory-eval` covers P1–P8 smoke, not OTEL/cloud/host-hook cases | Extend offline eval with otel buffer + host-hook emit + cloud status local_only |

### Host-gated (do not treat as in-repo “todo” for offline CI)

- Live OTLP collector / production exporter proof  
- Real managed SuperAI Cloud control plane + live `/health` proof  
- Auto-writing Claude Code / Grok / Cursor `settings.json`  
- Phase 99 multi-provider live smoke  

See also: `TASKBOARD.md` → **Grok Memory Track** `[!]` rows.

## Related

- P1–P8 roadmap: `docs/MEMORY_ROADMAP_COGNEE_GAPS.md`  
- Capture: `docs/SESSION_CAPTURE.md`  
- Offline eval: `docs/MEMORY_EVAL.md`  
- API contract: `docs/clients/MEMORY_API_CONTRACT.md`  
