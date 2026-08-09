"""Tests for response_language settings normalization."""

from backend.prompts import RESPONSE_LANGUAGE_DEFAULT
from backend.settings import _normalize_prompt_defaults


def test_invalid_response_language_falls_back_to_english():
    normalized = _normalize_prompt_defaults({"response_language": "Klingon"})
    assert normalized["response_language"] == RESPONSE_LANGUAGE_DEFAULT


def test_valid_response_language_is_preserved():
    normalized = _normalize_prompt_defaults({"response_language": "Spanish"})
    assert normalized["response_language"] == "Spanish"


def test_invalid_date_format_falls_back_to_auto():
    normalized = _normalize_prompt_defaults({"date_format": "INVALID"})
    assert normalized["date_format"] == "auto"
