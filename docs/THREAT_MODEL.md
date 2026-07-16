# SuperAI Threat Model (V6 M099)

**Updated:** 2026-07-16  
**Scope:** Local-first multi-model orchestrator CLI + optional web/MCP.

## Assets

| Asset | Sensitivity |
|-------|-------------|
| API keys / secrets | Critical |
| Memory Palace contents | High |
| Workspace source code | High |
| Run history / trails | Medium |
| Budget / spend state | Medium |

## Trust boundaries

1. **User host** — SuperAI process, `~/.superai/`, workspace jail
2. **External model providers** — OpenAI-compat, Anthropic, Google, local servers
3. **External CLIs** — aider, claude, gemini, etc. on PATH
4. **Optional web** — loopback vs non-loopback
5. **MCP clients** — IDE/agent hosts calling SuperAI tools

## Threats & mitigations

| Threat | Mitigation |
|--------|------------|
| Secret leakage in logs/TUI | `secrets.redact_*`, logger redact filter |
| SSRF via fetch tools | `net_safety` public-only / block private ranges |
| Workspace escape | Jail on `agent_tools` + external CLI cwd |
| Prompt injection via tool output | `injection_defense` scan/sanitize |
| Unbounded spend | `spend_guard` / `BudgetGuard` on model call lifecycle |
| Unsafe permission defaults | plan/ask/auto/yolo; goals no yolo inherit |
| Non-loopback web abuse | `SUPERAI_WEB_TOKEN` required off-loopback |
| Plugin supply chain | sha256 verify path |
| Live smoke false success | harness never sets live_passed offline |

## Residual risks

- Provider-side prompt injection cannot be fully eliminated
- External CLIs have their own trust models
- Optional integrations (Telegram/Slack) need host credentials and policy

## Quickstart security checklist

1. Prefer `permission=plan` or `ask` until trusted
2. Set budget limits: `superai config` / project budget
3. Store keys in keyring/env — never commit
4. Set `SUPERAI_WEB_TOKEN` before binding web off-loopback
5. Run `superai doctor` and `superai smoke-preflight` before live
