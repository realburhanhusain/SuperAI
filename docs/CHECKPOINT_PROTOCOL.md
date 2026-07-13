# Checkpoint protocol (SuperAI_v1)

## Why

Protect progress against power loss, OS crash, network drop, or agent session death.  
**TASKBOARD.md** is the plan/state board. **Checkpoints** freeze a recoverable moment.

## Rules (mandatory for agents)

1. After finishing any TASKBOARD item (or every ~30–45 min of work), create a checkpoint.
2. Update **TASKBOARD.md** Last session **before** the checkpoint.
3. Prefer **local git commit** + `docs/checkpoints/CHECKPOINT_*.md` (no force-push).
4. Never delete prior checkpoints.
5. On resume: open latest checkpoint + TASKBOARD, then continue first incomplete item.

## Commands

```powershell
cd C:\Users\burhan.husain\Documents\Personal\github\SuperAI_v1

# Full checkpoint (runs pytest + git commit if dirty)
powershell -File scripts\checkpoint.ps1 -Label "F3.1-embeddings"

# Faster (skip tests) when mid-item
powershell -File scripts\checkpoint.ps1 -Label "mid-F3" -SkipTests
```

## What is covered

| Layer | Mechanism |
|-------|-----------|
| Code | git history + working tree |
| Plan state | TASKBOARD.md in commit |
| Session evidence | docs/checkpoints/*.md |
| Runtime memory/config | `superai backup` → `~/.superai/backups/` |

## Suggested improvement (optional infra, still required product work elsewhere)

- Enable **Windows File History** or cloud sync of `Documents\Personal\github\SuperAI_v1` + export of `~/.superai/.backup_key`.
- Keep API keys only in env / secret store, not in git.
- Periodic `superai backup --full --keep 20` via Task Scheduler.

## Recovery after fault

```powershell
cd C:\Users\burhan.husain\Documents\Personal\github\SuperAI_v1
Get-ChildItem docs\checkpoints | Sort-Object LastWriteTime -Descending | Select-Object -First 3
# read latest CHECKPOINT_*.md + TASKBOARD.md
git log -5 --oneline
pytest -q
```
