import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from filelock import FileLock

class ClientKeyManager:
    """
    Manages SuperAI-minted API keys for downstream agents.
    Provides scoped access, token budgets, and expiration.

    This file holds live credentials in plaintext, so it is written the same
    way the rest of the repo writes sensitive state (C6.5):
      - atomic write + backup rotation, via config.atomic_write_with_backup (T06)
      - 0600 permissions on POSIX
      - a FileLock around every read-modify-write, matching key_pool.py
    """
    def __init__(self):
        self.config_path = Path.home() / ".superai" / "config" / "client_keys.json"
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.backups_dir = Path.home() / ".superai" / "backups"
        self.lock = FileLock(str(self.config_path) + ".lock")
        self.keys: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if self.config_path.exists():
            try:
                self.keys = json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception:
                self.keys = {}
        else:
            self.keys = {}

    def _restrict_permissions(self) -> None:
        """Owner-only. No-op in practice on Windows, correct and cheap on POSIX."""
        try:
            os.chmod(self.config_path, 0o600)
        except (OSError, NotImplementedError):
            pass

    def _save(self):
        from .config import atomic_write_with_backup

        atomic_write_with_backup(self.config_path, self.keys, self.backups_dir)
        self._restrict_permissions()

    def _match_key(self, key: str) -> Optional[str]:
        """
        Constant-time lookup of a presented key.

        A plain ``key in self.keys`` is a hash lookup whose timing correlates
        with the key material. Every stored key is compared, with no early
        exit, mirroring _check_management_auth's use of hmac.compare_digest.
        """
        if not key:
            return None
        presented = key.encode("utf-8")
        found: Optional[str] = None
        for stored in self.keys:
            if hmac.compare_digest(presented, stored.encode("utf-8")):
                found = stored
        return found

    def mint_key(self, name: str, token_budget: Optional[int] = None, allowed_models: Optional[List[str]] = None, expires_in_days: Optional[int] = None) -> str:
        """Mint a new client API key with optional restrictions."""
        prefix = "sk-sai-"
        key = prefix + secrets.token_urlsafe(32)
        
        expires_at = None
        if expires_in_days:
            expires_at = time.time() + (expires_in_days * 86400)

        with self.lock:
            self._load()  # re-read under lock: another process may have minted since __init__
            self.keys[key] = {
                "name": name,
                "created_at": time.time(),
                "expires_at": expires_at,
                "token_budget": token_budget,
                "tokens_used": 0,
                "allowed_models": allowed_models or [],
                "is_active": True
            }
            self._save()
        return key

    def revoke_key(self, key: str) -> bool:
        """Revoke a specific API key."""
        with self.lock:
            self._load()
            matched = self._match_key(key)
            if matched is None:
                return False
            self.keys[matched]["is_active"] = False
            self._save()
            return True

    def validate_key(self, key: str, requested_model: Optional[str] = None, estimated_tokens: int = 0) -> Dict[str, Any]:
        """Validate if a key is active, unexpired, and within budget/scope."""
        matched = self._match_key(key)
        if matched is None:
            return {"ok": False, "error": "Invalid API key"}

        key_data = self.keys[matched]
        
        if not key_data.get("is_active", True):
            return {"ok": False, "error": "API key has been revoked"}
            
        if key_data.get("expires_at") and time.time() > key_data["expires_at"]:
            return {"ok": False, "error": "API key has expired"}
            
        if requested_model and key_data.get("allowed_models"):
            if requested_model not in key_data["allowed_models"]:
                return {"ok": False, "error": f"API key is not authorized for model: {requested_model}"}
                
        if key_data.get("token_budget") is not None:
            if key_data.get("tokens_used", 0) + estimated_tokens > key_data["token_budget"]:
                return {"ok": False, "error": "API key token budget exceeded"}
                
        return {"ok": True, "key_data": key_data}

    def consume_budget(self, key: str, tokens: int):
        """
        Consume token budget after a successful request.

        Read-modify-write under the lock: without it, two concurrent requests
        both read the same tokens_used and one increment is lost, so budgets
        silently overrun.
        """
        with self.lock:
            self._load()
            matched = self._match_key(key)
            if matched is None:
                return
            self.keys[matched]["tokens_used"] = self.keys[matched].get("tokens_used", 0) + tokens
            self._save()

    def list_keys(self) -> List[Dict[str, Any]]:
        """List all keys (with sensitive parts redacted)."""
        safe_keys = []
        for k, v in self.keys.items():
            safe_k = f"{k[:11]}...{k[-4:]}"
            safe_keys.append({
                "id": safe_k,
                "name": v.get("name"),
                "created_at": v.get("created_at"),
                "expires_at": v.get("expires_at"),
                "token_budget": v.get("token_budget"),
                "tokens_used": v.get("tokens_used", 0),
                "allowed_models": v.get("allowed_models"),
                "is_active": v.get("is_active")
            })
        return safe_keys
