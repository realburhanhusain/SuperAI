"""
Host tool checklist + optional auto-install (not bundled in SuperAI package).

SuperAI discovers system CLIs on PATH and can install missing ones via the
host package manager (winget / choco / scoop / brew / apt) or pip/npm when
available — without shipping third-party binaries inside the SuperAI wheel.

Safety:
  - check is always safe
  - install defaults to dry-run
  - only tools with install recipes and auto_installable=True are attempted
  - manual-only tools get install URLs / notes
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class HostTool:
    id: str
    name: str
    category: str  # shell | vcs | cloud | ai_cli | container | utility
    detects: List[str]
    description: str = ""
    # Package-manager / alternate install recipes (platform-specific)
    winget: Optional[str] = None
    choco: Optional[str] = None
    scoop: Optional[str] = None
    brew: Optional[str] = None
    apt: Optional[str] = None
    pip: Optional[str] = None
    npm: Optional[str] = None
    url: Optional[str] = None
    notes: str = ""
    auto_installable: bool = True
    profiles: List[str] = field(default_factory=lambda: ["full"])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Curated host tools SuperAI can use or orchestrate
HOST_TOOL_CATALOG: List[HostTool] = [
    # ── Shell / OS ────────────────────────────────────────────────────
    HostTool(
        id="git",
        name="Git",
        category="vcs",
        detects=["git", "git.exe"],
        description="Version control (required for most agentic workflows)",
        winget="Git.Git",
        choco="git",
        scoop="git",
        brew="git",
        apt="git",
        profiles=["core", "agentic", "full"],
    ),
    HostTool(
        id="postgres",
        name="PostgreSQL",
        category="utility",
        detects=["psql", "psql.exe"],
        description="Postgres server client (Memory Palace pgvector). Prefer: superai install --with-postgres",
        winget="PostgreSQL.PostgreSQL.17",
        choco="postgresql",
        brew="postgresql@17",
        apt="postgresql",
        url="https://www.postgresql.org/download/",
        notes=(
            "Server install may need admin. After install: "
            "superai install-postgres --setup-only --live  "
            "(creates DB + vector extension + writes memory_dsn). "
            "pgvector extension must be available for your major version."
        ),
        profiles=["full"],
        auto_installable=True,
    ),
    HostTool(
        id="gh",
        name="GitHub CLI",
        category="vcs",
        detects=["gh", "gh.exe"],
        description="GitHub PRs, issues, auth from the terminal",
        winget="GitHub.cli",
        choco="gh",
        scoop="gh",
        brew="gh",
        apt="gh",
        url="https://cli.github.com/",
        profiles=["core", "agentic", "full"],
    ),
    HostTool(
        id="powershell",
        name="PowerShell",
        category="shell",
        detects=["pwsh", "pwsh.exe", "powershell", "powershell.exe"],
        description="Windows shell (usually preinstalled)",
        winget="Microsoft.PowerShell",
        choco="powershell-core",
        scoop="pwsh",
        brew="powershell",
        notes="Windows ships Windows PowerShell; prefer PowerShell 7 (pwsh).",
        profiles=["core", "full"],
        auto_installable=True,
    ),
    HostTool(
        id="bash",
        name="Bash",
        category="shell",
        detects=["bash", "bash.exe"],
        description="Unix shell (Git Bash / WSL / macOS / Linux)",
        winget="Git.Git",  # Git for Windows includes bash
        choco="git",
        brew="bash",
        apt="bash",
        notes="On Windows: install Git for Windows or WSL. Often already present on macOS/Linux.",
        profiles=["full"],
    ),
    # ── Cloud ─────────────────────────────────────────────────────────
    HostTool(
        id="aws",
        name="AWS CLI",
        category="cloud",
        detects=["aws", "aws.exe"],
        description="Amazon Web Services CLI",
        winget="Amazon.AWSCLI",
        choco="awscli",
        scoop="aws",
        brew="awscli",
        pip="awscli",
        url="https://aws.amazon.com/cli/",
        profiles=["cloud", "full"],
    ),
    HostTool(
        id="az",
        name="Azure CLI",
        category="cloud",
        detects=["az", "az.cmd", "az.exe"],
        description="Microsoft Azure CLI",
        winget="Microsoft.AzureCLI",
        choco="azure-cli",
        brew="azure-cli",
        url="https://learn.microsoft.com/cli/azure/install-azure-cli",
        profiles=["cloud", "full"],
    ),
    HostTool(
        id="gcloud",
        name="Google Cloud SDK",
        category="cloud",
        detects=["gcloud", "gcloud.cmd", "gcloud.exe"],
        description="Google Cloud CLI",
        winget="Google.CloudSDK",
        choco="gcloudsdk",
        brew="--cask google-cloud-sdk",
        url="https://cloud.google.com/sdk/docs/install",
        profiles=["cloud", "full"],
    ),
    HostTool(
        id="kubectl",
        name="kubectl",
        category="cloud",
        detects=["kubectl", "kubectl.exe"],
        description="Kubernetes CLI",
        winget="Kubernetes.kubectl",
        choco="kubernetes-cli",
        scoop="kubectl",
        brew="kubectl",
        profiles=["cloud", "full"],
    ),
    HostTool(
        id="terraform",
        name="Terraform",
        category="cloud",
        detects=["terraform", "terraform.exe"],
        description="Infrastructure as code",
        winget="Hashicorp.Terraform",
        choco="terraform",
        scoop="terraform",
        brew="terraform",
        profiles=["cloud", "full"],
    ),
    HostTool(
        id="docker",
        name="Docker",
        category="container",
        detects=["docker", "docker.exe"],
        description="Containers (sandbox / tool isolation)",
        winget="Docker.DockerDesktop",
        choco="docker-desktop",
        brew="--cask docker",
        url="https://docs.docker.com/get-docker/",
        notes="May require reboot / WSL2 on Windows.",
        profiles=["cloud", "full"],
    ),
    # ── AI agent CLIs ─────────────────────────────────────────────────
    HostTool(
        id="claude",
        name="Claude Code",
        category="ai_cli",
        detects=["claude", "claude.exe"],
        description="Anthropic Claude Code CLI",
        npm="@anthropic-ai/claude-code",
        url="https://docs.anthropic.com/en/docs/claude-code",
        notes="Official install via npm or Anthropic docs; requires Anthropic account.",
        profiles=["agentic", "full"],
        auto_installable=True,
    ),
    HostTool(
        id="aider",
        name="Aider",
        category="ai_cli",
        detects=["aider", "aider.exe"],
        description="AI pair-programming in the terminal",
        pip="aider-chat",
        url="https://aider.chat/",
        profiles=["agentic", "full"],
    ),
    HostTool(
        id="gemini",
        name="Gemini CLI",
        category="ai_cli",
        detects=["gemini", "gemini.exe"],
        description="Google Gemini CLI (if published on PATH)",
        npm="@google/gemini-cli",
        url="https://ai.google.dev/",
        notes="Install path varies by Google release; may need manual setup.",
        profiles=["agentic", "full"],
        auto_installable=True,
    ),
    HostTool(
        id="codex",
        name="OpenAI Codex CLI",
        category="ai_cli",
        detects=["codex", "codex.exe"],
        description="OpenAI Codex / coding CLI",
        npm="@openai/codex",
        url="https://github.com/openai/codex",
        notes="Install per OpenAI docs; package name may change.",
        profiles=["agentic", "full"],
        auto_installable=True,
    ),
    HostTool(
        id="grok",
        name="Grok CLI",
        category="ai_cli",
        detects=["grok", "grok.exe"],
        description="xAI Grok CLI (this repo's TUI may also be `grok`)",
        npm="@xai/grok-cli",
        pip="grok-cli",
        url="https://x.ai/",
        notes="Multiple products may provide a `grok` binary; install the one you use.",
        profiles=["agentic", "full"],
        auto_installable=False,  # ambiguous; avoid wrong package
    ),
    HostTool(
        id="cursor",
        name="Cursor CLI",
        category="ai_cli",
        detects=["cursor", "cursor.exe"],
        description="Cursor editor agent CLI",
        url="https://cursor.com/",
        notes="Usually installed with Cursor desktop app.",
        profiles=["agentic", "full"],
        auto_installable=False,
    ),
    HostTool(
        id="antigravity",
        name="Antigravity",
        category="ai_cli",
        detects=["antigravity", "antigravity.exe"],
        description="Antigravity agent CLI (if installed)",
        url="",
        notes="Install via vendor docs if available; not auto-installable.",
        profiles=["agentic", "full"],
        auto_installable=False,
    ),
    HostTool(
        id="continue",
        name="Continue CLI",
        category="ai_cli",
        detects=["continue", "cn", "continue.exe"],
        description="Continue.dev CLI",
        url="https://continue.dev/",
        notes="Often IDE extension; CLI optional.",
        profiles=["full"],
        auto_installable=False,
    ),
    # ── Utility ───────────────────────────────────────────────────────
    HostTool(
        id="ollama",
        name="Ollama",
        category="utility",
        detects=["ollama", "ollama.exe"],
        description="Local LLM runtime",
        winget="Ollama.Ollama",
        choco="ollama",
        brew="ollama",
        url="https://ollama.com/",
        profiles=["core", "agentic", "full"],
    ),
    HostTool(
        id="rclone",
        name="rclone",
        category="utility",
        detects=["rclone", "rclone.exe"],
        description="Cloud storage sync for SuperAI backups",
        winget="Rclone.Rclone",
        choco="rclone",
        scoop="rclone",
        brew="rclone",
        apt="rclone",
        url="https://rclone.org/install/",
        profiles=["core", "full"],
    ),
    HostTool(
        id="node",
        name="Node.js",
        category="utility",
        detects=["node", "node.exe"],
        description="Needed for npm-based AI CLIs (claude, codex, …)",
        winget="OpenJS.NodeJS.LTS",
        choco="nodejs-lts",
        scoop="nodejs-lts",
        brew="node",
        apt="nodejs",
        profiles=["agentic", "full"],
    ),
]


PROFILES = {
    "core": "Essentials: git, gh, shells, ollama, rclone",
    "agentic": "AI agent CLIs + git/gh/node for multi-CLI workflows",
    "cloud": "Cloud provider CLIs (aws, az, gcloud, k8s, terraform, docker)",
    "full": "Everything in the catalog that we know about",
}


def _system() -> str:
    return platform.system().lower()  # windows | linux | darwin


def _which_any(names: Sequence[str]) -> Optional[str]:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def detect_package_managers() -> Dict[str, bool]:
    return {
        "winget": shutil.which("winget") is not None,
        "choco": shutil.which("choco") is not None,
        "scoop": shutil.which("scoop") is not None,
        "brew": shutil.which("brew") is not None,
        "apt": shutil.which("apt-get") is not None or shutil.which("apt") is not None,
        "pip": True,  # always have current python
        "npm": shutil.which("npm") is not None,
    }


def list_catalog(
    profile: Optional[str] = None,
    category: Optional[str] = None,
) -> List[HostTool]:
    tools = list(HOST_TOOL_CATALOG)
    if profile and profile != "full":
        tools = [t for t in tools if profile in t.profiles]
    if category:
        tools = [t for t in tools if t.category == category]
    return tools


def check_tool(tool: HostTool) -> Dict[str, Any]:
    path = _which_any(tool.detects)
    return {
        "id": tool.id,
        "name": tool.name,
        "category": tool.category,
        "available": path is not None,
        "path": path,
        "description": tool.description,
        "auto_installable": tool.auto_installable,
        "profiles": list(tool.profiles),
        "install_hint": install_hint(tool),
        "url": tool.url,
        "notes": tool.notes,
    }


def install_hint(tool: HostTool) -> str:
    sysname = _system()
    managers = detect_package_managers()
    parts: List[str] = []
    if sysname == "windows":
        if tool.winget and managers.get("winget"):
            parts.append(f"winget install -e --id {tool.winget}")
        elif tool.winget:
            parts.append(f"winget install -e --id {tool.winget}")
        if tool.choco:
            parts.append(f"choco install {tool.choco} -y")
        if tool.scoop:
            parts.append(f"scoop install {tool.scoop}")
    elif sysname == "darwin":
        if tool.brew:
            pkg = tool.brew
            if pkg.startswith("--cask"):
                parts.append(f"brew install {pkg}")
            else:
                parts.append(f"brew install {pkg}")
    else:
        if tool.apt:
            parts.append(f"sudo apt-get install -y {tool.apt}")
        if tool.brew:
            parts.append(f"brew install {tool.brew}")
    if tool.pip:
        parts.append(f'{sys.executable} -m pip install "{tool.pip}"')
    if tool.npm:
        parts.append(f"npm install -g {tool.npm}")
    if tool.url:
        parts.append(f"docs: {tool.url}")
    if tool.notes:
        parts.append(f"note: {tool.notes}")
    if not parts:
        return "No automated recipe — install manually / see vendor docs."
    return " | ".join(parts)


def checklist(
    profile: str = "full",
    category: Optional[str] = None,
) -> Dict[str, Any]:
    tools = list_catalog(profile=profile, category=category)
    rows = [check_tool(t) for t in tools]
    present = [r for r in rows if r["available"]]
    missing = [r for r in rows if not r["available"]]
    missing_auto = [r for r in missing if r["auto_installable"]]
    return {
        "platform": platform.platform(),
        "system": _system(),
        "python": sys.version.split()[0],
        "profile": profile,
        "package_managers": detect_package_managers(),
        "totals": {
            "checked": len(rows),
            "present": len(present),
            "missing": len(missing),
            "missing_auto_installable": len(missing_auto),
        },
        "present": present,
        "missing": missing,
        "tools": rows,
        "profiles": PROFILES,
        "bundled_in_superai": False,
        "note": (
            "Host tools are NOT bundled in the SuperAI package. "
            "They are detected on PATH and can be installed via host package managers."
        ),
    }


def _build_install_argv(tool: HostTool) -> Optional[List[str]]:
    """Pick best install command for this OS/managers. Returns argv or None."""
    sysname = _system()
    managers = detect_package_managers()

    # Prefer OS package managers, then pip, then npm
    if sysname == "windows":
        if tool.winget and managers.get("winget"):
            return [
                "winget",
                "install",
                "-e",
                "--id",
                tool.winget,
                "--accept-package-agreements",
                "--accept-source-agreements",
            ]
        if tool.choco and managers.get("choco"):
            return ["choco", "install", tool.choco, "-y"]
        if tool.scoop and managers.get("scoop"):
            return ["scoop", "install", tool.scoop]
    elif sysname == "darwin":
        if tool.brew and managers.get("brew"):
            brew_args = tool.brew.split()
            return ["brew", "install", *brew_args]
    else:  # linux
        if tool.apt and managers.get("apt"):
            apt = "apt-get" if shutil.which("apt-get") else "apt"
            return ["sudo", apt, "install", "-y", tool.apt]
        if tool.brew and managers.get("brew"):
            brew_args = tool.brew.split()
            return ["brew", "install", *brew_args]

    if tool.pip:
        return [sys.executable, "-m", "pip", "install", tool.pip]
    if tool.npm and managers.get("npm"):
        return ["npm", "install", "-g", tool.npm]
    return None


def install_tools(
    tool_ids: Optional[List[str]] = None,
    *,
    profile: str = "core",
    dry_run: bool = True,
    only_missing: bool = True,
    timeout_sec: float = 600.0,
) -> Dict[str, Any]:
    """
    Install host tools via package managers (NOT bundled).

    dry_run=True (default): report commands only.
    """
    if tool_ids:
        by_id = {t.id: t for t in HOST_TOOL_CATALOG}
        wanted = [by_id[tid] for tid in tool_ids if tid in by_id]
        unknown = [tid for tid in tool_ids if tid not in by_id]
        if unknown:
            # recorded in results loop via empty wanted entries handled below
            pass
    else:
        wanted = list_catalog(profile=profile)

    results: List[Dict[str, Any]] = []
    for tool in wanted:
        status = check_tool(tool)
        if only_missing and status["available"]:
            results.append(
                {
                    "id": tool.id,
                    "status": "already_present",
                    "path": status["path"],
                }
            )
            continue
        if not tool.auto_installable:
            results.append(
                {
                    "id": tool.id,
                    "status": "manual_only",
                    "hint": install_hint(tool),
                    "url": tool.url,
                    "notes": tool.notes,
                }
            )
            continue

        argv = _build_install_argv(tool)
        if not argv:
            results.append(
                {
                    "id": tool.id,
                    "status": "no_recipe",
                    "hint": install_hint(tool),
                }
            )
            continue

        entry: Dict[str, Any] = {
            "id": tool.id,
            "command": argv,
            "command_str": " ".join(argv),
        }
        if dry_run:
            entry["status"] = "dry_run"
            results.append(entry)
            continue

        # Live install
        t0 = time.time()
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                shell=False,
            )
            entry["exit_code"] = proc.returncode
            entry["stdout_tail"] = (proc.stdout or "")[-1500:]
            entry["stderr_tail"] = (proc.stderr or "")[-1000:]
            entry["duration_sec"] = round(time.time() - t0, 2)
            # Re-check PATH (may need new shell for PATH refresh)
            after = check_tool(tool)
            entry["available_after"] = after["available"]
            entry["path_after"] = after["path"]
            entry["status"] = (
                "installed"
                if proc.returncode == 0
                else "failed"
            )
            if proc.returncode == 0 and not after["available"]:
                entry["status"] = "installed_path_pending"
                entry["notes"] = (
                    "Installer exited 0 but binary not on PATH yet — "
                    "open a new terminal or refresh PATH."
                )
        except subprocess.TimeoutExpired:
            entry["status"] = "timeout"
            entry["error"] = f"timeout after {timeout_sec}s"
        except Exception as e:  # noqa: BLE001
            entry["status"] = "error"
            entry["error"] = str(e)
        results.append(entry)

    try:
        from .audit_log import AuditLog

        AuditLog().record(
            "host_tools_install",
            {
                "profile": profile,
                "dry_run": dry_run,
                "count": len(results),
                "statuses": {
                    r.get("status"): sum(
                        1 for x in results if x.get("status") == r.get("status")
                    )
                    for r in results
                },
            },
        )
    except Exception:
        pass

    summary = {
        "ok": all(
            r.get("status")
            in {
                "already_present",
                "dry_run",
                "installed",
                "installed_path_pending",
                "manual_only",
            }
            for r in results
        )
        if results
        else True,
        "profile": profile,
        "dry_run": dry_run,
        "platform": _system(),
        "package_managers": detect_package_managers(),
        "results": results,
        "totals": {
            "attempted": len(results),
            "already_present": sum(
                1 for r in results if r.get("status") == "already_present"
            ),
            "dry_run": sum(1 for r in results if r.get("status") == "dry_run"),
            "installed": sum(1 for r in results if r.get("status") == "installed"),
            "failed": sum(
                1
                for r in results
                if r.get("status") in {"failed", "error", "timeout"}
            ),
            "manual_only": sum(
                1 for r in results if r.get("status") == "manual_only"
            ),
        },
        "next": [
            "Open a new terminal if PATH was updated",
            "superai host-tools check",
            "superai doctor",
            "superai discover",
        ],
    }
    return summary


def save_checklist_report(report: Dict[str, Any], path: Optional[Path] = None) -> Path:
    out = path or (Path.home() / ".superai" / "host_tools_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return out


def maybe_auto_install_on_setup() -> Optional[Dict[str, Any]]:
    """
    Called from init/onboard when SUPERAI_AUTO_HOST_TOOLS is set.

    SUPERAI_AUTO_HOST_TOOLS=1|true  → dry-run install of core profile
    SUPERAI_AUTO_HOST_TOOLS=install → live install core profile
    SUPERAI_AUTO_HOST_TOOLS=agentic → live install agentic profile
    """
    raw = (os.getenv("SUPERAI_AUTO_HOST_TOOLS") or "").strip().lower()
    if not raw or raw in {"0", "false", "no", "off"}:
        return None
    dry = True
    profile = "core"
    if raw in {"1", "true", "yes", "check", "dry", "dry-run"}:
        dry = True
        profile = "core"
    elif raw in {"install", "live"}:
        dry = False
        profile = "core"
    elif raw in PROFILES:
        dry = False
        profile = raw
    elif raw.startswith("install:"):
        dry = False
        profile = raw.split(":", 1)[1] or "core"
    else:
        # treat as profile name dry-run
        profile = raw if raw in PROFILES else "core"
        dry = True

    return install_tools(profile=profile, dry_run=dry, only_missing=True)
