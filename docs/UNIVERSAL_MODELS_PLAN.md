# Universal Models — full phase plan (source of truth)

**Created:** 2026-07-16  
**Updated:** 2026-07-16 (phases 0–5 code complete; smoke postponed)  
**Track:** `TASKBOARD.md` · **Charter:** `docs/UNIVERSAL_MODELS.md`  
**Rule:** implement phase tasks in order; commit+push after phases; smoke **only at end**.  
**Resume:** read this file + TASKBOARD only.

## Progress dashboard

| Phase | Name | Tasks | Done | Status | % |
|-------|------|------:|-----:|--------|--:|
| 0 | Charter + taskboard | 2 | 2 | complete | 100% |
| 1 | Provider catalog + caller + base catalog + Ollama/register CLI | 7 | 7 | complete | 100% |
| 2 | Richer catalogs + members/list filters | 5 | 5 | complete | 100% |
| 3 | Auto-discover on doctor/members (no live smoke) | 4 | 4 | complete | 100% |
| 4 | NL / pick by provider family | 4 | 4 | complete | 100% |
| 5 | Docs polish + QUICK_REFERENCE + checkpoint | 3 | 3 | complete | 100% |
| 99 | Live multi-provider smoke | 1 | 0 | **POSTPONED** | 0% |

**Overall (excl. smoke):** 25 / 25 tasks = **100%** code complete.  
**Smoke (Phase 99):** **0%** — deferred until after full development per product rule.  
**Weighted remaining:** smoke only (~4% of total if counted).

---

## Phase 0 — Charter `[x]`

- [x] P0.1 Write vision + principles (`UNIVERSAL_MODELS.md`)
- [x] P0.2 Wire TASKBOARD last-session section

## Phase 1 — Foundation `[x]`

- [x] P1.1 `provider_catalog.py` single map
- [x] P1.2 ModelCaller registry-aware base_url/key
- [x] P1.3 Expand `config/models.json` core multi-vendor
- [x] P1.4 `model_discovery.py` Ollama + register
- [x] P1.5 CLI `providers` / `models-sync-ollama` / `models-register`
- [x] P1.6 Unit tests
- [x] P1.7 Commit + push + checkpoint

## Phase 2 — Catalog depth + filters `[x]`

- [x] P2.1 Expand NVIDIA NIM entries (own + hosted open-weight)
- [x] P2.2 Expand gateway catalog (OpenRouter, Fireworks, SiliconFlow, Together)
- [x] P2.3 `list_selectable_members` filters: open_weight, local_only, provider, ollama soft
- [x] P2.4 CLI `members` / `list-models` filter flags
- [x] P2.5 Tests

## Phase 3 — Auto-discover (offline-safe) `[x]`

- [x] P3.1 Doctor reports provider catalog readiness
- [x] P3.2 Discovery `api_keys_present` includes new vendor envs + ollama_tags
- [x] P3.3 Soft Ollama in members via `--ollama-live`
- [x] P3.4 Tests  
- [ ] ~~P3.smoke~~ → **Phase 99**

## Phase 4 — Selection UX / NL `[x]`

- [x] P4.1 Expand NL API/provider hints (deepseek, kimi, glm, minimax, nvidia, gemma, ollama…)
- [x] P4.2 `prompt_pick_from_catalog` filters (provider / open_weight / local)
- [x] P4.3 `members --pick` respects filter flags
- [x] P4.4 Tests

## Phase 5 — Documentation closeout `[x]`

- [x] P5.1 Update UNIVERSAL_MODELS + PLAN dashboard to 100% (code)
- [x] P5.2 QUICK_REFERENCE + TASKBOARD
- [x] P5.3 Final checkpoint + commit/push

## Phase 99 — Live smoke `[POSTPONED]`

- [ ] P99.1 Live multi-provider smoke matrix (DeepSeek, Moonshot, Zhipu, NVIDIA, OpenRouter, Ollama, MiniMax) — **after complete development**

---

## Definition of done (code complete, pre-smoke)

- [x] Any OpenAI-compatible model registrable and callable
- [x] NVIDIA / open-weight / local / gateway present in catalog
- [x] members/list-models filterable
- [x] doctor/discovery surface provider readiness
- [x] NL can name major open-weight vendors
- [x] Phases 0–5 committed
- [ ] Smoke remaining host work only
