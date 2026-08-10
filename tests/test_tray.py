import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from unittest.mock import patch, MagicMock
from cli.tray import SuperAITray

class TestSuperAITray(unittest.TestCase):
    @patch('cli.tray.pystray.Icon')
    def test_tray_initialization_and_run(self, mock_icon_class):
        mock_icon_instance = MagicMock()
        mock_icon_class.return_value = mock_icon_instance

        tray = SuperAITray()
        tray.run()
        
        # Verify Icon is initialized
        mock_icon_class.assert_called_once()
        # Verify run is called
        mock_icon_instance.run.assert_called_once()

    @patch('cli.tray.webbrowser.open')
    def test_open_console(self, mock_open):
        tray = SuperAITray()
        tray._open_console(None, None)
        mock_open.assert_called_once_with("http://127.0.0.1:8000/console")

    def test_exit_app(self):
        tray = SuperAITray()
        mock_icon_instance = MagicMock()
        tray.icon = mock_icon_instance
        
        tray._exit_app(None, None)
        mock_icon_instance.stop.assert_called_once()

if __name__ == '__main__':
    unittest.main()
