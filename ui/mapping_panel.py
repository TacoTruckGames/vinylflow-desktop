"""
VinylFlow - Track Mapping Panel

Maps detected tracks to Discogs positions, with format selection
and process button.
"""

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox, QFrame, QProgressBar,
)

from audio_processor import OUTPUT_FORMATS
from ui.styles import (
    AMBER, AMBER_DARK, BG_MEDIUM, BG_LIGHT, BG_LIGHTER,
    BORDER, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, GREEN, RED,
)


class MappingPanel(QWidget):
    """Track mapping and processing panel."""

    process_requested = Signal(dict)  # full processing config

    def __init__(self, parent=None):
        super().__init__(parent)
        self._release = None
        self._detected_tracks = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Release info card
        self.release_card = QFrame()
        self.release_card.setStyleSheet(
            f"QFrame {{ background-color: {BG_LIGHTER}; border: 1px solid {BORDER}; "
            f"border-radius: 8px; }}"
        )
        card_layout = QHBoxLayout(self.release_card)
        card_layout.setContentsMargins(12, 12, 12, 12)

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(80, 80)
        self.cover_label.setStyleSheet(
            f"background-color: {BG_MEDIUM}; border-radius: 4px; border: none;"
        )
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.cover_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        self.artist_label = QLabel("")
        self.artist_label.setStyleSheet(
            f"font-weight: bold; font-size: 14px; color: {TEXT_PRIMARY}; border: none;"
        )
        info_layout.addWidget(self.artist_label)

        self.title_label = QLabel("")
        self.title_label.setStyleSheet(f"font-size: 13px; color: {TEXT_SECONDARY}; border: none;")
        info_layout.addWidget(self.title_label)

        self.meta_label = QLabel("")
        self.meta_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; border: none;")
        info_layout.addWidget(self.meta_label)

        info_layout.addStretch()
        card_layout.addLayout(info_layout, stretch=1)
        layout.addWidget(self.release_card)
        self.release_card.hide()

        # Options row
        opts = QHBoxLayout()
        opts.setSpacing(12)

        # Output format
        fmt_label = QLabel("Format:")
        fmt_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        opts.addWidget(fmt_label)

        self.format_combo = QComboBox()
        for fmt_id, fmt in OUTPUT_FORMATS.items():
            self.format_combo.addItem(fmt["label"], fmt_id)
        self.format_combo.setCurrentIndex(0)  # FLAC default
        self.format_combo.setFixedWidth(160)
        opts.addWidget(self.format_combo)

        opts.addSpacing(16)

        # Restoration toggle
        self.restore_cb = QCheckBox("Restore && Normalize")
        self.restore_cb.setToolTip(
            "Apply light audio restoration:\n"
            "- Remove sub-bass rumble (< 15 Hz)\n"
            "- Conservative click/pop removal\n"
            "- Loudness normalization (EBU R128)"
        )
        opts.addWidget(self.restore_cb)

        opts.addStretch()

        # Reverse button
        self.reverse_btn = QPushButton("Reverse Mapping")
        self.reverse_btn.setFixedWidth(160)
        self.reverse_btn.clicked.connect(self._reverse_mapping)
        opts.addWidget(self.reverse_btn)

        layout.addLayout(opts)

        # Mapping table
        self.mapping_table = QTableWidget()
        self.mapping_table.setColumnCount(4)
        self.mapping_table.setHorizontalHeaderLabels(["Track", "Discogs Position", "Title", "Length"])
        self.mapping_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.mapping_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.mapping_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.mapping_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.mapping_table.verticalHeader().setVisible(False)
        self.mapping_table.verticalHeader().setDefaultSectionSize(42)
        self.mapping_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        layout.addWidget(self.mapping_table, stretch=1)

        # Mismatch warning
        self.mismatch_label = QLabel("")
        self.mismatch_label.setStyleSheet(f"color: {AMBER}; font-size: 11px;")
        self.mismatch_label.hide()
        layout.addWidget(self.mismatch_label)

        # Progress bar (hidden until processing)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        self.progress_label.hide()
        layout.addWidget(self.progress_label)

        # Process button row
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.process_btn = QPushButton("Process Tracks")
        self.process_btn.setObjectName("primaryButton")
        self.process_btn.setFixedHeight(40)
        self.process_btn.setFixedWidth(180)
        self.process_btn.clicked.connect(self._on_process)
        btn_row.addWidget(self.process_btn)

        layout.addLayout(btn_row)

        # Success panel (hidden until complete)
        self.success_frame = QFrame()
        self.success_frame.setStyleSheet(
            f"QFrame {{ background-color: {BG_LIGHTER}; border: 1px solid {GREEN}; "
            f"border-radius: 8px; }}"
        )
        success_layout = QVBoxLayout(self.success_frame)
        success_layout.setContentsMargins(16, 16, 16, 16)

        success_label = QLabel("Processing Complete!")
        success_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {GREEN}; border: none;")
        success_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_layout.addWidget(success_label)

        self.output_path_label = QLabel("")
        self.output_path_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; border: none;")
        self.output_path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.output_path_label.setWordWrap(True)
        success_layout.addWidget(self.output_path_label)

        self.open_folder_btn = QPushButton("Open Output Folder")
        self.open_folder_btn.setObjectName("primaryButton")
        self.open_folder_btn.setFixedWidth(180)
        self.open_folder_btn.clicked.connect(self._open_output_folder)
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        btn_container.addWidget(self.open_folder_btn)
        btn_container.addStretch()
        success_layout.addLayout(btn_container)

        self.success_frame.hide()
        layout.addWidget(self.success_frame)

    def set_release(self, release, cover_data: bytes = None):
        """Set the selected Discogs release."""
        self._release = release

        self.artist_label.setText(release.artist)
        self.title_label.setText(release.title)

        parts = []
        if release.year:
            parts.append(str(release.year))
        if release.format:
            parts.append(release.format)
        if release.label:
            parts.append(release.label)
        self.meta_label.setText(" | ".join(parts))

        if cover_data:
            pixmap = QPixmap()
            pixmap.loadFromData(cover_data)
            if not pixmap.isNull():
                self.cover_label.setPixmap(
                    pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
                )

        self.release_card.show()
        self._update_mapping_table()

    def set_detected_tracks(self, tracks: list):
        """Set detected tracks (list of Track objects or boundary dicts)."""
        self._detected_tracks = tracks
        self._update_mapping_table()

    def _update_mapping_table(self):
        if not self._release or not self._detected_tracks:
            return

        discogs_positions = [t.position for t in self._release.tracks]
        num_detected = len(self._detected_tracks)
        num_discogs = len(discogs_positions)

        self.mapping_table.setRowCount(num_detected)

        for i, track in enumerate(self._detected_tracks):
            if hasattr(track, "number"):
                track_num = track.number
            else:
                track_num = track["number"]

            # Track number
            num_item = QTableWidgetItem(f"Track {track_num}")
            num_item.setFlags(num_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.mapping_table.setItem(i, 0, num_item)

            # Discogs position combo
            combo = QComboBox()
            for pos in discogs_positions:
                # Find matching track title
                dt = next((t for t in self._release.tracks if t.position == pos), None)
                label = f"{pos} - {dt.title}" if dt else pos
                combo.addItem(label, pos)

            # Default mapping: assign in order
            if i < num_discogs:
                combo.setCurrentIndex(i)
            self.mapping_table.setCellWidget(i, 1, combo)

            # Title (auto-filled from combo selection)
            if i < num_discogs:
                dt = self._release.tracks[i]
                title_item = QTableWidgetItem(dt.title)
            else:
                title_item = QTableWidgetItem("")
            title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.mapping_table.setItem(i, 2, title_item)

            # Duration from Discogs
            if i < num_discogs:
                dt = self._release.tracks[i]
                dur_str = getattr(dt, "duration_str", "") or "N/A"
            else:
                dur_str = "N/A"
            dur_item = QTableWidgetItem(dur_str)
            dur_item.setFlags(dur_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            dur_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.mapping_table.setItem(i, 3, dur_item)

            combo.currentIndexChanged.connect(
                lambda idx, row=i: self._on_combo_changed(row, idx)
            )

        # Show mismatch warning
        if num_detected != num_discogs:
            self.mismatch_label.setText(
                f"Track count mismatch: {num_detected} detected vs "
                f"{num_discogs} on Discogs"
            )
            self.mismatch_label.show()
        else:
            self.mismatch_label.hide()

    def _on_combo_changed(self, row: int, combo_idx: int):
        if self._release and combo_idx < len(self._release.tracks):
            dt = self._release.tracks[combo_idx]
            self.mapping_table.setItem(row, 2, QTableWidgetItem(dt.title))
            dur_str = getattr(dt, "duration_str", "") or "N/A"
            dur_item = QTableWidgetItem(dur_str)
            dur_item.setFlags(dur_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            dur_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.mapping_table.setItem(row, 3, dur_item)

    def _reverse_mapping(self):
        """Reverse the mapping order."""
        row_count = self.mapping_table.rowCount()
        if row_count < 2:
            return

        # Collect current indices
        indices = []
        for i in range(row_count):
            combo = self.mapping_table.cellWidget(i, 1)
            if combo:
                indices.append(combo.currentIndex())

        # Reverse and re-apply
        indices.reverse()
        for i in range(row_count):
            combo = self.mapping_table.cellWidget(i, 1)
            if combo and i < len(indices):
                combo.setCurrentIndex(indices[i])

    def get_track_mapping(self) -> list:
        """Return current mapping as list of {detected, discogs} dicts."""
        mapping = []
        for i in range(self.mapping_table.rowCount()):
            combo = self.mapping_table.cellWidget(i, 1)
            if combo:
                track = self._detected_tracks[i]
                track_num = track.number if hasattr(track, "number") else track["number"]
                mapping.append({
                    "detected": track_num,
                    "discogs": combo.currentData(),
                })
        return mapping

    def _on_process(self):
        if not self._release or not self._detected_tracks:
            return

        config = {
            "release_id": self._release.id,
            "track_mapping": self.get_track_mapping(),
            "output_format": self.format_combo.currentData(),
            "restoration_level": 1 if self.restore_cb.isChecked() else 0,
        }
        self.process_requested.emit(config)

    def set_processing(self, processing: bool):
        """Show/hide progress indicators."""
        self.process_btn.setEnabled(not processing)
        self.progress_bar.setVisible(processing)
        self.progress_label.setVisible(processing)
        if processing:
            self.success_frame.hide()
            self.progress_bar.setValue(0)

    def update_progress(self, progress: float, message: str):
        """Update processing progress (0.0 to 1.0)."""
        self.progress_bar.setValue(int(progress * 100))
        self.progress_label.setText(message)

    def show_success(self, output_path: str, files: list):
        """Show success panel."""
        self.progress_bar.hide()
        self.progress_label.hide()
        self.process_btn.setEnabled(True)

        self._output_path = output_path
        self.output_path_label.setText(f"Files saved to:\n{output_path}")
        self.success_frame.show()

    def show_error(self, message: str):
        """Show error state."""
        self.progress_bar.hide()
        self.progress_label.setText(f"Error: {message}")
        self.progress_label.setStyleSheet(f"color: {RED}; font-size: 12px;")
        self.process_btn.setEnabled(True)

    def _open_output_folder(self):
        if hasattr(self, "_output_path") and self._output_path:
            path = os.path.realpath(self._output_path)
            if os.path.isdir(path):
                os.startfile(path)
            else:
                import logging
                logging.getLogger(__name__).warning(
                    f"Output path is not a valid directory: {path}"
                )

    def clear(self):
        self._release = None
        self._detected_tracks = []
        self.mapping_table.setRowCount(0)
        self.release_card.hide()
        self.mismatch_label.hide()
        self.progress_bar.hide()
        self.progress_label.hide()
        self.success_frame.hide()
        self.process_btn.setEnabled(True)
