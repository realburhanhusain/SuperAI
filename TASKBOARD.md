# TASKBOARD — SuperAI (index)

**Layout:** `src/cli` (`scli`) · `src/core` (`core`) · entry `superai = scli.main:app`  
**Scorecard (strict):** [`docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md`](docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md)  
**Docs map:** [`docs/README.md`](docs/README.md) · V6 backlog: [`docs/IMPROVEMENT_V6_BACKLOG.md`](docs/IMPROVEMENT_V6_BACKLOG.md)

**Legend:** `[x]` done · `[!]` external host only  

---

## Active owner boards (use these)

| Owner | Board | Scope |
|-------|--------|--------|
| **Grok** | [`TASKBOARD_GROK.md`](TASKBOARD_GROK.md) | Learning product (M061–M063), routing/bandit (M068/M050), streaming honesty (M027/V4-M4), dashboard (M100), host smoke (M089) |
| **AGY** | [`TASKBOARD_AGY.md`](TASKBOARD_AGY.md) | Spend spine (V4-M1/DOD-1, V5-M1/M2), contracts (V4-M2), JSON/MCP (M079/M093), cost (V5-M4), TOP_30 (M090) |

Resume rules for agents: read **your** owner board first, then this index. Closed plans/reviews/checkpoints live under `docs/archive/` — see [`docs/README.md`](docs/README.md).

---

## Archives (closed — do not re-open unless regression)

| Archive | Contents |
|---------|----------|
| [`docs/archive/2026-07-24-wave-handoffs/`](docs/archive/2026-07-24-wave-handoffs/) | AGY W0–W4 + Grok memory handoffs |
| [`docs/archive/2026-07-25-closed-docs/`](docs/archive/2026-07-25-closed-docs/) | Stage I1 reviews, completed V1–V5 plans, old scorecards, status, closed gaps |
| [`docs/archive/2026-07-25-checkpoints/`](docs/archive/2026-07-25-checkpoints/) | Historical session checkpoints |

Old top-level paths were removed after archive — use the folders above (or git history).

---

## Shared host-gated (POSTPONED)

**Policy:** finish offline Must work first; live smoke is last. See `docs/UNIVERSAL_MODELS_PLAN.md` Phase 99.

- [!] Live multi-provider keys (all vendors / open-weight / NVIDIA / Ollama) — **M089** owned on Grok board when run  
- [!] Live Telegram/Slack  
- [!] rclone remote E2E  
- [!] GitHub Pages enable  
- [!] Live Postgres + pgvector server  
- [!] Real OTLP collector / cloud control plane (optional)

---

## Completed product tracks (reference)

| Track | Status |
|-------|--------|
| A–J foundations · Future Plan G1–G15 | `[x]` |
| Wave 2 M9–M13 / S13–S22 / N16–N30 | `[x]` |
| MoSCoW must+should+nice (offline) | `[x]` · N8 live = `[!]` |
| Improvement Phases 1–8 · V2–V5 · V6 phases 0–16 code | `[x]` (refuse-closed P386–P400 policy) |
| Universal models Phases 0–5 | `[x]` · Phase 99 `[!]` |
| Memory roadmap P1–P9 offline + MR residuals | `[x]` |
| AGY Hardening Wave W0–W4 | `[x]` archived |
| Grok handoff integrity (non-host) | `[x]` archived |

---

## Unassigned backlog (not on owner boards yet)

| ID | % | Note |
|----|--:|------|
| **M091** | 50 | Performance budgets for cold start — assign after near-complete 18 move |
| Other scorecard incomplete @ ≤70% / stubs | — | See improved scorecard § INCOMPLETE |

---

## Last session

| Field | Value |
|-------|--------|
| **When** | 2026-07-25 |
| **What** | Docs hygiene: archived closed I1 reviews, completed V1–V5 plans, old scorecards, status files, and historical checkpoints under `docs/archive/2026-07-25-*`. Active map: `docs/README.md`. Scorecard regen next if wanted. |
| **Still open** | Scorecard long-tail incomplete + host M089 |
| **Prior** | Stage I1 offline complete both boards |
