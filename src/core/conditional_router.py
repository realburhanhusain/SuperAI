import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

class ConditionalRouter:
    """
    Evaluates Header/Body conditions to dynamically override the target model route.
    Mimics CCR's condition-based routing (e.g., routing based on temperature or prompt keywords).
    """
    def __init__(self):
        self.config_path = Path.home() / ".superai" / "config" / "conditional_routes.json"
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.rules: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if self.config_path.exists():
            try:
                self.rules = json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception:
                self.rules = []
        else:
            self.rules = []

    def _evaluate_condition(self, condition: Dict[str, Any], payload: Dict[str, Any], headers: Dict[str, str]) -> bool:
        field = condition.get("field")
        source = condition.get("source", "body") # 'body' or 'header'
        operator = condition.get("operator", "equals")
        expected_value = condition.get("value")

        if source == "header":
            actual_value = headers.get(str(field).lower())
        else:
            # simple dot notation support for body
            actual_value = payload
            for part in str(field).split('.'):
                if isinstance(actual_value, dict):
                    actual_value = actual_value.get(part)
                else:
                    actual_value = None
                    break

        if actual_value is None and operator != "not_exists":
            # Special case for deeply nested prompts in messages array
            if field == "messages.content" and "messages" in payload:
                contents = [m.get("content", "") for m in payload["messages"] if isinstance(m, dict)]
                actual_value = " ".join(filter(None, contents))
            elif operator != "not_exists":
                return False

        if operator == "equals":
            return actual_value == expected_value
        elif operator == "not_equals":
            return actual_value != expected_value
        elif operator == "contains":
            return expected_value in str(actual_value)
        elif operator == "not_contains":
            return expected_value not in str(actual_value)
        elif operator == "regex":
            try:
                return bool(re.search(expected_value, str(actual_value)))
            except re.error:
                return False
        elif operator == "greater_than":
            try:
                return float(actual_value) > float(expected_value)
            except (ValueError, TypeError):
                return False
        elif operator == "less_than":
            try:
                return float(actual_value) < float(expected_value)
            except (ValueError, TypeError):
                return False
        elif operator == "exists":
            return actual_value is not None
        elif operator == "not_exists":
            return actual_value is None

        return False

    def evaluate(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Optional[str]:
        """
        Evaluates payload and headers against all rules.
        Returns the target_model override of the first fully matching rule, or None.
        """
        lower_headers = {k.lower(): v for k, v in headers.items()}
        
        for rule in self.rules:
            conditions = rule.get("conditions", [])
            match_type = rule.get("match_type", "all") # 'all' or 'any'
            
            if not conditions:
                continue

            results = [self._evaluate_condition(cond, payload, lower_headers) for cond in conditions]
            
            if match_type == "all" and all(results):
                return rule.get("target_model")
            elif match_type == "any" and any(results):
                return rule.get("target_model")
                
        return None
