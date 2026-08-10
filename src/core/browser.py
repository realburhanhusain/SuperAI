import urllib.request
from html.parser import HTMLParser

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_content = []
        self.ignore_tags = {'script', 'style', 'head', 'meta', 'link'}
        self.in_ignored_tag = False
        self.ignored_tag_name = ""

    def handle_starttag(self, tag, attrs):
        if tag in self.ignore_tags:
            self.in_ignored_tag = True
            self.ignored_tag_name = tag

    def handle_endtag(self, tag):
        if self.in_ignored_tag and tag == self.ignored_tag_name:
            self.in_ignored_tag = False
            self.ignored_tag_name = ""

    def handle_data(self, data):
        if not self.in_ignored_tag:
            text = data.strip()
            if text:
                self.text_content.append(text)

    def get_text(self):
        return ' '.join(self.text_content)


class BrowserAutomation:
    def __init__(self):
        self.use_playwright = PLAYWRIGHT_AVAILABLE

    def read_page(self, url: str) -> str:
        if self.use_playwright:
            return self._read_with_playwright(url)
        else:
            return self._read_with_urllib(url)

    def _read_with_playwright(self, url: str) -> str:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)
            content = page.locator("body").inner_text()
            browser.close()
            return content

    def _read_with_urllib(self, url: str) -> str:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
            extractor = TextExtractor()
            extractor.feed(html)
            return extractor.get_text()
