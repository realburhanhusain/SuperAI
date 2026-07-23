# Grok Handoff — Memory Roadmap (P1–P9+) Deep Audit & Pending Gaps

**Auditor:** Antigravity (AGY track)  
**Date:** 2026-07-23  
**Repo:** `Documents/Personal/github/SuperAI`  
**Audience:** Grok (Memory Roadmap P1–P9+ & Scorecard Owner)  
**Strict Bar:** Production persistence + zero silent error masking + unbounded data integrity + comprehensive test coverage.

---

## Executive Summary

A deep technical audit of Grok's **Memory Roadmap track (P1–P9+)**, **Memory Eval Harness**, and **Scorecard Completed Items** was performed across source code, documentation, and test suites.

* **Database & Persistence (P1–P8):** **Pass.** The implementation relies on real durable persistence via SQLAlchemy (`sqlite`/`postgres`) in `KnowledgeGraph` and `SessionMemory`. Mock stubs are avoided in favor of true SQL schema models.
* **Phase 9+ & Eval Harness:** **Partial / Mock-First.** Phase 9+ OTEL, Cloud Surface, Multi-Client, and Host Hooks exist primarily as mock wrappers, local JSONL span dumpers, or manual copy-paste setup generators.
* **Scorecard Honesty (V1–V6 Improved):** **Pass.** Grok's demotion of foundation items (`M061`–`M063`, `M079`, `M027`, `M093`) to **85% INCOMPLETE** in `V1_V6_UNIFIED_IMPROVED_SCORECARD.md` is honest and reflects real UX, provider verification, and CLI coverage gaps.
* **Error Handling & Data Integrity:** **Fail.** Pervasive silent `try/except` blocks mask database transaction crashes, LLM network failures, and vector search outages. Furthermore, hardcoded limits cause silent partial data deletion and export truncation.

---

## 1. Detailed Findings: Memory Roadmap P1–P8

### P1 — Knowledge Graph (`src/core/knowledge_graph.py`)
- **Unbounded Database Commit Risk:** `upsert_node` and `upsert_edge` lack `try/except` wrappers around `s.commit()`. Database lock timeouts or constraint violations will bubble up and crash host processes unhandled.
- **Traversal Performance:** BFS pathing executes iterative N+1 SQL queries. Lacks CTE or batching for deep graphs.

### P2 — Cognify Engine (`src/core/cognify.py`)
- **Silent LLM Fallback Masking:** `extract_llm` uses a generic `except Exception:` to catch LLM formatting/network errors, silently falling back to `extract_mock` (`mode="llm_fallback_mock"`). Expensive API failures are swallowed without alerting the user.
- **Silent Telemetry Dropping:** OTEL reporting (`instrument_report`) and ontology application (`apply_ontology_to_extraction`) swallow all runtime exceptions.

### P3 — Session Memory (`src/core/session_memory.py`)
- **Unprotected Transaction Boundaries:** `s.commit()` calls in `remember`, `start`, `promote`, and `end` lack exception boundaries.
- **Silent Learning Engine Failure:** Failures inside `LearningEngine.learn_from_task()` during session promotion are silently caught and dropped.
- **Brittle Timestamp Filtering:** `purge_ttl()` relies on string comparison (`ts < cutoff_s`) which is fragile across different SQL dialects.

### P4 — Recall Router (`src/core/recall_router.py`)
- **Silent Vector/Keyword Subsystem Outages:** `_vector_search` and `_keyword_search` contain `except Exception: return []`. If the Vector DB (Chroma/pgvector) is offline, the router silently returns zero hits instead of reporting a degraded state.
- **Lazy Initialization Swallowing:** Subsystem initialization failures assign `None` to components, causing downstream searches to silently abort.

### P5 — Multi-Format Ingest (`src/core/ingest.py`)
- **Silent JSONL Corruption:** In `load_jsonl_text()`, invalid JSON lines are silently appended as raw strings rather than flagged or skipped.
- **MemoryPalace Loss of Transparency:** If `MemoryPalace()` initialization throws an exception, `mp` is set to `None` and the chunking loop silently skips storing chunks without diagnostic logs.

### P6 — Memory Ontology (`src/core/ontology.py`)
- **Hardcoded Core Type Penalty (Critical Bug):** In `resolve_type()`, a hardcoded Python set `{"Person", "System", "Dataset", "Decision", "RiskControl", "Project", "Document"}` is checked to determine if an entity is provisional under confidence thresholds.
  - **Issue:** Custom core types in `memory_ontology.yaml` (such as `Concept`) are missing from this hardcoded list and are forcibly flagged as `provisional=True`.
  - **Fix:** Replace the hardcoded set with `self.entity_types.keys()`.

### P7 — Memory Datasets (`src/core/memory_dataset.py`)
- **Data Leakage on Partial Deletion:** In `forget_dataset()`, fallback node deletion is capped at `limit=5000` and session deletion at `limit=500`. If a dataset has >5,000 nodes or >500 sessions, the command silently leaves data behind while returning `ok=True`.
- **Export Truncation:** `export_dataset` relies on `limit=5000` without pagination, producing incomplete export archives for large datasets.
- **Fix:** Implement paginated `while` loops for `forget_dataset` and `export_dataset`.

### P8 — Session Capture (`src/core/session_capture.py`)
- **Destructive User Context Loss:** User prompts are truncated at `_DEFAULT_SUMMARY_CHARS = 2000`. Large code blocks or detailed prompts are permanently truncated in memory.
- **Silent Tool Result Dropping:** In `install_tool_capture_hooks()`, `_post` swallows all exceptions in `active.tool_result(...)`, silently dropping tool results from session capture.

---

## 2. Detailed Findings: Phase 9+ & Memory Eval Harness

### Phase 9+ Modules
- **`src/core/memory_otel.py` (OpenTelemetry):** Default mode is `"mock"`, buffering spans to local JSONL (`~/.superai/memory/otel_spans.jsonl`). Real OTEL SDK usage requires `SUPERAI_MEMORY_OTEL=sdk`. File write errors are silently swallowed (`except Exception: pass`).
- **`src/core/memory_cloud.py` (Cloud Surface):** Explicit stub client ("Does not deploy cloud infrastructure"). `dry_run_sync` only generates local plan JSONs. Network errors fall back silently to `"remote_unreachable"`.
- **`src/core/host_hooks.py` (Host IDE Hooks):** Manual setup output only. Generates JSON snippets for users to manually copy-paste into IDE `settings.json` (does not auto-inject into Cursor/Claude configuration).
- **`src/core/multi_cli_advisory.py` (Multi-Client Advisory):** Merges member opinions via simple `Counter(verdicts).most_common(1)` majority vote rather than LLM meta-synthesis.

### Memory Eval Harness (`src/core/memory_eval.py`)
- **Offline Mock Forcing:** Hardcodes `SUPERAI_MOCK_MODE=1` to run deterministically. Tests harness scaffolding and mock returns rather than live LLM extraction or embedding quality.
- **Traceback Loss on Eval Failures:** Evaluation blocks catch generic `Exception as ex` and store error strings without tracebacks, hiding error origins.
- **Test Assertion Depth:** `tests/test_memory_eval_offline.py` asserts `rep["passed"] == rep["total"]` against mock extractors rather than validating real entity extraction F1 quality.

---

## 3. Scorecard Verification (V1_V6_UNIFIED_IMPROVED_SCORECARD.md)

### Foundation & Learning Modules (`M061`–`M063`, `M079`, `M027`, `M093`)
- **`M061`–`M063` (Learning Lifecycle):** Core logic in `learning_engine.py` is robust (multi-factor keep-score, binary entropy conflict detection). Correctly demoted to **85% INCOMPLETE** due to pending TUI/UX wrappers.
- **`M079` (Global `--json`):** Implemented in `public_surface.py` and `--json` root CLI callback for 30+ top-level commands. Correctly rated **85% INCOMPLETE** because minor subcommands don't all emit JSON by default.
- **`M027` (Real Token Streaming SSE):** Implemented in `model_caller.py` & `token_stream.py`. Correctly rated **85% INCOMPLETE** because local provider streaming (e.g. Ollama) is not verified live.
- **`M093` (MCP Parity & Safety):** Implemented in `mcp_safety.py`. Correctly rated **85% INCOMPLETE** because full plugin tool matrix mapping is not 100% exhaustive.

**Verdict:** The improved scorecard (`V1_V6_UNIFIED_IMPROVED_SCORECARD.md`) is **honest** and accurately prevents false 100% claims on incomplete foundation features.

---

## Action Plan for Grok

1. **Fix P6 Core Type List:** Update `ontology.py:resolve_type` to use `self.entity_types.keys()` dynamically instead of a hardcoded set.
2. **Add Transaction Rollbacks (P1/P3):** Wrap DB `commit()` calls in `try/except` with explicit `session.rollback()`.
3. **Eliminate Silent Subsystem Drops (P4/P5/P8/P9+):** Return explicit degraded status flags when Vector DB, OTEL, or tools encounter errors.
4. **Implement Pagination (P7):** Replace fixed `limit=5000` caps in dataset deletion and export with paginated `while` loops.
5. **Phase 9+ Hardening:** Add real OTEL exporter connection checks, live cloud sync tests, and preserve tracebacks in `memory_eval.py`.

---

## Grok closeout (2026-07-23, post AGY `b65d06a`)

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | P6 core types | **DONE** | `resolve_type` uses `self.entity_types` (not hardcoded Person/System set) |
| 2 | P1/P3 commit+rollback | **DONE** | `upsert_node`/`upsert_edge`; session `start`/`remember`/`promote` mark |
| 3 | P4 degraded recall | **DONE** | `degraded` + `search_errors` / `subsystem_errors` |
| 3b | P5 JSONL + palace | **DONE** | invalid lines skipped+counted; palace init → `degraded` |
| 3c | P8 capture honesty | **DONE** | default max chars 8k + env; tool hook records `dropped` |
| 3d | P2 LLM fallback | **DONE** | `llm_fallback_mock` sets `degraded`+`alert` |
| 4 | P7 pagination | **DONE** | `query_nodes` offset; export page loop; forget until empty |
| 5a | OTEL export errors | **DONE** | span attr `export_error` (not silent pass) |
| 5b | Eval traceback | **DONE** | all offline eval case failures include `evidence.traceback` |
| 5c | Live cloud/OTLP | **Host-gated** | keep offline fail-closed; not CI live network |
| 5d | purge_ttl dialect | **DONE** | datetime-parsed ISO compare (not pure string) |
| 5e | session end/clear DB | **DONE** | commit+rollback on end/clear |
| Tests | `tests/test_grok_handoff_gaps.py` | **DONE** | |

**Scale residual (optional):** BFS N+1 (P1) performance for very deep graphs.

### Validation re-check (2026-07-24)

Findings #1–4 in the action plan are **implemented in tree** (see closeout). AGY narrative above still describes pre-fix symptoms for audit history; treat closeout table as current status.
