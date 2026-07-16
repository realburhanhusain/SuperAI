"""W7 — VS Code extension depth: thorough tests (Node suite + packaging)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "extensions" / "vscode-superai"


def test_extension_files_exist():
    assert (EXT / "extension.js").is_file()
    assert (EXT / "lib" / "cli.js").is_file()
    assert (EXT / "package.json").is_file()
    assert (EXT / "README.md").is_file()
    assert (EXT / "test" / "run.js").is_file()
    assert (ROOT / "docs" / "VSCODE_EXTENSION.md").is_file()


def test_package_json_w7_commands():
    pkg = json.loads((EXT / "package.json").read_text(encoding="utf-8"))
    assert pkg["version"].startswith("1.")
    assert pkg["main"] == "./extension.js"
    cmds = {c["command"] for c in pkg["contributes"]["commands"]}
    required = {
        "superai.ask",
        "superai.do",
        "superai.askSelection",
        "superai.reviewSelection",
        "superai.openAgentTerminal",
        "superai.insertLastOutput",
        "superai.pluginCatalog",
        "superai.status",
        "superai.smokePreflight",
    }
    missing = required - cmds
    assert not missing, f"missing commands: {missing}"
    assert "superai.cliPath" in pkg["contributes"]["configuration"]["properties"]
    assert len(pkg["contributes"]["keybindings"]) >= 1
    assert len(pkg["contributes"]["menus"]["editor/context"]) >= 2


def test_docs_thorough():
    doc = (ROOT / "docs" / "VSCODE_EXTENSION.md").read_text(encoding="utf-8")
    for needle in (
        "W7",
        "Definition of done",
        "Architecture",
        "Testing",
        "superai.ask",
        "Open Agent Terminal",
        "lib/cli.js",
    ):
        assert needle in doc, f"docs missing: {needle}"
    assert len(doc) > 1500
    readme = (EXT / "README.md").read_text(encoding="utf-8")
    assert "W7" in readme or "full depth" in readme.lower()
    assert "npm test" in readme


def test_node_unit_suite():
    run_js = EXT / "test" / "run.js"
    proc = subprocess.run(
        [sys.executable.replace("python", "node") if False else "node", str(run_js)],
        cwd=str(EXT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    # Prefer explicit node
    if proc.returncode != 0 and "not found" in (proc.stderr or "").lower():
        proc = subprocess.run(
            ["node", str(run_js)],
            cwd=str(EXT),
            capture_output=True,
            text=True,
            timeout=60,
        )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    assert "passed" in (proc.stdout or "")
    assert "failed" in (proc.stdout or "")
    # zero failed
    assert "0 failed" in (proc.stdout or "") or ", 0 failed" in (proc.stdout or "")


def test_cli_js_exports_mentioned_in_extension():
    ext_js = (EXT / "extension.js").read_text(encoding="utf-8")
    assert "buildArgs" in ext_js
    assert "runSuperaiCli" in ext_js
    assert "openAgentTerminal" in ext_js
    assert "askSelection" in ext_js
    cli_js = (EXT / "lib" / "cli.js").read_text(encoding="utf-8")
    assert "function buildArgs" in cli_js
    assert "function runSuperaiCli" in cli_js
    assert "validatePackageCommands" in cli_js
