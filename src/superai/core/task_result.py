"""
Pydantic models for task / step results (Phase 1 polish).

Orchestrator still returns dicts for JSON history compatibility;
use TaskResult.from_dict / .model_dump for typed access.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover
    # Extremely defensive — pydantic is a hard dependency
    BaseModel = object  # type: ignore
    Field = lambda **kwargs: None  # type: ignore


class StepResult(BaseModel):
    step: int
    description: str = ""
    model: Optional[str] = None
    status: str = "success"  # success | failed
    result: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    usage: Dict[str, Any] = Field(default_factory=dict)
    estimated_cost_usd: float = 0.0

    model_config = {"extra": "allow"}


class TaskResult(BaseModel):
    task_id: str
    task: str
    success: bool = False
    status: str = "failed"  # success | partial | failed
    message: str = ""
    model_used: Optional[str] = None
    steps: List[StepResult] = Field(default_factory=list)
    result: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    mode: str = "mock"
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskResult":
        steps_raw = data.get("steps") or []
        steps = []
        for s in steps_raw:
            if isinstance(s, StepResult):
                steps.append(s)
            elif isinstance(s, dict):
                steps.append(StepResult.model_validate(s))
        payload = {**data, "steps": steps}
        return cls.model_validate(payload)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="python")

    @property
    def steps_succeeded(self) -> int:
        return sum(1 for s in self.steps if s.status == "success")

    @property
    def steps_failed(self) -> int:
        return sum(1 for s in self.steps if s.status == "failed")
