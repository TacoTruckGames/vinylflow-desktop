"""
VinylFlow - Preview MP3 Generation Worker

Generates a temporary MP3 clip for track preview playback.
"""

import subprocess
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from audio_processor import _ffmpeg


class PreviewWorker(QThread):
    """Background thread to generate a preview MP3 for a track segment."""

    finished = Signal(str)   # path to generated MP3
    error = Signal(str)

    def __init__(self, source_path: str, start: float, duration: float,
                 output_path: str):
        super().__init__()
        self.source_path = source_path
        self.start = start
        self.duration = min(30.0, duration)  # max 30s preview
        self.output_path = output_path

    def run(self):
        try:
            cmd = [
                _ffmpeg(),
                "-y",
                "-i", self.source_path,
                "-ss", str(self.start),
                "-t", str(self.duration),
                "-acodec", "libmp3lame",
                "-b:a", "128k",
                self.output_path,
            ]
            subprocess.run(
                cmd, check=True, capture_output=True,
                encoding="utf-8", errors="replace",
            )
            self.finished.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))
