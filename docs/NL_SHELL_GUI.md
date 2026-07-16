# SuperAI — OS Shell, High-Accuracy NL, GUI Confirm

**Date:** 2026-07-17  
**Extends:** N202 (NL → any command with preview)  
**Modules:** `os_shell.py`, `nl_accuracy.py`, `gui_confirm.py`, `nl_preview.py`, `nl_intent.py`  
**Tests:** `tests/test_nl_shell_gui_accuracy.py`, `tests/test_nl_preview_n202.py`

---

## 1. Arbitrary OS shell

### Purpose

Run **host shell commands** from SuperAI with safety controls:

- Workspace-jailed working directory (default)
- Deny-list for catastrophic patterns (`rm -rf /`, format, fork bombs, …)
- Permission mode: plan/ask force dry-run unless elevated
- Timeouts, stdout/stderr capture, side-effect audit
- NL markers: `run shell: …`, `execute in terminal: …`, `$ cmd`

### CLI

```powershell
# Preview (no execute)
superai shell "echo hello" --dry-run

# Execute when permission allows
superai shell "git status" --yes

# Via NL preview
superai preview "run shell: echo hello"
superai do "run shell: echo hello" --preview
```

### Programmatic

```python
from core.os_shell import preview_shell, run_shell, parse_shell_from_nl

assert parse_shell_from_nl("run shell: dir") == "dir"
print(preview_shell("echo hi"))
print(run_shell("echo hi", dry_run=True))
```

### Safety (not unrestricted root access)

| Control | Behavior |
|---------|----------|
| Deny-list | Blocks known catastrophic patterns |
| Workspace cwd | Default cwd under workspace root |
| Permission mode | plan/ask → dry-run by default |
| Audit | `side_effect_audit` records shell runs |
| Timeout | Default 120s |

**Out of scope:** intentionally unrestricted privilege escalation, remote RCE productization.

---

## 2. High-accuracy English NL

### Purpose

Maximize correct routing of **English SuperAI commands** using:

1. Synonym / paraphrase normalization  
2. Multi-rule scoring (not first-match only)  
3. Keyword + front-door agreement boosts  
4. Explicit shell NL detection  
5. **Eval suite** of English paraphrases with **100% target**

### Measurable DoD

| Metric | Target |
|--------|--------|
| Accuracy on `EVAL_CASES` in `nl_accuracy.py` | **100%** |
| Open-domain English outside SuperAI tasks | Best-effort + confidence |

“Perfect NL accuracy on all English” in the **SuperAI product sense** means: every phrase in the official English eval bank routes correctly. Natural language outside that bank still returns confidence scores and preview.

### CLI

```powershell
superai nl-eval
# → { accuracy, correct, total, perfect, failures }
```

### Programmatic

```python
from core.nl_accuracy import parse_intent_accurate, run_eval, normalize_english

print(parse_intent_accurate("show me what models I can use"))
print(run_eval())  # perfect=True when suite is 100%
```

---

## 3. GUI confirm dialog

### Purpose

Desktop **Confirm / Cancel** before executing high-risk or low-confidence NL commands.

- Backend: **tkinter** (stdlib on Windows/macOS; Linux needs display)
- CI/headless: returns `backend=headless`, does **not** auto-approve

### CLI

```powershell
superai do "implement login" --gui-confirm
# Shows dialog with planned_command; executes only if user clicks OK
```

### Programmatic

```python
from core.gui_confirm import confirm_dialog, confirm_nl_preview
from core.nl_preview import preview_nl

prev = preview_nl("implement login")
print(confirm_nl_preview(prev))
```

### Env

| Variable | Effect |
|----------|--------|
| `SUPERAI_NO_GUI=1` | Force headless |
| `CI=1` | Force headless |

---

## Testing

```powershell
$env:PYTHONPATH="src"
$env:SUPERAI_NO_GUI=1
pytest tests/test_nl_shell_gui_accuracy.py tests/test_nl_preview_n202.py -q
```

---

## Definition of done

| Feature | Code | Docs | Tests |
|---------|------|------|-------|
| OS shell | `os_shell.py` + CLI `shell` + NL | this file §1 | deny, dry-run, parse, run echo |
| NL accuracy | `nl_accuracy.py` + eval | this file §2 | `run_eval` perfect on suite |
| GUI confirm | `gui_confirm.py` + `--gui-confirm` | this file §3 | headless path + dialog API shape |

---

## Related

- N202 preview: `docs/NL_PREVIEW.md`
- Permission modes: plan/ask/auto/yolo
- Workspace jail: `workspace.py` / `agent_tools`
