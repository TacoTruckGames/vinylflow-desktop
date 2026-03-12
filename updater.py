"""
VinylFlow - Auto-Update Checker

Checks GitHub releases for newer versions and notifies the user.
Only checks once per 24 hours to avoid excessive API calls.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests

from version import __version__

logger = logging.getLogger(__name__)

GITHUB_REPO = "TacoTruckGames/vinylflow-desktop"
CHECK_INTERVAL_HOURS = 24


def _settings_path() -> Path:
    import os
    config_dir = os.getenv("VINYLFLOW_CONFIG_DIR")
    if config_dir:
        return Path(config_dir) / "settings.json"
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "VinylFlow" / "config" / "settings.json"
    return Path.home() / "AppData" / "Roaming" / "VinylFlow" / "config" / "settings.json"


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


def _should_check() -> bool:
    settings = _load_settings()
    last_check = settings.get("last_update_check")
    if not last_check:
        return True
    try:
        last_dt = datetime.fromisoformat(last_check)
        return datetime.now() - last_dt > timedelta(hours=CHECK_INTERVAL_HOURS)
    except (ValueError, TypeError):
        return True


def _parse_version(version_str: str) -> tuple:
    """Parse version string like 'v1.2.3' or '1.2.3' into a comparable tuple."""
    v = version_str.lstrip("v").strip()
    parts = []
    for part in v.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def check_for_update() -> Optional[dict]:
    """Check GitHub for a newer release.

    Returns:
        dict with keys {update_available, latest_version, download_url, release_notes}
        or None if check was skipped or failed.
    """
    if not _should_check():
        return None

    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        response = requests.get(url, timeout=10, headers={"Accept": "application/vnd.github.v3+json"})

        # Record that we checked
        settings = _load_settings()
        settings["last_update_check"] = datetime.now().isoformat()
        _save_settings(settings)

        if response.status_code != 200:
            logger.debug(f"GitHub API returned {response.status_code}")
            return None

        data = response.json()
        latest_version = data.get("tag_name", "")
        current_tuple = _parse_version(__version__)
        latest_tuple = _parse_version(latest_version)

        update_available = latest_tuple > current_tuple

        # Find the installer asset URL, fall back to HTML release page
        download_url = data.get("html_url", "")
        for asset in data.get("assets", []):
            if "Setup" in asset.get("name", "") and asset["name"].endswith(".exe"):
                download_url = asset["browser_download_url"]
                break

        return {
            "update_available": update_available,
            "latest_version": latest_version,
            "download_url": download_url,
            "release_notes": data.get("body", ""),
        }

    except Exception as e:
        logger.debug(f"Update check failed: {e}")
        return None
