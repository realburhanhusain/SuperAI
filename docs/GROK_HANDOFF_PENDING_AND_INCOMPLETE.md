# Grok Handoff — Memory Roadmap (P1–P8) Deep Audit & Pending Gaps

**Auditor:** Antigravity (AGY track)  
**Date:** 2026-07-23  
**Repo:** `Documents/Personal/github/SuperAI`  
**Audience:** Grok (Memory Roadmap P1–P8 Owner)  
**Strict Bar:** Production persistence + zero silent error masking + unbounded data integrity + comprehensive test coverage.

---

## Executive Summary

A deep technical audit of Grok's **Memory Roadmap track (P1–P8)** was performed across source code, documentation, and test suites.

* **Database & Persistence:** **Pass.** The implementation relies on real durable persistence via SQLAlchemy (`sqlite`/`postgres`) in `KnowledgeGraph` and `SessionMemory`. Mock stubs are avoided in favor of true SQL schema models.
* **Test Suite Quality:** **Pass.** Tests execute against temporary SQLite files (`tmp_path`) and verify actual multi-hop BFS graph queries, session buffers, and dataset exports.
* **Error Handling & Data Integrity:** **Fail.** Pervasive silent `try/except` blocks mask database transaction crashes, LLM network failures, and vector search outages. Furthermore, hardcoded limits cause silent partial data deletion and export truncation.

---

## Detailed Findings by Subsystem

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

## Action Plan for Grok

1. **Fix P6 Core Type List:** Update `ontology.py:resolve_type` to use `self.entity_types` dynamically.
2. **Add Transaction Rollbacks (P1/P3):** Wrap DB `commit()` calls in `try/except` with explicit `session.rollback()`.
3. **Eliminate Silent Subsystem Drops (P4/P5/P8):** Return explicit degraded status flags when Vector DB or tools encounter errors.
4. **Implement Pagination (P7):** Replace fixed `limit=5000` caps in dataset deletion and export with paginated loops.
