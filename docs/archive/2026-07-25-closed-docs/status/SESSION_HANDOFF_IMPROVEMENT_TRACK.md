# Session handoff — compact summary (token-optimized resume)

**Date:** 2026-07-16  
**Repo:** SuperAI · branch `master` (push plan docs after this write)  
**Next action:** Implement **IMPROVEMENT_PLAN Phase 1** only — do not re-litigate vision.

---

## What SuperAI already is (do not rebuild)

- Multi-model orchestrator (plan → route → execute → learn)  
- Multi-CLI boards: `review` / `advise` / `council`; workers via `member_selection`  
- Universal models: provider_catalog, registry base_url/keys, Ollama sync, models-register, NVIDIA/OW/gateways (~40 models)  
- NL: `superai ask` + REPL + chat routing (`nl_intent`)  
- Memory Palace (pgvector/SQLite), install wizard, security hardening  
- Historical backlog M/S/N + G-tracks **code complete**  

**Not Claude Code fork** — orchestrator + multi-CLI hub; agent depth still partial.

---

## Standing policies

1. **Live smoke only after all planned code** (Phase 99 / PENDING_WORK).  
2. Phase → implement → test offline → commit/push → update plan %.  
3. Resume from **local MD only** (IMPROVEMENT_PLAN + TASKBOARD).  

---

## Planning just completed

| File | Role |
|------|------|
| `docs/IMPROVEMENT_PLAN.md` | Full phases 0–8 + 99, tasks, MoSCoW map, DoD |
| `TASKBOARD.md` | Improvement track dashboard 0% impl |
| `docs/PENDING_WORK.md` | Next track pointer |
| This handoff | Compact context |

**Must → Phases 1–3** · **Should → 4–6** · **Nice → Phase 8 backlog** · **Smoke → 99**

---

## Implementation order (next sessions)

1. **Phase 1** — Result contract, mock/dry_run honesty, budget hard-stop, cost fields  
2. **Phase 2** — Default agent entry, permission modes, ask multi-turn session  
3. **Phase 3** — Registry validation, profiles (cheap/balanced/quality/local-only), cost report  
4. **Phase 4** — Prefer OW/local failover, smart board size, board cache  
5. **Phase 5** — In-process Read/Edit/Bash (jailed), streaming progress, health UX  
6. **Phase 6** — Auto Ollama opt-in, NL map expand, Windows CLI hardening  
7. **Phase 7** — Docs closeout  
8. **Not yet:** N1–N8 agent TUI / personal assistant; Phase 99 smoke  

---

## Verify commands (after Phase 1 code)

```powershell
# Offline only
pytest tests/ -q --tb=line   # or targeted tests for touched modules
```

---

## Do NOT in next session

- Re-implement universal models from scratch  
- Run live multi-provider smoke  
- Start personal assistant / full Claude TUI (Phase 8)  
- Ask user for re-approval of this plan — execute Phase 1  

---

## One-line state

**Planning 100% · Implementation 0% · Smoke postponed · Start IMPROVEMENT_PLAN Phase 1.**
