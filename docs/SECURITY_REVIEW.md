# SuperAI_v1 — Completeness + Security Review

**Date:** 2026-07-14  
**Code:** `src/cli` (import `scli`), `src/core` (import `core`)  
**Tests:** 81+ passed (mock-first)

---

## Part A — Completeness revalidation

### Verdict

| Question | Answer |
|----------|--------|
| All claimed A–J / G1–G12 features present in code? | **Yes** |
| Runtime imports post-restructure OK? | **Yes** (`core` / `scli`) |
| Missing major modules? | **No** |
| Overall **code** completeness | **~93–95%** |
| Live production E2E | **Deferred smoke** (~0% of external E2E) |

### By phase (code implementation)

| Phase | % | Notes |
|------:|--:|-------|
| 1 Core | 99% | Complete |
| 2 Routing | 98% | Live keys deferred |
| 3 Memory/learning | 97% | FAISS/quant optional |
| 4 Skills | 96% | Complete |
| 5 Backup | 95% | rclone E2E deferred |
| 6 Polish/docs/CI | 96% | Pages admin deferred |
| 7 Advanced | 94% | Live bots deferred |
| 8 Agentic | 93% | Optional depth remains |

### Intentional non-100% (not “missed code”)

- Live multi-provider / Telegram / Slack / rclone / Pages **smoke**
- DuckDuckGo scrape (policy)
- Full GitHub Issues/PR product API
- FAISS backend / embedding quantization packaging
- Plugin **runtime loader** (registry is local catalog only)
- Memory-chat forced mock synthesis path when no live routing desired

### Stale docs only

- `codes.md`, some plan files still mention `src/superai/`
- `docs/PENDING_WORK.md` may show old test counts

---

## Part B — Security review

### Threat model

Local single-user CLI by default. Risk rises if: live external CLIs, non-loopback web, production DB DSN, or shared multi-user host.

### Critical / High findings (status)

| # | Issue | Severity | Status after this review |
|---|--------|----------|---------------------------|
| 1 | `ModelCaller` hard-coded `auto_approve=True` for `cli:*` | Critical | **Fixed** — honors `require_human_approval`; dry-run when approval required |
| 2 | Unauthenticated web API | Critical/High | **Mitigated** — optional `SUPERAI_WEB_TOKEN`; non-loopback bind refused without token |
| 3 | `edit_file` any path | High | **Fixed** — jails under `SUPERAI_WORKSPACE` or cwd |
| 4 | `run_shell` allows powershell/cmd | High | **Mitigated** — meta shells blocked unless `SUPERAI_ALLOW_SHELL_META=1` |
| 5 | Backup scope `../` path traversal | High | **Fixed** — known scopes only + path jail |
| 6 | Tar restore slip fallback | High | **Fixed** — member path validation always |
| 7 | SQL sanitizer keyword bypass | High | **Hardened** — comment strip + word-boundary bans |
| 8 | Gemini `modifies_files=False` | High | **Fixed** — treated as modifying |
| 9 | Plugin id path traversal | Medium-High | **Fixed** — id charset + root jail |
| 10 | XSS in web memory UI | Medium | **Fixed** — HTML escape in result render |
| 11 | Invalid task_id path | Low | **Fixed** — charset validation |

### Remaining residual risks (not fully eliminated)

| Issue | Severity | Recommendation |
|-------|----------|----------------|
| Backup key plaintext on disk next to archives | High | OS keystore / passphrase-derived key |
| Cleartext history/logs/memory (secrets if user pastes keys) | Medium | Redaction scanner; exclude logs from default backup |
| SQL still not full AST parser / no RO DB role | Medium | Use read-only DB user + sqlglot |
| Proposal `force=True` / `requires_human=False` API | Medium | Disallow in CLI production mode |
| Step-cache multi-process file races | Medium | File locks + atomic write |
| Messenger/webhook SSRF if env poisoned | Medium | HTTPS + private-IP blocklist |
| Skills “sandbox” is not OS isolation | Low | Document; treat skill text as untrusted |
| Encrypted backups ≠ protection from same-user malware | Info | Document threat model |

### Positive controls

- List-form `subprocess` (`shell=False`) for CLI/rclone
- AES-GCM backups with salt/nonce
- Web default bind `127.0.0.1`
- Discovery reports key *presence*, not values
- HITL veto/clarify available
- Skill filenames sanitized on create

---

## Security configuration checklist

```powershell
# Keep approval on (default)
superai config set require_human_approval true

# Web only on localhost, or set a token
$env:SUPERAI_WEB_TOKEN = "long-random-secret"
# superai web --host 0.0.0.0   # only with token set

# Constrain tool file edits
$env:SUPERAI_WORKSPACE = "C:\path\to\project"

# Never backup SSH keys via weird scopes (now rejected)
# Use production DSN only with a READ-ONLY DB role
```

---

## Bottom line

1. **Completeness:** Claimed features are implemented in code at ~**93–95%**; remaining is deferred external smoke + optional depth—not missing phase modules.  
2. **Security:** Several real loopholes existed (approval bypass, open web, path escapes). **Critical/High items above were patched in this pass.** Residual risk is mainly **local cleartext stores**, **backup key storage**, and **operator misconfiguration** (live DSN, non-loopback web, disabling approval).
