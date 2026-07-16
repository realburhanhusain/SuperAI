# N206 Deploy — K8s CronJob, Multi-Host Cluster, Windows Task Scheduler

**Status:** Production-ready deploy expansion for the goals/schedules daemon  
**Related:** [GOALS_DAEMON.md](GOALS_DAEMON.md) (local daemon)  
**Modules:**

| Module | Path |
|--------|------|
| Cluster coordination | `src/core/daemon_cluster.py` |
| K8s CronJob generator | `src/core/k8s_cronjob.py` |
| Windows Task Scheduler | `src/core/windows_task_scheduler.py` |
| Packaged manifest | `packaging/k8s/superai-goals-cronjob.yaml` |
| CLI | `superai daemon …` |
| Tests | `tests/test_daemon_deploy_n206.py` + `tests/test_goals_daemon_n206.py` |

---

## Purpose

N206’s local daemon (`superai daemon start|tick|run`) is enough for a single machine. This document covers **three production deploy paths** that were previously out of scope:

1. **Kubernetes CronJob** — periodic `daemon tick` in-cluster  
2. **Multi-host cluster** — shared-file membership + leader election so only one host (or shards) executes work  
3. **Windows installer** — Task Scheduler registers a long-running `daemon run` (Service-like without a custom SCM binary)

---

## Architecture overview

```text
                    ┌─────────────────────────┐
                    │  superai daemon tick    │
                    │  (or daemon run loop)   │
                    └───────────┬─────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
   K8s CronJob            Multi-host             Windows Task
   (batch/v1)             cluster store          Scheduler
   every 5m               membership.json        ONLOGON →
                          leader lease           daemon run
```

| Path | When to use |
|------|-------------|
| Local `daemon start` | Dev / single workstation |
| K8s CronJob | Clustered Linux; no long-lived pod required |
| Multi-host cluster env | Multiple machines share the same goals/schedules store path |
| Windows Task Scheduler | Windows login / hourly launch of long-running daemon |

---

## 1. Kubernetes CronJob

### Generate manifest

```powershell
# Default: packaging/k8s/superai-goals-cronjob.yaml
superai daemon k8s-render

# Custom namespace / schedule / image
superai daemon k8s-render -o .\out\cron.yaml --namespace superai --cron "*/10 * * * *" --image python:3.12-slim

# Optional goal execute (still capped; never yolo)
superai daemon k8s-render --execute-goals --max-goals 2

# Validate without cluster
superai daemon k8s-validate
superai daemon k8s-validate -o packaging/k8s/superai-goals-cronjob.yaml

# If kubectl is installed: client dry-run
superai daemon k8s-render --kubectl-dry-run
```

### Apply

```bash
kubectl apply -f packaging/k8s/superai-goals-cronjob.yaml
kubectl get cronjob -n superai
kubectl get jobs -n superai
```

### Manifest contents

- **Namespace** `superai`
- **ServiceAccount** `superai`
- **CronJob** `superai-goals-tick`
  - Schedule default: `*/5 * * * *`
  - `concurrencyPolicy: Forbid` (no overlapping ticks)
  - Container runs: install SuperAI if needed → `superai daemon tick --max-goals 2 --no-notify`
  - Env: `SUPERAI_NON_INTERACTIVE=1`, `SUPERAI_MOCK_MODE=1` (override for production), `MEMPALACE_MCP_ALLOW_PEER_WRITER=1`

### Production notes

| Topic | Guidance |
|-------|----------|
| Image | Prefer a private image with SuperAI preinstalled; override `--image` |
| Secrets | Mount API keys via Secret → env; do not bake keys into YAML |
| Mock mode | Set `SUPERAI_MOCK_MODE=0` (or unset) for real model calls |
| Persistent state | Mount volume or remote store for `~/.superai` if goals must survive pods |
| Cluster mode | Set `SUPERAI_CLUSTER_MODE=leader_only` + shared PVC for membership if multiple CronJobs race |

### Programmatic API

```python
from pathlib import Path
from core.k8s_cronjob import render_cronjob_yaml, write_manifest, validate_yaml_text

yaml = render_cronjob_yaml(schedule="*/15 * * * *", execute_goals=False)
assert validate_yaml_text(yaml)["ok"]
write_manifest(Path("packaging/k8s/superai-goals-cronjob.yaml"))
```

---

## 2. Multi-host cluster coordination

Local-first design: **no Redis/etcd required**. Hosts share a JSON membership + leader lease file (local path, NFS, or SMB).

### Environment variables

| Variable | Default | Meaning |
|----------|---------|---------|
| `SUPERAI_CLUSTER_MODE` | *(unset = single)* | `single` / `off` / `disabled` = no cluster; `leader_only` = only leader ticks; `sharded` = all healthy hosts tick, schedules partitioned |
| `SUPERAI_CLUSTER_STORE` | `~/.superai/cluster/membership.json` | Shared membership file path |
| `SUPERAI_CLUSTER_HOST_ID` | `{hostname}-{pid}` | Stable id per host (set explicitly in multi-host) |
| `SUPERAI_CLUSTER_SHARD_EXECUTE` | off | If `1`/`true`, sharded mode allows every host to execute goals (default: execute on leader only) |

### Modes

| Mode | Who runs tick | Who runs schedule jobs | Who executes goals |
|------|---------------|------------------------|--------------------|
| `single` / unset | This host | All due | This host (if `--execute-goals`) |
| `leader_only` | Leader only | Leader only | Leader only |
| `sharded` | All healthy | Hashed by `job_id` → host index | Leader only (unless `SUPERAI_CLUSTER_SHARD_EXECUTE=1`) |

### Leader election

1. Each tick (or `cluster-heartbeat`) writes/refreshes this host under `hosts` with TTL (default 90s).  
2. Expired hosts are pruned.  
3. If lease is free or leader is dead: **stable sort of healthy host ids**, pick first → new leader + lease.  
4. Current leader renews `lease_until` on heartbeat.

### CLI

```powershell
# Register / refresh this host + elect leader
superai daemon cluster-heartbeat

# Inspect membership
superai daemon cluster-status

# Tick respects cluster mode when SUPERAI_CLUSTER_MODE is set
$env:SUPERAI_CLUSTER_MODE = "leader_only"
$env:SUPERAI_CLUSTER_STORE = "\\fileserver\share\superai\membership.json"
$env:SUPERAI_CLUSTER_HOST_ID = "build-box-01"
superai daemon tick
```

### Multi-host setup checklist

1. Put goals/schedules data on a **shared filesystem** (or same machine store if HA is only about who runs work).  
2. Point every host at the **same** `SUPERAI_CLUSTER_STORE`.  
3. Set a **stable** `SUPERAI_CLUSTER_HOST_ID` per machine (not PID).  
4. Use `leader_only` unless you need schedule sharding.  
5. Run `superai daemon start` (or Windows task / systemd) on each host.  
6. Verify with `cluster-status` that one leader appears and followers skip ticks (`skipped: true`).

### Programmatic API

```python
from core.daemon_cluster import heartbeat, cluster_status, should_run_tick, shard_owns, filter_jobs_for_host

print(heartbeat(host_id="box-1"))
print(cluster_status())
print(should_run_tick(mode="leader_only"))
assert shard_owns("job-abc", host_index=0, host_count=2) in (True, False)
```

### Limits (honest)

- Shared-file election is **best-effort**, not linearizable like etcd.  
- Clock skew and NFS caching can delay failover by ~TTL.  
- Not a replacement for Kubernetes leader election for hard HA SLAs.  
- Suitable for home lab / small multi-box SuperAI installs.

---

## 3. Windows Task Scheduler installer

SuperAI does **not** ship a custom Windows Service binary (SCM). Instead it installs a **Scheduled Task** that launches the long-running daemon:

```text
superai daemon run --interval 60 [--execute-goals]
```

### CLI

```powershell
# Install (current user ONLOGON; HOURLY fallback if ONLOGON fails)
superai daemon windows-install
superai daemon windows-install --interval 120 --task-name SuperAI-Goals-Daemon
superai daemon windows-install --execute-goals --cli-path "C:\Python\Scripts\superai.exe"

# Query / uninstall
superai daemon windows-query
superai daemon windows-uninstall
```

### What install does

1. Writes helper script: `%USERPROFILE%\.superai\daemon\install_windows_task.ps1`  
2. Runs `schtasks /Create … /SC ONLOGON /RL LIMITED /F`  
3. On failure, retries with `/SC HOURLY /MO 1`  
4. Returns JSON with `task_name`, `command`, stdout/stderr, `query_hint`

### Manual schtasks

```powershell
schtasks /Create /TN "SuperAI-Goals-Daemon" /TR "superai daemon run --interval 60" /SC ONLOGON /RL LIMITED /F
schtasks /Query /TN "SuperAI-Goals-Daemon" /V /FO LIST
schtasks /Delete /TN "SuperAI-Goals-Daemon" /F
```

### Non-Windows

`windows-install` / `uninstall` / `query` return `ok: false`, `error: not_windows` with a hint to use K8s or systemd.

### Linux alternative (reference)

```ini
# /etc/systemd/system/superai-goals.service
[Unit]
Description=SuperAI Goals Daemon
After=network.target

[Service]
ExecStart=/usr/bin/superai daemon run --interval 60
Restart=on-failure
Environment=SUPERAI_CLUSTER_MODE=single

[Install]
WantedBy=default.target
```

---

## Safety model (all deploy paths)

| Rule | Behavior |
|------|----------|
| No yolo | Automated goal execute forces permission ≤ ask |
| Execute opt-in | Default tick does **not** execute goals; CronJob default matches |
| Caps | `--max-goals` (default 2) |
| Cluster followers | Skip work in `leader_only` (no double execute) |
| Windows task | LIMITED rights by default; admin not required for ONLOGON self |

---

## CLI reference (`superai daemon`)

| Action | Description |
|--------|-------------|
| `status` | PID / config / last tick |
| `tick` | One cycle (cluster-aware) |
| `start` / `stop` / `run` | Background / stop / foreground loop |
| `cluster-status` | Membership + leader |
| `cluster-heartbeat` | Register + elect |
| `k8s-render` | Write CronJob YAML (`-o`, `--namespace`, `--cron`, `--image`, `--execute-goals`, `--kubectl-dry-run`) |
| `k8s-validate` | Structural YAML checks |
| `windows-install` | schtasks create (`--interval`, `--task-name`, `--cli-path`, `--execute-goals`) |
| `windows-uninstall` | schtasks delete |
| `windows-query` | schtasks query |

---

## Testing

```powershell
$env:PYTHONPATH = "src"
pytest tests/test_goals_daemon_n206.py tests/test_daemon_deploy_n206.py -q
```

### Coverage (`test_daemon_deploy_n206.py`)

| Area | Cases |
|------|--------|
| Cluster | heartbeat, leader renewal, failover, prune dead, leader_only skip, single mode, sharded execute flags, shard partition, filter_jobs |
| K8s | render, execute flag, write_manifest, validate good/bad, packaged YAML, kubectl missing, kubectl dry-run mock |
| Windows | PS1 render, not_windows, install mock success, HOURLY fallback, query/uninstall mock, command shape |
| Integration | tick skips follower, tick leader runs, cluster disabled default, schedule job_filter |

---

## Definition of done (N206 deploy expansion)

| Criterion | Evidence |
|-----------|----------|
| K8s CronJob | `k8s_cronjob.py` + `packaging/k8s/superai-goals-cronjob.yaml` + CLI |
| Multi-host cluster | `daemon_cluster.py` + cluster-aware `goals_daemon.tick` + sharded schedule filter |
| Windows installer | `windows_task_scheduler.py` + CLI (Task Scheduler + `daemon run`) |
| Thorough docs | This file + updated GOALS_DAEMON.md |
| Fully tested | `tests/test_daemon_deploy_n206.py` |

---

## Related

- Local daemon: [GOALS_DAEMON.md](GOALS_DAEMON.md)  
- Goals store: `assistant_goals.py`  
- Schedules: `schedule_store.py`  
- Scorecard: N206 in `V1_V6_UNIFIED_IMPROVED_SCORECARD.md` only (do not edit unified immutable scorecard for routine updates)
