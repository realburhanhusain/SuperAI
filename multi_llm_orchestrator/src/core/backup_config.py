"""
Backup Configuration Manager
Handles storage and retrieval of backup-related settings (especially cloud remote).
"""

import json
from pathlib import Path
from typing import Optional, Dict

class BackupConfig:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "backup_config.json"
        self.config = self._load()

    def _load(self) -> Dict:
        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                return json.load(f)
        return {}

    def save(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=2)

    def set_cloud_remote(self, remote_name: str, remote_path: str = "superai-backups/"):
        self.config["cloud_remote"] = remote_name
        self.config["cloud_path"] = remote_path
        self.save()
        print(f"[BackupConfig] Cloud backup destination set to: {remote_name}:{remote_path}")

    def get_cloud_remote(self) -> Optional[Dict]:
        if "cloud_remote" in self.config:
            return {
                "remote": self.config["cloud_remote"],
                "path": self.config.get("cloud_path", "superai-backups/")
            }
        return None

    def is_cloud_backup_enabled(self) -> bool:
        return "cloud_remote" in self.config
