import time
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live

console = Console()

class GlobalActivityDashboard:
    def __init__(self):
        self.console = Console()

    def generate_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main")
        )
        
        layout["header"].update(Panel("Global Activity Dashboard - SuperAI", style="bold white on blue"))
        
        layout["main"].split_row(
            Layout(name="left_panel", ratio=1),
            Layout(name="right_panel", ratio=2)
        )
        
        # Left Panel - Metrics
        metrics_table = Table.grid(padding=1)
        metrics_table.add_column(style="cyan", justify="right")
        metrics_table.add_column(style="magenta")
        metrics_table.add_row("Active Agents:", "14")
        metrics_table.add_row("Total Spend:", "$42.50")
        metrics_table.add_row("Success Rate:", "98.2%")
        layout["left_panel"].update(Panel(metrics_table, title="Fleet Metrics", border_style="cyan"))
        
        # Right Panel - Agents
        agents_table = Table(expand=True)
        agents_table.add_column("Agent ID", style="cyan")
        agents_table.add_column("Status", style="green")
        agents_table.add_column("Task")
        agents_table.add_column("Spend", justify="right")
        
        agents_table.add_row("agent-alpha", "RUNNING", "Phase 4 implementation", "$2.10")
        agents_table.add_row("agent-beta", "IDLE", "Waiting for PR review", "$0.50")
        agents_table.add_row("agent-gamma", "RUNNING", "Security audit", "$5.30")
        
        layout["right_panel"].update(Panel(agents_table, title="Active Worktrees", border_style="blue"))
        
        return layout

    def run(self):
        with Live(self.generate_layout(), refresh_per_second=1, screen=True) as live:
            # Run for a few seconds to simulate activity
            for _ in range(3):
                time.sleep(1)

if __name__ == "__main__":
    GlobalActivityDashboard().run()
