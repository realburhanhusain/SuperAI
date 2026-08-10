from typing import Any
from .tracker import TokenTracker
from .compression import OutputCompressor

class LLMProxy:
    def __init__(self, llm_client: Any, tracker: TokenTracker):
        """
        Initialize the LLM proxy with an underlying LLM client and a token tracker.
        """
        self.llm_client = llm_client
        self.tracker = tracker

    def send_request(self, agent_id: str, prompt: str, **kwargs) -> str:
        """
        Proxy method to send requests to the LLM, enforcing guardrails and compression.
        """
        # 1. Compress the prompt to save on token costs
        compressed_prompt = OutputCompressor.compress(prompt)
        
        # 2. Estimate token count (heuristic: ~4 characters per token)
        estimated_tokens = len(compressed_prompt) // 4
        
        # 3. Check and record token usage, enforces hard spend caps
        self.tracker.record_usage(agent_id, estimated_tokens)
        
        # 4. Forward the request to the actual LLM client
        if hasattr(self.llm_client, 'generate'):
            response = self.llm_client.generate(compressed_prompt, **kwargs)
        elif callable(self.llm_client):
            response = self.llm_client(compressed_prompt, **kwargs)
        else:
            raise ValueError("llm_client must be callable or have a 'generate' method")
            
        return response
