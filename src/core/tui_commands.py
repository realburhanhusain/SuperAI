"""
Agent TUI slash command catalog (Not-important W5).
"""

from __future__ import annotations

from typing import Any, Dict, List


SLASH_COMMANDS: List[Dict[str, str]] = [
    {"cmd": "/help", "alias": "?", "desc": "Show help / command list"},
    {"cmd": "/commands", "alias": "cmds", "desc": "Command palette table"},
    {"cmd": "/trace", "alias": "", "desc": "Show tool/step events"},
    {"cmd": "/compact", "alias": "", "desc": "Compact context [smart]"},
    {"cmd": "/panel", "alias": "status", "desc": "Session summary panel"},
    {"cmd": "/stream", "alias": "", "desc": "Token streaming on|off"},
    {"cmd": "/cost", "alias": "tokens", "desc": "Session token/cost totals"},
    {"cmd": "/export", "alias": "", "desc": "Export session to markdown"},
    {"cmd": "/sessions", "alias": "ls", "desc": "List recent sessions"},
    {"cmd": "/resume", "alias": "", "desc": "Resume session id"},
    {"cmd": "/undo", "alias": "", "desc": "Remove last turn"},
    {"cmd": "/paste", "alias": "", "desc": "Multi-line paste until /end"},
    {"cmd": "/diff", "alias": "", "desc": "Git diff + confirm apply"},
    {"cmd": "/listen", "alias": "", "desc": "Voice STT (mic or voice_in.txt)"},
    {"cmd": "/speak", "alias": "", "desc": "Voice TTS (pyttsx3/SAPI/mock)"},
    {"cmd": "/voice", "alias": "", "desc": "Voice status|on|off|auto|queue|backends"},
    {"cmd": "/tool", "alias": "", "desc": "read/grep/write/diff_apply"},
    {"cmd": "/permission", "alias": "perm", "desc": "plan|ask|auto|yolo"},
    {"cmd": "/profile", "alias": "", "desc": "Apply run profile"},
    {"cmd": "/exit", "alias": "quit|q", "desc": "Leave TUI"},
]


def command_palette() -> List[Dict[str, str]]:
    return list(SLASH_COMMANDS)


def resolve_alias(cmd: str) -> str:
    c = (cmd or "").strip().lstrip("/").lower()
    if not c:
        return c
    for row in SLASH_COMMANDS:
        name = row["cmd"].lstrip("/").lower()
        if c == name:
            return name
        aliases = [a.strip() for a in (row.get("alias") or "").split("|") if a.strip()]
        if c in aliases:
            return name
    return c


def help_markdown() -> str:
    lines = ["### SuperAI Agent TUI commands", ""]
    for row in SLASH_COMMANDS:
        alias = f" ({row['alias']})" if row.get("alias") else ""
        lines.append(f"- `{row['cmd']}`{alias} — {row['desc']}")
    lines.append("")
    lines.append("Plain text runs the NL agent (`ask`).")
    return "\n".join(lines)
