import asyncio
import os
import time
from pathlib import Path
from .akbp import AKBP

class SubconsciousLoop:
    """
    Detached background loop ("subconscious") that diffs the workspace and auto-researches goals.
    """
    def __init__(self, workspace_root: str, scan_interval: int = 60):
        self.workspace_root = Path(workspace_root)
        self.akbp = AKBP(workspace_root)
        self.running = False
        self.scan_interval = scan_interval
        
    async def start(self):
        """Start the subconscious loop."""
        self.running = True
        print("[Subconscious] Starting background loop...")
        asyncio.create_task(self._loop())
        
    def stop(self):
        """Stop the subconscious loop."""
        self.running = False
        print("[Subconscious] Stopping background loop...")

    async def _loop(self):
        last_scan_time = time.time() - self.scan_interval # so it runs immediately
        while self.running:
            try:
                current_time = time.time()
                modified_files = self._diff_workspace(last_scan_time)
                
                if modified_files:
                    print(f"[Subconscious] Detected {len(modified_files)} modified files. Analyzing...")
                    self._auto_research(modified_files)
                    
                last_scan_time = current_time
            except Exception as e:
                print(f"[Subconscious] Error in background loop: {e}")
                
            await asyncio.sleep(self.scan_interval)

    def _diff_workspace(self, last_scan_time: float) -> list:
        """Find files modified since last_scan_time."""
        modified_files = []
        for root, dirs, files in os.walk(self.workspace_root):
            # Ignore hidden/system/heavy directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', 'venv', '__pycache__')]
            for file in files:
                filepath = Path(root) / file
                try:
                    if filepath.stat().st_mtime > last_scan_time:
                        modified_files.append(filepath)
                except OSError:
                    pass
        return modified_files

    def _auto_research(self, modified_files: list):
        """Perform 'auto-research' based on workspace diffs and store in Obsidian memory."""
        files_str = ", ".join([f.name for f in modified_files[:5]])
        if len(modified_files) > 5:
            files_str += f" and {len(modified_files) - 5} more"
            
        title = "Auto-Research: Workspace Changes Detected"
        content = f"The subconscious detected modifications in: {files_str}.\n\n"
        content += "### Analysis\n"
        content += "Automatically diffed the workspace and analyzing potential impact on current goals...\n"
        content += "Status: Synced to Obsidian memory (AKBP).\n"
        
        filepath = self.akbp.save_memory(
            title=title,
            content=content,
            tags=["subconscious", "auto-research", "diff"]
        )
        print(f"[Subconscious] Saved auto-research memory to {filepath}")

if __name__ == "__main__":
    loop = SubconsciousLoop(".")
    asyncio.run(loop.start())
