import logging
import requests
import json
from typing import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

logger = logging.getLogger(__name__)

class NotificationClient:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_notification(self, message: str, level: str = "info"):
        """Push notifications to mobile companion or chat channels."""
        if not self.webhook_url:
            logger.warning("No webhook URL configured for notifications.")
            return

        payload = {
            "content": f"[{level.upper()}] SuperAI: {message}"
        }
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            response.raise_for_status()
            logger.info(f"Notification sent successfully: {message}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

class WebhookHandler(BaseHTTPRequestHandler):
    steerage_callback: Callable[[str], None] = None

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            command = data.get('command', '')
            
            if command and self.steerage_callback:
                self.steerage_callback(command)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "acknowledged"}).encode('utf-8'))
            else:
                self.send_response(400)
                self.end_headers()
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()

class WebhookServer:
    def __init__(self, port: int = 8080):
        self.port = port
        self.server = None
        self.server_thread = None

    def start(self, callback: Callable[[str], None]):
        """Accept steerage commands via webhooks."""
        WebhookHandler.steerage_callback = callback
        self.server = HTTPServer(('0.0.0.0', self.port), WebhookHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        logger.info(f"Webhook server started on port {self.port}")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("Webhook server stopped.")

class RemoteControl:
    """Facade for Phase 6: Remote Control & Messaging Webhooks."""
    def __init__(self, webhook_url: str = "", port: int = 8080):
        self.notifier = NotificationClient(webhook_url)
        self.server = WebhookServer(port)

    def start_receiving(self, callback: Callable[[str], None]):
        self.server.start(callback)

    def notify(self, message: str, level: str = "info"):
        self.notifier.send_notification(message, level)

    def stop(self):
        self.server.stop()
