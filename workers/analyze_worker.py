"""
VinylFlow - Silence Detection Worker

Runs AudioProcessor.detect_silence() in a background QThread.
"""

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from audio_processor import AudioProcessor


class AnalyzeWorker(QThread):
    """Background thread for silence detection."""

    finished = Signal(list)       # List[Track]
    error = Signal(str)
    progress = Signal(str)        # status message

    def __init__(self, file_path: str, silence_threshold: float,
                 min_silence_duration: float, min_track_length: float):
        super().__init__()
        self.file_path = Path(file_path)
        self.silence_threshold = silence_threshold
        self.min_silence_duration = min_silence_duration
        self.min_track_length = min_track_length

    def run(self):
        try:
            self.progress.emit("Detecting silence boundaries...")
            processor = AudioProcessor(
                silence_threshold=self.silence_threshold,
                min_silence_duration=self.min_silence_duration,
                min_track_length=self.min_track_length,
            )
            tracks = processor.detect_silence(self.file_path)
            self.finished.emit(tracks)
        except Exception as e:
            self.error.emit(str(e))


class DurationSplitWorker(QThread):
    """Background thread for duration-based track splitting."""

    finished = Signal(list)
    error = Signal(str)

    def __init__(self, file_path: str, durations: list,
                 min_track_length: float = 30):
        super().__init__()
        self.file_path = Path(file_path)
        self.durations = durations
        self.min_track_length = min_track_length

    def run(self):
        try:
            processor = AudioProcessor(min_track_length=self.min_track_length)
            tracks = processor.split_tracks_duration_based(self.file_path, self.durations)
            self.finished.emit(tracks)
        except Exception as e:
            self.error.emit(str(e))
