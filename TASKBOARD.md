# TASKBOARD — SuperAI (index)

**Layout:** `src/cli` (`scli`) · `src/core` (`core`) · entry `superai = scli.main:app`  
**Scorecard (strict):** [`docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md`](docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md)  
**Backlog:** [`docs/FEATURE_BACKLOG.md`](docs/FEATURE_BACKLOG.md) · **Progress:** [`docs/PROGRESS.md`](docs/PROGRESS.md)

**Legend:** `[x]` done · `[!]` external host only  

---

## Active owner boards (use these)

| Owner | Board | Scope |
|-------|--------|--------|
| **Grok** | [`TASKBOARD_GROK.md`](TASKBOARD_GROK.md) | Learning product (M061–M063), routing/bandit (M068/M050), streaming honesty (M027/V4-M4), dashboard (M100), host smoke (M089) |
| **AGY** | [`TASKBOARD_AGY.md`](TASKBOARD_AGY.md) | Spend spine (V4-M1/DOD-1, V5-M1/M2), contracts (V4-M2), JSON/MCP (M079/M093), cost (V5-M4), TOP_30 (M090) |

Resume rules for agents: read **your** owner board first, then this index, then latest `docs/checkpoints/`.

---

## Archived waves (2026-07-24)

Prior **AGY Hardening Wave W0–W4** and **Grok memory handoff** residuals are **closed offline**.

| Artifact | Location |
|----------|----------|
| Archive folder | [`docs/archive/2026-07-24-wave-handoffs/`](docs/archive/2026-07-24-wave-handoffs/) |
| AGY findings (closed) | `…/AGY_HANDOFF_PENDING_AND_INCOMPLETE.md` |
| AGY W0–W4 plan (closed) | `…/AGY_IMPROVEMENT_PLAN.md` |
| Grok memory handoff (closed) | `…/GROK_HANDOFF_PENDING_AND_INCOMPLETE.md` |
| Stubs (redirect only) | `docs/AGY_HANDOFF_…`, `docs/GROK_HANDOFF_…`, `docs/AGY_IMPROVEMENT_PLAN.md` |

Do **not** re-open archived checklists unless a regression is proven.

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
| **When** | 2026-07-24 |
| **What** | Stage **I1**: Grok G1–G4 offline complete. AGY A1–A5 **not** complete — pickup [`docs/reviews/review_result_I1_v1.md`](docs/reviews/review_result_I1_v1.md). G5 M089 host-gated. |
| **Still open** | Owner-board near-complete Musts + shared host gates |
| **Prior** | Archived handoffs; created dual boards (`2059e3a`) |
