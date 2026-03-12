"""
VinylFlow - System Tray Icon

Provides a Windows system tray icon with menu using pystray.
Supports show/hide window and quit actions, plus toast notifications.
"""

import logging
import threading
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    import pystray
    from PIL import Image
    _PYSTRAY_AVAILABLE = True
except ImportError:
    _PYSTRAY_AVAILABLE = False


class SystemTray:
    """Windows system tray icon for VinylFlow."""

    def __init__(
        self,
        icon_path: str,
        on_show: Callable,
        on_quit: Callable,
    ):
        self._icon_path = icon_path
        self._on_show = on_show
        self._on_quit = on_quit
        self._icon: Optional["pystray.Icon"] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if not _PYSTRAY_AVAILABLE:
            logger.warning("pystray not available — system tray disabled")
            return

        try:
            image = Image.open(self._icon_path)
        except Exception:
            # Fallback: 16x16 amber square
            image = Image.new("RGB", (16, 16), color=(229, 161, 0))

        menu = pystray.Menu(
            pystray.MenuItem("Show VinylFlow", self._show_action, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit_action),
        )

        self._icon = pystray.Icon("VinylFlow", image, "VinylFlow", menu)
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    def show_notification(self, title: str, message: str) -> None:
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception as e:
                logger.debug(f"Tray notification failed: {e}")

    def _show_action(self, icon, item) -> None:
        self._on_show()

    def _quit_action(self, icon, item) -> None:
        self.stop()
        self._on_quit()
