# Other tool features — tracked checklist

**Source:** `Documents/Personal/github/SuperAI/OtherToolFeatures.txt` (copied 2026-07-14)  
**Policy:** inspire or reuse code as convenient. Plan features are **required** (sequenced).  
**Board:** also mirrored under Track J in `TASKBOARD.md`.

**Legend:** `[ ]` pending · `[~]` in progress · `[x]` done

---

## Overview / philosophy

- [x] SuperAI as unifying **supervisor** layer (orchestrator + CLI)
- [x] Modularity / extensibility (package layout, registries)
- [ ] Deeper plugin system for third-party adapters

---

## 1. LLM Council  
Repo: https://github.com/Mohamadreza-Shahmohamadi/LLM_Council_ApplimentAI_Enhanced

- [x] Multi-agent deliberation / debate patterns (`agentic`, `council`)
- [x] Debate, critique, extend workflows
- [x] Voting modes: **majority** | **supervisor** | **weighted** (user-selectable)
- [x] Stage-based task classification (router)
- [~] Richer multi-model collaboration stages (plan → debate → vote → act)
- [~] Advanced supervisor prompt packs
- [x] Structured agent message envelopes (JSON)

---

## 2. OpenClaw  
Repo: https://github.com/openclaw/openclaw

- [x] Local-first defaults (mock_mode, local memory/backup)
- [~] Personal assistant capabilities (partial via CLI suite)
- [x] Tool propose → approve → execute (`tool_proposals`)
- [x] Human approval default via **config flag** (`require_human_approval`)
- [~] Self-improving loop (learning + skills; deepen tool-usage learning)
- [~] User modeling / preference learning
- [x] Privacy-oriented local storage under `~/.superai/`

---

## 3. Hermes-Agent  
Repo: https://github.com/NousResearch/hermes-agent  
Related: https://github.com/AtomicBot-ai/atomic-hermes

- [x] Agentic workflows foundation (debate / critique-extend)
- [~] Advanced hierarchical delegation
- [x] Multi-round deliberation
- [~] Self-improving agent loops (stronger)
- [x] Observability via logs/history/health
- [x] Skill-like reusable components
- [ ] Atomic-hermes: time-travel file history, multi-messenger (later)

---

## 4. Mempalace  
Repo: https://github.com/MemPalace/mempalace

- [x] Wings & rooms
- [x] Semantic memory (Chroma + embeddings path)
- [x] Memory versioning / provenance fields (basic)
- [x] Long-term decay / distill / conflicts
- [~] Shared terminal + web memory query UI
- [x] Consolidation techniques (distill)

---

## 5. Databao-Agent  
Repo: https://github.com/realburhanhusain/databao-agent

- [ ] NL → tables/charts over SQLAlchemy sources
- [ ] Broad DB adapters (Postgres, MySQL, SQLite, DuckDB, BQ, Snowflake, …)
- [ ] Conversational analytical context

---

## Secondary CLIs (workers)

| Tool | Status |
|------|--------|
| Claude Code | `[x]` registered + approval gate |
| Aider | `[x]` registered |
| Cursor | `[x]` registered |
| Grok / Gemini / Codex | `[x]` registered |
| Continue.dev | `[x]` registered (discover when on PATH) |
| Cline | `[x]` registered |
| Roo Code | `[x]` registered |

---

## Decisions (2026-07-14)

| Topic | Decision |
|-------|----------|
| Code reuse | Inspire **or** reuse as convenient |
| Council voting | **majority** \| **supervisor** \| **weighted** (user selects) |
| Human approval default | **Config flag** `require_human_approval` (default true for file-modifying) |
| This checklist | Live under SuperAI_v1 `docs/OTHER_TOOL_FEATURES.md` + Track J |
