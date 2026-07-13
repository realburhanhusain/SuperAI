# Checkpoint: msn-backlog-implemented

- **When:** 2026-07-14 01:53:59 +03:00
- **Host:** IT-DV-110-L
- **Repo:** C:\Users\burhan.husain\Documents\Personal\github\SuperAI_v1
- **Git HEAD:** dd630fb
- **Git status:** ## master...origin/master [ahead 12]
- **Pytest:** skipped

## Recovery

1. Open this repo path.
2. Read `TASKBOARD.md` Last session + first `[ ]` / `[~]` item.
3. If tree is corrupted, restore from last git commit: `git status` / `git log -5 --oneline` / `git stash list`.
4. Runtime data (not always in git): `~/.superai/` â€” use `superai backup-verify` / `superai restore`.

## TASKBOARD snapshot (truncated)

```markdown
# TASKBOARD â€” SuperAI_v1

**Backlog:** `docs/FEATURE_BACKLOG.md`  
**Security:** `docs/SECURITY_REVIEW.md`  
**Layout:** `src/cli` (import `scli`) Â· `src/core` (import `core`)

**Legend:** `[x]` done Â· `[~]` partial Â· `[ ]` pending Â· `[!]` external smoke

---

## Tracks Aâ€“J (prior)

| Track | Status |
|-------|--------|
| Aâ€“J foundations | `[x]` |
| Future Plan G1â€“G12 | `[x]` |
| Thin-layer depth finish | `[x]` |
| Security hardening pass | `[x]` |
| Package restructure src/cli + src/core | `[x]` |

---

## Must have (M)

| ID | Feature | Status |
|----|---------|--------|
| M1 | Live smoke / health pack | `[x]` `superai doctor` |
| M2 | Secret redaction | `[x]` `core/secrets.py` + history scrub |
| M3 | Workspace jail | `[x]` `core/workspace.py` + tool proposals |
| M4 | Approval path for live CLI | `[x]` ModelCaller dry-run when approval required |
| M5 | Data read-only mode | `[x]` `data_read_only` config + SELECT-only SQL |
| M6 | Resume UX | `[x]` incomplete-run hints + `runs resume` |
| M7 | First-run / doctor path | `[x]` doctor next_steps |
| M8 | Web auth when exposed | `[x]` token + non-loopback refuse |

---

## Should have (S)

| ID | Feature | Status |
|----|---------|--------|
| S1 | Streaming run output | `[x]` `run --stream -m model` |
| S2 | Chat session mode | `[x]` `superai chat` |
| S3 | LLM planner when live | `[x]` `prefer_llm_planner` |
| S4 | Budget guards | `[x]` `superai budget` |
| S5 | Failover chain | `[x]` `superai failover` |
| S6 | Tool schemas | `[x]` `core/tool_schemas.py` |
| S7 | Project-local config | `[x]` `.superai/config.json` merge |
| S8 | Audit log | `[x]` `superai audit` |
| S9 | Backup key export/import | `[x]` `superai backup-key` |
| S10 | Plugin load runtime | `[x]` `plugins load` |
| S11 | Error classification | `[x]` `core/error_recovery.py` |
| S12 | Offline eval harness | `[x]` `superai evals` |

---

## Nice to have (N)

| ID | Feature | Status |
|----|---------|--------|
| N1 | MCP server surface | `[x]` `superai mcp-serve` |
| N2 | IDE extension | `[ ]` product (out of repo CLI scope) |
| N3 | Multi-user profiles | `[x]` `superai profile` |
| N4 | Policy engine | `[x]` `superai policy` |
| N5 | FAISS path | `[~]` HNSW env knobs only |
| N6 | Messenger inbound | `[x]` `msg-inbound` |
| N7 | Plan Mermaid graph | `[x]` `plan --export mermaid` |
| N8 | Benchmark report | `[x]` `compare` / `benchmark` (prior) |
| N9 | Git helpers | `[x]` `git-helper` |
| N10 | Scheduled tasks | `[x]` `superai schedule` |
| N11 | Metrics export | `[x]` `superai metrics` |
| N12 | Ticket stub | `[x]` `superai ticket` |
| N13 | Mobile PWA | `[ ]` product |
| N14 | Constitution | `[x]` `superai constitution` |
| N15 | Container sandbox flag | `[x]` config `prefer_container_sandbox` |

---

## External smoke (last)

- [!] Live multi-provider keys E2E  
- [!] Live Telegram/Slack tokens  
- [!] rclone remote E2E  
- [!] GitHub Pages enable  

---

## Last session

| Field | Value |
|-------|--------|
| **When** | 2026-07-14 |
| **What** | Wired M/S/N backlog; implemented doctor, chat, budget, audit, policy, schedule, MCP, constitution, â€¦ |
| **Verify** | `pytest -q` â†’ **93 passed** |

```
