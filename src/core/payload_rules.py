import json
import os
import re
from pathlib import Path
from typing import Callable, Dict, Any, List, Optional

class PayloadRulesError(Exception):
    pass

class PersistentPayloadRules:
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path:
            self.path = Path(storage_path)
        else:
            self.path = Path.home() / ".superai" / "config" / "payload_rules.json"
        
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.rules = {"blocked_keywords": [], "system_append": ""}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.rules["blocked_keywords"] = data.get("blocked_keywords", [])
                    self.rules["system_append"] = data.get("system_append", "")
            except Exception:
                pass

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.rules, f, indent=2)

    def set_system_append(self, text: str):
        self._load()
        self.rules["system_append"] = text
        self._save()

    def add_blocked_keyword(self, keyword: str):
        self._load()
        if keyword not in self.rules["blocked_keywords"]:
            self.rules["blocked_keywords"].append(keyword)
            self._save()

    def remove_blocked_keyword(self, keyword: str):
        self._load()
        if keyword in self.rules["blocked_keywords"]:
            self.rules["blocked_keywords"].remove(keyword)
            self._save()

    def apply(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Applies persistent rules to a payload."""
        self._load()
        prompt = str(payload.get("prompt", ""))
        sys_prompt = str(payload.get("system_prompt", ""))
        
        lower_prompt = prompt.lower()
        for kw in self.rules["blocked_keywords"]:
            if kw.lower() in lower_prompt:
                raise PayloadRulesError(f"Prompt contains blocked keyword: {kw}")
                
        if self.rules["system_append"]:
            if sys_prompt:
                payload["system_prompt"] = sys_prompt + "\n\n" + self.rules["system_append"]
            else:
                payload["system_prompt"] = self.rules["system_append"]
                
        return payload

class PrivacyFilterInterceptor:
    def __call__(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = payload.copy()
        
        api_key_pattern = r"sk-[a-zA-Z0-9]{32,}"
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        
        for key in ["prompt", "system_prompt"]:
            if key in payload and isinstance(payload[key], str):
                text = payload[key]
                text = re.sub(api_key_pattern, "[REDACTED_API_KEY]", text)
                text = re.sub(email_pattern, "[REDACTED_EMAIL]", text)
                payload[key] = text
        return payload

class AntigravityCodingFilterInterceptor:
    def __call__(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = payload.copy()
        
        patterns = [
            ("<identity>You are Antigravity</identity>", "You are a helpful coding assistant"),
            ("You are Antigravity", "You are a helpful coding assistant")
        ]
        
        for key in ["prompt", "system_prompt"]:
            if key in payload and isinstance(payload[key], str):
                text = payload[key]
                for pattern, replacement in patterns:
                    text = text.replace(pattern, replacement)
                payload[key] = text
        return payload

class SessionArchiveInterceptor:
    def __init__(self, log_dir: str):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "session_archive.jsonl"
        
    def __call__(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception:
            pass
        return payload

class InterceptorChain:
    """
    A middleware/interceptor chain pattern that can intercept LLM requests 
    to modify the payload (e.g., inject system prompts or filter keywords)
    before the request is sent.
    """
    def __init__(self, use_persistent_rules: bool = True, use_privacy_filter: bool = False, use_antigravity_filter: bool = False, archive_dir: Optional[str] = None):
        self.interceptors: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = []
        if use_persistent_rules:
            self.persistent_rules = PersistentPayloadRules()
            self.add_interceptor(self.persistent_rules.apply)
        if use_privacy_filter:
            self.add_interceptor(PrivacyFilterInterceptor())
        if use_antigravity_filter:
            self.add_interceptor(AntigravityCodingFilterInterceptor())
        if archive_dir:
            self.add_interceptor(SessionArchiveInterceptor(archive_dir))

    def add_interceptor(self, interceptor: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """Adds an interceptor to the chain."""
        self.interceptors.append(interceptor)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Executes all interceptors on the payload in order."""
        current_payload = payload
        for interceptor in self.interceptors:
            current_payload = interceptor(current_payload)
        return current_payload
