# TASKBOARD — SuperAI_v1

**Purpose:** Source of truth for *done* vs *left*. Resume here after any fault.  
**Progress table:** `docs/PROGRESS.md`  
**Checkpoints:** `docs/checkpoints/` via `scripts/checkpoint.ps1`  
**Guides:** `implementation_plan_detailed.md`, `implementation_plan_v2.md`, `codes.md`  
**Rules:** `AGENTS.md` + `docs/CHECKPOINT_PROTOCOL.md`

### Scope rule

- Everything in the implementation plans is **required**.
- Work may be **sequenced later** (Tracks G–I). Never mark plan work optional or cancelled.

### Autonomous work

- Agents may continue the next pending item without waiting for human approval between items.
- After each item (or ~30–45 min), run a **checkpoint** and update Last session.

**Status legend:** `[ ]` pending · `[~]` in progress · `[x]` done · `[!]` blocked

---

## Current focus

| Priority | ID | Item | Status |
|----------|-----|------|--------|
| P0–P4 | A–E | Stabilize + Phase 1–5 core | `[x]` |
| P5 | F | Phase 2–5 remaining | `[x]` |
| P6 | G | Phase 6 polish / docs / CI | `[ ]` **← START HERE (G1)** |
| P7 | H | Phase 7 advanced | `[ ]` |
| P8 | I | Phase 8 agentic + ecosystem | `[ ]` |

---

## Track A — Stabilize (DONE)

- [x] A1–A5 packaging, wiring, smoke mock run

## Track B — Phase 1 foundation (DONE)

- [x] B0–B7 config, history, tests, honest docs, DoD

## Track C — Phase 2 routing core (DONE)

- [x] C1–C6 scoring, LB, cost/usage, stats (live path code present)

## Track D — Phase 3 learning core (DONE)

- [x] D1–D4 LearningEngine, persist distill, success signals, CLI

## Track E — Skills + local backup (DONE)

- [x] E1–E5 skill inject/auto-create; local backup/verify/restore/atexit

## Track F — Phase 2–5 remaining (DONE 2026-07-13)

### F2
- [x] F2.1 smoke-providers
- [x] F2.2 list-models --refresh
- [x] F2.3 provider health persistence
- [x] F2.4 quota windows
- [x] F2.5 streaming foundation
- [x] F2.6 override tests

### F3
- [x] F3.1 embeddings path (hash offline; EmbeddingGemma/ST via `.[embeddings]` + `SUPERAI_EMBEDDING_MODEL`)
- [x] F3.2 memory collections facade
- [x] F3.3 feedback CLI
- [x] F3.4 mid-task adaptation
- [x] F3.5 `superai evolve <topic>` knowledge evolution

### F4
- [x] F4.1–F4.4 sandbox/promote/rollback/stats/relevance

### F5
- [x] F5.1 backup --cloud
- [x] F5.2 restore --cloud (rclone pull then restore)
- [x] F5.3 retention --keep
- [x] F5.4 key warnings
- [x] F5.5 CI backup-verify job

**Note:** Live API keys and rclone remotes must exist on the host for end-to-end cloud/live verification; code paths are implemented.

---

## Track G — Phase 6 (PENDING) — **NEXT**

- [ ] G1 Rich progress bars / spinners on long ops
- [ ] G2 Error messages with suggested fixes everywhere
- [ ] G3 Shell auto-completion install path
- [ ] G4 Docs aligned: README, FEATURES, QUICK_REFERENCE, ARCHITECTURE
- [x] G5 GitHub Actions CI (tests + backup verify)
- [ ] G6 GitHub Pages (or equivalent) for docs
- [ ] G7 CONTRIBUTING / release notes accuracy

## Track H — Phase 7 (PENDING)

- [ ] H1–H8 external CLI delegation, RL routing, dual dashboards, tool proposals

## Track I — Phase 8 (PENDING)

- [ ] I1–I7 MCP-deep context, agentic workflows, wings/rooms, ecosystem, advanced init

---

## Last session

| Field | Value |
|-------|--------|
| **When** | 2026-07-13 |
| **What** | Checkpoint protocol; F3.1 embeddings; F3.5 evolve CLI; F5.2 cloud restore; PROGRESS.md; Track F closed |
| **Next agent action** | **G1** (progress UX) without waiting for approval; checkpoint after each G item |
| **Verify** | `pytest -q` → **31 passed** |
| **Checkpoint** | Run `scripts/checkpoint.ps1 -Label "track-F-complete"` |
