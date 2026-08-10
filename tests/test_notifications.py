import unittest
from unittest.mock import patch, MagicMock
import sys
import io

from src.core.notifications import NotificationManager

class TestNotificationManager(unittest.TestCase):
    @patch('src.core.notifications.requests.post')
    @patch('src.core.notifications.config.get')
    def test_send_notification_with_webhook(self, mock_config_get, mock_post):
        mock_config_get.return_value = "http://test.webhook"
        mock_response = MagicMock()
        mock_post.return_value = mock_response

        # Capture stdout
        captured_output = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            manager = NotificationManager()
            manager.send_notification("Test Title", "Test Message")
        finally:
            sys.stdout = original_stdout

        output = captured_output.getvalue()
        
        # Check print output
        self.assertIn("[NOTIFICATION] Test Title: Test Message", output)
        self.assertIn("\a", output)
        
        # Check webhook post
        mock_post.assert_called_once_with(
            "http://test.webhook",
            json={"title": "Test Title", "message": "Test Message"},
            timeout=5.0
        )
        mock_response.raise_for_status.assert_called_once()

    @patch('src.core.notifications.requests.post')
    @patch('src.core.notifications.config.get')
    def test_send_notification_no_webhook(self, mock_config_get, mock_post):
        mock_config_get.return_value = None

        captured_output = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            manager = NotificationManager()
            manager.send_notification("No Webhook", "Hello")
        finally:
            sys.stdout = original_stdout

        output = captured_output.getvalue()
        
        self.assertIn("[NOTIFICATION] No Webhook: Hello", output)
        self.assertIn("\a", output)
        
        mock_post.assert_not_called()
