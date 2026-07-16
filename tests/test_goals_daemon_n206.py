"""N206 — Goals/schedules daemon: thorough offline tests."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture()
def daemon_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    # reset module paths by re-import after home patch
    import importlib

    import core.goals_daemon as gd

    importlib.reload(gd)
    yield tmp_path, gd


def test_status_not_running(daemon_home):
    tmp_path, gd = daemon_home
    st = gd.status()
    assert st.get("ok") is True
    assert st.get("running") is False
    assert st.get("pid") is None
    assert "daemon status" in str(st.get("commands"))


def test_tick_updates_state(daemon_home):
    tmp_path, gd = daemon_home
    from core.assistant_goals import GoalStore

    GoalStore().add("ship n206", detail="daemon tick test")
    out = gd.tick(execute_goals=False, notify=False, schedule_due=True)
    assert out.get("ok") is True
    assert out.get("daemon_tick") is True
    assert "due_count" in out
    state = gd.load_state()
    assert state.get("ticks_total", 0) >= 1
    assert state.get("last_tick")
    assert gd.log_path().is_file()


def test_tick_does_not_execute_by_default(daemon_home):
    tmp_path, gd = daemon_home
    from core.assistant_goals import GoalStore

    GoalStore().add("open goal now")
    out = gd.tick(execute_goals=False, notify=False)
    exec_part = out.get("execute") or {}
    assert exec_part.get("executed", 0) == 0


def test_run_loop_max_ticks(daemon_home):
    tmp_path, gd = daemon_home
    result = gd.run_loop(
        interval_sec=0.2,
        execute_goals=False,
        notify=False,
        schedule_due=False,
        max_ticks=2,
        write_pid_file=True,
    )
    assert result.get("ok") is True
    assert result.get("ticks") == 2
    assert result.get("stopped") is True
    # pid cleared after loop
    assert gd.read_pid() is None or not gd._pid_alive(gd.read_pid() or 0)


def test_stop_stale_pid(daemon_home):
    tmp_path, gd = daemon_home
    gd.write_pid(99999999)  # almost certainly dead
    out = gd.stop()
    assert out.get("ok") is True
    assert out.get("stopped") is True
    assert gd.read_pid() is None


def test_start_already_running(daemon_home, monkeypatch):
    tmp_path, gd = daemon_home
    # fake alive pid
    gd.write_pid(1)

    def always_alive(pid):
        return True

    monkeypatch.setattr(gd, "_pid_alive", always_alive)
    out = gd.start_background(interval_sec=60)
    assert out.get("ok") is True
    assert out.get("already_running") is True


def test_schedule_store_run_due_with_goals_tick(daemon_home):
    tmp_path, gd = daemon_home
    from core.schedule_store import ScheduleStore

    store = ScheduleStore()
    job = store.add("gt", "goals-tick", every_hours=0.0001)
    # force due
    for j in store.data["jobs"]:
        if j["id"] == job["id"]:
            j["next_run"] = 0
    store.save()
    results = store.run_due()
    assert results
    assert results[0].get("ok") is not False


def test_daemon_config_persist(daemon_home):
    tmp_path, gd = daemon_home
    gd.save_state({"interval_sec": 42, "execute_goals": True})
    st = gd.load_state()
    assert st["interval_sec"] == 42
    assert st["execute_goals"] is True


def test_goal_store_daemon_tick_still_works(daemon_home):
    tmp_path, gd = daemon_home
    from core.assistant_goals import GoalStore

    store = GoalStore()
    store.add("legacy tick")
    out = store.daemon_tick(execute=False, notify=False, schedule_due=False)
    assert out.get("ok") is True
    assert out.get("due_count", 0) >= 1
