"""
VinylFlow - Main Window

QMainWindow orchestrating all panels and workers.
"""

import logging
import os
import shutil
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QIcon, QFontDatabase, QFont, QCloseEvent
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QFrame, QApplication, QMessageBox, QMenuBar,
)

from config import Config
from version import __version__
from audio_processor import Track

from ui.styles import (
    AMBER, AMBER_DARK, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_LIGHTER,
    BORDER, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, get_stylesheet,
)
from ui.file_panel import FilePanel
from ui.waveform_widget import WaveformWidget
from ui.tracks_panel import TracksPanel
from ui.search_panel import SearchPanel
from ui.mapping_panel import MappingPanel
from ui.tray import TrayIcon
from ui.settings_dialog import SettingsDialog
from ui.setup_dialog import SetupDialog

from workers.analyze_worker import AnalyzeWorker, DurationSplitWorker
from workers.waveform_worker import WaveformWorker
from workers.preview_worker import PreviewWorker
from workers.search_worker import SearchWorker, CoverArtWorker
from workers.process_worker import ProcessWorker


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


class MainWindow(QMainWindow):
    """VinylFlow main application window."""

    files_received = Signal(list)  # for inter-process file forwarding

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self._current_file_id = None
        self._current_file_info = None
        self._detected_tracks = []
        self._selected_release = None
        self._cover_cache = {}  # release_id -> bytes
        self._analyze_results = {}  # file_id -> list of Track objects
        self._analyze_queue = []
        self._workers = []  # keep references to prevent GC

        self._setup_window()
        self._build_ui()
        self._connect_signals()
        self._start_cleanup_timer()
        self._check_first_run()
        self._check_update()

        self.files_received.connect(self._on_external_files)

    def _setup_window(self):
        self.setWindowTitle(f"VinylFlow v{__version__}")

        icon_file = _icon_path()
        if icon_file:
            self.setWindowIcon(QIcon(icon_file))

        self.setMinimumSize(900, 700)

        # Load saved window state
        state = self.config.load_window_state()
        w = state.get("width", 1280)
        h = state.get("height", 900)
        self.resize(w, h)
        if "x" in state and "y" in state:
            self.move(state["x"], state["y"])

        # Load custom font
        fonts_dir = Path(__file__).parent.parent / "assets" / "fonts"
        if fonts_dir.exists():
            for font_file in fonts_dir.glob("*.ttf"):
                QFontDatabase.addApplicationFont(str(font_file))

    def _build_ui(self):
        # Menu bar
        self._build_menu_bar()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Update banner (hidden by default)
        self.update_banner = QFrame()
        self.update_banner.setStyleSheet(
            f"QFrame {{ background-color: {AMBER_DARK}; }}"
        )
        banner_layout = QHBoxLayout(self.update_banner)
        banner_layout.setContentsMargins(16, 6, 16, 6)
        self.update_label = QLabel("")
        self.update_label.setStyleSheet("color: #000; font-weight: bold; font-size: 12px;")
        banner_layout.addWidget(self.update_label, stretch=1)
        self.update_btn = QPushButton("Download")
        self.update_btn.setStyleSheet(
            "QPushButton { background: #000; color: #fff; border-radius: 4px; "
            "padding: 4px 12px; font-size: 11px; }"
        )
        self.update_btn.clicked.connect(self._open_update_url)
        banner_layout.addWidget(self.update_btn)
        dismiss_btn = QPushButton("x")
        dismiss_btn.setFixedSize(20, 20)
        dismiss_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #000; border: none; font-weight: bold; }"
        )
        dismiss_btn.clicked.connect(self.update_banner.hide)
        banner_layout.addWidget(dismiss_btn)
        self.update_banner.hide()
        main_layout.addWidget(self.update_banner)

        # Header bar
        header = QFrame()
        header.setFixedHeight(48)
        header.setStyleSheet(
            f"QFrame {{ background-color: {BG_MEDIUM}; border-bottom: 1px solid {BORDER}; }}"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)

        title = QLabel(f"VinylFlow")
        title.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {AMBER}; border: none;"
        )
        header_layout.addWidget(title)

        version_label = QLabel(f"v{__version__}")
        version_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; border: none;")
        header_layout.addWidget(version_label)

        header_layout.addStretch()

        settings_btn = QPushButton("Settings")
        settings_btn.setFixedHeight(30)
        settings_btn.clicked.connect(self._open_settings)
        header_layout.addWidget(settings_btn)

        main_layout.addWidget(header)

        # Content area with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # Left panel: files + tracks
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 6, 12)
        left_layout.setSpacing(12)

        upload_dir = os.environ.get(
            "VINYLFLOW_UPLOAD_DIR",
            str(Path.home() / "AppData" / "Roaming" / "VinylFlow" / "temp_uploads"),
        )
        self.file_panel = FilePanel(upload_dir)
        left_layout.addWidget(self.file_panel, stretch=1)

        self.tracks_panel = TracksPanel()
        left_layout.addWidget(self.tracks_panel, stretch=1)

        # Analyze button
        self.analyze_btn = QPushButton("Analyze")
        self.analyze_btn.setObjectName("primaryButton")
        self.analyze_btn.setFixedHeight(36)
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._on_analyze)
        left_layout.addWidget(self.analyze_btn)

        splitter.addWidget(left_panel)

        # Center/right panel: waveform + search + mapping
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(6, 12, 12, 12)
        right_layout.setSpacing(12)

        self.waveform = WaveformWidget()
        right_layout.addWidget(self.waveform)

        # Search + Mapping tabs area
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.search_panel = SearchPanel()
        bottom_splitter.addWidget(self.search_panel)

        self.mapping_panel = MappingPanel()
        bottom_splitter.addWidget(self.mapping_panel)

        bottom_splitter.setSizes([400, 500])
        right_layout.addWidget(bottom_splitter, stretch=1)

        splitter.addWidget(right_panel)
        splitter.setSizes([300, 900])

        main_layout.addWidget(splitter, stretch=1)

        # System tray
        self.tray = TrayIcon(self)
        self.tray.show()

    def _connect_signals(self):
        # File panel
        self.file_panel.file_selected.connect(self._on_file_selected)
        self.file_panel.file_removed.connect(self._on_file_removed)
        self.file_panel.files_registered.connect(self._on_files_registered)

        # Waveform
        self.waveform.regions_changed.connect(self._on_regions_changed)
        self.waveform.split_added.connect(self._on_split_added)
        self.waveform.track_deleted.connect(self._on_track_deleted)
        self.waveform.track_preview.connect(self._on_track_preview)

        # Tracks panel
        self.tracks_panel.preview_requested.connect(self._on_track_preview)
        self.tracks_panel.track_deleted.connect(self._on_track_deleted)

        # Search panel
        self.search_panel.search_requested.connect(self._on_search)
        self.search_panel.release_selected.connect(self._on_release_selected)

        # Mapping panel
        self.mapping_panel.process_requested.connect(self._on_process)

    # ----- File management -----

    def _on_file_selected(self, file_id: str):
        info = self.file_panel.get_file_info(file_id)
        if not info:
            return

        self._current_file_id = file_id
        self._current_file_info = info
        self._selected_release = None

        self.analyze_btn.setEnabled(True)
        self.tracks_panel.clear()
        self.mapping_panel.clear()
        self.waveform.clear()

        # Restore cached analysis results if this file was already analyzed
        cached = getattr(self, "_analyze_results", {}).get(file_id)
        if cached:
            self._detected_tracks = cached
        else:
            self._detected_tracks = []

        # Auto-suggest search from filename
        filename_stem = Path(info["filename"]).stem
        self.search_panel.search_input.setText(filename_stem.replace("-", " ").replace("_", " "))

        # Load waveform
        self._load_waveform(info)

    def _on_file_removed(self, file_id: str):
        if file_id == self._current_file_id:
            self._current_file_id = None
            self._current_file_info = None
            self._detected_tracks = []
            self.analyze_btn.setEnabled(False)
            self.waveform.clear()
            self.tracks_panel.clear()
            self.mapping_panel.clear()

    def _on_files_registered(self, files: list):
        """Enable Analyze button when files are added."""
        if files:
            self.analyze_btn.setEnabled(True)

    def _on_external_files(self, file_paths: list):
        self.file_panel.add_external_files(file_paths)
        self.show()
        self.raise_()
        self.activateWindow()

    # ----- Waveform -----

    def _load_waveform(self, file_info: dict):
        worker = WaveformWorker(file_info["path"], file_info["duration"])
        worker.finished.connect(self._on_waveform_loaded)
        worker.error.connect(lambda e: print(f"Waveform error: {e}"))
        self._start_worker(worker)

    def _on_waveform_loaded(self, peaks: list, duration: float):
        self.waveform.load_peaks(peaks, duration)
        if self._detected_tracks:
            self.waveform.set_track_regions(self._detected_tracks)

    # ----- Analysis -----

    def _on_analyze(self):
        # Collect all files ready to analyze
        analyzable = self.file_panel.get_analyzable_file_ids()
        if not analyzable:
            return

        self._analyze_queue = list(analyzable)
        self._analyze_results = {}  # file_id -> tracks
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Analyzing...")

        # Mark all as Analyzing
        for fid in self._analyze_queue:
            self.file_panel.set_file_status(fid, "Analyzing")

        self._analyze_next()

    def _analyze_next(self):
        if not self._analyze_queue:
            # All done
            self.analyze_btn.setEnabled(True)
            self.analyze_btn.setText("Analyze")
            return

        file_id = self._analyze_queue[0]
        info = self.file_panel.get_file_info(file_id)
        if not info:
            self._analyze_queue.pop(0)
            self._analyze_next()
            return

        worker = AnalyzeWorker(
            info["path"],
            self.config.default_silence_threshold,
            self.config.default_min_silence_duration,
            self.config.default_min_track_length,
        )
        worker.finished.connect(lambda tracks, fid=file_id: self._on_analysis_complete(fid, tracks))
        worker.error.connect(lambda err, fid=file_id: self._on_analysis_error(fid, err))
        self._start_worker(worker)

    def _on_analysis_complete(self, file_id: str, tracks: list):
        self._analyze_results[file_id] = tracks
        self.file_panel.set_file_status(file_id, "Analyzed")

        # Update UI if this is the currently selected file
        if file_id == self._current_file_id:
            self._detected_tracks = tracks
            self.waveform.set_track_regions(tracks)
            self.tracks_panel.set_tracks(tracks)
            self.mapping_panel.set_detected_tracks(tracks)

        # Continue to next file
        if self._analyze_queue and self._analyze_queue[0] == file_id:
            self._analyze_queue.pop(0)
        self._analyze_next()

    def _on_analysis_error(self, file_id: str, error: str):
        self.file_panel.set_file_status(file_id, "Error")

        # Continue to next file
        if self._analyze_queue and self._analyze_queue[0] == file_id:
            self._analyze_queue.pop(0)
        self._analyze_next()

        if file_id == self._current_file_id:
            QMessageBox.warning(self, "Analysis Failed", f"Silence detection failed:\n{error}")

    # ----- Waveform editing -----

    def _on_regions_changed(self):
        boundaries = self.waveform.get_track_boundaries()
        # Convert to Track objects
        tracks = []
        for b in boundaries:
            t = Track(b["number"], b["start"], b["end"])
            tracks.append(t)
        self._detected_tracks = tracks
        self.tracks_panel.set_tracks(tracks)
        self.mapping_panel.set_detected_tracks(tracks)

    def _on_split_added(self, time_sec: float):
        self.waveform.add_split_at_time(time_sec)

    def _on_track_deleted(self, track_number: int):
        self.waveform.delete_track(track_number)

    # ----- Track preview -----

    def _on_track_preview(self, track_number: int):
        if not self._current_file_info or not self._detected_tracks:
            return

        track = next((t for t in self._detected_tracks if t.number == track_number), None)
        if not track:
            return

        upload_dir = Path(self._current_file_info["path"]).parent
        preview_path = str(upload_dir / f"preview_{track_number}.mp3")

        worker = PreviewWorker(
            self._current_file_info["path"],
            track.start,
            track.duration,
            preview_path,
        )
        worker.finished.connect(lambda path: self.waveform.play_preview(path))
        worker.error.connect(lambda e: print(f"Preview error: {e}"))
        self._start_worker(worker)

    # ----- Discogs search -----

    def _on_search(self, query: str):
        self.search_panel.set_loading(True)

        worker = SearchWorker(
            query,
            self.config.discogs_token,
            self.config.discogs_user_agent,
        )
        worker.finished.connect(self._on_search_results)
        worker.error.connect(self._on_search_error)
        self._start_worker(worker)

    def _on_search_results(self, results: list):
        self.search_panel.show_results(results)

        # Fetch cover art for each result
        for idx, release in results:
            if release.cover_url:
                cover_worker = CoverArtWorker(
                    release.cover_url,
                    str(release.id),
                    self.config.discogs_user_agent,
                )
                cover_worker.finished.connect(self._on_cover_art_loaded)
                self._start_worker(cover_worker)

    def _on_search_error(self, error: str):
        self.search_panel.show_error(error)

    def _on_cover_art_loaded(self, release_id: str, image_data: bytes):
        self._cover_cache[release_id] = image_data
        self.search_panel.update_cover_art(release_id, image_data)

    # ----- Release selection -----

    def _on_release_selected(self, release):
        self._selected_release = release

        cover_data = self._cover_cache.get(str(release.id))
        self.mapping_panel.set_release(release, cover_data)

        if self._detected_tracks:
            self.mapping_panel.set_detected_tracks(self._detected_tracks)

    # ----- Processing -----

    def _on_process(self, process_config: dict):
        if not self._current_file_info or not self._selected_release:
            return

        self.mapping_panel.set_processing(True)
        self.file_panel.set_file_status(self._current_file_id, "Processing")

        boundaries = self.waveform.get_track_boundaries()
        tracks_for_processing = []
        for b in boundaries:
            t = Track(b["number"], b["start"], b["end"])
            tracks_for_processing.append(t)

        worker = ProcessWorker(
            file_path=self._current_file_info["path"],
            release_id=process_config["release_id"],
            track_mapping=process_config["track_mapping"],
            detected_tracks=tracks_for_processing,
            output_format=process_config["output_format"],
            output_dir=self.config.default_output_dir,
            discogs_token=self.config.discogs_token,
            discogs_user_agent=self.config.discogs_user_agent,
            flac_compression=self.config.default_flac_compression,
            restoration_level=process_config["restoration_level"],
        )
        worker.progress.connect(self._on_process_progress)
        worker.finished.connect(self._on_process_complete)
        worker.error.connect(self._on_process_error)
        self._start_worker(worker)

    def _on_process_progress(self, progress: float, message: str):
        self.mapping_panel.update_progress(progress, message)

    def _on_process_complete(self, output_path: str, files: list):
        self.mapping_panel.show_success(output_path, files)
        self.file_panel.set_file_status(self._current_file_id, "Complete")
        self.tray.notify("VinylFlow", f"Processing complete! {len(files)} tracks saved.")

    def _on_process_error(self, error: str):
        self.mapping_panel.show_error(error)
        self.file_panel.set_file_status(self._current_file_id, "Error")

    # ----- Settings -----

    def _open_settings(self):
        dialog = SettingsDialog(self.config, self)
        dialog.settings_changed.connect(self._apply_settings)
        dialog.exec()

    def _apply_settings(self, settings: dict):
        self.config.default_silence_threshold = settings["silence_threshold"]
        self.config.default_min_silence_duration = settings["min_silence_duration"]
        self.config.default_min_track_length = settings["min_track_length"]
        self.config.default_flac_compression = settings["flac_compression"]

        if settings["output_dir"] != self.config.default_output_dir:
            self.config.default_output_dir = settings["output_dir"]
            self.config.save_output_dir(settings["output_dir"])

        if settings["discogs_token"] and settings["discogs_token"] != self.config.discogs_token:
            self.config.save_token(settings["discogs_token"])
            self.config.reload()

    # ----- First-run setup -----

    def _check_first_run(self):
        if not self.config.discogs_token:
            QTimer.singleShot(500, self._show_setup)

    def _show_setup(self):
        dialog = SetupDialog(self)
        dialog.token_saved.connect(self._on_setup_token_saved)
        dialog.exec()

    def _on_setup_token_saved(self, token: str, user_agent: str):
        self.config.save_token(token, user_agent)
        self.config.reload()

    # ----- Auto-update -----

    def _check_update(self):
        def _check():
            try:
                from updater import check_for_update
                result = check_for_update()
                if result and result.get("update_available"):
                    self._update_info = result
                    QTimer.singleShot(0, self._show_update_banner)
            except Exception:
                pass

        threading.Thread(target=_check, daemon=True).start()

    def _show_update_banner(self):
        if hasattr(self, "_update_info"):
            info = self._update_info
            self.update_label.setText(
                f"VinylFlow {info['latest_version']} is available!"
            )
            self._update_url = info.get("download_url", "")
            self.update_banner.show()

    def _open_update_url(self):
        if hasattr(self, "_update_url") and self._update_url:
            url = self._update_url
            if url.startswith("https://github.com/"):
                os.startfile(url)
            else:
                logging.getLogger(__name__).warning(
                    f"Blocked non-GitHub update URL: {url}"
                )

    # ----- Cleanup timer -----

    def _start_cleanup_timer(self):
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.timeout.connect(self._cleanup_old_files)
        self._cleanup_timer.start(30 * 60 * 1000)  # 30 minutes

    def _cleanup_old_files(self):
        upload_dir = Path(os.environ.get(
            "VINYLFLOW_UPLOAD_DIR",
            str(Path.home() / "AppData" / "Roaming" / "VinylFlow" / "temp_uploads"),
        ))
        if not upload_dir.exists():
            return

        cutoff = datetime.now() - timedelta(hours=self.config.temp_ttl_hours)
        for entry in upload_dir.iterdir():
            if not entry.is_dir():
                continue
            try:
                source_files = list(entry.glob("source.*"))
                mtime_path = source_files[0] if source_files else entry
                if datetime.fromtimestamp(mtime_path.stat().st_mtime) < cutoff:
                    shutil.rmtree(entry, ignore_errors=True)
            except Exception:
                pass

    # ----- Worker management -----

    def _start_worker(self, worker):
        """Start a QThread worker and keep reference to prevent GC."""
        self._workers.append(worker)
        worker.finished.connect(lambda *a: self._cleanup_worker(worker))
        if hasattr(worker, 'error'):
            worker.error.connect(lambda *a: self._cleanup_worker(worker))
        worker.start()

    def _cleanup_worker(self, worker):
        """Remove worker reference after completion."""
        try:
            self._workers.remove(worker)
        except ValueError:
            pass

    # ----- Menu bar -----

    def _build_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        minimize_action = QAction("&Minimize to Tray", self)
        minimize_action.triggered.connect(self._minimize_to_tray)
        file_menu.addAction(minimize_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.force_quit)
        file_menu.addAction(exit_action)

    def _minimize_to_tray(self):
        self.hide()
        self.tray.notify("VinylFlow", "VinylFlow is still running in the system tray.")

    # ----- Window events -----

    def closeEvent(self, event: QCloseEvent):
        # Save window state and minimize to tray
        geo = self.geometry()
        self.config.save_window_state(geo.x(), geo.y(), geo.width(), geo.height())

        if self.tray.isVisible():
            event.ignore()
            self._minimize_to_tray()
        else:
            event.accept()

    def force_quit(self):
        """Save state and truly exit the application."""
        geo = self.geometry()
        self.config.save_window_state(geo.x(), geo.y(), geo.width(), geo.height())
        self.tray.hide()
        QApplication.instance().quit()
