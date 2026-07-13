# TASKBOARD — SuperAI_v1

**Backlog:** `docs/FEATURE_BACKLOG.md`  
**Security:** `docs/SECURITY_REVIEW.md`  
**Progress:** `docs/PROGRESS.md`  
**Layout:** `src/cli` (`scli`) · `src/core` (`core`) · entry `superai = scli.main:app`

**Legend:** `[x]` done · `[!]` external host only

---

## Prior tracks

| Track | Status |
|-------|--------|
| A–J foundations | `[x]` |
| Future Plan G1–G12 | `[x]` |
| Depth finish + security harden | `[x]` |
| M1–M8 / S1–S12 / N1–N15 | `[x]` |
| **Wave 2 M9–M13 / S13–S22 / N16–N30** | `[x]` |

---

## Wave 2 commands (highlights)

| Command | ID |
|---------|-----|
| `secrets` / `update` / `diagnose` / `rate-queue` | M10–M13 |
| `diff-edit` / `tdd` / `workspace-index` / `profile-bundle` | S13–S21 |
| `forecast` / `ab-route` / `compliance` / `onboard` | N20–N28 |
| `browse` / `speak` / `listen` / `pr-review` / `notebook` | N17–N26 |
| `memory-forget` / `memory-ttl` / `memory-sync` | N19/N27 |
| `langgraph-export` / `plugin-catalog` / `skill-perms` / `telemetry` / `lang` | N16+ |
| `merge-results` / `validate-json` | S16/S18 |

---

## External smoke (LAST — not code)

- [!] Live multi-provider keys  
- [!] Live Telegram/Slack  
- [!] rclone remote E2E  
- [!] GitHub Pages enable  

---

## Last session

| Field | Value |
|-------|--------|
| **When** | 2026-07-14 |
| **What** | Implemented wave-2 features M9–N30; docs updated |
| **Verify** | `pytest -q` → **114+ passed** |
