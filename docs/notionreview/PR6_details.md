# PR 6 — Escape trust-boundary delimiters on the memory write path

**PR:** https://github.com/realburhanhusain/SuperAI/pull/6
**Branch:** `security/sanitize-memory-on-write` → **`security/untrusted-memory-delimiting`** (stacked on PR #2, *not* master)
**Files:** `src/core/central_memory.py`, `tests/test_central_memory_sanitize.py` (new, 13 tests)
**Status:** open, awaiting review. Blocked on PR #2 merging first.

---

## ⚠️ Merge order

This PR calls `neutralize_delimiters`, which exists only on PR #2's branch. Its base is therefore PR #2's branch, not master. **Merge PR #2 first**; GitHub retargets this to master automatically. Do not repoint the base to master by hand — it will not build.

## What was there

`central_memory.write_back` redacted secrets before persisting a body (`redact_text`) but escaped nothing. Memory bodies are attacker-influenced: they can originate from a web page, a file, a tool result, or another CLI's stdout. So a body could be stored containing the literal markers the orchestrator uses to fence untrusted data, and close that fence from the inside when the memory was retrieved into a later prompt.

PR #2 fixed the read side. This is the write side of the same problem.

## Why it was picked

It was the open decision recorded against item 3 of the backlog, and the owner chose escape.

The reason it matters more than a normal defence-in-depth item: the memory store is long-lived and shared across every mediated CLI. A poisoned row outlives the run that created it, and will be retrieved into unrelated future tasks. Read-side wrapping protects the current build; it does nothing about what is already sitting in the store, or about a future retrieval path that forgets to wrap.

## Why escape, and not reject or quarantine

- **Reject** hands attacker-controlled content a veto over what the system may remember. Feed the agent a page containing the delimiter string and its memory of that task silently vanishes. That is a denial-of-memory primitive, and a quiet one.
- **Quarantine** requires a second store, a review surface, and a human who actually reads it. None exist here. An unread quarantine is deletion with extra bookkeeping.
- **Escape** keeps the text, keeps it readable to the model, and removes only the property that made it dangerous: the ability to terminate its own span. `rm -rf /` still survives in the stored body, and a test asserts that it does. The aim was never to censor content — only to stop it escaping the fence.

## What changed

A single helper, `_sanitize_for_memory`, and four call sites that use it in place of a bare `redact_text`: the learning task description, the learning error message, the stdout/stderr envelope, and the outcome snippet.

Redaction runs first so a secret cannot hide behind escaping; neutralization runs last so redaction markers cannot reintroduce a delimiter. Each step is individually exception-guarded and degrades to identity — a memory write is not worth failing a live run over. The `untrusted_data` import is guarded too, so the file does not hard-break if ever built without PR #2.

The `write_back` docstring now states the invariant: every body persisted here goes through the helper, and no new store call in that function may write a raw string.

## Scope limit — half of this is deliberately undone

This covers `central_memory.write_back`. It does **not** cover `learning_engine.learn_from_step`, which the orchestrator calls directly on its own path.

That site is in `src/core/learning_engine.py` — 68,569 bytes. The only write tool available to me replaces whole files, and at that size my own output limit truncated a previous write and committed syntactically invalid Python (see PR #2's history, commit `b604280`, repaired in `7ae47fc`). Rather than risk that again, that half is left visibly open.

Consequence: PR #2's read-side envelope remains the defence that covers both write paths. This PR hardens one of them.

## What happens if it is not implemented

Nothing regresses — the read-side envelope from PR #2 is the boundary that actually matters, and it stays in place. What is lost is the second layer: rows written by an older build, or retrieved by some future path that forgets to wrap, keep the ability to forge a delimiter. Because the store is shared and long-lived, that exposure does not expire with the run.

## Risk

Low. No control flow changed. Every added step is exception-guarded and falls back to prior behaviour. Stored text changes only when it contains the delimiter strings, which no legitimate body should.

One genuine behavioural change: a body containing the literal marker text is now stored slightly altered. That is the intent, not a side effect.

## Verification

- `src/core/central_memory.py` read back in full after the push; complete, ends correctly.
- The 13 new tests have **not been run** — I cannot execute code:

```
pytest tests/test_central_memory_sanitize.py -v
pytest tests/test_orchestrator_untrusted_memory.py -v
```

- 11 of the 13 exercise the helper directly and must pass. The remaining 2 reach the real write path and will `skip`, not fail, when the memory backend is unavailable. Skips there are expected.
