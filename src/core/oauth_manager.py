import os
import json
import uuid
from typing import Dict, Any, Optional

class OAuthManager:
    def __init__(self):
        self.state_store = {}
        
    def start_device_flow(self, provider: str) -> Dict[str, Any]:
        device_code = str(uuid.uuid4())
        user_code = str(uuid.uuid4())[:8].upper()
        self.state_store[device_code] = {"provider": provider, "status": "pending", "user_code": user_code}
        
        return {
            "device_code": device_code,
            "user_code": user_code,
            "verification_uri": f"https://superai.local/device?code={user_code}",
            "expires_in": 900
        }

    def poll_device_flow(self, device_code: str) -> Dict[str, Any]:
        state = self.state_store.get(device_code)
        if not state:
            return {"status": "expired"}
        return state