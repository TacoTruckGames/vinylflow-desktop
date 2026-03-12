"""
VinylFlow - Waveform Peak Generation Worker

Runs FFmpeg + numpy peak extraction in a background QThread.
"""

import json
import subprocess
from pathlib import Path

import numpy as np
from PySide6.QtCore import QThread, Signal

from audio_processor import _ffmpeg


class WaveformWorker(QThread):
    """Background thread to generate waveform peak data."""

    finished = Signal(list, float)  # peaks, duration
    error = Signal(str)

    def __init__(self, file_path: str, duration: float, target_peaks: int = 3000):
        super().__init__()
        self.file_path = Path(file_path)
        self.duration = duration
        self.target_peaks = target_peaks

    def run(self):
        try:
            # Check for cached peaks
            cache_path = self.file_path.parent / "peaks.json"
            if cache_path.exists():
                with open(cache_path, "r") as f:
                    cached = json.load(f)
                    self.finished.emit(cached["peaks"], cached["duration"])
                    return

            # Extract raw PCM mono audio at 8kHz
            cmd = [
                _ffmpeg(),
                "-i", str(self.file_path),
                "-f", "s16le",
                "-acodec", "pcm_s16le",
                "-ac", "1",
                "-ar", "8000",
                "-",
            ]
            result = subprocess.run(cmd, capture_output=True, check=True)
            audio_data = np.frombuffer(result.stdout, dtype=np.int16)

            samples_per_peak = max(1, len(audio_data) // self.target_peaks)
            peaks = []
            for i in range(0, len(audio_data), samples_per_peak):
                chunk = audio_data[i:i + samples_per_peak]
                if len(chunk) > 0:
                    peak_value = float(np.max(np.abs(chunk)))
                    peaks.append(peak_value / 32768.0)

            if not peaks:
                peaks = [0.0]

            # Cache peaks
            cache_data = {"peaks": peaks, "duration": self.duration}
            try:
                with open(cache_path, "w") as f:
                    json.dump(cache_data, f)
            except Exception:
                pass

            self.finished.emit(peaks, self.duration)

        except subprocess.CalledProcessError as e:
            self.error.emit(f"FFmpeg failed: {e.stderr.decode(errors='replace')}")
        except Exception as e:
            self.error.emit(str(e))
