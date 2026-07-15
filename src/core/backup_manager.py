"""
Backup Manager for SuperAI (Phase 5)

AES-256-GCM + Zstandard encrypted backups with incremental manifests.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import zstandard as zstd
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


BACKUP_SCOPES: Dict[str, List[str]] = {
    "config": ["config.json", "config"],
    "history": ["history", "learning_history.json"],
    "memory": ["memory"],
    "skills": ["skills"],
    "logs": ["logs"],
    "plugins": ["plugins"],
    "full": [
        "config.json",
        "learning_history.json",
        "history",
        "memory",
        "skills",
        "config",
        "logs",
        "plugins",
        "bandit_state.json",
        "provider_health.json",
        "model_pins.json",
        "model_blacklist.json",
        "step_cache.json",
        "preferences.json",
    ],
}


def default_backup_sources(home: Optional[Path] = None) -> List[Path]:
    """Paths that should be backed up (files and/or directories)."""
    root = home or (Path.home() / ".superai")
    return [
        root / "config.json",
        root / "learning_history.json",
        root / "history",
        root / "memory",
        root / "skills",
        root / "config",
        root / "logs",
    ]


def sources_for_scopes(
    scopes: Optional[List[str]] = None,
    home: Optional[Path] = None,
) -> List[Path]:
    """
    Selective backup: scopes like memory,skills,config or full.
    Unknown scope names are rejected (no path traversal via ../).
    """
    root = (home or (Path.home() / ".superai")).resolve()
    if not scopes:
        return default_backup_sources(root)
    names: List[str] = []
    for s in scopes:
        key = (s or "").strip().lower()
        if not key:
            continue
        if key == "full" or key == "all":
            names = list(BACKUP_SCOPES["full"])
            break
        if key not in BACKUP_SCOPES:
            raise ValueError(
                f"Unknown backup scope '{key}'. "
                f"Allowed: {', '.join(sorted(BACKUP_SCOPES))} or full"
            )
        names.extend(BACKUP_SCOPES[key])
    # unique preserve order; jail under root
    seen = set()
    paths: List[Path] = []
    for n in names:
        if n in seen:
            continue
        if ".." in Path(n).parts or Path(n).is_absolute():
            raise ValueError(f"Invalid backup path segment: {n}")
        seen.add(n)
        p = (root / n).resolve()
        try:
            p.relative_to(root)
        except ValueError as e:
            raise ValueError(f"Backup path escapes home: {n}") from e
        paths.append(p)
    return paths or default_backup_sources(root)


class BackupManager:
    """Encrypted incremental backups; cloud sync via rclone (Track F5)."""

    def __init__(
        self,
        backup_dir: Optional[str] = None,
        encryption_key: Optional[bytes] = None,
        superai_home: Optional[str] = None,
        key_file: Optional[str] = None,
    ):
        self.superai_home = Path(superai_home or (Path.home() / ".superai"))
        self.backup_dir = Path(
            backup_dir or (self.superai_home / "backups")
        )
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.key_file = Path(
            key_file or (self.superai_home / ".backup_key")
        )
        self.encryption_key = encryption_key or self._get_or_create_key()

    def _get_or_create_key(self) -> bytes:
        # Prefer OS keyring when available (avoids long-lived plaintext beside archives)
        try:
            from .keyring_store import HAS_KEYRING, SecretStore

            if HAS_KEYRING:
                store = SecretStore()
                existing = store.get("SUPERAI_BACKUP_KEY_B64")
                if existing:
                    import base64

                    return base64.b64decode(existing.encode("ascii"))
        except Exception:
            pass

        if self.key_file.exists():
            key = self.key_file.read_bytes()
            self._maybe_migrate_key_to_keyring(key)
            return key
        key = os.urandom(32)
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        self.key_file.write_bytes(key)
        try:
            os.chmod(self.key_file, 0o600)
        except OSError:
            pass
        self._maybe_migrate_key_to_keyring(key)
        print(
            "[BackupManager] New encryption key generated at "
            f"{self.key_file}. Prefer OS keyring (SUPERAI_BACKUP_KEY_B64); "
            "back this file up securely if keyring is unavailable!"
        )
        return key

    def _maybe_migrate_key_to_keyring(self, key: bytes) -> None:
        try:
            import base64

            from .keyring_store import HAS_KEYRING, SecretStore

            if not HAS_KEYRING:
                return
            store = SecretStore()
            if store.get("SUPERAI_BACKUP_KEY_B64"):
                return
            store.set(
                "SUPERAI_BACKUP_KEY_B64",
                base64.b64encode(key).decode("ascii"),
            )
        except Exception:
            pass

    def export_key(self, dest: str | Path) -> Path:
        """S9: copy encryption key to a secure path chosen by user."""
        dest_p = Path(dest).expanduser()
        dest_p.parent.mkdir(parents=True, exist_ok=True)
        dest_p.write_bytes(self.encryption_key)
        try:
            os.chmod(dest_p, 0o600)
        except OSError:
            pass
        return dest_p

    def import_key(self, src: str | Path) -> Path:
        """S9: import encryption key from backup path (overwrites current)."""
        src_p = Path(src).expanduser()
        if not src_p.is_file():
            raise FileNotFoundError(f"Key file not found: {src}")
        data = src_p.read_bytes()
        if len(data) < 16:
            raise ValueError("Key file too short")
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        self.key_file.write_bytes(data)
        try:
            os.chmod(self.key_file, 0o600)
        except OSError:
            pass
        self.encryption_key = data
        return self.key_file

    def _derive_key(self, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        return kdf.derive(self.encryption_key)

    def _encrypt_data(self, data: bytes) -> bytes:
        salt = os.urandom(16)
        key = self._derive_key(salt)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return salt + nonce + ciphertext

    def _decrypt_data(self, encrypted_data: bytes) -> bytes:
        salt = encrypted_data[:16]
        nonce = encrypted_data[16:28]
        ciphertext = encrypted_data[28:]
        key = self._derive_key(salt)
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None)

    def _get_file_hash(self, file_path: Path) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _collect_files(
        self, sources: List[Path]
    ) -> List[Tuple[Path, str]]:
        """Return (absolute_path, archive_name) pairs."""
        collected: List[Tuple[Path, str]] = []
        root = self.superai_home

        for src in sources:
            if not src.exists():
                continue
            if src.is_file():
                try:
                    rel = str(src.relative_to(root))
                except ValueError:
                    rel = src.name
                collected.append((src, rel.replace("\\", "/")))
            elif src.is_dir():
                for file_path in src.rglob("*"):
                    if not file_path.is_file():
                        continue
                    # Skip backup dir itself if nested
                    try:
                        if self.backup_dir in file_path.parents or file_path == self.backup_dir:
                            continue
                    except Exception:
                        pass
                    try:
                        rel = str(file_path.relative_to(root))
                    except ValueError:
                        rel = str(file_path.relative_to(src.parent))
                    collected.append((file_path, rel.replace("\\", "/")))
        return collected

    def create_backup(
        self,
        source_dirs: Optional[List[str]] = None,
        incremental: bool = True,
        force_full: bool = False,
        quiet: bool = False,
        scopes: Optional[List[str]] = None,
    ) -> str:
        if source_dirs is None:
            if scopes:
                sources = sources_for_scopes(scopes, self.superai_home)
            else:
                sources = default_backup_sources(self.superai_home)
        else:
            sources = [Path(p) for p in source_dirs]

        if force_full:
            incremental = False

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"superai_backup_{timestamp}.tar.zst.enc"
        backup_path = self.backup_dir / backup_name

        previous_inventory: Dict[str, str] = {}
        if incremental:
            previous_manifests = sorted(
                self.backup_dir.glob("manifest_*.json"), reverse=True
            )
            if previous_manifests:
                try:
                    with open(previous_manifests[0], "r", encoding="utf-8") as f:
                        prev = json.load(f)
                    # Support new nested format and legacy flat {path: hash}
                    if isinstance(prev, dict) and "full_inventory" in prev:
                        previous_inventory = prev.get("full_inventory") or {}
                    elif isinstance(prev, dict) and "files_in_archive" in prev:
                        previous_inventory = prev.get("files_in_archive") or {}
                    elif isinstance(prev, dict):
                        previous_inventory = {
                            k: v
                            for k, v in prev.items()
                            if isinstance(v, str) and len(v) == 64
                        }
                except Exception:
                    previous_inventory = {}

        candidates = self._collect_files(sources)
        files_to_backup: List[Tuple[Path, str]] = []
        manifest: Dict[str, str] = {}

        for file_path, rel in candidates:
            file_hash = self._get_file_hash(file_path)
            manifest[rel] = file_hash
            if incremental and previous_inventory.get(rel) == file_hash:
                continue
            files_to_backup.append((file_path, rel))

        def _log(msg: str) -> None:
            if not quiet:
                print(msg)

        # Always keep a full manifest of current state even if empty delta
        if not files_to_backup and incremental and previous_inventory:
            _log("[BackupManager] No new or changed files to backup.")
            return ""

        if not files_to_backup and not candidates:
            _log("[BackupManager] No source files found to backup.")
            return ""

        # If first backup and we have files, use all (already in files_to_backup)
        if not files_to_backup and candidates and not incremental:
            files_to_backup = candidates
            for fp, rel in files_to_backup:
                manifest[rel] = self._get_file_hash(fp)

        if not files_to_backup:
            _log("[BackupManager] No new or changed files to backup.")
            return ""

        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w:") as tar:
            for file_path, arcname in files_to_backup:
                tar.add(file_path, arcname=arcname)
        tar_buffer.seek(0)
        tar_data = tar_buffer.read()

        compressor = zstd.ZstdCompressor(level=3)
        compressed_data = compressor.compress(tar_data)
        encrypted_data = self._encrypt_data(compressed_data)

        with open(backup_path, "wb") as f:
            f.write(encrypted_data)

        # Full current inventory + which files were in this archive
        meta = {
            "created_at": datetime.now().isoformat(),
            "backup_file": backup_name,
            "file_count": len(files_to_backup),
            "incremental": incremental,
            "sha256_payload": hashlib.sha256(encrypted_data).hexdigest(),
            "files_in_archive": {rel: manifest[rel] for _, rel in files_to_backup},
            "full_inventory": manifest,
        }
        manifest_path = self.backup_dir / f"manifest_{timestamp}.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        _log(
            f"[BackupManager] Encrypted backup created: {backup_path} "
            f"({len(files_to_backup)} files)"
        )
        return str(backup_path)

    def verify_backup(self, backup_path: Optional[str] = None) -> Dict:
        """Decrypt + decompress + list archive; verify checksum if manifest present."""
        path = Path(backup_path) if backup_path else None
        if path is None:
            backups = self.list_backups()
            if not backups:
                return {"ok": False, "error": "No backups found"}
            path = backups[0]

        if not path.exists():
            return {"ok": False, "error": f"Backup not found: {path}"}

        result: Dict = {
            "ok": False,
            "path": str(path),
            "size_bytes": path.stat().st_size,
        }
        try:
            encrypted = path.read_bytes()
            result["sha256"] = hashlib.sha256(encrypted).hexdigest()

            # Match manifest by timestamp in filename if possible
            stem = path.name.replace("superai_backup_", "").replace(".tar.zst.enc", "")
            manifest_path = self.backup_dir / f"manifest_{stem}.json"
            if manifest_path.exists():
                with open(manifest_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                expected = meta.get("sha256_payload")
                if expected and expected != result["sha256"]:
                    result["error"] = "SHA256 mismatch vs manifest"
                    return result
                result["manifest"] = str(manifest_path)
                result["file_count_manifest"] = meta.get("file_count")

            compressed = self._decrypt_data(encrypted)
            tar_data = zstd.ZstdDecompressor().decompress(compressed)
            members: List[str] = []
            with tarfile.open(fileobj=io.BytesIO(tar_data), mode="r:") as tar:
                members = [m.name for m in tar.getmembers() if m.isfile()]
            result["ok"] = True
            result["members"] = members
            result["member_count"] = len(members)
            result["message"] = f"Backup OK — {len(members)} file(s) in archive"
            return result
        except Exception as e:  # noqa: BLE001
            result["error"] = str(e)
            return result

    def restore_backup(
        self, backup_path: str, restore_dir: Optional[str] = None
    ) -> Dict:
        backup_file = Path(backup_path)
        if not backup_file.exists():
            return {"ok": False, "error": f"Backup not found: {backup_path}"}

        try:
            encrypted_data = backup_file.read_bytes()
            compressed_data = self._decrypt_data(encrypted_data)
            tar_data = zstd.ZstdDecompressor().decompress(compressed_data)

            restore_path = Path(
                restore_dir or (self.superai_home / "restore")
            )
            restore_path.mkdir(parents=True, exist_ok=True)

            with tarfile.open(fileobj=io.BytesIO(tar_data), mode="r:") as tar:
                # Always validate members (tar-slip defense even without data_filter)
                restore_path = restore_path.resolve()
                safe_members = []
                for m in tar.getmembers():
                    name = m.name.replace("\\", "/")
                    if name.startswith("/") or name.startswith("..") or "/../" in f"/{name}/":
                        return {
                            "ok": False,
                            "error": f"Unsafe tar member path rejected: {m.name}",
                        }
                    target = (restore_path / name).resolve()
                    try:
                        target.relative_to(restore_path)
                    except ValueError:
                        return {
                            "ok": False,
                            "error": f"Tar member escapes restore dir: {m.name}",
                        }
                    if m.issym() or m.islnk():
                        return {
                            "ok": False,
                            "error": f"Symlink/hardlink members not allowed: {m.name}",
                        }
                    safe_members.append(m)
                try:
                    tar.extractall(
                        path=restore_path,
                        members=safe_members,
                        filter=tarfile.data_filter,
                    )
                except TypeError:
                    tar.extractall(path=restore_path, members=safe_members)
                members = [m.name for m in safe_members if m.isfile()]

            return {
                "ok": True,
                "restore_path": str(restore_path),
                "member_count": len(members),
                "members": members[:50],
                "message": f"Restored {len(members)} file(s) to {restore_path}",
            }
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def sync_to_cloud(self, remote: str, remote_path: str) -> bool:
        try:
            import subprocess

            latest_backup = self.list_backups()
            if not latest_backup:
                print("[BackupManager] No backups found to sync.")
                return False
            latest = latest_backup[0]
            # Also sync matching manifest if present
            stem = latest.name.replace("superai_backup_", "").replace(
                ".tar.zst.enc", ""
            )
            manifest = self.backup_dir / f"manifest_{stem}.json"
            targets = [str(latest)]
            if manifest.exists():
                targets.append(str(manifest))
            for local in targets:
                cmd = ["rclone", "copy", local, f"{remote}:{remote_path}"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"[BackupManager] rclone failed: {result.stderr}")
                    return False
            print(f"[BackupManager] Backup synced to {remote}:{remote_path}")
            return True
        except Exception as e:  # noqa: BLE001
            print(f"[BackupManager] Cloud sync error: {e}")
            return False

    def pull_from_cloud(
        self,
        remote: str,
        remote_path: str,
        filename: Optional[str] = None,
    ) -> Dict:
        """
        Pull backup archive(s) from rclone remote into local backup_dir (F5.2).
        """
        import subprocess

        dest = str(self.backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        if filename:
            src = f"{remote}:{remote_path.rstrip('/')}/{filename}"
            cmd = ["rclone", "copy", src, dest]
        else:
            # Pull all superai backups from remote path
            src = f"{remote}:{remote_path}"
            cmd = [
                "rclone",
                "copy",
                src,
                dest,
                "--include",
                "superai_backup_*.tar.zst.enc",
                "--include",
                "manifest_*.json",
            ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return {
                    "ok": False,
                    "error": result.stderr or result.stdout or "rclone failed",
                    "cmd": " ".join(cmd),
                }
            backups = self.list_backups()
            return {
                "ok": True,
                "backup_directory": dest,
                "latest_backup": str(backups[0]) if backups else None,
                "total_backups": len(backups),
                "message": f"Pulled from {remote}:{remote_path}",
            }
        except FileNotFoundError:
            return {
                "ok": False,
                "error": "rclone not found on PATH",
            }
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def restore_from_cloud(
        self,
        remote: str,
        remote_path: str,
        filename: Optional[str] = None,
        restore_dir: Optional[str] = None,
    ) -> Dict:
        """Pull from cloud then restore latest (or named) backup locally."""
        pull = self.pull_from_cloud(remote, remote_path, filename=filename)
        if not pull.get("ok"):
            return pull
        if filename:
            local = self.backup_dir / filename
        else:
            backups = self.list_backups()
            if not backups:
                return {"ok": False, "error": "No local backups after cloud pull"}
            local = backups[0]
        if not local.exists():
            return {"ok": False, "error": f"Expected backup missing after pull: {local}"}
        restored = self.restore_backup(str(local), restore_dir=restore_dir)
        restored["cloud_pull"] = pull
        restored["local_backup"] = str(local)
        return restored

    def list_backups(self) -> List[Path]:
        backups = list(self.backup_dir.glob("superai_backup_*.tar.zst.enc"))
        return sorted(backups, reverse=True)

    def apply_retention(self, keep: int = 10) -> Dict:
        """Keep newest N backups + matching manifests; delete older (F5.3)."""
        backups = self.list_backups()
        removed = []
        if keep < 1:
            keep = 1
        for old in backups[keep:]:
            try:
                stem = old.name.replace("superai_backup_", "").replace(".tar.zst.enc", "")
                manifest = self.backup_dir / f"manifest_{stem}.json"
                old.unlink(missing_ok=True)
                if manifest.exists():
                    manifest.unlink(missing_ok=True)
                removed.append(str(old))
            except OSError:
                continue
        return {"kept": min(keep, len(backups)), "removed": removed, "removed_count": len(removed)}

    def get_backup_status(self) -> Dict:
        backups = self.list_backups()
        total_size = sum(f.stat().st_size for f in backups) if backups else 0
        key_exists = self.key_file.exists()
        return {
            "total_backups": len(backups),
            "latest_backup": str(backups[0]) if backups else None,
            "backup_directory": str(self.backup_dir),
            "total_size_bytes": total_size,
            "encryption": "AES-256-GCM + Zstandard (incremental)",
            "incremental": True,
            "cloud_sync_supported": True,
            "key_file": str(self.key_file),
            "key_present": key_exists,
            "sources": [str(p) for p in default_backup_sources(self.superai_home)],
        }
