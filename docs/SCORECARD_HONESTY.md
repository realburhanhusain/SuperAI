# Scorecard honesty notice (for external reviewers)

**Date:** 2026-07-16  
**Audience:** Claude / Gemini / Codex / human auditors  
**Files:** `docs/V6_SCORECARD.md`, `docs/V1_V5_SCORECARD.md`

## What went wrong

A bulk pass briefly reclassified almost all `foundation` items as `full` after a shared infrastructure lift (`call_lifecycle`, preflight, redact, etc.). That **overstated** production readiness. That bulk upgrade is **reverted**.

## What “full” means here

| Status | Meaning (use this when auditing) |
|--------|----------------------------------|
| **full** | Production-usable for the **stated backlog/plan intent**; real code; tests where the track required them |
| **foundation** | Real working code; **DoD incomplete** (not universal, thin UX, or partial) |
| **stub** | Flag / sample / placeholder only |
| **absent** | No meaningful implementation |
| **host** | Code path exists; live proof needs credentials/environment |
| **refuse** | Intentionally blocked (safety) |

`full` ≠ “enterprise SaaS complete” or “rivals every specialist product.”  
`full` ≠ “one helper function exists.”

## How to validate (recommended)

1. **Ignore status first.** Open the module named in **Why**.
2. Run offline: `pytest -m unit -q` and `pytest tests/test_foundation_lift.py -q`.
3. For each `full` claim: does code + tests meet the **literal backlog title**?
4. Prefer **downgrade** on doubt.

## Expected rough counts after re-audit (V6)

These are intentional order-of-magnitude targets after the fix (regenerate to see exact):

- **full:** ~100 (original solid spine + ~10–15 honestly re-earned)
- **foundation:** ~80–90 (real code, incomplete)
- **stub / absent / refuse / host:** largely unchanged from pre-inflation

## Re-earned `full` only (post-lift, honest)

Must: M003, M012, M029, M067, M092, M094, M099  
Should: S103, S130, S131, S133, S134, S135  

Everything else that was bulk-marked full and used to be foundation is **foundation again** (or still stub/absent).

## Generators

```text
python scripts/gen_v6_scorecard.py
python scripts/gen_v1_v5_scorecard.py
```

Do **not** reintroduce bulk foundation→full overlays.

## Author note

The overclaim damaged trust. This correction prioritizes **truth for public/review scrutiny** over looking complete.
