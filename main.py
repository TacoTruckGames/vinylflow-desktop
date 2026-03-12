#!/usr/bin/env python3
"""
VinylFlow Desktop Application (Windows-only)

Native PySide6 desktop app for vinyl record digitization.
Single-instance via Win32 mutex with inter-process file forwarding.
"""

import ctypes
import ctypes.wintypes
import logging
import os
import sys
from pathlib import Path

from audio_processor import SUPPORTED_INPUT_EXTENSIONS

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("VinylFlow")

APP_NAME = "VinylFlow"
MUTEX_NAME = "Global\\VinylFlow_SingleInstance_Mutex"
LOCAL_SERVER_NAME = "VinylFlow_LocalServer"

# ---------------------------------------------------------------------------
# SSL certs (bundled builds)
# ---------------------------------------------------------------------------

def _configure_ssl_certs() -> None:
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return
    cacert = Path(meipass) / "certifi" / "cacert.pem"
    if cacert.exists():
        os.environ.setdefault("SSL_CERT_FILE", str(cacert))
        os.environ.setdefault("REQUESTS_CA_BUNDLE", str(cacert))

_configure_ssl_certs()

# ---------------------------------------------------------------------------
# Single-instance enforcement (Win32 mutex)
# ---------------------------------------------------------------------------

_mutex_handle = None


def _acquire_single_instance() -> bool:
    global _mutex_handle
    kernel32 = ctypes.windll.kernel32
    _mutex_handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = ctypes.get_last_error()
    if last_error == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(_mutex_handle)
        _mutex_handle = None
        return False
    return True


def _collect_argv_files() -> list[str]:
    files = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.exists() and p.is_file() and p.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS:
            files.append(str(p.resolve()))
    return files


# ---------------------------------------------------------------------------
# Environment setup (ported from desktop_launcher.py)
# ---------------------------------------------------------------------------

def _windows_app_support_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    return Path.home() / "AppData" / "Roaming" / APP_NAME


def _bundled_ffmpeg_path() -> Path | None:
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return None
    path = Path(meipass) / "ffmpeg_bin" / "ffmpeg.exe"
    if path.exists() and path.is_file():
        return path
    return None


def _find_system_ffmpeg() -> Path | None:
    """Find ffmpeg.exe on PATH or in common Windows install locations."""
    import shutil
    which = shutil.which("ffmpeg")
    if which:
        return Path(which)

    # Common install paths (winget, chocolatey, manual)
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages",
        Path("C:/ProgramData/chocolatey/bin"),
        Path("C:/ffmpeg/bin"),
    ]
    for base in candidates:
        if not base.exists():
            continue
        for match in base.rglob("ffmpeg.exe"):
            return match
    return None


def configure_desktop_environment():
    app_data_dir = _windows_app_support_dir()

    config_dir = app_data_dir / "config"
    upload_dir = app_data_dir / "temp_uploads"
    output_dir = Path.home() / "Music" / APP_NAME

    config_dir.mkdir(parents=True, exist_ok=True)
    upload_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("VINYLFLOW_CONFIG_DIR", str(config_dir))
    os.environ.setdefault("VINYLFLOW_UPLOAD_DIR", str(upload_dir))
    os.environ.setdefault("DEFAULT_OUTPUT_DIR", str(output_dir))

    bundled_ffmpeg = _bundled_ffmpeg_path()
    if not bundled_ffmpeg:
        # Dev mode: find ffmpeg on PATH or in common install locations
        bundled_ffmpeg = _find_system_ffmpeg()
    if bundled_ffmpeg:
        bundled_str = str(bundled_ffmpeg)
        os.environ.setdefault("VINYLFLOW_FFMPEG_PATH", bundled_str)
        os.environ.setdefault("FFMPEG_BINARY", bundled_str)
        os.environ.setdefault("IMAGEIO_FFMPEG_EXE", bundled_str)

        ffmpeg_dir = str(bundled_ffmpeg.parent)
        current_path = os.environ.get("PATH", "")
        path_parts = [p for p in current_path.split(os.pathsep) if p]
        if ffmpeg_dir not in path_parts:
            os.environ["PATH"] = os.pathsep.join([ffmpeg_dir, *path_parts])


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    argv_files = _collect_argv_files()

    # Single-instance check
    if not _acquire_single_instance():
        if argv_files:
            # Forward files to running instance via QLocalSocket
            _send_files_to_running_instance(argv_files)
        else:
            ctypes.windll.user32.MessageBoxW(
                0,
                "VinylFlow is already running.\n\nCheck your system tray for the VinylFlow icon.",
                "VinylFlow",
                0x00000040,
            )
        sys.exit(0)

    configure_desktop_environment()

    # Import Qt after environment is configured
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from PySide6.QtNetwork import QLocalServer, QLocalSocket

    from config import Config
    from ui.styles import get_stylesheet
    from ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(get_stylesheet())

    # Initialize config
    config = Config()

    # Create main window
    window = MainWindow(config)
    window.show()

    # Load files from command line
    if argv_files:
        QTimer.singleShot(500, lambda: window.files_received.emit(argv_files))

    # Inter-process file forwarding via QLocalServer
    server = QLocalServer(app)
    server.removeServer(LOCAL_SERVER_NAME)  # clean up stale socket

    def on_new_connection():
        socket = server.nextPendingConnection()
        if socket:
            socket.waitForReadyRead(3000)
            data = socket.readAll().data().decode("utf-8", errors="replace")
            if data:
                paths = [p for p in data.split("\n") if p.strip()]
                if paths:
                    window.files_received.emit(paths)
            socket.disconnectFromServer()

    server.newConnection.connect(on_new_connection)
    if not server.listen(LOCAL_SERVER_NAME):
        logger.warning(f"Could not start local server: {server.errorString()}")

    sys.exit(app.exec())


def _send_files_to_running_instance(file_paths: list[str]):
    """Send file paths to a running instance via QLocalSocket."""
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtNetwork import QLocalSocket

        # Need a QApplication for event loop
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)

        socket = QLocalSocket()
        socket.connectToServer(LOCAL_SERVER_NAME)
        if socket.waitForConnected(3000):
            data = "\n".join(file_paths)
            socket.write(data.encode("utf-8"))
            socket.flush()
            socket.waitForBytesWritten(3000)
            socket.disconnectFromServer()
    except Exception as e:
        logger.warning(f"Failed to forward files: {e}")


if __name__ == "__main__":
    main()
