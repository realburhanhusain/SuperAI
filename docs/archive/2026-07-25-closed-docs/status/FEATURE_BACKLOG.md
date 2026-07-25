# SuperAI feature backlog

**Updated:** 2026-07-14  
**Layout:** `src/cli` → import `scli` · `src/core` → import `core`  
**Tests:** 114 passed  

All implementable backlog items below are **done in code**.  
Host-only remaining: live API keys, live bots, rclone remote, GitHub Pages admin.

---

## Original M/S/N (first wave) — done

M1–M8 · S1–S12 · N1–N15 (see prior sections / TASKBOARD).

---

## Wave 2 — Must (M9–M13)

| ID | Feature | Status | Entry |
|----|---------|--------|-------|
| M9 | Interactive mid-run approval TUI | **done** | `approval_tui` + ModelCaller |
| M10 | OS keyring / secret store | **done** | `superai secrets` |
| M11 | Version / update check | **done** | `superai update` |
| M12 | Diagnostics zip | **done** | `superai diagnose` |
| M13 | Rate-limit queue / retry | **done** | `superai rate-queue` + `RateLimitQueue` |

## Wave 2 — Should (S13–S22)

| ID | Feature | Status | Entry |
|----|---------|--------|-------|
| S13 | Diff-first edits | **done** | `superai diff-edit` |
| S14 | Test-driven loop | **done** | `superai tdd` |
| S15 | Context window manager | **done** | chat uses `context_manager` |
| S16 | Merge parallel results | **done** | `superai merge-results` |
| S17 | Routing explain in history | **done** | `metadata.routing_explain` |
| S18 | Structured JSON validation | **done** | `superai validate-json` |
| S19 | Workspace code index | **done** | `superai workspace-index` |
| S20 | Feedback → bandit/prefs | **done** | `feedback` wires bandit |
| S21 | Profile export/import | **done** | `superai profile-bundle` |
| S22 | WebSocket dashboard | **done** | `ws://…/ws/dashboard` |

## Wave 2 — Nice (N16–N30)

| ID | Feature | Status | Entry |
|----|---------|--------|-------|
| N16 | LangGraph export | **done** | `langgraph-export` |
| N17 | Browser tool | **done** | `browse` (Playwright optional) |
| N18 | Voice I/O | **done** | `speak` / `listen` |
| N19 | Encrypted memory sync | **done** | `memory-sync` |
| N20 | Cost forecast | **done** | `forecast` |
| N21 | A/B routing | **done** | `ab-route` |
| N22 | Compliance mode | **done** | `compliance enable` |
| N23 | Remote plugin catalog | **done** | `plugin-catalog` |
| N24 | Skill tool permissions | **done** | `skill-perms` |
| N25 | Notebook runner | **done** | `notebook` |
| N26 | PR review mode | **done** | `pr-review` |
| N27 | Memory forget / TTL | **done** | `memory-forget` / `memory-ttl` |
| N28 | Onboarding wizard | **done** | `onboard` |
| N29 | Telemetry opt-in | **done** | `telemetry` |
| N30 | CLI i18n | **done** | `lang` |

## External (not code)

- Live multi-provider / Telegram / Slack / rclone / Pages smoke
