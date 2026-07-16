# N206 — Daemon for goals / schedules

**Status:** Production-ready local daemon  
**Module:** `src/core/goals_daemon.py`  
**Integrates:** `assistant_goals.GoalStore`, `schedule_store.ScheduleStore`  
**CLI:** `superai daemon …` · `superai goals tick`  
**Tests:** `tests/test_goals_daemon_n206.py`

---

## Purpose

Run SuperAI **goals** and **schedules** on a recurring loop without external cron:

1. **Tick** — one cycle: due schedules → goals heartbeat → optional notify → optional execute  
2. **Daemon** — background or foreground loop with PID, state, and log files  
3. **Safety** — never inherits `yolo`; goal execute is **opt-in**; max goals capped  

---

## Architecture

```text
superai daemon start
        │
        ▼
  background process (PID ~/.superai/daemon/goals.pid)
        │
        ▼ loop every interval_sec
  goals_daemon.tick()
        ├─ ScheduleStore.run_due()     (backup|doctor|run:|ask:|goals-tick)
        ├─ GoalStore.heartbeat()
        ├─ GoalStore.notify_due()      (opt)
        └─ GoalStore.execute_due()     (opt, never yolo)
```

### Files

| Path | Role |
|------|------|
| `~/.superai/daemon/goals.pid` | Running process id |
| `~/.superai/daemon/goals_daemon.json` | Config + last tick stats |
| `~/.superai/logs/goals_daemon.log` | Append-only daemon log |
| `~/.superai/assistant_goals.json` | Goals store |
| `~/.superai/schedules.json` | Schedule jobs |

---

## CLI

```powershell
# Status
superai daemon status

# One tick (schedules + heartbeat; no goal execute by default)
superai daemon tick

# Tick and execute due goals (safe caps)
superai daemon tick --execute-goals --max-goals 2

# Foreground loop (Ctrl+C to stop) — great for debug
superai daemon run --interval 30 --max-ticks 3

# Background start / stop
superai daemon start --interval 60
superai daemon start --interval 120 --execute-goals
superai daemon stop

# Existing goals alias for single tick
superai goals tick
superai goals tick --execute
superai goals daemon   # → status
```

### Options

| Flag | Default | Meaning |
|------|---------|---------|
| `--interval / -i` | 60 | Seconds between ticks |
| `--execute-goals` | off | Run due goals via ask (capped) |
| `--notify / --no-notify` | on | Messenger notify for due goals |
| `--schedule / --no-schedule` | on | Run due schedule jobs |
| `--max-goals` | 2 | Cap goals executed per tick |
| `--max-ticks` | 0 | Stop after N ticks (0 = forever) |
| `--foreground / -f` | off | With `start`: block in this process |

---

## Safety model

| Rule | Behavior |
|------|----------|
| No yolo | Automated execute forces permission ≤ ask |
| Budget | Auto goals tighten run budget (see `execute_due`) |
| Execute opt-in | Default tick does **not** execute goals |
| Caps | `max_goals` default 2 (hard max 3 in store) |
| Plan mode notify | Messenger send dry-runs when permission=plan |

---

## Programmatic API

```python
from core.goals_daemon import status, tick, start_background, stop, run_loop

print(status())
print(tick(execute_goals=False))
# run_loop(interval_sec=5, max_ticks=2)  # tests / foreground
```

### Schedule commands supported

| Command | Action |
|---------|--------|
| `backup` | Incremental backup |
| `doctor` | Quick doctor |
| `run:<task>` | Orchestrator run_task |
| `ask:<nl>` | NL ask_superai |
| `goals-tick` | Goals heartbeat tick only |

```powershell
superai schedule add "nightly-doctor" doctor --every-hours 24
superai daemon tick
```

---

## Testing

```powershell
$env:PYTHONPATH="src"
pytest tests/test_goals_daemon_n206.py -q
```

Coverage: status shape, tick updates state, run_loop max_ticks, start already-running, stop stale pid, schedule integration, safety defaults.

---

## Definition of done (N206)

| Criterion | Evidence |
|-----------|----------|
| Production-ready code | `goals_daemon.py` + CLI `daemon` |
| Thorough documentation | This file |
| Fully tested | `tests/test_goals_daemon_n206.py` |

### Out of scope

- Kubernetes CronJob / cloud scheduler product  
- Multi-host distributed daemon cluster  
- Windows Service installer (use Task Scheduler + `daemon run` if needed)

---

## Related

- Goals store: `assistant_goals.py` (Phase 8 N2)  
- Schedules: `schedule_store.py` (N10)  
- Caps / goals safety: M096  
