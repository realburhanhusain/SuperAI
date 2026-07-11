"""
SuperAI Backup Manager
Handles local and cloud backups of memory, configs, skills, and settings.
"""

import os
import shutil
import tarfile
import datetime
from pathlib import Path
from typing import Optional

class BackupManager:
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.critical_paths = [
            "config",
            "superai_memory",
            "superai_skills",
        ]

    def create_local_backup(self, backup_dir: str = "backups") -> str:
        """Create a timestamped local backup of critical data."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"superai_backup_{timestamp}.tar.gz"
        backup_path = Path(backup_dir) / backup_name
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        with tarfile.open(backup_path, "w:gz") as tar:
            for path_name in self.critical_paths:
                path = self.base_dir / path_name
                if path.exists():
                    tar.add(path, arcname=path_name)
                else:
                    print(f"[Backup] Skipping missing path: {path_name}")

        print(f"[Backup] Local backup created: {backup_path}")
        return str(backup_path)

    def restore_from_local_backup(self, backup_file: str):
        """Restore from a local backup tarball."""
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")

        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(path=self.base_dir)

        print(f"[Backup] Restored from: {backup_file}")

    def backup_to_cloud(self, cloud_path: str):
        """
        Placeholder for cloud backup.
        In production, integrate with boto3 (S3), google-cloud-storage, etc.
        """
        print(f"[Backup] Cloud backup to {cloud_path} is not yet implemented.")
        print("You can manually upload the latest local backup or integrate cloud SDK here.")

    def list_backups(self, backup_dir: str = "backups") -> list:
        """List available local backups."""
        backup_path = Path(backup_dir)
        if not backup_path.exists():
            return []
        return sorted([f.name for f in backup_path.glob("superai_backup_*.tar.gz")])
