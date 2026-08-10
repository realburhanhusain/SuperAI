import webbrowser
from PIL import Image, ImageDraw
import pystray

class SuperAITray:
    def __init__(self, console_url="http://127.0.0.1:8000/console"):
        self.console_url = console_url
        self.icon = None

    def _create_image(self, width, height, color1, color2):
        # Generate an image for the tray icon
        image = Image.new('RGB', (width, height), color1)
        dc = ImageDraw.Draw(image)
        dc.rectangle(
            (width // 2, 0, width, height // 2),
            fill=color2)
        dc.rectangle(
            (0, height // 2, width // 2, height),
            fill=color2)
        return image

    def _open_console(self, icon, item):
        webbrowser.open(self.console_url)

    def _exit_app(self, icon, item):
        self.stop()

    def run(self):
        menu = pystray.Menu(
            pystray.MenuItem('SuperAI Status: Online', None, enabled=False),
            pystray.MenuItem('Open Management Console', self._open_console),
            pystray.MenuItem('Exit', self._exit_app)
        )
        image = self._create_image(64, 64, 'black', 'white')
        self.icon = pystray.Icon("superai", image, "SuperAI", menu)
        self.icon.run()

    def stop(self):
        if self.icon:
            self.icon.stop()
