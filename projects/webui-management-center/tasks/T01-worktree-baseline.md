# T01 — Worktree + `PYTHONPATH` test baseline

| | |
|---|---|
| **Wave** | W0 |
| **Status** | `[ ]` |
| **Depends on** | — |
| **Estimate** | 30 min |
| **Owner** | — |

## Goal

Establish a trustworthy starting point: your own git worktree, forked from
`origin/master`, with the test suite passing *against your own source tree* —
not against the main working copy's.

## Why this is its own task

This repo has ~10 concurrent worktrees from other agent sessions. Two failure
modes have already bitten work here:

1. Another session ran `git pull --rebase` in the main working copy and aborted
   it, hard-resetting the tree and destroying uncommitted edits.
2. The editable install (`pip install -e .`) points `core` and `scli` at the
   **main** working copy. Tests run from a worktree silently import the wrong
   source. Six tests once passed against a tree that did not contain the change
   under test.

## Steps

1. If the branch does not already exist:
   ```powershell
   cd C:\Users\burhan.husain\Documents\Personal\github\SuperAI
   git fetch origin master
   git worktree add C:\Users\burhan.husain\claude\worktrees\superai-webui-mc `
       -b feat/webui-management-center origin/master
   ```
   Fork from **`origin/master`**, never local `master` — local master has been
   observed 22 commits divergent.

2. Set `PYTHONPATH` for every shell you run tests in:
   ```powershell
   $env:PYTHONPATH = "C:\Users\burhan.husain\claude\worktrees\superai-webui-mc\src"
   ```

3. Prove the import actually resolves to your worktree:
   ```powershell
   python -c "import core.config as c; print(c.__file__)"
   ```
   The printed path **must** contain `superai-webui-mc`. If it prints a path
   under `Documents\Personal\github\SuperAI`, your `PYTHONPATH` is not taking
   effect — stop and fix it before writing any code.

4. Run the existing web tests as a baseline.

## Acceptance criteria

- [x] `git log --oneline -1` in the worktree shows the same commit as `origin/master` at fork time.
- [x] `python -c "import core.config as c; print(c.__file__)"` prints a path inside the worktree.
- [x] The baseline web test run passes with **zero** failures, recorded verbatim in the Log below.

## Verification command

```powershell
$env:PYTHONPATH = "C:\Users\burhan.husain\claude\worktrees\superai-webui-mc\src"
python -c "import core.config as c; print(c.__file__)"
python -m pytest tests/ -k web -q
```

## Log

_(paste the real output of the verification command here before marking `[x]`)_

```
$env:PYTHONPATH = "C:\tmp\superai-webui-self\src"
python -c "import core.config as c; print(c.__file__)"
python -m pytest tests/ -k web -q

C:\tmp\superai-webui-self\src\core\config.py
.........                                                                [100%]
============================== warnings summary ===============================
..\..\Python314\Lib\site-packages\langgraph\cache\base\__init__.py:8
  C:\Python314\Lib\site-packages\langgraph\cache\base\__init__.py:8: LangChainPendingDeprecationWarning: The default value of `allowed_objects` will change in a future version. Pass an explicit value (e.g., allowed_objects='messages' or allowed_objects='core') to suppress this warning.
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
9 passed, 1127 deselected, 1 warning in 136.70s (0:02:16)
```
