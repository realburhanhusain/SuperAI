"""N206 expansion — K8s CronJob, multi-host cluster, Windows Task Scheduler."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Multi-host cluster
# ---------------------------------------------------------------------------


@pytest.fixture()
def cluster_env(tmp_path, monkeypatch):
    store = tmp_path / "cluster" / "membership.json"
    monkeypatch.setenv("SUPERAI_CLUSTER_STORE", str(store))
    monkeypatch.delenv("SUPERAI_CLUSTER_HOST_ID", raising=False)
    monkeypatch.setenv("SUPERAI_CLUSTER_MODE", "leader_only")
    import importlib

    import core.daemon_cluster as dc

    importlib.reload(dc)
    yield tmp_path, dc, store


def test_heartbeat_elects_leader(cluster_env):
    tmp_path, dc, store = cluster_env
    a = dc.heartbeat(host_id="host-a", ttl_sec=60)
    assert a["ok"] is True
    assert a["is_leader"] is True
    assert a["leader"] == "host-a"
    assert a["host_count"] == 1

    b = dc.heartbeat(host_id="host-b", ttl_sec=60)
    assert b["ok"] is True
    # stable sort: host-a before host-b
    assert b["leader"] == "host-a"
    assert b["is_leader"] is False
    assert b["host_count"] == 2
    assert store.is_file()


def test_leader_renewal(cluster_env):
    tmp_path, dc, store = cluster_env
    a1 = dc.heartbeat(host_id="solo", ttl_sec=90)
    lease1 = a1["lease_until"]
    a2 = dc.heartbeat(host_id="solo", ttl_sec=90)
    assert a2["is_leader"] is True
    assert a2["lease_until"] >= lease1


def test_leader_failover_when_expired(cluster_env, monkeypatch):
    tmp_path, dc, store = cluster_env
    # seed store with dead leader
    store.parent.mkdir(parents=True, exist_ok=True)
    now = 1_000_000.0
    monkeypatch.setattr(dc, "_now", lambda: now)
    store.write_text(
        json.dumps(
            {
                "hosts": {
                    "old-leader": {
                        "host_id": "old-leader",
                        "last_seen": now - 200,
                        "expires": now - 100,
                        "meta": {},
                    }
                },
                "leader": "old-leader",
                "lease_until": now - 50,
            }
        ),
        encoding="utf-8",
    )
    hb = dc.heartbeat(host_id="new-host", ttl_sec=60)
    assert hb["is_leader"] is True
    assert hb["leader"] == "new-host"


def test_cluster_status_prunes_dead(cluster_env, monkeypatch):
    tmp_path, dc, store = cluster_env
    dc.heartbeat(host_id="alive", ttl_sec=120)
    data = json.loads(store.read_text(encoding="utf-8"))
    data["hosts"]["dead"] = {
        "host_id": "dead",
        "last_seen": 0,
        "expires": 1,
        "meta": {},
    }
    store.write_text(json.dumps(data), encoding="utf-8")
    st = dc.cluster_status()
    assert st["ok"] is True
    assert "alive" in st["hosts"]
    assert "dead" not in st["hosts"]


def test_should_run_tick_leader_only(cluster_env):
    tmp_path, dc, store = cluster_env
    dc.heartbeat(host_id="alpha", ttl_sec=60)
    leader = dc.should_run_tick(host_id="alpha", mode="leader_only")
    assert leader["run_tick"] is True
    assert leader["run_execute"] is True

    follower = dc.should_run_tick(host_id="beta", mode="leader_only")
    assert follower["run_tick"] is False
    assert follower["reason"] == "follower_skip"


def test_should_run_tick_single_mode(cluster_env):
    tmp_path, dc, store = cluster_env
    out = dc.should_run_tick(host_id="any", mode="single")
    assert out["run_tick"] is True
    assert out["mode"] == "single"


def test_should_run_tick_sharded(cluster_env, monkeypatch):
    tmp_path, dc, store = cluster_env
    monkeypatch.delenv("SUPERAI_CLUSTER_SHARD_EXECUTE", raising=False)
    dc.heartbeat(host_id="h0", ttl_sec=60)
    dc.heartbeat(host_id="h1", ttl_sec=60)
    leader = dc.should_run_tick(host_id="h0", mode="sharded")
    assert leader["run_tick"] is True
    # leader (sorted first) may execute
    follower = dc.should_run_tick(host_id="h1", mode="sharded")
    assert follower["run_tick"] is True
    assert follower["run_execute"] is False  # default: execute leader only


def test_should_run_tick_sharded_execute_all(cluster_env, monkeypatch):
    tmp_path, dc, store = cluster_env
    monkeypatch.setenv("SUPERAI_CLUSTER_SHARD_EXECUTE", "1")
    dc.heartbeat(host_id="h0", ttl_sec=60)
    dc.heartbeat(host_id="h1", ttl_sec=60)
    follower = dc.should_run_tick(host_id="h1", mode="sharded")
    assert follower["run_execute"] is True


def test_shard_owns_partition(cluster_env):
    tmp_path, dc, store = cluster_env
    n = 3
    buckets = {0: 0, 1: 0, 2: 0}
    for i in range(30):
        for idx in range(n):
            if dc.shard_owns(f"job-{i}", idx, n):
                buckets[idx] += 1
                break
    assert sum(buckets.values()) == 30
    # each host gets some work (not all on one)
    assert all(v > 0 for v in buckets.values())


def test_filter_jobs_for_host(cluster_env):
    tmp_path, dc, store = cluster_env
    jobs = [{"id": f"j{i}"} for i in range(10)]
    owned0 = dc.filter_jobs_for_host(jobs, host_index=0, host_count=2)
    owned1 = dc.filter_jobs_for_host(jobs, host_index=1, host_count=2)
    ids0 = {j["id"] for j in owned0}
    ids1 = {j["id"] for j in owned1}
    assert ids0.isdisjoint(ids1)
    assert ids0 | ids1 == {f"j{i}" for i in range(10)}


def test_default_host_id_from_env(cluster_env, monkeypatch):
    tmp_path, dc, store = cluster_env
    monkeypatch.setenv("SUPERAI_CLUSTER_HOST_ID", "fixed-id-9")
    assert dc.default_host_id() == "fixed-id-9"


# ---------------------------------------------------------------------------
# K8s CronJob
# ---------------------------------------------------------------------------


def test_render_cronjob_yaml_valid():
    from core.k8s_cronjob import render_cronjob_yaml, validate_yaml_text

    yaml = render_cronjob_yaml(
        name="superai-goals-tick",
        namespace="superai",
        schedule="*/10 * * * *",
        execute_goals=False,
    )
    assert "kind: CronJob" in yaml
    assert "kind: Namespace" in yaml
    assert "*/10 * * * *" in yaml
    assert "daemon tick" in yaml or "daemon" in yaml
    assert "concurrencyPolicy: Forbid" in yaml
    v = validate_yaml_text(yaml)
    assert v["ok"] is True
    assert all(v["checks"].values())


def test_render_execute_goals_flag():
    from core.k8s_cronjob import render_cronjob_yaml

    yaml = render_cronjob_yaml(execute_goals=True, max_goals=3)
    assert "--execute-goals" in yaml
    assert "--max-goals" in yaml


def test_write_manifest(tmp_path):
    from core.k8s_cronjob import write_manifest, validate_yaml_text

    out = tmp_path / "cj.yaml"
    res = write_manifest(out, namespace="ns-test", schedule="0 * * * *")
    assert res["ok"] is True
    assert out.is_file()
    assert res["namespace"] == "ns-test"
    assert "kubectl apply" in res["apply_hint"]
    v = validate_yaml_text(out.read_text(encoding="utf-8"))
    assert v["ok"] is True


def test_validate_yaml_rejects_incomplete():
    from core.k8s_cronjob import validate_yaml_text

    bad = validate_yaml_text("apiVersion: v1\nkind: Pod\n")
    assert bad["ok"] is False
    assert bad["checks"]["has_cronjob"] is False


def test_packaged_manifest_valid():
    from core.k8s_cronjob import validate_yaml_text

    root = Path(__file__).resolve().parents[1]
    path = root / "packaging" / "k8s" / "superai-goals-cronjob.yaml"
    assert path.is_file(), "packaging/k8s/superai-goals-cronjob.yaml missing"
    v = validate_yaml_text(path.read_text(encoding="utf-8"))
    assert v["ok"] is True


def test_try_kubectl_apply_no_kubectl(tmp_path, monkeypatch):
    from core import k8s_cronjob as k8s
    import shutil

    # shutil is imported inside try_kubectl_apply — patch the module-level which
    monkeypatch.setattr(shutil, "which", lambda _x: None)
    p = tmp_path / "x.yaml"
    p.write_text("kind: CronJob\n", encoding="utf-8")
    res = k8s.try_kubectl_apply(p, dry_run=True)
    assert res["ok"] is False
    assert res["error"] == "kubectl_not_found"


def test_try_kubectl_apply_dry_run_mocked(tmp_path, monkeypatch):
    from core import k8s_cronjob as k8s
    import shutil
    import subprocess

    monkeypatch.setattr(shutil, "which", lambda _x: "/usr/bin/kubectl")
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "cronjob.batch/superai-goals-tick created (dry run)"
    mock_proc.stderr = ""
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_proc)
    p = tmp_path / "x.yaml"
    p.write_text("kind: CronJob\n", encoding="utf-8")
    res = k8s.try_kubectl_apply(p, dry_run=True)
    assert res["ok"] is True
    assert res["dry_run"] is True


# ---------------------------------------------------------------------------
# Windows Task Scheduler
# ---------------------------------------------------------------------------


def test_render_ps1_installer():
    from core.windows_task_scheduler import render_ps1_installer, TASK_NAME_DEFAULT

    ps1 = render_ps1_installer(interval_sec=45.0, execute_goals=True)
    assert "schtasks /Create" in ps1
    assert TASK_NAME_DEFAULT in ps1
    assert "daemon" in ps1
    assert "run" in ps1
    assert "--interval" in ps1
    assert "--execute-goals" in ps1


def test_install_task_not_windows(monkeypatch):
    from core import windows_task_scheduler as wts

    monkeypatch.setattr(wts, "is_windows", lambda: False)
    res = wts.install_task(write_script=False)
    assert res["ok"] is False
    assert res["error"] == "not_windows"


def test_uninstall_task_not_windows(monkeypatch):
    from core import windows_task_scheduler as wts

    monkeypatch.setattr(wts, "is_windows", lambda: False)
    res = wts.uninstall_task()
    assert res["ok"] is False


def test_install_task_mocked_schtasks(tmp_path, monkeypatch):
    from core import windows_task_scheduler as wts
    import subprocess

    monkeypatch.setattr(wts, "is_windows", lambda: True)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "SUCCESS: The scheduled task was successfully created."
    mock_proc.stderr = ""
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_proc)

    res = wts.install_task(
        name="SuperAI-Test-Task",
        interval_sec=30,
        execute_goals=False,
        write_script=True,
    )
    assert res["ok"] is True
    assert res["task_name"] == "SuperAI-Test-Task"
    assert "daemon" in res["command"]
    script = Path(res["script"])
    assert script.is_file()
    assert "schtasks" in script.read_text(encoding="utf-8")


def test_install_task_hourly_fallback(tmp_path, monkeypatch):
    from core import windows_task_scheduler as wts
    import subprocess

    monkeypatch.setattr(wts, "is_windows", lambda: True)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    calls = []

    def fake_run(args, **kwargs):
        calls.append(list(args))
        p = MagicMock()
        # first ONLOGON fails, second HOURLY succeeds
        p.returncode = 1 if len(calls) == 1 else 0
        p.stdout = ""
        p.stderr = "ACCESS DENIED" if len(calls) == 1 else ""
        return p

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = wts.install_task(name="SuperAI-Fallback", write_script=False)
    assert res["ok"] is True
    assert any("HOURLY" in a for a in calls[-1])


def test_query_and_uninstall_mocked(tmp_path, monkeypatch):
    from core import windows_task_scheduler as wts
    import subprocess

    monkeypatch.setattr(wts, "is_windows", lambda: True)

    def fake_run(args, **kwargs):
        p = MagicMock()
        p.returncode = 0
        p.stdout = "TaskName: SuperAI-Goals-Daemon\nStatus: Ready"
        p.stderr = ""
        return p

    monkeypatch.setattr(subprocess, "run", fake_run)
    q = wts.query_task(name="SuperAI-Goals-Daemon")
    assert q["ok"] is True
    assert q["installed"] is True
    u = wts.uninstall_task(name="SuperAI-Goals-Daemon")
    assert u["ok"] is True


def test_superai_cmd_shape():
    from core.windows_task_scheduler import _superai_cmd

    cmd = _superai_cmd(interval_sec=60, execute_goals=True, cli_path="superai")
    assert cmd.startswith("superai daemon run")
    assert "--interval 60" in cmd or "--interval 60.0" in cmd
    assert "--execute-goals" in cmd


# ---------------------------------------------------------------------------
# goals_daemon.tick cluster integration
# ---------------------------------------------------------------------------


@pytest.fixture()
def daemon_cluster_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    store = tmp_path / "cluster" / "membership.json"
    monkeypatch.setenv("SUPERAI_CLUSTER_STORE", str(store))
    import importlib

    import core.daemon_cluster as dc
    import core.goals_daemon as gd

    importlib.reload(dc)
    importlib.reload(gd)
    yield tmp_path, gd, dc


def test_tick_skips_follower(daemon_cluster_home, monkeypatch):
    tmp_path, gd, dc = daemon_cluster_home
    monkeypatch.setenv("SUPERAI_CLUSTER_MODE", "leader_only")
    dc.heartbeat(host_id="leader-x", ttl_sec=90)
    monkeypatch.setenv("SUPERAI_CLUSTER_HOST_ID", "follower-y")
    # reload default host not needed — should_run_tick accepts via heartbeat inside
    # Force follower by host id in should_run_tick path
    import importlib

    importlib.reload(dc)
    importlib.reload(gd)

    # seed leader first as different host
    monkeypatch.setenv("SUPERAI_CLUSTER_HOST_ID", "leader-x")
    importlib.reload(dc)
    dc.heartbeat(host_id="leader-x", ttl_sec=90)
    monkeypatch.setenv("SUPERAI_CLUSTER_HOST_ID", "follower-y")
    importlib.reload(dc)
    importlib.reload(gd)

    out = gd.tick(
        execute_goals=False,
        notify=False,
        schedule_due=False,
        cluster=True,
    )
    assert out.get("ok") is True
    assert out.get("skipped") is True
    assert out.get("cluster", {}).get("enabled") is True


def test_tick_leader_runs(daemon_cluster_home, monkeypatch):
    tmp_path, gd, dc = daemon_cluster_home
    monkeypatch.setenv("SUPERAI_CLUSTER_MODE", "leader_only")
    monkeypatch.setenv("SUPERAI_CLUSTER_HOST_ID", "only-host")
    import importlib

    importlib.reload(dc)
    importlib.reload(gd)
    from core.assistant_goals import GoalStore

    GoalStore().add("cluster leader goal")
    out = gd.tick(
        execute_goals=False,
        notify=False,
        schedule_due=False,
        cluster=True,
    )
    assert out.get("ok") is True
    assert not out.get("skipped")
    assert out.get("daemon_tick") is True
    assert out.get("cluster", {}).get("enabled") is True


def test_tick_cluster_disabled_by_default(daemon_cluster_home, monkeypatch):
    tmp_path, gd, dc = daemon_cluster_home
    monkeypatch.delenv("SUPERAI_CLUSTER_MODE", raising=False)
    monkeypatch.setenv("SUPERAI_CLUSTER_MODE", "single")
    out = gd.tick(
        execute_goals=False,
        notify=False,
        schedule_due=False,
        cluster=True,
    )
    assert out.get("ok") is True
    assert out.get("cluster", {}).get("enabled") is False


def test_schedule_run_due_job_filter(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.schedule_store import ScheduleStore

    store = ScheduleStore()
    j1 = store.add("a", "goals-tick", every_hours=0.0001)
    j2 = store.add("b", "goals-tick", every_hours=0.0001)
    for j in store.data["jobs"]:
        j["next_run"] = 0
    store.save()

    allowed = {j1["id"]}
    results = store.run_due(job_filter=lambda job: job.get("id") in allowed)
    assert len(results) == 1
    assert results[0]["job"] == j1["id"]
