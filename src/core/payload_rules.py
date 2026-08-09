from typing import Callable, Dict, Any, List

class InterceptorChain:
    """
    A middleware/interceptor chain pattern that can intercept LLM requests 
    to modify the payload (e.g., inject system prompts or filter keywords)
    before the request is sent.
    """
    def __init__(self):
        self.interceptors: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = []

    def add_interceptor(self, interceptor: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """Adds an interceptor to the chain."""
        self.interceptors.append(interceptor)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Executes all interceptors on the payload in order."""
        current_payload = payload
        for interceptor in self.interceptors:
            current_payload = interceptor(current_payload)
        return current_payload
