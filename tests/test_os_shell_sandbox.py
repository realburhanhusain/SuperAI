"""Tests for container-sandbox routing in os_shell.run_shell.

These tests never start Docker and never run a real shell command. The
sandbox entry point and subprocess.run are both replaced, so what is under
test is the routing and the fail-closed policy, not Docker itself.
"""

from __future__ import annotations

import subprocess

import pytest

from core import container_sandbox, os_shell


class _FakeProc:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.stdout = "host-output"
        self.stderr = ""


@pytest.fixture()
def host_calls(monkeypatch, tmp_path):
    """Record host subprocess execution instead of performing it."""
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    calls: list[dict] = []

    def _fake_run(cmd, **kwargs):
        calls.append({"cmd": cmd, "kwargs": kwargs})
        return _FakeProc(0)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    return calls


def _sandbox_returns(monkeypatch, value):
    seen: list[list[str]] = []

    def _fake(argv, timeout=60.0, prefer=False):
        seen.append(list(argv))
        return value

    monkeypatch.setattr(container_sandbox, "try_sandboxed_shell", _fake)
    return seen


_DOCKER_OK = {
    "exit_code": 0,
    "stdout": "container-output",
    "stderr": "",
    "sandbox": "docker",
    "image": "python:3.12-slim",
    "workspace": "/workspace",
    "workspace_readonly": False,
}


def test_sandbox_not_enabled_runs_on_host(host_calls, monkeypatch):
    # try_sandboxed_shell returns None when the sandbox is not enabled.
    _sandbox_returns(monkeypatch, None)
    res = os_shell.run_shell("echo hi", permission_mode="yolo")
    assert res.get("executed") is True
    assert res.get("sandbox") == "none"
    assert len(host_calls) == 1


def test_sandbox_enabled_runs_in_container_not_on_host(host_calls, monkeypatch):
    _sandbox_returns(monkeypatch, dict(_DOCKER_OK))
    res = os_shell.run_shell("echo hi", permission_mode="yolo")
    assert res.get("sandbox") == "docker"
    assert res.get("stdout") == "container-output"
    assert res.get("executed") is True
    # The whole point: nothing ran on the host.
    assert host_calls == []


def test_command_reaches_container_via_sh_lc(host_calls, monkeypatch):
    seen = _sandbox_returns(monkeypatch, dict(_DOCKER_OK))
    os_shell.run_shell("ls -la | head -3", permission_mode="yolo")
    assert seen == [["sh", "-lc", "ls -la | head -3"]]


def test_sandbox_unavailable_fails_closed(host_calls, monkeypatch):
    _sandbox_returns(
        monkeypatch,
        {
            "exit_code": -1,
            "stdout": "",
            "stderr": "Sandbox requested but docker not available",
            "sandbox": "unavailable",
            "fallback": False,
            "fail_closed": True,
        },
    )
    res = os_shell.run_shell("echo hi", permission_mode="yolo")
    assert res.get("ok") is False
    assert res.get("executed") is False
    assert res.get("error_code") == "sandbox_unavailable"
    assert host_calls == []


def test_sandbox_error_fails_closed(host_calls, monkeypatch):
    _sandbox_returns(
        monkeypatch,
        {
            "exit_code": -1,
            "stdout": "",
            "stderr": "boom",
            "sandbox": "error",
            "fallback": False,
            "fail_closed": True,
        },
    )
    res = os_shell.run_shell("echo hi", permission_mode="yolo")
    assert res.get("ok") is False
    assert res.get("error_code") == "sandbox_unavailable"
    assert host_calls == []


def test_sandbox_exception_fails_closed(host_calls, monkeypatch):
    def _boom(argv, timeout=60.0, prefer=False):
        raise RuntimeError("docker exploded")

    monkeypatch.setattr(container_sandbox, "try_sandboxed_shell", _boom)
    res = os_shell.run_shell("echo hi", permission_mode="yolo")
    assert res.get("ok") is False
    assert res.get("error_code") == "sandbox_unavailable"
    assert host_calls == []


def test_explicit_opt_out_allows_host_fallback(host_calls, monkeypatch):
    # fallback=True is what container_sandbox returns when
    # SUPERAI_SANDBOX_FAIL_CLOSED=0 has been set deliberately.
    _sandbox_returns(
        monkeypatch,
        {
            "exit_code": -1,
            "stdout": "",
            "stderr": "Sandbox requested but docker not available",
            "sandbox": "unavailable",
            "fallback": True,
            "fail_closed": False,
        },
    )
    res = os_shell.run_shell("echo hi", permission_mode="yolo")
    assert res.get("executed") is True
    assert len(host_calls) == 1


def test_nonzero_container_exit_is_not_ok(host_calls, monkeypatch):
    bad = dict(_DOCKER_OK)
    bad["exit_code"] = 2
    bad["stderr"] = "failed"
    _sandbox_returns(monkeypatch, bad)
    res = os_shell.run_shell("false", permission_mode="yolo")
    assert res.get("ok") is False
    assert res.get("returncode") == 2


def test_denied_command_never_reaches_the_sandbox(host_calls, monkeypatch):
    seen = _sandbox_returns(monkeypatch, dict(_DOCKER_OK))
    res = os_shell.run_shell("rm -rf /", permission_mode="yolo")
    assert res.get("ok") is False
    assert seen == []
    assert host_calls == []


def test_dry_run_never_reaches_the_sandbox(host_calls, monkeypatch):
    seen = _sandbox_returns(monkeypatch, dict(_DOCKER_OK))
    res = os_shell.run_shell("echo hi", dry_run=True, permission_mode="yolo")
    assert res.get("executed") is False
    assert res.get("dry_run") is True
    assert seen == []
    assert host_calls == []


def test_plan_mode_never_reaches_the_sandbox(host_calls, monkeypatch):
    seen = _sandbox_returns(monkeypatch, dict(_DOCKER_OK))
    res = os_shell.run_shell("echo hi", permission_mode="plan")
    assert res.get("executed") is False
    assert seen == []
    assert host_calls == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
