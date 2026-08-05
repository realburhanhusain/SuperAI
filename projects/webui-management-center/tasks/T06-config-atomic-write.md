# T06 — `Config.save()` atomic write + backup

| | |
|---|---|
| **Wave** | W2 |
| **Status** | `[ ]` |
| **Depends on** | T01 |
| **Estimate** | 1.5 h |
| **Owner** | — |

## Goal

Make config writes crash-safe and reversible **before** any HTTP endpoint can
trigger them.

## Why this comes before the endpoint

`src/core/config.py:239-244` today is:

```python
def save(self, quiet: bool = False) -> None:
    self._ensure_home()
    with open(self.config_path, "w", encoding="utf-8") as f:
        json.dump(self.config, f, indent=2)
```

`open(..., "w")` truncates immediately. A crash between truncate and complete
write leaves a **corrupt or empty** `config.json`. That is tolerable today
because only interactive CLI commands reach it. Add an HTTP route and the same
line becomes remotely triggerable config destruction.

**Adding a UI does not just add UI — it promotes every latent weakness behind
it into a reachable one.** Close this first.

## Steps

1. Rewrite `Config.save()` as write-temp → `flush` → `os.fsync` → `os.replace`:
   - Write to a temp file **in the same directory** as the target (`os.replace`
     is only atomic within a filesystem).
   - `fsync` the file handle before replacing.
   - `os.replace()` is atomic on both POSIX and Windows — use it, not
     `os.rename`, which fails on Windows when the destination exists.
2. Before replacing, copy the current file to
   `~/.superai/backups/config-<UTC-timestamp>.json`. The `backups/` directory
   already exists in `Config.initialize()`'s layout (`config.py:137`) and is
   currently unused for this purpose.
   - Skip the backup silently when no config file exists yet (first run).
   - Cap retention (e.g. keep the newest 20) so the directory does not grow
     without bound.
3. Do **not** change `save()`'s signature or its `quiet` behaviour. Every
   existing caller must keep working untouched.
4. Clean up the temp file on failure; never leave `config.json.tmp` behind.

## The singleton caveat — record findings, do not fix here

`config.py:281` defines a module-level `config = Config()`. Any module importing
**that object** holds a snapshot taken at import time and will not observe a
later write until the process restarts.

Enumerate the importers:

```powershell
Select-String -Path src\**\*.py -Pattern "from core.config import config|from core import config"
```

Write the list into the Log below. **Do not attempt a fix in this task** — it
determines whether T09 may claim "hot reload" in docs, and it may need an owner
decision.

## Acceptance criteria

- [ ] `save()` uses temp-file → fsync → `os.replace`.
- [ ] A backup lands in `~/.superai/backups/` before each overwrite; first run does not error.
- [ ] **Crash test:** monkeypatch a failure *after* the temp write and *before* the replace; assert the original `config.json` is byte-identical to what it was.
- [ ] Retention cap enforced and tested.
- [ ] All existing config tests still pass, unmodified.
- [ ] Singleton importer list recorded in the Log.

## Verification command

```powershell
$env:PYTHONPATH = "C:\Users\burhan.husain\claude\worktrees\superai-webui-mc\src"
python -m pytest tests/ -k config -q
```

## Log

| Date | Agent | Change |
|------|-------|--------|
| 2026-08-05 | self | Completed T06. Added atomic write and backups for `Config.save()`. |

**Singleton importer list:** None found (no direct `config` module-level imports, only `Config` class).

**Crash test result:** The monkeypatched crash test passes correctly.

**Verification output:**
```
...................                                                      [100%]
============================== warnings summary ===============================
..\..\Python314\Lib\site-packages\langgraph\cache\base\__init__.py:8
  C:\Python314\Lib\site-packages\langgraph\cache\base\__init__.py:8: LangChainPendingDeprecationWarning: The default value of `allowed_objects` will change in a future version. Pass an explicit value (e.g., allowed_objects='messages' or allowed_objects='core') to suppress this warning.
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
20 passed, 1117 deselected, 1 warning in 34.78s
```
