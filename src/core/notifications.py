import sys
import requests
from src.core.config import config
from src.core.logger import get_logger

logger = get_logger("superai.notifications")

class NotificationManager:
    def __init__(self):
        self.webhook_url = config.get("notification_webhook_url")

    def send_notification(self, title: str, message: str) -> None:
        # Print nice console message
        print(f"[NOTIFICATION] {title}: {message}")
        
        # Emit terminal bell
        sys.stdout.write("\a")
        sys.stdout.flush()

        # Send webhook if configured
        if self.webhook_url:
            try:
                payload = {"title": title, "message": message}
                response = requests.post(self.webhook_url, json=payload, timeout=5.0)
                response.raise_for_status()
            except Exception as e:
                logger.error(f"Failed to send notification to webhook: {e}")
