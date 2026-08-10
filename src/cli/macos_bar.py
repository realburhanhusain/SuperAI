import os
import sys
import threading
import time
import requests
import logging

logger = logging.getLogger(__name__)

class SuperAIMacOSBar:
    """
    macOS Native Status Bar (SuperAI Bar).
    Displays live routing limits, quotas, and active proxy status
    in the macOS menu bar. Uses 'rumps' on Darwin.
    """
    def __init__(self):
        self.app = None
        self.proxy_url = "http://127.0.0.1:8787/api/status"
        self._running = False
        
        if sys.platform == "darwin":
            try:
                import rumps
                class RumpsApp(rumps.App):
                    def __init__(self, parent):
                        super().__init__("SuperAI")
                        self.parent = parent
                        self.quota_menu = rumps.MenuItem("Quota: Loading...")
                        self.menu = [
                            self.quota_menu,
                            None,
                            rumps.MenuItem("Open Dashboard", callback=self.open_dashboard)
                        ]
                    
                    @rumps.timer(10)
                    def update_status(self, _):
                        try:
                            res = requests.get(self.parent.proxy_url, timeout=2).json()
                            if res.get("ok"):
                                self.title = "🟢 SuperAI"
                                self.quota_menu.title = f"Spend: ${res.get('spend', '0.00')}"
                        except Exception:
                            self.title = "🔴 SuperAI"
                            self.quota_menu.title = "Offline"
                            
                    def open_dashboard(self, _):
                        import webbrowser
                        webbrowser.open("http://127.0.0.1:8787/console")
                        
                self.app = RumpsApp(self)
            except ImportError:
                logger.warning("rumps library not installed; macOS bar disabled.")
        else:
            logger.info("macOS bar is only available on Darwin. Skipping initialization.")

    def run(self):
        if self.app:
            self._running = True
            logger.info("Starting SuperAI macOS Menu Bar...")
            self.app.run()
        else:
            logger.info("macOS bar app not available to run.")

def launch_bar():
    bar = SuperAIMacOSBar()
    bar.run()

if __name__ == "__main__":
    launch_bar()
