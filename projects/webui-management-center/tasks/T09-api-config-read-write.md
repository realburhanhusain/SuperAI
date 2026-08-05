# T09 — `GET` / `POST /api/config`

| | |
|---|---|
| **Wave** | W2 |
| **Status** | `[ ]` |
| **Depends on** | T06, T07, T08 |
| **Estimate** | 2 h |
| **Owner** | — |

## Goal

The first endpoint in SuperAI that **writes configuration over HTTP**. Treat it
accordingly.

## Preconditions

Do not start until T06 (atomic write + backup), T07 (validation + diff) and T08
(flag + management token) are all `[x]`. This task is the thin layer on top; if
any of the three underneath is missing, this endpoint is a liability.

## `GET /api/config`

- Source: `core.config.Config().show()` (`config.py:246-247`).
- **Redact before serializing**: run the dict through
  `core.secrets.redact_obj` (`secrets.py:30-39`).
- Redact even though SuperAI's config holds no raw provider keys today (they
  come from env vars via `provider_catalog.py`). This is defence in depth
  against a future field that does, and against a user pasting a key into a
  free-text value. The cost is one function call; the failure it prevents is a
  secret rendered into a browser.
- Auth: management token, unconditionally — including loopback (T08).

## `POST /api/config`

Body: `{"changes": {"key": value, ...}}`. Order of operations, strictly:

1. **Authorise** (management token, T08).
2. **Validate** via `validate_changes` (T07). Any problem → refuse with the
   per-key messages, write nothing.
3. **Write** via the atomic, backed-up `save()` (T06), targeting
   `~/.superai/config.json` — **never** a repo-tracked file (constraint C2).
4. **Audit** via `AuditLog().record("config.write", detail=..., actor="web",
   outcome=...)` (`audit_log.py:20-36`). It already redacts `detail` at `:32`.
   Log the **outcome too, including failures** — an audit log that records only
   successes cannot answer "who tried?", which is usually the question that
   matters.
5. **Respond** with what changed and the backup id created, so the UI can offer
   an immediate undo.

## The singleton caveat — do not overclaim

`config.py:281` is a module-level `config = Config()`. Modules importing that
object hold an import-time snapshot and will **not** see a web-issued write
until the process restarts.

T06 recorded the importer list. Use it:

- If nothing meaningful imports the singleton → a write takes effect immediately;
  say so.
- If something does → the response and the docs must say **which** settings need
  a restart. Do not write "changes apply immediately" unless it has been
  demonstrated. An unverified reassurance in a config UI is worse than an
  honest caveat, because the user stops looking for the real cause.

## Acceptance criteria

- [ ] `GET /api/config` returns the config, redacted, management-token gated.
- [ ] Redaction test: a config value shaped like `sk-...` round-trips as redacted.
- [ ] `POST` with an invalid change → refused, per-key messages, **file unchanged** (assert content hash).
- [ ] `POST` with a valid change → written atomically, backup created, audit entry appended.
- [ ] Audit entry is written on failure paths too.
- [ ] Test proves no repo-tracked file is touched (fake `HOME`; assert repo `config/` hashes unchanged).
- [ ] Hot-reload behaviour is **stated accurately** in the response/docs, based on T06's importer list.

## Verification command

```powershell
$env:PYTHONPATH = "C:\Users\burhan.husain\claude\worktrees\superai-webui-mc\src"
python -m pytest tests/test_web_management_center.py -k "config" -q
```

## Log

_(record the real result, and the hot-reload verdict with evidence, before marking `[x]`)_
