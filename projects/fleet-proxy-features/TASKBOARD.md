# TASKBOARD — Fleet Proxy Features

**Owner:** unassigned (open to any agent)
**Repo index:** [`../../TASKBOARD.md`](../../TASKBOARD.md)
**Created:** 2026-08-09

**Legend:** `[ ]` open · `[~]` in progress · `[x]` done · `[!]` blocked externally · `[?]` disputed / needs owner

---

## Scope
This project board tracks the implementation of advanced orchestration and proxy routing features natively within SuperAI. These features were identified as critical gaps compared to enterprise proxy gateways like `CLIProxyAPIBusiness`, but are highly valuable for local/distributed AI fleets.

---

## Tasks

| ID | Task | Component | Est | Status | Owner |
|----|------|-----------|-----|--------|-------|
| T17 | Granular Quotas & Agent Budgets | `core/quota_manager.py` | 2h | `[x]` | agent-fleet |
| T18 | Provider API Key Pooling & Rotation | `core/key_pool.py` | 2h | `[x]` | agent-fleet |
| T19 | Model Mappings & Aliasing | `core/model_router.py` | 1.5h | `[x]` | agent-fleet |
| T20 | Token-Bucket Rate Limiting (RPM/TPM) | `core/rate_limiter.py` | 1.5h | `[x]` | agent-fleet |
| T21 | Model Payload Rules & Interceptors | `core/payload_rules.py` | 1.5h | `[x]` | agent-fleet |
| T22 | Clean House (Remove Vendored UI) | `cli/web_app.py` | 1h | `[x]` | agent-fleet |
| T23 | Setup Static Hosting | `cli/web_app.py` | 0.5h | `[x]` | agent-fleet |
| T24 | Native Management APIs | `cli/web_app.py` | 2h | `[x]` | agent-fleet |
| T25 | Core Design System (Vanilla CSS) | `cli/static/console/styles.css` | 2h | `[x]` | agent-fleet |
| T26 | Dashboard Modules (Vanilla JS) | `cli/static/console/app.js` | 3h | `[x]` | agent-fleet |
| T27 | SuperAI Bar (System Tray) | `cli/tray.py` | 2h | `[~]` | agent-fleet |
| T28 | Shorthand Model Profiling | `cli/main.py` | 1h | `[x]` | agent-fleet |
| T29 | Browser Automation Tools | `core/browser.py` | 2h | `[~]` | agent-fleet |

**Total estimate:** ~8.5 hours.

---

## Feature Details

### T17: Granular Quotas & Agent Budgets
- **Goal:** Implement agent-level budgets. When launching a task or sub-agent, assign it a maximum budget (e.g., $1.00). If it hits the limit, SuperAI pauses the agent instead of running up the bill.
- **Why:** Protects against runaway loops in autonomous agents.

### T18: Provider API Key Pooling & Rotation
- **Goal:** Allow an array of API keys for a single provider in the SuperAI config. SuperAI must catch `HTTP 429 Too Many Requests` errors and automatically rotate to the next key.
- **Why:** Ensures high availability for agents hitting heavily rate-limited providers.

### T19: Model Mappings & Aliasing
- **Goal:** Add an "Alias" engine in SuperAI where agents can request generic identifiers like `router:fast` or `router:smart`. The configuration layer maps those aliases dynamically to upstream models.
- **Why:** Future-proofs agents against model deprecations without changing prompt code.

### T20: Token-Bucket Rate Limiting
- **Goal:** Introduce an internal Token-Bucket rate limiter (RPM and TPM limits) in Python to throttle outgoing requests before they hit the upstream provider.
- **Why:** Prevents SuperAI from getting your provider accounts banned due to sudden request spikes.

### T21: Model Payload Rules & Interceptors
- **Goal:** Add middleware to SuperAI that can automatically inject a global "Safety System Prompt" or filter out specific keywords before requests leave the machine.
- **Why:** Enforces global guardrails on all agent actions natively.

### T27: SuperAI Bar (System Tray Companion)
- **Goal:** Build a system tray app using `pystray` (or similar) to show token spend, quota usage, and a launch button for the Web Management Center.
- **Why:** Brings SuperAI metrics natively to the macOS/Windows desktop, inspired by CCS Bar.

### T28: Shorthand Model Profiling CLI Syntax
- **Goal:** Support CLI invocations like `superai o1 "refactor this"` by parsing the first argument against `AliasRouter`.
- **Why:** Significantly improves CLI UX by reducing typing overhead compared to `--model`.

### T29: Automatic Browser Automation Provisioning
- **Goal:** Expose Playwright-based browser rendering as an integrated Tool (fallback) for Agent models.
- **Why:** Allows agents to scrape and parse complex websites on-demand.
