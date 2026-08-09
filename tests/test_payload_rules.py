import os
import json
import pytest
from pathlib import Path
from src.core.payload_rules import (
    InterceptorChain,
    PrivacyFilterInterceptor,
    AntigravityCodingFilterInterceptor,
    SessionArchiveInterceptor
)

def test_interceptor_chain_safety_and_filter():
    chain = InterceptorChain()
    
    def add_safety_prompt(payload):
        payload = payload.copy()
        if "messages" in payload:
            # Injecting safety system prompt at the beginning
            payload["messages"].insert(0, {"role": "system", "content": "Safety System Prompt"})
        return payload

    def filter_keywords(payload):
        payload = payload.copy()
        if "messages" in payload:
            for msg in payload["messages"]:
                if "content" in msg:
                    msg["content"] = msg["content"].replace("dangerous", "***")
        return payload

    chain.add_interceptor(add_safety_prompt)
    chain.add_interceptor(filter_keywords)

    initial_payload = {
        "messages": [
            {"role": "user", "content": "This is a dangerous message."}
        ]
    }

    final_payload = chain.execute(initial_payload)

    assert len(final_payload["messages"]) == 2
    assert final_payload["messages"][0]["role"] == "system"
    assert final_payload["messages"][0]["content"] == "Safety System Prompt"
    assert final_payload["messages"][1]["role"] == "user"
    assert final_payload["messages"][1]["content"] == "This is a *** message."

def test_privacy_filter_interceptor():
    interceptor = PrivacyFilterInterceptor()
    payload = {
        "prompt": "Here is my key sk-1234567890abcdef1234567890abcdef and email test@example.com",
        "system_prompt": "Another key sk-abcdef1234567890abcdef1234567890 here."
    }
    result = interceptor(payload)
    assert result["prompt"] == "Here is my key [REDACTED_API_KEY] and email [REDACTED_EMAIL]"
    assert result["system_prompt"] == "Another key [REDACTED_API_KEY] here."

def test_antigravity_coding_filter_interceptor():
    interceptor = AntigravityCodingFilterInterceptor()
    payload = {
        "prompt": "Hello! You are Antigravity, right?",
        "system_prompt": "<identity>You are Antigravity</identity>\nPlease help me."
    }
    result = interceptor(payload)
    assert result["prompt"] == "Hello! You are a helpful coding assistant, right?"
    assert result["system_prompt"] == "You are a helpful coding assistant\nPlease help me."

def test_session_archive_interceptor(tmp_path):
    log_dir = str(tmp_path / "logs")
    interceptor = SessionArchiveInterceptor(log_dir)
    payload = {"prompt": "test", "value": 42}
    result = interceptor(payload)
    
    assert result == payload
    log_file = Path(log_dir) / "session_archive.jsonl"
    assert log_file.exists()
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        assert json.loads(lines[0]) == payload

def test_interceptor_chain_init(tmp_path):
    log_dir = str(tmp_path / "logs")
    chain = InterceptorChain(
        use_persistent_rules=False,
        use_privacy_filter=True,
        use_antigravity_filter=True,
        archive_dir=log_dir
    )
    assert len(chain.interceptors) == 3
    
    payload = {
        "prompt": "email is test@example.com and You are Antigravity",
    }
    result = chain.execute(payload)
    assert result["prompt"] == "email is [REDACTED_EMAIL] and You are a helpful coding assistant"
    
    log_file = Path(log_dir) / "session_archive.jsonl"
    assert log_file.exists()
    with open(log_file, "r", encoding="utf-8") as f:
        saved = json.loads(f.read().strip())
        assert saved["prompt"] == "email is [REDACTED_EMAIL] and You are a helpful coding assistant"

