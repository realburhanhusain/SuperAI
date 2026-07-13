"""
Structured output validation (S18).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Type

try:
    from pydantic import BaseModel, ValidationError
except ImportError:  # pragma: no cover
    BaseModel = object  # type: ignore
    ValidationError = Exception  # type: ignore


def extract_json(text: str) -> Optional[Any]:
    text = (text or "").strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # find object/array
    for open_c, close_c in (("{", "}"), ("[", "]")):
        a, b = text.find(open_c), text.rfind(close_c)
        if a >= 0 and b > a:
            try:
                return json.loads(text[a : b + 1])
            except json.JSONDecodeError:
                continue
    return None


def validate_json_schema_simple(data: Any, required_keys: Optional[list] = None) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {"ok": False, "error": "expected object"}
    missing = [k for k in (required_keys or []) if k not in data]
    if missing:
        return {"ok": False, "error": f"missing keys: {missing}", "data": data}
    return {"ok": True, "data": data}


def validate_pydantic(data: Any, model: Type[BaseModel]) -> Dict[str, Any]:
    try:
        obj = model.model_validate(data) if hasattr(model, "model_validate") else model(**data)
        dump = obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()
        return {"ok": True, "data": dump}
    except ValidationError as e:
        return {"ok": False, "error": str(e)}
