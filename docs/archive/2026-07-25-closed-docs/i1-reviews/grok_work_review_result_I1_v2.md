# Grok Work Review Result — Stage I1 (v2.0)

**Date:** 2026-07-24  
**Stage:** Implementation Stage I1 — Deep Re-Review  
**Auditor:** AGY (Claude Opus 4.6 Thinking) — 4 parallel deep auditors  
**Prior version:** [`grok_work_review_result_I1_v1.md`](grok_work_review_result_I1_v1.md) — all v1 items **CLOSED**  
**Target Board:** [`TASKBOARD_GROK.md`](../TASKBOARD_GROK.md)  
**Scorecard:** [`docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md`](V1_V6_UNIFIED_IMPROVED_SCORECARD.md)  

**Pickup closed by:** Grok · **2026-07-24** · all P0–P2 checklist items implemented + tests  

---

## 1. Executive Summary

The v1 review confirmed Waves G1–G4 offline DoD and G5 code completion. This v2 deep re-review (using 4 parallel auditors with Claude Opus 4.6 Thinking) uncovered **2 CRITICAL, 4 HIGH, and 4 MEDIUM** issues — primarily around fault tolerance, test integrity, and architectural drift — that were not visible in the initial pass.

### Close-out (Grok)

All acceptance checklist rows in §3 are **DONE** offline. See §3 status column.

### Outcome Matrix

| Wave | v1 Status | v2 Status | Issues Found |
|------|-----------|-----------|--------------|
| **G1** M061–M063 | PASS | ⚠️ ~85% | 1 CRITICAL + 2 HIGH + 2 MEDIUM |
| **G2** M068, M050 | PASS | ⚠️ ~75% | 2 HIGH + 2 MEDIUM |
| **G3** M027 | PASS | ✅ ~95% | 1 MEDIUM (noted, acceptable) |
| **G4** M100 | PASS | ✅ ~95% | 1 MEDIUM (noted, acceptable) |
| **G5** M089 | CODE PASS | ✅ CODE PASS | None |

---

## 2. Pickup Items — Prioritized

### P0 — Must Fix (Blocks 100% DoD)

#### P0.1 — Silent Data Loss in `distill_knowledge` 🔴 CRITICAL

**File:** `src/core/learning_engine.py` (~line 1371)  
**Wave:** G1 (M063)  
**Impact:** Knowledge loss — originals deprecated but consolidated summary never stored  

**Problem:** When `distill_knowledge` runs, it first marks duplicate memories as deprecated (~line 1336-1358), then attempts to store a consolidated summary. If `self.memory.store()` fails, the exception is swallowed with `except Exception: pass`. The originals are already deprecated but the summary is gone.

```python
# Current (~line 1371):
try:
    sid = self.memory.store(summary, tags=[...], metadata={...})
    summary_ids.append(sid)
except Exception:
    pass  # ← CRITICAL: originals deprecated, summary lost
```

**Fix required:**
1. Wrap the deprecation + summary store in a transaction-like pattern
2. If summary `store()` fails, **un-deprecate** the originals (call `undeprecate_memory` for each)
3. Set `ok: False` and include the error in the return dict
4. Add a test that mocks `memory.store` to raise during distill and verifies originals are NOT deprecated

**Acceptance:** `distill_knowledge` must never leave memories in a state where originals are deprecated AND summary is missing.

---

#### P0.2 — Fake Integration Test `test_model_caller_uses_bias_candidates` 🟠 HIGH

**File:** `tests/test_routing_prefs_bandit_g2.py` lines 91-132  
**Wave:** G2 (M068)  
**Impact:** False test coverage — claims integration proof but tests nothing  

**Problem:** This test:
1. Imports `core.model_caller as mc` but **never instantiates** a `ModelCaller`
2. Creates `FakeReg` and `fake_escalate` but **never uses them**
3. Tests the disconnected `route_candidates()` function (see P1.1) instead of the actual live path
4. Ends with a self-fulfilling assertion:
   ```python
   calls["ok"] = True   # ← Sets it to True right before asserting
   assert calls["ok"]   # ← Always passes
   ```

**Fix required:**
1. Rewrite to actually instantiate `ModelCaller(use_mock=True, registry=FakeReg())`
2. Call `caller.call(model="a", prompt="test")` and verify the failover chain was reordered by preferences
3. OR — if full ModelCaller integration is too complex to unit-test, rename the test to accurately reflect what it tests (e.g., `test_bias_candidates_reorders_list`) and remove the misleading docstring

**Acceptance:** Test must either prove ModelCaller integration or be honestly renamed.

---

### P1 — Should Fix (Quality / Correctness)

#### P1.1 — `route_candidates` Dead Code 🟠 HIGH

**File:** `src/core/bandit_router.py` line 130  
**Wave:** G2 (M068, M050)  
**Impact:** Architectural drift — tested pipeline ≠ production pipeline  

**Problem:** `route_candidates()` is documented as the "shared routing pipeline" (preferences → bandit). However, neither `model_router.py` nor `model_caller.py` calls it. Both files implement the logic inline:
- `model_router.py:263` → `UserPreferenceModel().bias_candidates()`
- `model_router.py:280-281` → `self.bandit.select()`
- `model_caller.py:453` → `pref.bias_candidates()`

Tests in `test_routing_prefs_bandit_g2.py` verify `route_candidates` but not the actual inline implementation. This means tests can pass while the live path has different behavior.

**Fix required (pick one):**
- **Option A:** Wire `route_candidates` into `model_router.py` as the single routing entry point, removing the inline duplicated logic
- **Option B:** Remove `route_candidates` as dead code and update tests to verify the actual inline routing in `model_router.py`

**Acceptance:** The tested code path must match the production code path.

---

#### P1.2 — `promote_durable` Silent Failure 🟠 HIGH

**File:** `src/core/learning_engine.py` (~line 694)  
**Wave:** G1 (M061)  
**Impact:** Silent no-op when store is unreachable  

**Problem:**
```python
try:
    pool = self.memory.retrieve_by_tags(["learning"], limit=200)
except Exception:
    pool = []  # ← Returns empty, proceeds with ok: True
```

When the memory store is unreachable, `promote_durable` returns `{ok: True, count: 0}` — the operator sees "success" with zero promotions and has no way to know the store was down.

**Fix required:**
1. Catch the exception, set `ok: False`, include `error` and `error_code: "store_unreachable"` in the result
2. Add a test that mocks `retrieve_by_tags` to raise and verifies `ok: False`

---

#### P1.3 — `_apply_learning_update` Silent Failures 🟠 HIGH

**File:** `src/core/learning_engine.py` (~line 493)  
**Wave:** G1 (M061–M063)  
**Impact:** Callers assume metadata updates succeeded when they may have failed  

**Problem:** `_apply_learning_update` tries multiple backend APIs and swallows all exceptions with `except Exception: pass`. It returns `False` on total failure, but callers (like `distill_knowledge` ~line 1346) **ignore the return value**.

**Fix required:**
1. Replace `pass` with `logger.warning("metadata update failed for %s: %s", mid, e)`
2. In callers that depend on the update (especially `distill_knowledge`), check the return value and handle failure

---

#### P1.4 — Double Epsilon Bug 🟡 MEDIUM

**File:** `src/core/model_router.py` line 280  
**Wave:** G2 (M050)  
**Impact:** Bandit exploration rate is 1% instead of intended 10%  

**Problem:** Epsilon is checked twice:
```python
# model_router.py:280
if random.random() < self.bandit.epsilon:   # First check (10%)
    chosen = self.bandit.select(candidates)  # select() checks again (10%)
```

`EpsilonGreedyBandit.select()` at `bandit_router.py:54` also checks `random.random() < self.epsilon`.

With ε=0.1: true exploration = 0.1 × 0.1 = 1%, not 10%.

**Fix required:** Remove the outer epsilon check in `model_router.py:280`. Let `bandit.select()` handle exploration internally, since that's its contract.

```python
# Fixed:
if self.use_bandit and self.bandit and len(ranked) > 1:
    chosen = self.bandit.select(candidates)  # select() handles epsilon internally
```

---

### P2 — Nice to Have (Hardening)

#### P2.1 — Similarity Fallback Without Warning 🟡 MEDIUM

**File:** `src/core/learning_engine.py` (~line 106)  
**Wave:** G1 (M063)  

**Problem:** `_content_similarity` silently falls back from cosine/embedding similarity to Jaccard when the embedding function throws, with no warning logged.

**Fix:** Add `logger.warning("Embedding similarity failed, falling back to Jaccard: %s", e)`.

---

#### P2.2 — No Failure-Path Tests for Learning Lifecycle 🟡 MEDIUM

**File:** `tests/test_learning_lifecycle_m061_m063.py`  
**Wave:** G1  

**Problem:** The 22-test suite only covers happy paths. No tests verify behavior when `memory.store()`, `memory.retrieve_by_tags()`, or `memory.update()` raise exceptions.

**Fix:** Add at least 3 tests:
1. `test_distill_rollback_on_summary_store_failure` — mock `memory.store` to raise on summary; verify originals not deprecated
2. `test_promote_reports_error_on_store_failure` — mock `retrieve_by_tags` to raise; verify `ok: False`
3. `test_apply_learning_update_logs_warning_on_failure` — mock `memory.update` to raise; verify warning logged

---

#### P2.3 — Missing `post_call` Idempotency Guard 🟡 MEDIUM

**File:** `src/core/call_lifecycle.py` line 77  
**Wave:** G2 (M050)  

**Problem:** `post_call` updates bandit rewards, preference signals, and spend history without any idempotency check. If called twice for the same result dict, weights and spend are double-counted.

**Fix:** Add a `_post_call_done` sentinel key to the result dict:
```python
def post_call(result, ...):
    if result.get("_post_call_done"):
        return result
    # ... existing logic ...
    result["_post_call_done"] = True
    return result
```

---

#### P2.4 — Static Provider Matrix (G3) — NOTED

**File:** `src/core/token_stream.py` lines 185-220  
**Status:** Acceptable for offline DoD. The honesty message correctly states "Live SSE success is host-gated by API keys."

#### P2.5 — Config-Flag MOCK/LIVE Detection (G4) — NOTED

**File:** `src/core/observability.py`  
**Status:** Acceptable simplification. Active provider probing would add latency to dashboard snapshots.

---

## 3. Acceptance Criteria — Full Checklist

| # | Item | Priority | Criterion | Status |
|---|------|----------|-----------|--------|
| P0.1 | Distill rollback | P0 | Summary store first; on failure originals **not** deprecated + test | **DONE** — store-before-deprecate; `summary_store_failed` |
| P0.2 | Fix fake test | P0 | Real ModelCaller integration via `route_candidates` tracking | **DONE** |
| P1.1 | route_candidates alignment | P1 | Wired into `ModelCaller.call` + `ModelRouter` prefs path | **DONE** |
| P1.2 | promote_durable error reporting | P1 | `ok: False` + `store_unreachable` on retrieve failure | **DONE** |
| P1.3 | _apply_learning_update logging | P1 | `logger.warning` on failure paths | **DONE** |
| P1.4 | Double epsilon fix | P1 | Outer epsilon removed; single `bandit.select` | **DONE** |
| P2.1 | Similarity fallback warning | P2 | `logger.warning` on embedding → Jaccard | **DONE** |
| P2.2 | Failure-path tests | P2 | distill rollback, promote error, apply warning (+ post_call) | **DONE** |
| P2.3 | post_call idempotency | P2 | `_post_call_done` sentinel | **DONE** |

---

## 4. Verify

```powershell
# After fixes (Grok close-out):
pytest tests/test_learning_lifecycle_m061_m063.py tests/test_routing_prefs_bandit_g2.py tests/test_msg_vega_plugin_bandit.py -q
# → 35 passed
pytest tests/test_stream_dashboard_g3_g4.py tests/test_grok_i1_residuals.py -q
```

---

## 5. What Passed Clean ✅

| Area | Evidence |
|------|----------|
| G3 streaming SSE (Anthropic + OpenAI-compat) | Real `client.messages.stream()` + `stream=True` with delta extraction |
| G3 fallback honesty | `fallback_reason` populated on every fallback path |
| G3 cancel between chunks | `_cancelled()` checked in every chunk loop |
| G4 dashboard aggregation | Real data from TaskHistory, ProviderHealthStore, MemoryPalace |
| G5 never-false-pass | `live_passed` requires `passed > 0 AND failed == 0` |
| G5 atomic file operations | Cross-platform FileLock (msvcrt/fcntl) + tmp-rename with Windows retry |
| G5 budget precheck on live path | `budget_precheck(command_name="live-smoke")` guards live branch |
| I1 residual close-out (v1) | All v1 items closed: atomic prefs/bandit, stream aggregate, harness honesty |

---

*Deep re-review by AGY (Claude Opus 4.6 Thinking) with 4 parallel auditors. Stage I1 v2.0 — 2026-07-24.*
