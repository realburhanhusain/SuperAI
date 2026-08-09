import pytest
from src.core.payload_rules import InterceptorChain

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
