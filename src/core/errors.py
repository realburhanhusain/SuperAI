"""SuperAI error hierarchy (Phase 1)."""

from __future__ import annotations

from typing import Optional


class SuperAIError(Exception):
    """Base error for SuperAI with optional user-facing hint."""

    def __init__(self, message: str, hint: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.hint = hint

    def user_message(self) -> str:
        if self.hint:
            return f"{self.message}\nHint: {self.hint}"
        return self.message


class ConfigError(SuperAIError):
    """Configuration load/save/validation failure."""


class OrchestratorError(SuperAIError):
    """Task planning or execution failure."""


class HistoryError(SuperAIError):
    """Task history persistence failure."""


class UserInputError(SuperAIError):
    """Invalid user input."""


class ModelError(SuperAIError):
    """Model selection or provider call failure."""
