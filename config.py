"""
VinylFlow - Configuration Management

Loads settings from settings.json / .env / environment variables.
Handles Discogs API credentials, audio processing parameters, and output settings.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Configuration manager for VinylFlow."""

    def __init__(self, env_path=None, settings_path=None):
        """
        Initialize configuration with fallback chain:
        1. settings.json (persistent, user-editable via UI)
        2. .env file (backward compatibility)
        3. Environment variables

        Args:
            env_path: Optional path to .env file. If None, looks in current directory.
            settings_path: Optional path to settings.json. If None, uses config/settings.json.
        """
        # Store paths for reload
        if env_path is None:
            env_path = Path(__file__).parent / ".env"
        else:
            env_path = Path(env_path)

        if settings_path is None:
            config_dir_env = os.getenv("VINYLFLOW_CONFIG_DIR")
            if config_dir_env:
                settings_path = Path(config_dir_env) / "settings.json"
            else:
                settings_path = Path(__file__).parent / "config" / "settings.json"
        else:
            settings_path = Path(settings_path)

        self._env_path = env_path
        self._settings_path = settings_path

        # Load .env file if it exists
        if env_path.exists():
            load_dotenv(env_path, override=True)

        # Load JSON settings (takes precedence over .env)
        json_settings = self._load_from_json(settings_path)

        # Discogs API settings (priority: JSON > env var > default)
        self.discogs_token = (
            json_settings.get('DISCOGS_USER_TOKEN') or
            os.getenv("DISCOGS_USER_TOKEN", "")
        )
        self.discogs_user_agent = (
            json_settings.get('DISCOGS_USER_AGENT') or
            os.getenv("DISCOGS_USER_AGENT", "VinylFlow/1.0")
        )

        # Output settings — default to ~/Music/VinylFlow
        self.default_output_dir = (
            json_settings.get('DEFAULT_OUTPUT_DIR') or
            os.getenv("DEFAULT_OUTPUT_DIR", str(Path.home() / "Music" / "VinylFlow"))
        )

        # Audio processing settings
        self.default_silence_threshold = float(os.getenv("DEFAULT_SILENCE_THRESHOLD", "-40"))
        self.default_min_silence_duration = float(os.getenv("DEFAULT_MIN_SILENCE_DURATION", "1.5"))
        self.default_min_track_length = float(os.getenv("DEFAULT_MIN_TRACK_LENGTH", "30"))
        self.default_flac_compression = int(os.getenv("DEFAULT_FLAC_COMPRESSION", "8"))

        # Temp file management
        self.temp_ttl_hours = float(os.getenv("TEMP_TTL_HOURS", "2"))

    def validate(self):
        """
        Validate configuration.

        Returns:
            tuple: (is_valid, error_message)
        """
        if not self.discogs_token:
            return False, "DISCOGS_USER_TOKEN not set"

        if self.default_flac_compression < 0 or self.default_flac_compression > 8:
            return False, "FLAC compression level must be between 0 and 8"

        if self.default_silence_threshold > 0:
            return False, "Silence threshold should be negative (dB)"

        if self.default_min_silence_duration <= 0:
            return False, "Minimum silence duration must be positive"

        if self.default_min_track_length <= 0:
            return False, "Minimum track length must be positive"

        if self.temp_ttl_hours <= 0:
            return False, "Temp file TTL must be positive"

        return True, None

    def test_discogs_connection(self):
        """
        Test Discogs API connection with current token.

        Returns:
            tuple: (success, message)
        """
        try:
            import discogs_client

            client = discogs_client.Client(self.discogs_user_agent, user_token=self.discogs_token)
            identity = client.identity()
            return True, f"Connected as: {identity.username}"
        except Exception as e:
            return False, f"Discogs connection failed: {str(e)}"

    def _load_from_json(self, settings_path: Path) -> dict:
        """Load settings from JSON file if it exists."""
        if settings_path.exists():
            try:
                with open(settings_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load settings.json: {e}")
        return {}

    def _save_json(self, updates: dict) -> bool:
        """Merge updates into settings.json and write."""
        settings_path = Path(self._settings_path)
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        settings = {}
        if settings_path.exists():
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
            except Exception:
                pass

        settings.update(updates)

        try:
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save settings: {e}")
            return False

    def save_token(self, token: str, user_agent: str = None) -> bool:
        """Save Discogs token to settings.json."""
        updates = {'DISCOGS_USER_TOKEN': token}
        if user_agent:
            updates['DISCOGS_USER_AGENT'] = user_agent
        return self._save_json(updates)

    def save_output_dir(self, output_dir: str) -> bool:
        """Save default output directory to settings.json."""
        return self._save_json({'DEFAULT_OUTPUT_DIR': output_dir})

    # ------------------------------------------------------------------
    # Window state persistence
    # ------------------------------------------------------------------

    def save_window_state(self, x: int, y: int, width: int, height: int) -> bool:
        """Save window geometry to settings.json under the 'window' key."""
        return self._save_json({"window": {"x": x, "y": y, "width": width, "height": height}})

    def load_window_state(self) -> dict:
        """Return saved window geometry or defaults."""
        settings = self._load_from_json(Path(self._settings_path))
        return settings.get("window", {"width": 1280, "height": 900})

    def reload(self):
        """Reload configuration from all sources."""
        self.__init__(env_path=self._env_path, settings_path=self._settings_path)

    def __repr__(self):
        """String representation of config (safe — no token)."""
        return (
            f"Config(\n"
            f"  discogs_token={'*' * len(self.discogs_token) if self.discogs_token else 'NOT SET'},\n"
            f"  output_dir={self.default_output_dir},\n"
            f"  silence_threshold={self.default_silence_threshold}dB,\n"
            f"  min_silence_duration={self.default_min_silence_duration}s,\n"
            f"  min_track_length={self.default_min_track_length}s,\n"
            f"  flac_compression={self.default_flac_compression},\n"
            f"  temp_ttl_hours={self.temp_ttl_hours}h\n"
            f")"
        )
