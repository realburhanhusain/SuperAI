# SuperAI Memory API Contract (Phase 9+ multi-client)

**Status:** Implemented (contract + thin clients)  
**Date:** 2026-07-23  
**Transports:**
1. **MCP** (stdio NDJSON) — preferred for agents  
2. **CLI** — `superai …` for humans/scripts  
3. **Library** — Python `core.*` in-process  

Thin clients **must not** open SuperAI SQLite/Postgres files directly.

## Common response envelope

```json
{
  "ok": true,
  "product": "string",
  "message": "human summary",
  "error": null,
  "error_code": null
}
```

On failure: `ok=false`, `error` string, optional `error_code` (`validation|ssrf|not_found|…`).

## Operations

| Op | MCP tool | CLI | Notes |
|----|----------|-----|--------|
| Status | `superai_status` | `superai doctor` / status | Env snapshot |
| Search / recall | `superai_memory_search` | `superai recall` | strategy=auto\|… |
| Store | `superai_memory_store` | (palace via API) | tags, importance |
| Cognify | `superai_cognify` | `superai cognify` | mode=mock\|llm |
| Ingest | `superai_ingest` | `superai ingest` | path/url |
| KG query | `superai_kg_query` | `superai kg query` | |
| Session | `superai_session` | `superai memory-session` | |
| Dataset | `superai_dataset` | `superai dataset` | |
| Ontology | `superai_ontology` | `superai ontology` | |
| Capture | `superai_capture` | `superai capture` | |
| Host hook | `superai_host_hook` | `superai host-hook` | Phase 9+ |
| Cloud status | `superai_memory_cloud` | `superai cloud` | Phase 9+ |
| OTEL status | `superai_memory_otel` | `superai otel` | Phase 9+ |
| Eval | — | `superai memory-eval` | Offline |

## Auth

Local MCP/CLI: process identity (user machine).  
Managed cloud (optional): `SUPERAI_MEMORY_CLOUD_TOKEN` bearer — never log.

## Thin clients

| Language | Path |
|----------|------|
| Python | `clients/python/superai_memory_client.py` |
| TypeScript | `clients/typescript/superaiMemoryClient.ts` |

Both wrap **CLI subprocess** by default (portable, no native DB). Optional HTTP if `SUPERAI_HTTP_BASE` is set (future web surface).
