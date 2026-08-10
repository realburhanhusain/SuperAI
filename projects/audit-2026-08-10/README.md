# Project Audit — 2026-08-10

Independent audit of every taskboard, completion record and executable surface
in this repository, plus a remediation plan. Read-only: no code was changed to
produce it.

**Audited by:** Claude Code (Opus 5)
**Target:** `545745d` (master, verified stable)
**Boundary tag:** `audit-checkpoint-20260810` → `c5d33f5` (local tag; the two
commits after it are frontend-only and add no defects)

---

## The files

| File | What it is |
|---|---|
| [`AUDIT_REPORT.md`](AUDIT_REPORT.md) | The complete audit, Parts 1–9. Records, boards, scorecard, functional correctness, and AGY's 08-10 work. |
| [`CORRECTION_PLAN.md`](CORRECTION_PLAN.md) | 34 items in 7 waves, ≈15–18 h. Each with file, line, fix, verification command and the regression test that should have caught it. |
| [`CHECKPOINT.md`](CHECKPOINT.md) | The audit boundary, the measured baseline, and a **reusable procedure** for auditing everything developed after this point. |

## Start here

1. `AUDIT_REPORT.md` → "The finding, in one paragraph" and Part 7 (defect count).
2. `CORRECTION_PLAN.md` → "Recommended execution order". **Not** wave order —
   wave numbers reflect the order findings were made.
3. First action is **C6.1**: classify 3 unclassified MCP tools. One edit,
   clears 5 of the 6 test failures.

## Measured baseline at `545745d`

Re-measure these to tell whether the plan has landed. The full acceptance gate
is at the end of `CORRECTION_PLAN.md`.

| Measurement | Value |
|---|---|
| Test suite | 6 failed / 1185 passed (16m49s) |
| MCP tools / unclassified | 28 / **3** |
| CLI names / hijacked (T28) | 207 / **192** |
| Shadowed `/api/*` GET routes | **14** |
| `/openapi.json` | **500** |
| `/council`, `/cliproxy-admin` | 404, 404 |
| `/dashboard` handlers | **2** |
| Scorecard COMPLETE / HOST-GATED | 282 / **0** (both unmeasured) |

Note two of these are expected to move *down* when fixed: scorecard COMPLETE
falls from 282, and HOST-GATED rises from 0 to 3. A report where every metric
improved has measured the wrong thing.

## The headline finding

The codebase is in better functional health than its records suggest — 249
modules import cleanly, the MCP safety subsystem is genuinely rigorous, and
T17–T21 behave correctly under test. The problem is the completion-tracking
system: an improvement is COMPLETE if its ID appears in a hand-maintained
Python list, and the three-pillar "evidence" beneath each entry is generated
prose, not measurement.

**This is not a claim that 282 features are fake.** It is a claim that the
number was never measured, so it cannot be relied on in either direction.

## Method, and its limits

- Everything executable was **run** against a clean clone at a pinned commit
  with isolated `HOME`/`USERPROFILE` — routes, argv handling, auth gates, the
  full suite, the repo's own self-audits.
- The 533 scorecard IDs were audited for **evidence integrity**, not functional
  correctness. No estimate of "what fraction works" is offered.
- **Not covered:** live multi-provider behaviour. No API keys were used and no
  vendor was contacted, so M089 / MOS-N8 / V1-P99 remain genuinely unproven.

## One trap worth knowing before you verify anything

SuperAI is installed here as an **editable install** whose meta-path finder
maps `core` and `scli` straight at the working tree:

```
site-packages/__editable___superai_0_1_0_finder.py
```

A meta-path finder overrides `sys.path`, so an `import` check can silently
resolve to the developer's live tree instead of the tree under test. This
produced one false negative during the audit.

**Verify module presence with `git cat-file` / `git ls-files`, never with
`import`.**
