"""
SuperAI Dynamic Dashboard
Supports both Terminal (Rich) and prepares for Web dashboard.
Shows live status, logs, memory palace queries, and CLI Strength panel.
"""

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from datetime import datetime
import time
from typing import List, Dict, Any

console = Console()

class SuperAIDashboard:
    def __init__(self):
        self.console = Console()
        self.delegations: List[Dict] = []
        self.cli_strengths: Dict[str, Dict] = {}
        self.recent_logs: List[Dict] = []
        self.memory_queries: List[Dict] = []
        self.feedback_prompt: Dict | None = None  # For supervisor feedback requests

    def add_delegation(self, delegation: Dict):
        """Add or update a delegation (for realtime updates)."""
        self.delegations = [d for d in self.delegations if d.get("id") != delegation.get("id")]
        self.delegations.append(delegation)

    def update_cli_strength(self, cli_name: str, success_rate: float, notes: str = ""):
        self.cli_strengths[cli_name] = {
            "success_rate": success_rate,
            "last_updated": datetime.now().isoformat(),
            "notes": notes
        }

    def add_log(self, log_entry: Dict):
        self.recent_logs.insert(0, log_entry)
        if len(self.recent_logs) > 10:
            self.recent_logs.pop()

    def add_memory_query_result(self, query: str, results: List[Dict]):
        self.memory_queries.insert(0, {"query": query, "results": results, "timestamp": datetime.now().isoformat()})
        if len(self.memory_queries) > 5:
            self.memory_queries.pop()

    def set_feedback_prompt(self, prompt: Dict):
        """Set a feedback prompt from the supervisor (shown as highlighted message)."""
        self.feedback_prompt = prompt

    def clear_feedback_prompt(self):
        """Clear feedback prompt after user responds."""
        self.feedback_prompt = None

    def generate_layout(self) -> Layout:
        layout = Layout()

        # Feedback prompt (highlighted) - shown when supervisor requests feedback
        if self.feedback_prompt:
            layout.split_column(
                Layout(name="feedback", size=3),
                Layout(name="main")
            )
            layout["feedback"].update(Panel(
                Text(self.feedback_prompt.get("message", "Supervisor requests your feedback on recent delegations."), style="bold yellow on black"),
                title="📝 Supervisor Feedback Request",
                border_style="yellow",
                style="yellow"
            ))
            main_layout = layout["main"]
        else:
            main_layout = layout

        # Main content
        main_layout.split_row(
            Layout(name="delegations", ratio=2),
            Layout(name="strengths", ratio=1)
        )

        main_layout["delegations"].update(self._delegations_panel())
        main_layout["strengths"].update(self._cli_strengths_panel())

        main_layout.split_column(
            main_layout["delegations"],
            main_layout["strengths"],
            Layout(name="bottom", ratio=1)
        )

        main_layout["bottom"].split_row(
            Layout(name="logs", ratio=1),
            Layout(name="memory", ratio=1)
        )

        main_layout["bottom"]["logs"].update(self._logs_panel())
        main_layout["bottom"]["memory"].update(self._memory_panel())

        return layout

    def _delegations_panel(self) -> Panel:
        table = Table(title="Live Delegations", expand=True)
        table.add_column("ID", style="cyan")
        table.add_column("To", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Duration", justify="right")

        for d in self.delegations[-8:]:
            table.add_row(
                str(d.get("id", ""))[:8],
                d.get("delegated_to", ""),
                d.get("status", ""),
                f"{d.get('duration_seconds', 0):.1f}s"
            )
        return Panel(table, title="Live Status & Observability", border_style="blue")

    def _cli_strengths_panel(self) -> Panel:
        table = Table(title="CLI Strengths (Auto-learned)", expand=True)
        table.add_column("CLI", style="yellow")
        table.add_column("Success Rate", justify="right")
        table.add_column("Notes")

        for cli, data in self.cli_strengths.items():
            rate = data.get("success_rate", 0)
            color = "green" if rate > 0.8 else "yellow" if rate > 0.5 else "red"
            table.add_row(
                cli,
                f"[{color}]{rate*100:.0f}%[/{color}]",
                data.get("notes", "")[:40]
            )
        return Panel(table, border_style="green")

    def _logs_panel(self) -> Panel:
        text = Text()
        for log in self.recent_logs[:6]:
            text.append(f"[{log.get('timestamp', '')}] ", style="dim")
            text.append(f"{log.get('event_type', '')}: ", style="bold")
            text.append(f"{str(log.get('details', ''))[:60]}\n")
        return Panel(text, title="Recent Logs", border_style="red")

    def _memory_panel(self) -> Panel:
        text = Text()
        for item in self.memory_queries[:4]:
            text.append(f"Q: {item['query']}\n", style="cyan")
            if item.get("results"):
                text.append(f"  → {len(item['results'])} results\n", style="dim")
        return Panel(text, title="Memory Palace Queries", border_style="magenta")

    def run_terminal_dashboard(self):
        """Run a live updating terminal dashboard (refreshes every 5 seconds)."""
        with Live(self.generate_layout(), refresh_per_second=0.2, screen=True) as live:
            while True:
                live.update(self.generate_layout())
                time.sleep(5)  # 5-second refresh as requested


# Example usage (for testing)
if __name__ == "__main__":
    dashboard = SuperAIDashboard()
    
    # Simulate some data
    dashboard.add_delegation({
        "id": "del-001",
        "delegated_to": "claude-code-cli",
        "status": "running",
        "duration_seconds": 8.2
    })
    dashboard.update_cli_strength("claude-code-cli", 0.91, "Excellent at careful edits")
    dashboard.add_log({"timestamp": "08:45", "event_type": "delegation_completed", "details": "claude-code-cli finished auth task"})
    
    dashboard.run_terminal_dashboard()
