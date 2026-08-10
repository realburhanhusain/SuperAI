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

class ToolHubInterceptor:
    """
    Proxy-Level ToolHub plugin ecosystem.
    Intercepts raw API payloads on-the-fly and extends them by dynamically running tools
    before the request hits the LLM.
    Syntax in prompt: [ToolHub: search "query"] or [ToolHub: run "read" path="x"]
    """
    def __call__(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = payload.copy()
        
        pattern = re.compile(r'\[ToolHub:\s*([a-zA-Z0-9_-]+)\s*(.*?)\]', re.IGNORECASE)
        
        def replacer(match):
            tool_name = match.group(1).lower()
            args = match.group(2).strip()
            
            try:
                if tool_name == "search":
                    # Mock or naive search for now, could integrate with DuckDuckGo G14
                    return f"[ToolHub Result: Searched for '{args}'. In a real implementation this would fetch search results.]"
                
                from .agent_tools import run_tool
                
                # Parse args loosely for 'run'
                kwargs = {}
                if tool_name == "run":
                    # e.g. [ToolHub: run read path="foo.py"]
                    parts = args.split(None, 1)
                    if not parts:
                        return "[ToolHub Error: missing tool name for run]"
                    actual_tool = parts[0]
                    arg_str = parts[1] if len(parts) > 1 else ""
                    
                    import shlex
                    try:
                        tokens = shlex.split(arg_str)
                    except Exception:
                        tokens = arg_str.split()
                        
                    for tok in tokens:
                        if "=" in tok:
                            k, v = tok.split("=", 1)
                            kwargs[k.strip()] = v.strip()
                        else:
                            kwargs.setdefault("path", tok)
                            
                    res = run_tool(actual_tool, **kwargs)
                    if res.get("ok"):
                        content = res.get("content") or res.get("hits") or res.get("stdout") or str(res)
                        return f"[ToolHub Result ({actual_tool}):\n{content}\n]"
                    else:
                        return f"[ToolHub Error ({actual_tool}): {res.get('error')}]"
                else:
                    return f"[ToolHub Error: Tool {tool_name} not found]"
            except Exception as e:
                return f"[ToolHub Error: {str(e)}]"

        for key in ["prompt", "system_prompt"]:
            if key in payload and isinstance(payload[key], str):
                payload[key] = pattern.sub(replacer, payload[key])
                
        if "messages" in payload and isinstance(payload["messages"], list):
            for msg in payload["messages"]:
                if isinstance(msg.get("content"), str):
                    msg["content"] = pattern.sub(replacer, msg["content"])
                    
        return payload


class FusionVisionInterceptor:
    """
    Fusion Vision proxy-level interceptor.
    Splices image capabilities into text-only models by pre-processing images
    locally (or via a fast vision API) and injecting the descriptions into the text prompt.
    """
    def __call__(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = payload.copy()
        
        vision_attachments = payload.get("vision_attachments")
        if not vision_attachments:
            return payload
            
        # Optional: check if the target model natively supports vision.
        # For this implementation, if 'force_fusion' is True or model doesn't support it, we run it.
        # To make it universal, we just run it if vision_attachments exist.
        
        try:
            # We use a fast fallback vision model for analysis (e.g. gpt-4o-mini or claude-3-haiku)
            from .model_caller import ModelCaller
            from .model_registry import ModelRegistry
            
            # Prevent infinite loops if the fallback model is called
            if payload.get("fusion_processed"):
                return payload
                
            caller = ModelCaller(registry=ModelRegistry(), use_mock=False)
            
            descriptions = []
            for idx, attachment in enumerate(vision_attachments):
                # Send to a fast vision-capable model
                vision_prompt = "Describe this image in detail so a text-only AI can understand what it contains. Include all text, diagrams, UI elements, and relevant context."
                
                # We do a direct call to a reliable vision model (hardcoded or from config)
                # In production, this would use a 'vision_fallback' config.
                result = caller.call(
                    model="gpt-4o-mini",  # typically fast/cheap for vision
                    prompt=vision_prompt,
                    vision_attachments=[attachment],
                    fusion_processed=True  # avoid loops
                )
                
                desc = result.get("response", "Could not process image.")
                descriptions.append(f"--- Image {idx+1} Description ---\n{desc}\n")
                
            # Append descriptions to the prompt
            current_prompt = payload.get("prompt", "")
            fusion_text = "\n\n[Fusion Vision System: The user attached images which have been analyzed for you:]\n" + "\n".join(descriptions)
            payload["prompt"] = current_prompt + fusion_text
            
            # Clear attachments so the upstream text-only model doesn't crash
            payload["vision_attachments"] = None
            
        except Exception as e:
            import logging
            logging.getLogger("superai.fusion").warning(f"Fusion Vision failed: {e}")
            
        return payload

class InterceptorChain:
    """
    A middleware/interceptor chain pattern that can intercept LLM requests 
    to modify the payload (e.g., inject system prompts or filter keywords)
    before the request is sent.
    """
    def __init__(self, use_persistent_rules: bool = True, use_privacy_filter: bool = False, use_antigravity_filter: bool = False, archive_dir: Optional[str] = None, use_toolhub: bool = True, use_fusion_vision: bool = True):
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
        if use_toolhub:
            self.add_interceptor(ToolHubInterceptor())
        if use_fusion_vision:
            self.add_interceptor(FusionVisionInterceptor())

    def add_interceptor(self, interceptor: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """Adds an interceptor to the chain."""
        self.interceptors.append(interceptor)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Executes all interceptors on the payload in order."""
        current_payload = payload
        for interceptor in self.interceptors:
            current_payload = interceptor(current_payload)
        return current_payload
