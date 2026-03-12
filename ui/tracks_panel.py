"""
VinylFlow - Tracks Panel

Displays detected tracks with preview, ignore, and delete controls.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QCheckBox,
)

from ui.styles import (
    AMBER, BG_MEDIUM, BG_LIGHT, BORDER, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    TRACK_COLORS,
)


class TrackItem(QWidget):
    """Widget for a single detected track in the list."""

    preview_clicked = Signal(int)
    ignore_toggled = Signal(int, bool)
    delete_clicked = Signal(int)

    def __init__(self, track_number: int, start: float, end: float, parent=None):
        super().__init__(parent)
        self.track_number = track_number
        self.start = start
        self.end = end
        self.duration = end - start

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Color indicator
        color = TRACK_COLORS[(track_number - 1) % len(TRACK_COLORS)]
        dot = QLabel()
        dot.setFixedSize(12, 12)
        dot.setStyleSheet(
            f"background-color: {color}; border-radius: 6px; border: none;"
        )
        layout.addWidget(dot)

        # Track info
        info = QVBoxLayout()
        info.setSpacing(0)

        title = QLabel(f"Track {track_number}")
        title.setStyleSheet(f"font-weight: bold; color: {TEXT_PRIMARY}; font-size: 12px;")
        info.addWidget(title)

        s_min, s_sec = int(start // 60), int(start % 60)
        e_min, e_sec = int(end // 60), int(end % 60)
        d_min, d_sec = int(self.duration // 60), int(self.duration % 60)
        time_text = f"{s_min}:{s_sec:02d} - {e_min}:{e_sec:02d}  ({d_min}:{d_sec:02d})"
        time_label = QLabel(time_text)
        time_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        info.addWidget(time_label)

        layout.addLayout(info, stretch=1)

        # Preview button
        preview_btn = QPushButton("Play")
        preview_btn.setFixedWidth(50)
        preview_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 11px; padding: 4px 8px;
                background-color: transparent; border: 1px solid {BORDER};
                border-radius: 4px; color: {TEXT_SECONDARY};
            }}
            QPushButton:hover {{ border-color: {AMBER}; color: {AMBER}; }}
        """)
        preview_btn.clicked.connect(lambda: self.preview_clicked.emit(self.track_number))
        layout.addWidget(preview_btn)

        # Ignore checkbox
        self.ignore_cb = QCheckBox()
        self.ignore_cb.setToolTip("Ignore this track")
        self.ignore_cb.toggled.connect(
            lambda checked: self.ignore_toggled.emit(self.track_number, checked)
        )
        layout.addWidget(self.ignore_cb)

        # Delete button
        del_btn = QPushButton("x")
        del_btn.setFixedSize(22, 22)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; color: {TEXT_MUTED};
                font-size: 13px; font-weight: bold; border-radius: 11px;
            }}
            QPushButton:hover {{ color: #ef4444; }}
        """)
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.track_number))
        layout.addWidget(del_btn)


class TracksPanel(QWidget):
    """Panel showing detected tracks."""

    preview_requested = Signal(int)
    track_ignored = Signal(int, bool)
    track_deleted = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ignored = set()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QLabel("Detected Tracks")
        header.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {AMBER};")
        layout.addWidget(header)

        self.track_list = QListWidget()
        self.track_list.setSpacing(2)
        layout.addWidget(self.track_list, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(self.status_label)

    def set_tracks(self, tracks: list):
        """Populate from list of Track objects or boundary dicts."""
        self.track_list.clear()
        self._ignored.clear()

        for track in tracks:
            if hasattr(track, "number"):
                num, start, end = track.number, track.start, track.end
            else:
                num, start, end = track["number"], track["start"], track["end"]

            item_widget = TrackItem(num, start, end)
            item_widget.preview_clicked.connect(self.preview_requested.emit)
            item_widget.ignore_toggled.connect(self._on_ignore)
            item_widget.delete_clicked.connect(self.track_deleted.emit)

            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            self.track_list.addItem(list_item)
            self.track_list.setItemWidget(list_item, item_widget)

        self.status_label.setText(f"{len(tracks)} tracks detected")

    def _on_ignore(self, track_number: int, ignored: bool):
        if ignored:
            self._ignored.add(track_number)
        else:
            self._ignored.discard(track_number)
        self.track_ignored.emit(track_number, ignored)

    def get_active_track_numbers(self) -> list:
        """Return track numbers that are not ignored."""
        all_nums = []
        for i in range(self.track_list.count()):
            item = self.track_list.item(i)
            widget = self.track_list.itemWidget(item)
            if isinstance(widget, TrackItem) and widget.track_number not in self._ignored:
                all_nums.append(widget.track_number)
        return all_nums

    def clear(self):
        self.track_list.clear()
        self._ignored.clear()
        self.status_label.setText("")
