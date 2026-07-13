# Changelog

## [0.1.0] — 2026-07-14

### Code complete (feature waves)

**Foundation (Tracks A–J)**  
Multi-model orchestration, routing, load balancing, memory palace, skills, encrypted backup, council, hierarchy, messengers, databao, plugins, web UI.

**Wave 1 (M1–M8, S1–S12, N1–N15)**  
Doctor, secrets redaction, workspace jail, chat, budget, audit, policy, schedule, MCP, FAISS backend, Docker sandbox, PWA, VS Code scaffold, constitution, etc.

**Wave 2 (M9–M13, S13–S22, N16–N30)**  
- Interactive approval TUI for external CLIs  
- Keyring/secret store, version check, diagnostics zip, rate-limit queue  
- Diff-first edits, TDD loop, context trim, merge-results, routing explain  
- Workspace index, profile bundle, WebSocket dashboard  
- LangGraph export, browser tool, voice, memory sync, cost forecast  
- A/B routing, compliance mode, plugin catalog, skill perms  
- Notebook runner, PR review, GDPR forget/TTL, onboarding, telemetry, i18n  

### Package layout

- `src/cli` (import `scli`) + `src/core` (import `core`)  
- Console: `superai = scli.main:app`

### Tests

- `pytest -q` → **114 passed** (mock-first)

### Deferred (host)

- Live API keys multi-provider smoke  
- Live Telegram/Slack tokens  
- rclone remote E2E  
- GitHub Pages admin enable  

### Checkpoints

See `docs/checkpoints/` and `scripts/checkpoint.ps1`.
