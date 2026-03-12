"""
VinylFlow - Discogs Search Panel

Search bar + results grid with cover art thumbnails.
"""

from io import BytesIO
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QFrame, QGridLayout,
)

from ui.styles import (
    AMBER, AMBER_DARK, BG_MEDIUM, BG_LIGHT, BG_LIGHTER, BG_HOVER,
    BORDER, BORDER_LIGHT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
)


class ReleaseCard(QFrame):
    """Card displaying a single Discogs release search result."""

    clicked = Signal(object)  # DiscogsRelease

    def __init__(self, release, parent=None):
        super().__init__(parent)
        self.release = release
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(100)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_LIGHTER};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border-color: {AMBER};
                background-color: {BG_HOVER};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 12, 8)
        layout.setSpacing(12)

        # Cover art placeholder
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(80, 80)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet(
            f"background-color: {BG_MEDIUM}; border-radius: 4px; border: none;"
        )
        self.cover_label.setText("?")
        layout.addWidget(self.cover_label)

        # Info
        info = QVBoxLayout()
        info.setSpacing(2)

        artist_title = QLabel(f"{release.artist} - {release.title}")
        artist_title.setStyleSheet(
            f"font-weight: bold; color: {TEXT_PRIMARY}; font-size: 12px; border: none;"
        )
        artist_title.setWordWrap(True)
        info.addWidget(artist_title)

        year_label = f"{release.year}" if release.year else ""
        format_label = release.format if release.format else ""
        detail_parts = [p for p in [year_label, format_label, release.label] if p]
        detail = QLabel(" | ".join(detail_parts))
        detail.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; border: none;")
        info.addWidget(detail)

        track_count = len(release.tracks)
        tracks_text = QLabel(f"{track_count} tracks")
        tracks_text.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; border: none;")
        info.addWidget(tracks_text)

        info.addStretch()
        layout.addLayout(info, stretch=1)

    def set_cover_art(self, image_data: bytes):
        """Set cover art from downloaded image bytes."""
        try:
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    80, 80,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.cover_label.setPixmap(scaled)
        except Exception:
            pass

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.release)
        super().mousePressEvent(event)


class SearchPanel(QWidget):
    """Discogs search panel with results."""

    search_requested = Signal(str)         # query
    release_selected = Signal(object)      # DiscogsRelease

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards = []  # list of ReleaseCard
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header = QLabel("Discogs Search")
        header.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {AMBER};")
        layout.addWidget(header)

        # Search bar
        search_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search artist, album, or catalog number...")
        self.search_input.returnPressed.connect(self._on_search)
        search_row.addWidget(self.search_input, stretch=1)

        self.search_btn = QPushButton("Search")
        self.search_btn.setObjectName("primaryButton")
        self.search_btn.setFixedWidth(80)
        self.search_btn.clicked.connect(self._on_search)
        search_row.addWidget(self.search_btn)

        layout.addLayout(search_row)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(self.status_label)

        # Results scroll area
        self.results_area = QScrollArea()
        self.results_area.setWidgetResizable(True)
        self.results_area.setFrameShape(QFrame.Shape.NoFrame)

        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(4)
        self.results_layout.addStretch()

        self.results_area.setWidget(self.results_container)
        layout.addWidget(self.results_area, stretch=1)

    def _on_search(self):
        query = self.search_input.text().strip()
        if query:
            self.status_label.setText("Searching...")
            self.search_btn.setEnabled(False)
            self.search_requested.emit(query)

    def set_loading(self, loading: bool):
        self.search_btn.setEnabled(not loading)
        if loading:
            self.status_label.setText("Searching Discogs...")

    def show_results(self, results: list):
        """Display search results.

        Args:
            results: list of (index, DiscogsRelease) tuples
        """
        # Clear previous results
        self._cards.clear()
        while self.results_layout.count() > 1:
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not results:
            self.status_label.setText("No results found")
            self.search_btn.setEnabled(True)
            return

        for idx, release in results:
            card = ReleaseCard(release)
            card.clicked.connect(self._on_release_clicked)
            self.results_layout.insertWidget(self.results_layout.count() - 1, card)
            self._cards.append(card)

        self.status_label.setText(f"{len(results)} results")
        self.search_btn.setEnabled(True)

    def update_cover_art(self, release_id: str, image_data: bytes):
        """Update cover art on matching cards."""
        for card in self._cards:
            if str(card.release.id) == release_id:
                card.set_cover_art(image_data)

    def show_error(self, message: str):
        self.status_label.setText(f"Error: {message}")
        self.search_btn.setEnabled(True)

    def _on_release_clicked(self, release):
        self.release_selected.emit(release)

    def clear(self):
        self._cards.clear()
        while self.results_layout.count() > 1:
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.status_label.setText("")
        self.search_input.clear()
