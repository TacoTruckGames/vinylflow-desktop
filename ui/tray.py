"""
VinylFlow - System Tray Icon (PySide6)

QSystemTrayIcon wrapper with show/quit menu and balloon notifications.
"""

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


def _icon_path() -> str:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        p = Path(meipass) / "assets" / "VinylFlow.ico"
        if p.exists():
            return str(p)
    p = Path(__file__).parent.parent / "assets" / "VinylFlow.ico"
    if p.exists():
        return str(p)
    return ""


class TrayIcon(QSystemTrayIcon):
    """System tray icon for VinylFlow."""

    def __init__(self, parent=None):
        icon_file = _icon_path()
        icon = QIcon(icon_file) if icon_file else QIcon()
        super().__init__(icon, parent)

        self.setToolTip("VinylFlow")

        menu = QMenu()
        show_action = menu.addAction("Show VinylFlow")
        show_action.triggered.connect(self._on_show)
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self._on_quit)
        self.setContextMenu(menu)

        self.activated.connect(self._on_activated)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._on_show()

    def _on_show(self):
        window = self.parent()
        if window:
            window.show()
            window.raise_()
            window.activateWindow()

    def _on_quit(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()

    def notify(self, title: str, message: str):
        if self.supportsMessages():
            self.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 5000)
