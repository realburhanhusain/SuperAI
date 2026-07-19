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
    # N209 split-pane
    {"cmd": "/layout", "alias": "", "desc": "N209: set/show split-pane layout preset"},
    {"cmd": "/split", "alias": "", "desc": "N209: shortcut for /layout h|v|triple|quad|…"},
    {"cmd": "/focus", "alias": "", "desc": "N209: focus a pane (highlight)"},
    {"cmd": "/cycle", "alias": "tab|next-pane", "desc": "N209: cycle focus to next pane"},
    {"cmd": "/hide", "alias": "", "desc": "N209: hide pane and reflow"},
    {"cmd": "/show", "alias": "", "desc": "N209: show hidden pane"},
    {"cmd": "/ratio", "alias": "", "desc": "N209: pane ratio e.g. 3:1"},
    {"cmd": "/panes", "alias": "", "desc": "N209: list visible/hidden panes"},
    {"cmd": "/layouts", "alias": "", "desc": "N209: list layout presets"},
    {"cmd": "/split-help", "alias": "splithelp", "desc": "N209: split-pane help"},
    # N208–N215 advanced TUI
    {"cmd": "/mux", "alias": "window|w", "desc": "N208: multiplexed sessions (tmux-like)"},
    {"cmd": "/pmux", "alias": "process-mux|pane", "desc": "N208: OS process panes (PTY/pipe)"},
    {"cmd": "/vim", "alias": "vi", "desc": "N210: vim keys on|off|status|help"},
    {"cmd": "/mouse", "alias": "", "desc": "N211: mouse on|off|status|hit|help"},
    {"cmd": "/a11y", "alias": "sr", "desc": "N215: screen-reader mode on|off|verbosity"},
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
