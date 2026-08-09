"""Ollama provider wrapper."""

from typing import List, Dict, Any
from .base import LLMProvider
from .. import ollama_client
from ..settings import get_settings

class OllamaProvider(LLMProvider):
    """Ollama API provider."""
    
    async def query(self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7) -> Dict[str, Any]:
        # Strip prefix if present
        model = model_id.removeprefix("ollama:")
        return await ollama_client.query_model(model, messages, timeout, temperature)

    async def get_models(self) -> List[Dict[str, Any]]:
        import httpx
        settings = get_settings()
        base_url = settings.ollama_base_url
        
        if base_url.endswith('/'):
            base_url = base_url[:-1]
            
        try:
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                response = await client.get(f"{base_url}/api/tags")
                
                if response.status_code != 200:
                    return []
                    
                data = response.json()
                models = []
                for model in data.get("models", []):
                    model_name = model.get("name", "")
                    # Filter out embedding models
                    if "embed" in model_name.lower():
                        continue
                        
                    models.append({
                        "id": f"ollama:{model_name}",
                        "name": f"{model_name} [Ollama]",
                        "provider": "Ollama",
                        "is_free": True
                    })
                return sorted(models, key=lambda x: x["name"])
        except Exception:
            return []

    async def validate_key(self, api_key: str) -> Dict[str, Any]:
        # For Ollama, api_key is treated as base_url
        import httpx
        base_url = api_key
        if base_url.endswith('/'):
            base_url = base_url[:-1]
            
        try:
            async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
                response = await client.get(f"{base_url}/api/tags")
                
                if response.status_code == 200:
                    return {"success": True, "message": "Successfully connected to Ollama"}
                else:
                    return {"success": False, "message": f"Ollama API error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": str(e)}
