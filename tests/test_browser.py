import unittest
from unittest.mock import patch, MagicMock
from src.core.browser import BrowserAutomation, TextExtractor

class TestBrowserAutomation(unittest.TestCase):

    def test_text_extractor(self):
        html = "<html><body><h1>Hello</h1><script>var x = 1;</script><p>World</p></body></html>"
        extractor = TextExtractor()
        extractor.feed(html)
        self.assertEqual(extractor.get_text(), "Hello World")

    @patch('src.core.browser.urllib.request.urlopen')
    def test_read_page_fallback(self, mock_urlopen):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html><body><p>Fallback Content</p></body></html>"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        browser = BrowserAutomation()
        # Explicitly force fallback for this test
        browser.use_playwright = False
        
        content = browser.read_page("http://example.com")
        self.assertEqual(content, "Fallback Content")
        mock_urlopen.assert_called_once()

    @patch('src.core.browser.sync_playwright', create=True)
    def test_read_page_playwright(self, mock_sync_playwright):
        # Setup playwright mock
        mock_p = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_locator = MagicMock()
        
        mock_sync_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        mock_page.locator.return_value = mock_locator
        mock_locator.inner_text.return_value = "Playwright Content"

        browser = BrowserAutomation()
        browser.use_playwright = True  # Force playwright

        content = browser.read_page("http://example.com")
        
        self.assertEqual(content, "Playwright Content")
        mock_page.goto.assert_called_once_with("http://example.com")
        mock_browser.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()
