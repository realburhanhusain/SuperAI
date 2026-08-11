"""DiffAwareGate must fail closed — a safety gate that passes on error is worse than none."""

import subprocess
from unittest import mock

from core.workflow.gates import DiffAwareGate


def _run(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=["git", "diff", "--cached", "--name-only"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_fails_closed_when_git_errors():
    """
    The regression this guards: `git diff` failing produced empty stdout,
    which read as "nothing staged" and returned True — the gate approving a
    commit it never inspected.
    """
    gate = DiffAwareGate()
    with mock.patch.object(
        subprocess, "run", return_value=_run(returncode=128, stderr="fatal: not a git repository")
    ):
        assert gate.validate({}) is False


def test_passes_when_nothing_is_staged():
    gate = DiffAwareGate()
    with mock.patch.object(subprocess, "run", return_value=_run(returncode=0, stdout="")):
        assert gate.validate({}) is True


def test_fails_closed_when_git_is_missing():
    gate = DiffAwareGate()
    with mock.patch.object(subprocess, "run", side_effect=FileNotFoundError("git")):
        assert gate.validate({}) is False


def test_fails_closed_on_timeout():
    gate = DiffAwareGate()
    with mock.patch.object(
        subprocess, "run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=30)
    ):
        assert gate.validate({}) is False


def test_rejects_a_staged_file_with_a_syntax_error(tmp_path, monkeypatch):
    bad = tmp_path / "broken.py"
    bad.write_text("def f(:\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    gate = DiffAwareGate()
    with mock.patch.object(subprocess, "run", return_value=_run(stdout="broken.py\n")):
        assert gate.validate({}) is False


def test_accepts_a_clean_staged_file(tmp_path, monkeypatch):
    good = tmp_path / "fine.py"
    good.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    gate = DiffAwareGate()
    with mock.patch.object(subprocess, "run", return_value=_run(stdout="fine.py\n")):
        assert gate.validate({}) is True
