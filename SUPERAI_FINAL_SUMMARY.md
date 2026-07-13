# SuperAI — Project Summary (honest)

**Updated:** 2026-07-13  
**Codebase:** SuperAI  

## Overview

SuperAI aims to be a multi-model orchestration platform with learning, skills, and encrypted backup.  
**What exists today is a solid Phase 1 foundation plus draft modules for later phases** — not a finished production product.

## What works now (verified)

- Installable package (`pip install -e .`) with CLI entry `superai`
- `init`, `run` (mock), `plan`, `status`, `history`, `config *`, `list-models`
- Config under `~/.superai/`, dual logging, task history JSON
- Orchestrator: plan → sequential steps → structured result → history
- Model registry loads `config/models.json`
- Unit tests for config, history, orchestrator, registry

## What is partial / draft

| Module | Reality |
|--------|---------|
| ModelRouter / LoadBalancer | Wired for selection + mock calls; scoring/fallback incomplete |
| ModelCaller live APIs | Code paths exist; need keys + extras; not fully hardened |
| MemoryPalace / LearningEngine | Present; integration best-effort; some methods need cleanup |
| SkillsManager | File CRUD; light orchestrator hook |
| BackupManager | Encrypt/compress sketch; restore/verify UX incomplete |
| External CLI discovery | Not implemented |
| Web dashboard | Sketch only |

## How to continue work

1. Open **[TASKBOARD.md](TASKBOARD.md)** — resume first incomplete track item.  
2. Follow **[AGENTS.md](AGENTS.md)** and the implementation plans.  
3. Reuse **[codes.md](codes.md)** before rewriting.

## Technology

- Python 3.10+, Typer, Rich, Pydantic, ChromaDB, cryptography, zstandard

## Conclusion

SuperAI is a **resumable engineering codebase**. Tracks A–E are complete for foundation + core Phases 2–5 (mock/local).  
**All remaining plan features are required** and sequenced as Tracks F–I (not optional).  
Future agents must **update the taskboard** and continue pending tracks — never restart from zero or drop plan scope.
