"""
VinylFlow - File Management Panel

Drag-and-drop upload zone + file queue list.
"""

import os
import uuid
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QFileDialog, QFrame,
)

from audio_processor import AudioProcessor, SUPPORTED_INPUT_EXTENSIONS
from ui.styles import (
    AMBER, AMBER_DARK, BG_MEDIUM, BG_LIGHT, BORDER, BORDER_LIGHT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
)


class DropZone(QFrame):
    """Drag-and-drop area for audio files."""

    files_dropped = Signal(list)  # list of file path strings

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_MEDIUM};
                border: 2px dashed {BORDER_LIGHT};
                border-radius: 12px;
            }}
        """)
        self._dragging = False

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel("Drop audio files here")
        icon_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px; border: none;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        hint = QLabel("WAV, AIFF, FLAC")
        hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; border: none;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {BG_LIGHT};
                    border: 2px dashed {AMBER};
                    border-radius: 12px;
                }}
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_MEDIUM};
                border: 2px dashed {BORDER_LIGHT};
                border-radius: 12px;
            }}
        """)

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_MEDIUM};
                border: 2px dashed {BORDER_LIGHT};
                border-radius: 12px;
            }}
        """)
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and Path(path).suffix.lower() in SUPPORTED_INPUT_EXTENSIONS:
                paths.append(path)
        if paths:
            self.files_dropped.emit(paths)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_file_dialog()

    def _open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Audio Files", "",
            "Audio Files (*.wav *.aiff *.aif *.flac)"
        )
        if files:
            self.files_dropped.emit(files)


class FileQueueItem(QWidget):
    """Custom widget for a file in the queue list."""

    remove_clicked = Signal(str)  # file_id
    select_clicked = Signal(str)  # file_id

    def __init__(self, file_id: str, filename: str, size: int, duration: float,
                 parent=None):
        super().__init__(parent)
        self.file_id = file_id
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # File info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = QLabel(filename)
        name_label.setStyleSheet(f"font-weight: bold; color: {TEXT_PRIMARY}; font-size: 12px;")
        info_layout.addWidget(name_label)

        size_mb = size / (1024 * 1024)
        mins = int(duration // 60)
        secs = int(duration % 60)
        detail = QLabel(f"{size_mb:.1f} MB  |  {mins}:{secs:02d}")
        detail.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        info_layout.addWidget(detail)

        layout.addLayout(info_layout, stretch=1)

        # Status badge
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; padding: 2px 8px; "
            f"border: 1px solid {BORDER}; border-radius: 8px;"
        )
        layout.addWidget(self.status_label)

        # Remove button
        remove_btn = QPushButton("x")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; color: {TEXT_MUTED};
                font-size: 14px; font-weight: bold; border-radius: 12px;
            }}
            QPushButton:hover {{ background-color: {BG_LIGHT}; color: {TEXT_PRIMARY}; }}
        """)
        remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self.file_id))
        layout.addWidget(remove_btn)

    def set_status(self, status: str):
        color_map = {
            "Ready": TEXT_MUTED,
            "Analyzing": AMBER,
            "Analyzed": AMBER_DARK,
            "Processing": AMBER,
            "Complete": "#22c55e",
            "Error": "#ef4444",
        }
        color = color_map.get(status, TEXT_MUTED)
        self.status_label.setText(status)
        self.status_label.setStyleSheet(
            f"color: {color}; font-size: 10px; padding: 2px 8px; "
            f"border: 1px solid {color}; border-radius: 8px;"
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.select_clicked.emit(self.file_id)
        super().mousePressEvent(event)


class FilePanel(QWidget):
    """File management panel with drop zone and queue."""

    file_selected = Signal(str)       # file_id
    file_removed = Signal(str)        # file_id
    files_registered = Signal(list)   # list of file info dicts

    def __init__(self, upload_dir: str, parent=None):
        super().__init__(parent)
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self._files = {}  # file_id -> info dict
        self._items = {}  # file_id -> (QListWidgetItem, FileQueueItem)
        self._processor = AudioProcessor()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header = QLabel("Files")
        header.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {AMBER};")
        layout.addWidget(header)

        # Drop zone
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        layout.addWidget(self.drop_zone)

        # Queue list
        self.queue_list = QListWidget()
        self.queue_list.setSpacing(2)
        layout.addWidget(self.queue_list, stretch=1)

    def _on_files_dropped(self, file_paths: list):
        registered = []
        for path_str in file_paths:
            file_path = Path(path_str)
            file_ext = file_path.suffix.lower()
            if file_ext not in SUPPORTED_INPUT_EXTENSIONS:
                continue

            file_id = str(uuid.uuid4())
            session_dir = self.upload_dir / file_id
            session_dir.mkdir(parents=True, exist_ok=True)

            target = session_dir / f"source{file_ext}"
            try:
                os.symlink(str(file_path.resolve()), str(target))
            except (OSError, NotImplementedError):
                shutil.copy2(str(file_path), str(target))

            duration = self._processor.get_audio_duration(target) or 0
            size = target.stat().st_size

            info = {
                "id": file_id,
                "filename": file_path.name,
                "path": str(target),
                "size": size,
                "duration": duration,
                "status": "uploaded",
            }
            self._files[file_id] = info
            self._add_queue_item(info)
            registered.append(info)

        if registered:
            self.files_registered.emit(registered)
            # Auto-select the first file if none selected
            if len(self._files) == len(registered):
                self.file_selected.emit(registered[0]["id"])

    def _add_queue_item(self, info: dict):
        item_widget = FileQueueItem(
            info["id"], info["filename"], info["size"], info["duration"]
        )
        item_widget.remove_clicked.connect(self._on_remove)
        item_widget.select_clicked.connect(self._on_select)

        list_item = QListWidgetItem()
        list_item.setSizeHint(item_widget.sizeHint())
        self.queue_list.addItem(list_item)
        self.queue_list.setItemWidget(list_item, item_widget)
        self._items[info["id"]] = (list_item, item_widget)

    def _on_remove(self, file_id: str):
        if file_id in self._items:
            list_item, _ = self._items.pop(file_id)
            row = self.queue_list.row(list_item)
            self.queue_list.takeItem(row)

        if file_id in self._files:
            # Clean up session directory
            session_dir = self.upload_dir / file_id
            if session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)
            del self._files[file_id]

        self.file_removed.emit(file_id)

    def _on_select(self, file_id: str):
        self.file_selected.emit(file_id)

    def get_file_info(self, file_id: str) -> dict | None:
        return self._files.get(file_id)

    def set_file_status(self, file_id: str, status: str):
        if file_id in self._files:
            self._files[file_id]["status"] = status
        if file_id in self._items:
            _, item_widget = self._items[file_id]
            item_widget.set_status(status)

    def get_analyzable_file_ids(self) -> list[str]:
        """Return file IDs with status 'uploaded' (ready to analyze)."""
        return [
            fid for fid, info in self._files.items()
            if info.get("status") in ("uploaded",)
        ]

    def get_all_files(self) -> dict:
        """Return all file info dicts keyed by file_id."""
        return dict(self._files)

    def add_external_files(self, file_paths: list):
        """Add files from command-line args or second instance."""
        self._on_files_dropped(file_paths)
