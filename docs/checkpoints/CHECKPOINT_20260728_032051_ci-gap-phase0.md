# Checkpoint: ci-gap-phase0

- **When:** 2026-07-28 03:20:51 +03:00
- **Host:** IT-DV-110-L
- **Repo:** C:\Users\burhan.husain\Documents\Personal\github\SuperAI
- **Git HEAD:** a6b7f1f
- **Git status:** ## codex/ci-gap-remediation-20260728
- **Pytest:** skipped

## Recovery

1. Open this repo path.
2. Read `TASKBOARD.md` Last session + first `[ ]` / `[~]` item.
3. If tree is corrupted, restore from last git commit: `git status` / `git log -5 --oneline` / `git stash list`.
4. Runtime data (not always in git): `~/.superai/` â€” use `superai backup-verify` / `superai restore`.

## TASKBOARD snapshot (truncated)

```markdown
# TASKBOARD â€” SuperAI (index)

**Layout:** `src/cli` (`scli`) Â· `src/core` (`core`) Â· entry `superai = scli.main:app`  
**Scorecard (strict):** [`docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md`](docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md)  
**Docs map:** [`docs/README.md`](docs/README.md) Â· V6 backlog: [`docs/IMPROVEMENT_V6_BACKLOG.md`](docs/IMPROVEMENT_V6_BACKLOG.md)

**Legend:** `[x]` done Â· `[!]` external host only  

---

## Active owner boards (use these)

| Owner | Board | Scope |
|-------|--------|--------|
| **Grok** | [`TASKBOARD_GROK.md`](TASKBOARD_GROK.md) | Learning product (M061â€“M063), routing/bandit (M068/M050), streaming honesty (M027/V4-M4), dashboard (M100), host smoke (M089) |
| **AGY** | [`TASKBOARD_AGY.md`](TASKBOARD_AGY.md) | Spend spine (V4-M1/DOD-1, V5-M1/M2), contracts (V4-M2), JSON/MCP (M079/M093), cost (V5-M4), TOP_30 (M090) |

Resume rules for agents: read **your** owner board first, then this index. Closed plans/reviews/checkpoints live under `docs/archive/` â€” see [`docs/README.md`](docs/README.md).

---

## Archives (closed â€” do not re-open unless regression)

| Archive | Contents |
|---------|----------|
| [`docs/archive/2026-07-24-wave-handoffs/`](docs/archive/2026-07-24-wave-handoffs/) | AGY W0â€“W4 + Grok memory handoffs |
| [`docs/archive/2026-07-25-closed-docs/`](docs/archive/2026-07-25-closed-docs/) | Stage I1 reviews, completed V1â€“V5 plans, old scorecards, status, closed gaps |
| [`docs/archive/2026-07-25-checkpoints/`](docs/archive/2026-07-25-checkpoints/) | Historical session checkpoints |

Old top-level paths were removed after archive â€” use the folders above (or git history).

---

## Shared host-gated (POSTPONED)

**Policy:** finish offline Must work first; live smoke is last. See `docs/UNIVERSAL_MODELS_PLAN.md` Phase 99.

- [!] Live multi-provider keys (all vendors / open-weight / NVIDIA / Ollama) â€” **M089** owned on Grok board when run  
- [!] Live Telegram/Slack  
- [!] rclone remote E2E  
- [!] GitHub Pages enable  
- [!] Live Postgres + pgvector server  
- [!] Real OTLP collector / cloud control plane (optional)

---

## Completed product tracks (reference)

| Track | Status |
|-------|--------|
| Aâ€“J foundations Â· Future Plan G1â€“G15 | `[x]` |
| Wave 2 M9â€“M13 / S13â€“S22 / N16â€“N30 | `[x]` |
| MoSCoW must+should+nice (offline) | `[x]` Â· N8 live = `[!]` |
| Improvement Phases 1â€“8 Â· V2â€“V5 Â· V6 phases 0â€“16 code | `[x]` (refuse-closed P386â€“P400 policy) |
| Universal models Phases 0â€“5 | `[x]` Â· Phase 99 `[!]` |
| Memory roadmap P1â€“P9 offline + MR residuals | `[x]` |
| AGY Hardening Wave W0â€“W4 | `[x]` archived |
| Grok handoff integrity (non-host) | `[x]` archived |

---

## Unassigned backlog (not on owner boards yet)

| ID | % | Note |
|----|--:|------|
| **M091** | 50 | Performance budgets for cold start â€” assign after near-complete 18 move |
| Other scorecard incomplete @ â‰¤70% / stubs | â€” | See improved scorecard Â§ INCOMPLETE |

---

## Last session

| Field | Value |
|-------|--------|
| **When** | 2026-07-28 |
| **What** | Phase 0 CI stabilization: repaired CLI discovery/routing and MCP in-memory fallback visibility; added pytest timeout guard to CI. Focused affected tests pass. |
| **Still open** | Finish a clean full protected suite (latest restart reached 149 passing before explicit-worker ordering fix); incomplete long-tail + host M089 / MOS-N8 / V1-P99. |
| **Prior** | Strict scorecard regeneration (2026-07-25) |

```
