#!/usr/bin/env python3
"""
VinylFlow Desktop Launcher (Windows-only)

Runs VinylFlow as a native Windows desktop application:
- Enforces single instance via a named mutex
- Starts the FastAPI backend on a dynamic port
- Opens a pywebview window (WebView2 / edgechromium)
- Persists and restores window geometry
- Integrates system tray and auto-update checker
"""

import ctypes
import ctypes.wintypes
import json
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from socket import create_connection

import uvicorn

# Must be set before `import webview` so pywebview picks the correct backend.
os.environ.setdefault("PYWEBVIEW_GUI", "edgechromium")

# Point requests/urllib3 at the bundled certifi CA bundle when running from a
# PyInstaller one-folder bundle.  The runtime hook already does this, but we
# repeat it here in case the launcher is run outside a bundle (development).
def _configure_ssl_certs() -> None:
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return
    cacert = Path(meipass) / "certifi" / "cacert.pem"
    if cacert.exists():
        os.environ.setdefault("SSL_CERT_FILE", str(cacert))
        os.environ.setdefault("REQUESTS_CA_BUNDLE", str(cacert))

_configure_ssl_certs()

try:
    import webview
    _WEBVIEW_IMPORT_ERROR: Exception | None = None
except Exception as exc:
    webview = None
    _WEBVIEW_IMPORT_ERROR = exc


logger = logging.getLogger(__name__)

APP_NAME = "VinylFlow"
MUTEX_NAME = "Global\\VinylFlow_SingleInstance_Mutex"

# ---------------------------------------------------------------------------
# Icon path helper
# ---------------------------------------------------------------------------

def _icon_path() -> str:
    """Return the path to VinylFlow.ico, works in dev and bundled modes."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        p = Path(meipass) / "assets" / "VinylFlow.ico"
        if p.exists():
            return str(p)
    p = Path(__file__).parent / "assets" / "VinylFlow.ico"
    if p.exists():
        return str(p)
    return ""

# ---------------------------------------------------------------------------
# Single-instance enforcement
# ---------------------------------------------------------------------------

_mutex_handle = None


def _acquire_single_instance() -> bool:
    """Try to acquire a named mutex.  Returns True if this is the first instance."""
    global _mutex_handle
    kernel32 = ctypes.windll.kernel32
    _mutex_handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = ctypes.get_last_error()
    # ERROR_ALREADY_EXISTS = 183
    if last_error == 183:
        kernel32.CloseHandle(_mutex_handle)
        _mutex_handle = None
        return False
    return True


def _show_already_running_message() -> None:
    ctypes.windll.user32.MessageBoxW(
        0,
        "VinylFlow is already running.\n\nCheck your system tray for the VinylFlow icon.",
        "VinylFlow",
        0x00000040,  # MB_ICONINFORMATION
    )


# ---------------------------------------------------------------------------
# Window state persistence
# ---------------------------------------------------------------------------

def _settings_path() -> Path:
    config_dir = os.getenv("VINYLFLOW_CONFIG_DIR")
    if config_dir:
        return Path(config_dir) / "settings.json"
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME / "config" / "settings.json"
    return Path.home() / "AppData" / "Roaming" / APP_NAME / "config" / "settings.json"


def _load_settings() -> dict:
    path = _settings_path()
    if path.exists():
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_settings(settings: dict) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save settings: {e}")


def _load_window_state() -> dict:
    settings = _load_settings()
    return settings.get("window", {"width": 1280, "height": 900})


def _save_window_state(window) -> None:
    try:
        settings = _load_settings()
        settings["window"] = {
            "x": window.x,
            "y": window.y,
            "width": window.width,
            "height": window.height,
        }
        _save_settings(settings)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Desktop API exposed to frontend via window.pywebview.api
# ---------------------------------------------------------------------------

class DesktopApi:
    def __init__(self):
        self._window = None
        self._tray = None
        self._server_port = 8000

    def set_window(self, window):
        self._window = window

    def set_tray(self, tray):
        self._tray = tray

    def set_server_port(self, port: int):
        self._server_port = port

    def select_output_folder(self, initial_path: str = "") -> str | None:
        if webview is None:
            return None
        try:
            directory = None
            if initial_path:
                candidate = Path(initial_path).expanduser()
                if candidate.exists() and candidate.is_dir():
                    directory = str(candidate)

            window = webview.windows[0]
            dialog_type = webview.FOLDER_DIALOG
            if hasattr(webview, "FileDialog") and hasattr(webview.FileDialog, "FOLDER"):
                dialog_type = webview.FileDialog.FOLDER

            result = window.create_file_dialog(dialog_type, directory=directory)
            if not result:
                return None

            return str(result[0])
        except Exception:
            return None

    def select_input_files(self) -> list[str] | None:
        """Open a native Windows file dialog filtered to supported audio formats."""
        if webview is None:
            return None
        try:
            window = webview.windows[0]
            file_types = ("Audio Files (*.wav;*.aiff;*.aif;*.flac)",)

            dialog_type = webview.OPEN_DIALOG
            if hasattr(webview, "FileDialog") and hasattr(webview.FileDialog, "OPEN"):
                dialog_type = webview.FileDialog.OPEN

            result = window.create_file_dialog(
                dialog_type,
                allow_multiple=True,
                file_types=file_types,
            )
            if not result:
                return None
            return [str(p) for p in result]
        except Exception:
            return None

    def open_folder(self, path: str) -> bool:
        """Open a folder in Windows Explorer."""
        try:
            os.startfile(path)
            return True
        except Exception:
            return False

    def reveal_in_explorer(self, path: str) -> bool:
        """Highlight a file in Windows Explorer."""
        try:
            subprocess.Popen(["explorer", "/select,", path])
            return True
        except Exception:
            return False

    def get_app_version(self) -> str:
        from version import __version__
        return __version__

    def open_url(self, url: str) -> bool:
        """Open a URL in the default browser."""
        try:
            os.startfile(url)
            return True
        except Exception:
            return False

    def minimize_to_tray(self) -> None:
        """Hide the window and keep running in the system tray."""
        if self._window:
            self._window.hide()

    def notify(self, title: str, message: str) -> None:
        """Show a system tray notification."""
        if self._tray:
            self._tray.show_notification(title, message)


# ---------------------------------------------------------------------------
# Environment & path setup
# ---------------------------------------------------------------------------

def _windows_app_support_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    return Path.home() / "AppData" / "Roaming" / APP_NAME


def _bundled_ffmpeg_path() -> Path | None:
    """Return path to bundled ffmpeg.exe, or None if not found."""
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return None
    path = Path(meipass) / "ffmpeg_bin" / "ffmpeg.exe"
    if path.exists() and path.is_file():
        return path
    return None


def _check_webview2_available() -> bool:
    """Return True if the Microsoft WebView2 Runtime is installed."""
    try:
        import winreg
        client_guid = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
        subkeys = [
            rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{client_guid}",
            rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{client_guid}",
        ]
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for subkey in subkeys:
                try:
                    with winreg.OpenKey(hive, subkey):
                        return True
                except OSError:
                    pass
    except Exception:
        pass
    return False


def _find_available_port(start: int = 8000, end: int = 8100) -> int:
    """Find the first available port in the given range."""
    import socket
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return start  # fallback


def configure_desktop_environment() -> tuple[str, int]:
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
    os.environ.setdefault("HOST", "127.0.0.1")
    os.environ.setdefault("AUTO_OPEN_BROWSER", "0")

    bundled_ffmpeg = _bundled_ffmpeg_path()
    if bundled_ffmpeg:
        bundled_ffmpeg_str = str(bundled_ffmpeg)
        os.environ.setdefault("VINYLFLOW_FFMPEG_PATH", bundled_ffmpeg_str)
        os.environ.setdefault("FFMPEG_BINARY", bundled_ffmpeg_str)
        os.environ.setdefault("IMAGEIO_FFMPEG_EXE", bundled_ffmpeg_str)

        ffmpeg_dir = str(bundled_ffmpeg.parent)
        current_path = os.environ.get("PATH", "")
        path_parts = [p for p in current_path.split(os.pathsep) if p]
        if ffmpeg_dir not in path_parts:
            os.environ["PATH"] = os.pathsep.join([ffmpeg_dir, *path_parts])

    host = os.environ["HOST"]
    port = _find_available_port()
    os.environ["PORT"] = str(port)
    return host, port


# ---------------------------------------------------------------------------
# Server management
# ---------------------------------------------------------------------------

def _run_server(host: str, port: int) -> None:
    from backend.api import app
    uvicorn.run(app, host=host, port=port)


def _wait_for_server(host: str, port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


# ---------------------------------------------------------------------------
# Auto-update (background)
# ---------------------------------------------------------------------------

def _check_update_background(window) -> None:
    """Check for updates in a background thread; push banner via JS if available."""
    try:
        from updater import check_for_update
        result = check_for_update()
        if result and result.get("update_available"):
            version = result["latest_version"]
            url = result["download_url"]
            js = (
                f"if(window._vinylflowShowUpdateBanner) "
                f"window._vinylflowShowUpdateBanner('{version}','{url}');"
            )
            window.evaluate_js(js)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# File associations / command-line args
# ---------------------------------------------------------------------------

def _post_files_to_server(host: str, port: int, file_paths: list[str]) -> None:
    """POST local file paths to /api/upload-local after the server is ready."""
    import requests as req
    try:
        url = f"http://{host}:{port}/api/upload-local"
        req.post(url, json={"file_paths": file_paths}, timeout=10)
    except Exception as e:
        logger.warning(f"Failed to post files to server: {e}")


def _post_files_to_running_instance(file_paths: list[str]) -> None:
    """Try to POST file paths to an already-running VinylFlow instance."""
    import requests as req
    # Scan ports 8000-8099 for a running instance
    for port in range(8000, 8100):
        try:
            url = f"http://127.0.0.1:{port}/api/open-files"
            resp = req.post(url, json={"file_paths": file_paths}, timeout=2)
            if resp.status_code == 200:
                return
        except Exception:
            continue


def _collect_argv_files() -> list[str]:
    """Collect file paths from sys.argv (passed by Windows shell associations)."""
    files = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.exists() and p.is_file() and p.suffix.lower() in {".wav", ".aiff", ".aif", ".flac"}:
            files.append(str(p.resolve()))
    return files


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    argv_files = _collect_argv_files()

    # Single-instance check
    if not _acquire_single_instance():
        if argv_files:
            _post_files_to_running_instance(argv_files)
        else:
            _show_already_running_message()
        sys.exit(0)

    host, port = configure_desktop_environment()
    server_thread = threading.Thread(target=lambda: _run_server(host, port), daemon=True)
    server_thread.start()

    if not _wait_for_server(host, port):
        ctypes.windll.user32.MessageBoxW(
            0,
            f"VinylFlow backend failed to start on http://{host}:{port}",
            "VinylFlow — Startup Error",
            0x00000010,  # MB_ICONERROR
        )
        sys.exit(1)

    app_url = f"http://{host}:{port}"

    # Post any files passed via command line
    if argv_files:
        threading.Thread(
            target=lambda: _post_files_to_server(host, port, argv_files),
            daemon=True,
        ).start()

    # Check pywebview
    if webview is None:
        ctypes.windll.user32.MessageBoxW(
            0,
            f"pywebview is not available ({_WEBVIEW_IMPORT_ERROR}).\n\n"
            "Please reinstall VinylFlow or install pywebview manually.",
            "VinylFlow — Missing Dependency",
            0x00000010,
        )
        sys.exit(1)

    # Check WebView2
    if not _check_webview2_available():
        ctypes.windll.user32.MessageBoxW(
            0,
            "Microsoft WebView2 Runtime is required but was not found.\n\n"
            "Please download it from:\n"
            "https://developer.microsoft.com/microsoft-edge/webview2/",
            "VinylFlow — WebView2 Required",
            0x00000010,
        )
        sys.exit(1)

    # Load saved window state
    win_state = _load_window_state()

    desktop_api = DesktopApi()
    desktop_api.set_server_port(port)

    window = webview.create_window(
        "VinylFlow",
        app_url,
        width=win_state.get("width", 1280),
        height=win_state.get("height", 900),
        x=win_state.get("x"),
        y=win_state.get("y"),
        min_size=(900, 700),
        js_api=desktop_api,
    )

    desktop_api.set_window(window)

    # System tray
    tray = None
    icon = _icon_path()

    def on_tray_show():
        if window:
            window.show()
            window.restore()

    def on_tray_quit():
        if window:
            window.destroy()

    try:
        from system_tray import SystemTray
        tray = SystemTray(icon, on_show=on_tray_show, on_quit=on_tray_quit)
        tray.start()
        desktop_api.set_tray(tray)
    except Exception as e:
        logger.warning(f"System tray unavailable: {e}")

    # Save window state on close & start update check after load
    def on_loaded():
        threading.Thread(target=lambda: _check_update_background(window), daemon=True).start()

    def on_closing():
        _save_window_state(window)
        if tray:
            tray.stop()

    window.events.loaded += on_loaded
    window.events.closing += on_closing

    webview.start(gui="edgechromium")


if __name__ == "__main__":
    main()
