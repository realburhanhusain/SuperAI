import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

class NativeOSIntegrations:
    """
    Provides native OS capabilities mimicking Electron desktop features.
    Capabilities: Desktop Screenshot, Window Capture, Notifications.
    """
    
    @staticmethod
    def capture_screen_png(filename: Optional[str] = None, rect: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """
        Captures the screen or a specific region to PNG.
        Requires 'Pillow' to be installed.
        """
        try:
            from PIL import ImageGrab
            
            bbox = None
            if rect:
                bbox = (rect["x"], rect["y"], rect["x"] + rect["width"], rect["y"] + rect["height"])
                
            img = ImageGrab.grab(bbox=bbox, all_screens=True)
            
            if not filename:
                filename = f"capture_{int(time.time())}.png"
                
            out_path = Path.home() / ".superai" / "captures"
            out_path.mkdir(parents=True, exist_ok=True)
            
            full_path = out_path / filename
            img.save(full_path, "PNG")
            
            return {"ok": True, "file": str(full_path)}
        except ImportError:
            return {"ok": False, "error": "Pillow library is required for screen capture (pip install Pillow)"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @staticmethod
    def send_notification(title: str, message: str) -> bool:
        """
        Sends a native OS desktop notification.
        """
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_name="SuperAI",
                timeout=5
            )
            return True
        except Exception:
            return False
