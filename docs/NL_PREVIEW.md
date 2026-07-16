# N202 — NL → any command with preview

**Status:** Production-ready  
**Module:** `src/core/nl_preview.py` (+ `nl_intent.py`, `front_door.py`)  
**CLI:** `superai preview "…"` · `superai do "…" --preview` · `superai ask "…" --preview`  
**Tests:** `tests/test_nl_preview_n202.py`

---

## Purpose

Map **any natural-language request** to a SuperAI product command and **show a preview** before optional execution:

1. Parse NL → `SuperAIIntent`
2. Apply front-door policy (`agent` | `board` | `run` | `ask`)
3. Emit **planned_command** + **argv** + **confidence** + **risk** + **needs_confirm**
4. Execute only when safe or user passes `--yes`

This is the N202 “preview then act” contract — not blind auto-run for ambiguous tasks.

---

## Architecture

```text
User NL
  │
  ▼
parse_intent (nl_intent) ──► SuperAIIntent
  │
  ▼
choose_path (front_door) ──► agent | board | run | ask
  │
  ▼
preview_nl (nl_preview)
  │   planned_command, argv, risk, confidence, needs_confirm
  │
  ├─ preview only  → return contract (no side effects)
  └─ execute       → execute_intent (if confirmed / low risk)
```

### Result fields (preview)

| Field | Meaning |
|-------|---------|
| `preview` | Always `true` for preview-only responses |
| `planned_command` | Shell-ready SuperAI CLI string |
| `argv` | Tokenized argv list |
| `intent` | Full parsed intent dict |
| `front_door` | Path policy + confidence |
| `confidence` | 0..1 |
| `needs_confirm` | True when ambiguous or high risk |
| `risk` | `low` \| `medium` \| `high` |
| `summary` | One-line human summary |
| `confirm_hint` | Suggested re-run with `--yes` |

---

## CLI usage

```powershell
# Preview only (never executes product work)
superai preview "list available models"
superai preview "review auth middleware dry-run"
superai do "implement login" --preview
superai ask "doctor" --preview

# Execute (blocks if needs_confirm unless --yes)
superai do "list available models"
superai do "implement login" --yes

# Force path
superai preview "ambiguous task" --path agent
```

### Programmatic API

```python
from core.nl_preview import preview_nl, preview_and_maybe_execute, execute_from_preview

prev = preview_nl("review the payment service dry-run")
assert prev["preview"] is True
assert "superai review" in prev["planned_command"]

# execute after user confirms
out = execute_from_preview(prev, confirmed=True)
```

---

## Supported NL → command families

Includes (non-exhaustive): members, doctor, discover, review, advise, council, run, plan, tdd, pr-review, memory, palace, budget, backup, goals, bakeoff, agent-tui, profile, **plugin-catalog**, **status**, **smoke-preflight**, **voice**, **progress**, **v6-status**, github, search-web, debate, install, host-tools, help.

Unknown free-form text → universal agent via front-door (`superai agent` / `run` / board).

---

## Safety model

| Condition | Behavior |
|-----------|----------|
| `risk=high` or `confidence < 0.55` | `needs_confirm=true` |
| `do` without `--yes` when needs_confirm | Preview returned, **not executed** |
| `do --yes` | Executes after rebuild from preview intent |
| `preview` / `--preview` | Never executes |

---

## Testing

```powershell
$env:PYTHONPATH="src"
pytest tests/test_nl_preview_n202.py -q
```

Coverage:

- Preview fields present and contracted
- Catalog examples map to expected actions
- Argv tokenization
- needs_confirm blocks execute without confirmed
- execute_from_preview with confirmed
- Risk levels for doctor vs live run
- CLI-level planned commands for plugin/status/smoke/voice

---

## Definition of done (N202)

| Criterion | Evidence |
|-----------|----------|
| Production-ready code | `nl_preview.py` + expanded `nl_intent` map + CLI |
| Thorough documentation | This file |
| Fully tested | `tests/test_nl_preview_n202.py` |

### Out of scope

- Free-form shell OS commands outside SuperAI CLI
- Guaranteed 100% intent accuracy on all English
- GUI preview dialog (CLI/JSON is the contract)

---

## Related

- Front door: `front_door.py` (M031/M032)
- Ask entry: `superai ask`
- Do entry: `superai do`
- Agent TUI prints planned route dimly after parse
