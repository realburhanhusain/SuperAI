"""N208 process mux + N215 native a11y bridges — thorough offline tests."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai" / "tui").mkdir(parents=True)
    import importlib

    import core.tui_a11y_native as native
    import core.tui_process_mux as pmux

    importlib.reload(pmux)
    importlib.reload(native)
    yield tmp_path, pmux, native


# =============================================================================
# Process mux
# =============================================================================


def test_default_shell_command(home):
    tmp, pmux, _ = home
    cmd = pmux.default_shell_command()
    assert cmd
    assert isinstance(cmd[0], str)


def test_conpty_probe_bool(home):
    tmp, pmux, _ = home
    assert isinstance(pmux.conpty_available(), bool)


def _wait_pane_output(mux, needle: str, *, timeout: float = 15.0) -> str:
    """Poll process-mux output until needle appears or timeout.

    Windows Python cold-start for ``python -c`` commonly takes 2–5s here;
    a 1.5s wait was a major source of flaky test_spawn_and_read_python.
    """
    deadline = time.time() + timeout
    got = ""
    while time.time() < deadline:
        r = mux.read()
        # read() returns the full buffer (clear=False); don't double-concat
        got = r.get("output") or ""
        if needle in got:
            return got
        time.sleep(0.1)
    r = mux.read()
    return r.get("output") or got


def test_spawn_and_read_python(home):
    tmp, pmux, _ = home
    mux = pmux.ProcessMux(persist=True)
    # short-lived process
    out = mux.spawn(
        [sys.executable, "-c", "print('hello-pmux'); import time; time.sleep(0.3)"],
        title="py",
        use_pty=False,
        start=True,
    )
    assert out["ok"] is True
    assert out["active_id"]
    got = _wait_pane_output(mux, "hello-pmux", timeout=15.0)
    r = mux.read()
    assert r["ok"] is True
    pane = mux.active()
    st_pane = pane.status() if pane else {}
    assert "hello-pmux" in got, (
        f"missing output after wait; got={got!r} pane={st_pane} backend={out.get('backend')}"
    )
    st = mux.status()
    assert st["pane_count"] >= 1
    assert "py" in st["bar"] or "•" in st["bar"] or "○" in st["bar"]
    mux.kill_all()


def test_spawn_write_echo(home):
    tmp, pmux, _ = home
    mux = pmux.ProcessMux(persist=True)
    # Python REPL-like one-shot reader
    out = mux.spawn(
        [
            sys.executable,
            "-c",
            "import sys; print(sys.stdin.readline().strip())",
        ],
        title="echo",
        use_pty=False,
    )
    assert out["ok"] is True
    w = mux.write("ping-line\n")
    assert w.get("ok") is True
    got = _wait_pane_output(mux, "ping-line", timeout=15.0)
    assert "ping-line" in got, f"echo missing; got={got!r}"
    mux.kill_all()


def test_select_next_prev(home):
    tmp, pmux, _ = home
    mux = pmux.ProcessMux(persist=True)
    mux.spawn([sys.executable, "-c", "import time; time.sleep(2)"], title="a", use_pty=False)
    mux.spawn([sys.executable, "-c", "import time; time.sleep(2)"], title="b", use_pty=False)
    assert mux.status()["pane_count"] == 2
    first = mux.active_id
    mux.prev_pane()
    # cycling works
    mux.next_pane()
    mux.select("0")
    assert mux.active() is not None
    mux.kill_all()
    assert first  # was set


def test_kill_pane(home):
    tmp, pmux, _ = home
    mux = pmux.ProcessMux(persist=True)
    mux.spawn([sys.executable, "-c", "import time; time.sleep(5)"], title="long", use_pty=False)
    pid = mux.active_id
    out = mux.kill(pid)
    assert out["ok"] is True
    assert pid not in mux.panes


def test_pmux_slash_status_help(home):
    tmp, pmux, _ = home
    mux = pmux.ProcessMux(persist=True)
    st = pmux.handle_pmux_slash("status", mux=mux)
    assert st["ok"] is True and st["handled"] is True
    h = pmux.handle_pmux_slash("help", mux=mux)
    assert "Process mux" in (h.get("help") or "")


def test_pmux_slash_spawn_python(home):
    tmp, pmux, _ = home
    mux = pmux.ProcessMux(persist=True)
    # use spawn with python -c via rest tokens
    out = pmux.handle_pmux_slash(
        f"spawn {sys.executable} -c print(123)",
        mux=mux,
    )
    # On Windows handle joins as cmd /c — still ok if process starts
    assert out.get("handled") is True
    mux.kill_all()


def test_external_mux_tools_shape(home):
    tmp, pmux, _ = home
    tools = pmux.external_mux_tools()
    assert "tmux" in tools
    assert "available" in tools["tmux"]


def test_tmux_new_session_without_tmux(home, monkeypatch):
    tmp, pmux, _ = home
    monkeypatch.setattr(pmux.shutil, "which", lambda _n: None)
    out = pmux.tmux_new_session("x")
    assert out["ok"] is False
    assert out["error"] == "tmux_not_found"


def test_link_session(home, monkeypatch):
    tmp, pmux, _ = home
    mux = pmux.ProcessMux(persist=True)
    mux.spawn([sys.executable, "-c", "import time; time.sleep(1)"], title="L", use_pty=False)
    # mock SessionMux attach
    class FakeMux:
        def attach(self, sid, title=""):
            return {"ok": True, "session_id": sid}

    monkeypatch.setattr(
        "core.tui_mux.SessionMux",
        lambda persist=True: FakeMux(),
    )
    out = mux.link_session("sa-test123")
    assert out["ok"] is True
    assert mux.active().spec.session_id == "sa-test123"
    mux.kill_all()


def test_persist_meta(home):
    tmp, pmux, _ = home
    mux = pmux.ProcessMux(persist=True)
    mux.spawn([sys.executable, "-c", "print(1)"], title="persist", use_pty=False)
    path = pmux.process_mux_path()
    assert path.is_file()
    data = path.read_text(encoding="utf-8")
    assert "persist" in data or "panes" in data
    mux.kill_all()


# =============================================================================
# Native a11y
# =============================================================================


def test_detect_backends(home):
    tmp, _, native = home
    b = native.detect_backends()
    assert "system" in b or "platform" in b
    assert b.get("file_live_region") is True


def test_write_uia_live_region(home):
    tmp, _, native = home
    path = native.write_uia_live_region("Hello Narrator")
    assert path.is_file()
    assert "Hello Narrator" in path.read_text(encoding="utf-8")


def test_announce_native_file_prefer(home):
    tmp, _, native = home
    cfg = native.NativeA11yConfig(enabled=True, prefer="file", also_file=True, also_notify=False)
    out = native.announce_native("SR test message", cfg=cfg)
    assert out["ok"] is True
    assert out.get("live_region")
    assert Path(out["live_region"]).is_file()


def test_announce_native_disabled(home):
    tmp, _, native = home
    cfg = native.NativeA11yConfig(enabled=False, also_file=True)
    out = native.announce_native("x", cfg=cfg)
    assert out["ok"] is True
    assert out.get("backend") in {"file_only", "disabled"}


def test_speak_windows_mocked_powershell(home, monkeypatch):
    tmp, _, native = home
    if sys.platform != "win32":
        pytest.skip("windows path")
    monkeypatch.setattr(native, "_win32com_sapi_available", lambda: False)

    class P:
        returncode = 0
        stderr = ""
        stdout = ""

    monkeypatch.setattr(native.subprocess, "run", lambda *a, **k: P())
    monkeypatch.setattr(native.shutil, "which", lambda n: "powershell" if "power" in n or n == "powershell" else None)
    out = native.speak_windows_sapi("hello")
    assert out["ok"] is True
    assert "powershell" in out["backend"] or out["backend"] == "system_speech_powershell"


def test_speak_linux_spd_mocked(home, monkeypatch):
    tmp, _, native = home

    class P:
        returncode = 0

    monkeypatch.setattr(native.shutil, "which", lambda n: "/usr/bin/spd-say" if n == "spd-say" else None)
    monkeypatch.setattr(native.subprocess, "run", lambda *a, **k: P())
    out = native.speak_linux_spd("hi")
    assert out["ok"] is True
    assert out["backend"] == "spd-say"


def test_speak_macos_say_mocked(home, monkeypatch):
    tmp, _, native = home

    class P:
        returncode = 0

    monkeypatch.setattr(native.shutil, "which", lambda n: "/usr/bin/say" if n == "say" else None)
    monkeypatch.setattr(native.subprocess, "run", lambda *a, **k: P())
    out = native.speak_macos_say("hi")
    assert out["ok"] is True


def test_native_bridge_status_and_slash(home):
    tmp, _, native = home
    br = native.NativeA11yBridge()
    st = br.status()
    assert st["ok"] is True
    assert "backends" in st
    h = native.handle_native_a11y_slash("help")
    assert "Native screen-reader" in (h.get("help") or "")
    out = native.handle_native_a11y_slash("prefer file")
    assert out["ok"] is True
    say = native.handle_native_a11y_slash("say Hello bridge")
    assert say.get("handled") is True


def test_a11y_slash_native_integration(home):
    tmp, _, native = home
    import importlib

    import core.tui_a11y as a11y

    importlib.reload(a11y)
    out = a11y.handle_a11y_slash("native status")
    assert out.get("handled") is True
    assert out.get("ok") is True


def test_config_persist_native(home):
    tmp, _, native = home
    cfg = native.NativeA11yConfig(enabled=True, prefer="file", rate=2)
    native.save_native_config(cfg)
    loaded = native.load_native_config()
    assert loaded.prefer == "file"
    assert loaded.rate == 2
