import json
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class OpenCodeSyncPlugin:
    """
    Synchronizes SuperAI proxy states, fallback configs, and routing 
    environments to the OpenCode CLI configuration.
    """
    def __init__(self):
        self.opencode_dir = Path.home() / ".opencode"
        self.config_path = self.opencode_dir / "config.json"
        
    def ensure_dir(self):
        if not self.opencode_dir.exists():
            self.opencode_dir.mkdir(parents=True, exist_ok=True)
            
    def sync(self, proxy_url: str = "http://127.0.0.1:8787", fallback_model: str = "opencode-default"):
        """
        Pushes SuperAI active states directly into OpenCode.
        """
        self.ensure_dir()
        
        config = {}
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load opencode config: {e}")
                
        # Inject SuperAI routing states
        if "api" not in config:
            config["api"] = {}
            
        config["api"]["base_url"] = proxy_url
        config["api"]["fallback_model"] = fallback_model
        config["superai_managed"] = True
        
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            logger.info(f"Synchronized SuperAI routing state to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to write opencode config: {e}")

def run_sync() -> None:
    plugin = OpenCodeSyncPlugin()
    plugin.sync()
