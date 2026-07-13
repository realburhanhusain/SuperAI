"""
SuperAI Dynamic Dashboard — terminal (Rich) + shared snapshot with web.

Both surfaces use `superai.core.observability.build_dashboard_snapshot`.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


class SuperAIDashboard:
    def __init__(self):
        self.console = Console()
        self.delegations: List[Dict[str, Any]] = []
        self.cli_strengths: Dict[str, Dict[str, Any]] = {}
        self.recent_logs: List[Dict[str, Any]] = []
        self.memory_queries: List[Dict[str, Any]] = []
        self.feedback_prompt: Optional[Dict[str, Any]] = None
        self._snapshot: Dict[str, Any] = {}

    def refresh_from_system(self) -> Dict[str, Any]:
        """Pull shared observability snapshot into local panels."""
        from superai.core.observability import (
            build_dashboard_snapshot,
            recent_feedback,
        )

        snap = build_dashboard_snapshot()
        self._snapshot = snap

        # Map history → delegations panel
        self.delegations = []
        for h in snap.get("history") or []:
            self.delegations.append(
                {
                    "id": h.get("task_id") or "",
                    "delegated_to": h.get("model") or "—",
                    "status": h.get("status") or "",
                    "duration_seconds": float(h.get("duration") or 0),
                    "task": h.get("task") or "",
                }
            )

        # CLI strengths from discovery
        self.cli_strengths = {}
        for name in snap.get("clis") or []:
            self.cli_strengths[name] = {
                "success_rate": 0.85,
                "notes": "discovered on PATH",
                "last_updated": snap.get("ts"),
            }

        # Logs
        self.recent_logs = []
        for line in snap.get("recent_logs") or []:
            self.recent_logs.append(
                {
                    "timestamp": "",
                    "event_type": "log",
                    "details": line[-120:] if isinstance(line, str) else str(line),
                }
            )
        for h in (snap.get("history") or [])[:5]:
            self.recent_logs.insert(
                0,
                {
                    "timestamp": (h.get("task_id") or "")[:15],
                    "event_type": h.get("status") or "task",
                    "details": (h.get("task") or "")[:80],
                },
            )

        # Memory panel from stats
        self.memory_queries = [
            {
                "query": "memory stats",
                "results": [snap.get("memory") or {}],
                "timestamp": snap.get("ts"),
            }
        ]

        # Cross-surface feedback
        fb = recent_feedback(3)
        if fb:
            self.feedback_prompt = {
                "message": f"[{fb[0].get('surface')}] {fb[0].get('message')}"
            }
        else:
            self.feedback_prompt = None

        return snap

    def add_delegation(self, delegation: Dict[str, Any]) -> None:
        self.delegations = [
            d for d in self.delegations if d.get("id") != delegation.get("id")
        ]
        self.delegations.append(delegation)

    def update_cli_strength(
        self, cli_name: str, success_rate: float, notes: str = ""
    ) -> None:
        self.cli_strengths[cli_name] = {
            "success_rate": success_rate,
            "last_updated": datetime.now().isoformat(),
            "notes": notes,
        }

    def add_log(self, log_entry: Dict[str, Any]) -> None:
        self.recent_logs.insert(0, log_entry)
        if len(self.recent_logs) > 12:
            self.recent_logs.pop()

    def add_memory_query_result(self, query: str, results: List[Dict]) -> None:
        self.memory_queries.insert(
            0,
            {
                "query": query,
                "results": results,
                "timestamp": datetime.now().isoformat(),
            },
        )
        if len(self.memory_queries) > 5:
            self.memory_queries.pop()

    def set_feedback_prompt(self, prompt: Dict[str, Any]) -> None:
        self.feedback_prompt = prompt

    def clear_feedback_prompt(self) -> None:
        self.feedback_prompt = None

    def generate_layout(self) -> Layout:
        layout = Layout()

        if self.feedback_prompt:
            layout.split_column(
                Layout(name="feedback", size=3),
                Layout(name="main"),
            )
            layout["feedback"].update(
                Panel(
                    Text(
                        self.feedback_prompt.get(
                            "message", "Supervisor requests feedback."
                        ),
                        style="bold yellow on black",
                    ),
                    title="Supervisor Feedback",
                    border_style="yellow",
                )
            )
            main_layout = layout["main"]
        else:
            main_layout = layout

        main_layout.split_column(
            Layout(name="top", ratio=2),
            Layout(name="bottom", ratio=1),
        )
        main_layout["top"].split_row(
            Layout(name="delegations", ratio=2),
            Layout(name="strengths", ratio=1),
        )
        main_layout["bottom"].split_row(
            Layout(name="logs", ratio=1),
            Layout(name="memory", ratio=1),
        )

        main_layout["top"]["delegations"].update(self._delegations_panel())
        main_layout["top"]["strengths"].update(self._cli_strengths_panel())
        main_layout["bottom"]["logs"].update(self._logs_panel())
        main_layout["bottom"]["memory"].update(self._memory_panel())
        return layout

    def _delegations_panel(self) -> Panel:
        table = Table(title="Recent tasks", expand=True)
        table.add_column("ID", style="cyan", max_width=18)
        table.add_column("Model", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Sec", justify="right")
        table.add_column("Task", max_width=36)

        for d in self.delegations[-8:]:
            table.add_row(
                str(d.get("id", ""))[:16],
                str(d.get("delegated_to", ""))[:16],
                str(d.get("status", "")),
                f"{float(d.get('duration_seconds', 0)):.1f}",
                str(d.get("task", ""))[:36],
            )
        ver = (self._snapshot or {}).get("version") or ""
        return Panel(
            table,
            title=f"SuperAI Dashboard {ver}",
            border_style="blue",
        )

    def _cli_strengths_panel(self) -> Panel:
        table = Table(title="CLIs & plugins", expand=True)
        table.add_column("Name", style="yellow")
        table.add_column("Info")

        snap = self._snapshot or {}
        table.add_row("bandit arms", str(snap.get("bandit_arms", 0)))
        table.add_row("plugins on", str(snap.get("plugins_enabled", 0)))
        for cli, data in list(self.cli_strengths.items())[:6]:
            table.add_row(cli, data.get("notes", "")[:40])
        if not self.cli_strengths:
            table.add_row("(none)", "no external CLIs on PATH")
        return Panel(table, border_style="green")

    def _logs_panel(self) -> Panel:
        text = Text()
        for log in self.recent_logs[:8]:
            text.append(f"[{log.get('timestamp', '')}] ", style="dim")
            text.append(f"{log.get('event_type', '')}: ", style="bold")
            text.append(f"{str(log.get('details', ''))[:70]}\n")
        if not self.recent_logs:
            text.append("No recent history/logs yet.\n", style="dim")
        return Panel(text, title="Recent activity", border_style="red")

    def _memory_panel(self) -> Panel:
        text = Text()
        mem = (self._snapshot or {}).get("memory") or {}
        if mem:
            text.append(str(mem)[:400] + "\n", style="dim")
        for item in self.memory_queries[:3]:
            text.append(f"Q: {item.get('query')}\n", style="cyan")
        return Panel(text, title="Memory / status", border_style="magenta")

    def run_terminal_dashboard(self, refresh_sec: float = 3.0, once: bool = False) -> None:
        """Live terminal dashboard. Ctrl+C to exit."""
        self.refresh_from_system()
        if once:
            self.console.print(self.generate_layout())
            return
        with Live(self.generate_layout(), refresh_per_second=0.5, screen=True) as live:
            while True:
                self.refresh_from_system()
                live.update(self.generate_layout())
                time.sleep(refresh_sec)


if __name__ == "__main__":
    SuperAIDashboard().run_terminal_dashboard()
