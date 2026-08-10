import os
from typing import Dict, Any, Optional

class AgentLaunchProfiles:
    """
    Provides pre-configured launch profiles for third-party agents 
    (Claude Code, Grok CLI, OpenCode, etc.). 
    Automatically configures environment variables so they route traffic through SuperAI.
    """
    
    @staticmethod
    def get_profiles() -> Dict[str, Dict[str, Any]]:
        # Assuming SuperAI runs on localhost:8000
        proxy_url = "http://127.0.0.1:8000/v1"
        
        return {
            "claude-code": {
                "name": "Claude Code (CLI)",
                "command": ["npx", "@anthropic-ai/claude-code"],
                "env": {
                    "ANTHROPIC_BASE_URL": proxy_url,
                    # We inject a client key if available, otherwise a placeholder
                    "ANTHROPIC_API_KEY": "sk-sai-default" 
                },
                "protocol": "anthropic"
            },
            "grok-cli": {
                "name": "Grok CLI",
                "command": ["npx", "grok-cli"],
                "env": {
                    "XAI_BASE_URL": proxy_url,
                    "XAI_API_KEY": "sk-sai-default"
                },
                "protocol": "openai"
            },
            "opencode": {
                "name": "OpenCode",
                "command": ["opencode"],
                "env": {
                    "OPENAI_BASE_URL": proxy_url,
                    "OPENAI_API_KEY": "sk-sai-default"
                },
                "protocol": "openai"
            },
            "kimi-cli": {
                "name": "Kimi CLI",
                "command": ["kimi"],
                "env": {
                    "MOONSHOT_BASE_URL": proxy_url,
                    "MOONSHOT_API_KEY": "sk-sai-default"
                },
                "protocol": "openai"
            }
        }

    @staticmethod
    def build_launch_env(profile_id: str, client_key: str) -> Optional[Dict[str, str]]:
        """
        Builds the environment variables required to force a third-party agent
        to route its traffic through SuperAI.
        """
        profiles = AgentLaunchProfiles.get_profiles()
        if profile_id not in profiles:
            return None
            
        profile = profiles[profile_id]
        env_updates = profile["env"].copy()
        
        # Inject the generated client key securely
        for k, v in env_updates.items():
            if v == "sk-sai-default":
                env_updates[k] = client_key
                
        return env_updates
