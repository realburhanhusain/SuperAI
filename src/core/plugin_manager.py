import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List
import logging

logger = logging.getLogger("superai.plugins")

class PluginManager:
    """
    Dynamic Plugin Marketplace Manager.
    Loads external Python plugins from ~/.superai/plugins/ to inject new routes,
    interceptors, and MCP tools dynamically.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PluginManager, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.plugin_dir = Path.home() / ".superai" / "plugins"
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self.plugins: Dict[str, Any] = {}
        self.interceptors: List[Callable] = []
        self.routes = []

    def load_all_plugins(self):
        """Discovers and loads all plugins in the plugins directory."""
        if not self.plugin_dir.exists():
            return
            
        for item in self.plugin_dir.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                plugin_name = item.name
                try:
                    spec = importlib.util.spec_from_file_location(plugin_name, str(item / "__init__.py"))
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[plugin_name] = module
                        spec.loader.exec_module(module)
                        
                        if hasattr(module, "setup_plugin"):
                            module.setup_plugin(self)
                        
                        self.plugins[plugin_name] = module
                        logger.info(f"Loaded plugin: {plugin_name}")
                except Exception as e:
                    logger.error(f"Failed to load plugin {plugin_name}: {e}")

    def register_interceptor(self, interceptor: Callable):
        """Allows a plugin to register a new payload interceptor."""
        self.interceptors.append(interceptor)

    def register_route(self, method: str, path: str, handler: Callable):
        """Allows a plugin to register a new web route."""
        self.routes.append({"method": method, "path": path, "handler": handler})

    def apply_interceptors(self, chain):
        """Inject plugin interceptors into the main InterceptorChain."""
        for interceptor in self.interceptors:
            chain.add_interceptor(interceptor)

    def apply_routes(self, app):
        """Inject plugin routes into the FastAPI app."""
        for r in self.routes:
            app.add_api_route(r["path"], r["handler"], methods=[r["method"]])
