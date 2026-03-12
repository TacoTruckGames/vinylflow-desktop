"""
VinylFlow - Processing Pipeline Worker

Replicates the full processing pipeline from api.py:process_file_background().
Runs in a QThread with progress signals.
"""

import copy
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from audio_processor import AudioProcessor, Track, OUTPUT_FORMATS
from metadata_handler import MetadataHandler


class ProcessWorker(QThread):
    """Background thread for the full track processing pipeline."""

    progress = Signal(float, str)   # progress (0-1), message
    finished = Signal(str, list)    # output_path, list of output filenames
    error = Signal(str)

    def __init__(
        self,
        file_path: str,
        release_id: int,
        track_mapping: list,       # list of dicts: {detected: int, discogs: str}
        detected_tracks: list,     # list of Track objects
        output_format: str,
        output_dir: str,
        discogs_token: str,
        discogs_user_agent: str,
        flac_compression: int = 8,
        restoration_level: int = 0,
        hum_freq: int = 50,
    ):
        super().__init__()
        self.file_path = Path(file_path)
        self.release_id = release_id
        self.track_mapping = track_mapping
        self.detected_tracks = copy.deepcopy(detected_tracks)
        self.output_format = output_format
        self.output_dir = Path(output_dir)
        self.discogs_token = discogs_token
        self.discogs_user_agent = discogs_user_agent
        self.flac_compression = flac_compression
        self.restoration_level = restoration_level
        self.hum_freq = hum_freq

    def run(self):
        try:
            self.progress.emit(0.1, "Starting processing...")

            # Initialize handlers
            metadata_handler = MetadataHandler(self.discogs_token, self.discogs_user_agent)
            audio_processor = AudioProcessor(flac_compression=self.flac_compression)

            # Fetch release
            self.progress.emit(0.2, "Fetching release metadata from Discogs...")
            release = metadata_handler.get_release_by_id(self.release_id)
            if not release:
                self.error.emit("Failed to fetch Discogs release")
                return

            # Apply vinyl numbers from track mapping
            for mapping in self.track_mapping:
                track = next(
                    (t for t in self.detected_tracks if t.number == mapping["detected"]),
                    None,
                )
                if track:
                    track.vinyl_number = mapping["discogs"]

            # Create output directory
            album_folder = self.output_dir / metadata_handler.create_album_folder_name(release)
            album_folder.mkdir(parents=True, exist_ok=True)

            # Download cover art
            self.progress.emit(0.3, "Downloading cover art...")
            cover_data = None
            if release.cover_url:
                cover_path = album_folder / "folder.jpg"
                if metadata_handler.download_cover_art(release.cover_url, cover_path):
                    cover_data = metadata_handler.prepare_cover_for_embedding(cover_path)

            # Process each track
            format_config = OUTPUT_FORMATS[self.output_format]
            ext = format_config["extension"]
            output_files = []
            total = len(self.detected_tracks)

            for i, track in enumerate(self.detected_tracks):
                pct = 0.4 + (i / total) * 0.5
                self.progress.emit(pct, f"Processing track {i + 1}/{total}...")

                temp_output = album_folder / f"temp_{track.vinyl_number}{ext}"

                # Extract and convert
                audio_processor.extract_track(
                    self.file_path, track, temp_output, self.output_format,
                    restoration_level=self.restoration_level,
                    hum_freq=self.hum_freq,
                )

                # Tag with metadata
                metadata_handler.tag_file(
                    temp_output, track, release, cover_data, self.output_format
                )

                # Rename to final filename
                final_filename = metadata_handler.create_track_filename(
                    track, release, self.output_format
                )
                final_path = album_folder / final_filename
                if final_path.exists():
                    final_path.unlink()
                temp_output.rename(final_path)
                output_files.append(final_filename)

            self.progress.emit(1.0, "Complete!")
            self.finished.emit(str(album_folder), output_files)

        except Exception as e:
            self.error.emit(f"Processing failed: {e}")
