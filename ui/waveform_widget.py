"""
VinylFlow - Waveform Widget

QGraphicsView-based waveform display with draggable track regions.
Replaces WaveSurfer.js functionality.
"""

from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QUrl, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QCursor, QFont, QIcon, QPixmap,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsRectItem, QGraphicsLineItem,
    QPushButton, QLabel, QMenu, QSlider, QApplication,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from ui.styles import (
    AMBER, AMBER_DARK, BG_DARK, BG_MEDIUM, BG_LIGHT, BORDER, BORDER_LIGHT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TRACK_COLORS,
)


WAVEFORM_HEIGHT = 200
HANDLE_WIDTH = 6


def _make_play_icon(size: int = 20) -> QIcon:
    """Draw a solid play triangle."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(QColor(TEXT_SECONDARY)))
    p.setPen(QPen(Qt.PenStyle.NoPen))
    p.drawPolygon([QPointF(4, 2), QPointF(4, size - 2), QPointF(size - 2, size / 2)])
    p.end()
    return QIcon(pixmap)


def _make_pause_icon(size: int = 20) -> QIcon:
    """Draw two vertical bars for pause."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(QColor(TEXT_SECONDARY)))
    p.setPen(QPen(Qt.PenStyle.NoPen))
    bar_w = 4
    p.drawRect(4, 3, bar_w, size - 6)
    p.drawRect(size - 4 - bar_w, 3, bar_w, size - 6)
    p.end()
    return QIcon(pixmap)


def _make_stop_icon(size: int = 20) -> QIcon:
    """Draw a solid square for stop."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(QColor(TEXT_SECONDARY)))
    p.setPen(QPen(Qt.PenStyle.NoPen))
    margin = 4
    p.drawRect(margin, margin, size - margin * 2, size - margin * 2)
    p.end()
    return QIcon(pixmap)


def _make_zoom_icon(sign: str, size: int = 20) -> QIcon:
    """Draw a magnifying glass icon with + or - sign."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Glass circle
    pen = QPen(QColor(TEXT_SECONDARY))
    pen.setWidth(2)
    p.setPen(pen)
    p.drawEllipse(2, 2, 12, 12)

    # Handle
    p.drawLine(12, 12, 17, 17)

    # + or - sign inside circle
    pen.setWidth(2)
    p.setPen(pen)
    if sign == "+":
        p.drawLine(5, 8, 11, 8)
        p.drawLine(8, 5, 8, 11)
    else:
        p.drawLine(5, 8, 11, 8)

    p.end()
    return QIcon(pixmap)


class WaveformBarsItem(QGraphicsItem):
    """Draws the waveform as vertical bars."""

    def __init__(self, peaks: list, duration: float):
        super().__init__()
        self.peaks = peaks
        self.duration = duration
        self.width = len(peaks)
        self.height = WAVEFORM_HEIGHT
        self.setZValue(0)

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        mid = self.height / 2
        pen = QPen()
        pen.setWidth(1)

        for i, peak in enumerate(self.peaks):
            bar_height = peak * mid * 0.95
            brightness = 80 + int(peak * 175)
            pen.setColor(QColor(brightness, brightness, brightness))
            painter.setPen(pen)
            painter.drawLine(
                QPointF(i, mid - bar_height),
                QPointF(i, mid + bar_height),
            )


class RegionHandle(QGraphicsRectItem):
    """Draggable handle on the edge of a track region."""

    def __init__(self, region, side: str, scene_height: float):
        width = HANDLE_WIDTH
        super().__init__(0, 0, width, scene_height)
        self.region = region
        self.side = side  # "left" or "right"
        self.setBrush(QBrush(QColor(255, 255, 255, 60)))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        self.setZValue(30)
        self._dragging = False

    def mousePressEvent(self, event):
        self._dragging = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        if self.region and self.region.waveform_view:
            self.region.waveform_view.regions_changed.emit()
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self._dragging:
            new_x = value.x()
            # Constrain to scene bounds
            scene_width = 0
            if self.scene():
                scene_width = self.scene().width()
            new_x = max(0, min(new_x, scene_width - HANDLE_WIDTH))
            # Notify region of handle move
            if self.region:
                self.region.handle_moved(self.side, new_x)
            return QPointF(new_x, self.pos().y())
        return super().itemChange(change, value)


class TrackRegionItem(QGraphicsRectItem):
    """Colored region representing a track on the waveform."""

    def __init__(self, track_number: int, start_x: float, end_x: float,
                 height: float, waveform_view):
        super().__init__(start_x, 0, end_x - start_x, height)
        self.track_number = track_number
        self.waveform_view = waveform_view
        self._height = height

        color_idx = (track_number - 1) % len(TRACK_COLORS)
        self._base_color = QColor(TRACK_COLORS[color_idx])

        fill = QColor(self._base_color)
        fill.setAlpha(40)
        self.setBrush(QBrush(fill))

        border = QColor(self._base_color)
        border.setAlpha(120)
        self.setPen(QPen(border, 1))
        self.setZValue(10)

        # Track number label
        self._label = None

        # Handles
        self.left_handle = RegionHandle(self, "left", height)
        self.right_handle = RegionHandle(self, "right", height)

    def add_to_scene(self, scene: QGraphicsScene):
        scene.addItem(self)
        scene.addItem(self.left_handle)
        scene.addItem(self.right_handle)
        self._update_handle_positions()

    def remove_from_scene(self, scene: QGraphicsScene):
        if self.scene():
            scene.removeItem(self)
        if self.left_handle.scene():
            scene.removeItem(self.left_handle)
        if self.right_handle.scene():
            scene.removeItem(self.right_handle)

    def _update_handle_positions(self):
        rect = self.rect()
        self.left_handle.setPos(rect.x(), 0)
        self.right_handle.setPos(rect.x() + rect.width() - HANDLE_WIDTH, 0)

    def handle_moved(self, side: str, new_x: float):
        rect = self.rect()
        if side == "left":
            old_right = rect.x() + rect.width()
            new_x = min(new_x, old_right - 10)  # minimum region width
            self.setRect(QRectF(new_x, 0, old_right - new_x, self._height))
        else:
            new_right = new_x + HANDLE_WIDTH
            new_right = max(new_right, rect.x() + 10)
            self.setRect(QRectF(rect.x(), 0, new_right - rect.x(), self._height))
        self._update_handle_positions()

    def start_x(self) -> float:
        return self.rect().x()

    def end_x(self) -> float:
        return self.rect().x() + self.rect().width()

    def contextMenuEvent(self, event):
        if self.waveform_view:
            self.waveform_view._show_region_context_menu(
                event.screenPos(), self.track_number
            )


class PlaybackCursor(QGraphicsLineItem):
    """Vertical line showing current playback position."""

    def __init__(self, height: float):
        super().__init__(0, 0, 0, height)
        pen = QPen(QColor(AMBER))
        pen.setWidthF(2.0)
        pen.setCosmetic(True)  # constant screen width regardless of zoom
        self.setPen(pen)
        self.setZValue(50)
        self.hide()


class WaveformWidget(QWidget):
    """Waveform display with track regions and controls."""

    regions_changed = Signal()           # emitted when regions are dragged
    split_added = Signal(float)          # time in seconds where split was added
    track_deleted = Signal(int)          # track number
    track_preview = Signal(int)          # track number to preview

    def __init__(self, parent=None):
        super().__init__(parent)
        self._peaks = []
        self._duration = 0.0
        self._regions = []        # list of TrackRegionItem
        self._waveform_item = None
        self._cursor = None
        self._player = None
        self._audio_output = None
        self._current_zoom = 1.0
        self._source_path = None
        self._cursor_timer = QTimer(self)
        self._cursor_timer.setInterval(30)  # ~33fps
        self._cursor_timer.timeout.connect(self._update_cursor_position)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Controls bar
        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.zoom_out_btn = QPushButton()
        self.zoom_out_btn.setIcon(_make_zoom_icon("-"))
        self.zoom_out_btn.setFixedSize(28, 28)
        self.zoom_out_btn.setToolTip("Zoom out")
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        controls.addWidget(self.zoom_out_btn)

        self.zoom_label = QLabel("1x")
        self.zoom_label.setFixedWidth(32)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        controls.addWidget(self.zoom_label)

        self.zoom_in_btn = QPushButton()
        self.zoom_in_btn.setIcon(_make_zoom_icon("+"))
        self.zoom_in_btn.setFixedSize(28, 28)
        self.zoom_in_btn.setToolTip("Zoom in")
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        controls.addWidget(self.zoom_in_btn)

        controls.addSpacing(16)

        # Playback controls
        self.play_btn = QPushButton()
        self.play_btn.setIcon(_make_play_icon())
        self.play_btn.setFixedSize(28, 28)
        self.play_btn.setToolTip("Play")
        self.play_btn.clicked.connect(self._on_play)
        controls.addWidget(self.play_btn)

        self.pause_btn = QPushButton()
        self.pause_btn.setIcon(_make_pause_icon())
        self.pause_btn.setFixedSize(28, 28)
        self.pause_btn.setToolTip("Pause")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause)
        controls.addWidget(self.pause_btn)

        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(_make_stop_icon())
        self.stop_btn.setFixedSize(28, 28)
        self.stop_btn.setToolTip("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        controls.addWidget(self.stop_btn)

        controls.addStretch()

        self.time_label = QLabel("")
        self.time_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        controls.addWidget(self.time_label)

        layout.addLayout(controls)

        # Graphics view
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.view.setStyleSheet(f"background-color: {BG_DARK};")
        self.view.setMinimumHeight(WAVEFORM_HEIGHT + 20)
        self.view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)

        # Enable context menu on the view
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._on_view_context_menu)

        # Click-to-seek: intercept mouse events on the view
        self.view.viewport().installEventFilter(self)

        layout.addWidget(self.view)

        # Accept keyboard focus for spacebar
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Time axis
        self._time_axis = QLabel("")
        self._time_axis.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
        self._time_axis.setFixedHeight(16)
        layout.addWidget(self._time_axis)

    def load_peaks(self, peaks: list, duration: float, source_path: str = None):
        """Load waveform peaks and display."""
        self._stop_playback()
        self._peaks = peaks
        self._duration = duration
        self._source_path = source_path
        self._current_zoom = 1.0

        self.scene.clear()
        self._regions = []

        self._waveform_item = WaveformBarsItem(peaks, duration)
        self.scene.addItem(self._waveform_item)

        self._cursor = PlaybackCursor(WAVEFORM_HEIGHT)
        self.scene.addItem(self._cursor)

        self.scene.setSceneRect(0, 0, len(peaks), WAVEFORM_HEIGHT)
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.IgnoreAspectRatio)

        mins = int(duration // 60)
        secs = int(duration % 60)
        self.time_label.setText(f"{mins}:{secs:02d}")
        self.zoom_label.setText("1x")
        self._set_playback_buttons("stopped")

    def set_track_regions(self, tracks: list):
        """Set track regions from a list of Track objects.

        Args:
            tracks: list of audio_processor.Track objects with .start, .end, .number
        """
        # Remove existing regions
        for region in self._regions:
            region.remove_from_scene(self.scene)
        self._regions = []

        if not self._peaks or self._duration <= 0:
            return

        px_per_sec = len(self._peaks) / self._duration

        for track in tracks:
            start_x = track.start * px_per_sec
            end_x = track.end * px_per_sec
            region = TrackRegionItem(
                track.number, start_x, end_x, WAVEFORM_HEIGHT, self
            )
            region.add_to_scene(self.scene)
            self._regions.append(region)

    def get_track_boundaries(self) -> list:
        """Return current track boundaries as list of dicts.

        Returns:
            List of {number, start, end, duration} dicts
        """
        if not self._peaks or self._duration <= 0:
            return []

        px_per_sec = len(self._peaks) / self._duration
        boundaries = []
        for region in self._regions:
            start = region.start_x() / px_per_sec
            end = region.end_x() / px_per_sec
            boundaries.append({
                "number": region.track_number,
                "start": max(0, start),
                "end": min(self._duration, end),
                "duration": end - start,
            })
        boundaries.sort(key=lambda b: b["start"])
        # Renumber
        for i, b in enumerate(boundaries):
            b["number"] = i + 1
        return boundaries

    def add_split_at_time(self, time_sec: float):
        """Add a split at the given time, splitting the region that contains it."""
        if not self._peaks or self._duration <= 0:
            return

        px_per_sec = len(self._peaks) / self._duration
        split_x = time_sec * px_per_sec

        # Find region containing this point
        target = None
        for region in self._regions:
            if region.start_x() < split_x < region.end_x():
                target = region
                break

        if not target:
            return

        # Split into two
        old_start = target.start_x()
        old_end = target.end_x()
        target.remove_from_scene(self.scene)
        self._regions.remove(target)

        # Renumber all regions
        boundaries = self.get_track_boundaries()
        # Add the new split
        new_boundaries = []
        for b in boundaries:
            start_x = b["start"] * px_per_sec
            end_x = b["end"] * px_per_sec
            if start_x < split_x < end_x:
                new_boundaries.append({
                    "start": b["start"],
                    "end": time_sec,
                })
                new_boundaries.append({
                    "start": time_sec,
                    "end": b["end"],
                })
            else:
                new_boundaries.append({
                    "start": b["start"],
                    "end": b["end"],
                })

        # Rebuild regions
        for region in self._regions:
            region.remove_from_scene(self.scene)
        self._regions = []

        for i, b in enumerate(new_boundaries):
            start_x = b["start"] * px_per_sec
            end_x = b["end"] * px_per_sec
            region = TrackRegionItem(
                i + 1, start_x, end_x, WAVEFORM_HEIGHT, self
            )
            region.add_to_scene(self.scene)
            self._regions.append(region)

        self.regions_changed.emit()

    def delete_track(self, track_number: int):
        """Delete a track region by number, merging with the next region."""
        target = None
        for region in self._regions:
            if region.track_number == track_number:
                target = region
                break

        if not target:
            return

        target.remove_from_scene(self.scene)
        self._regions.remove(target)

        # Renumber remaining regions
        self._regions.sort(key=lambda r: r.start_x())
        for i, region in enumerate(self._regions):
            if region.track_number != i + 1:
                # Create new region with correct number
                old = region
                new_region = TrackRegionItem(
                    i + 1, old.start_x(), old.end_x(), WAVEFORM_HEIGHT, self
                )
                old.remove_from_scene(self.scene)
                new_region.add_to_scene(self.scene)
                self._regions[i] = new_region

        self.regions_changed.emit()

    def _on_view_context_menu(self, pos):
        scene_pos = self.view.mapToScene(pos)
        if not self._peaks or self._duration <= 0:
            return

        px_per_sec = len(self._peaks) / self._duration
        time_sec = scene_pos.x() / px_per_sec

        if time_sec < 0 or time_sec > self._duration:
            return

        menu = QMenu(self)
        mins = int(time_sec // 60)
        secs = int(time_sec % 60)

        add_split = menu.addAction(f"Add split at {mins}:{secs:02d}")
        add_split.triggered.connect(lambda: self.split_added.emit(time_sec))

        menu.exec(self.view.mapToGlobal(pos))

    def _show_region_context_menu(self, screen_pos, track_number: int):
        menu = QMenu(self)

        preview_action = menu.addAction(f"Preview Track {track_number}")
        preview_action.triggered.connect(lambda: self.track_preview.emit(track_number))

        menu.addSeparator()

        # Get the time at the click position for split
        split_action = menu.addAction("Add split here")
        split_action.triggered.connect(lambda: self._split_region_at_center(track_number))

        if len(self._regions) > 1:
            delete_action = menu.addAction(f"Delete Track {track_number}")
            delete_action.triggered.connect(lambda: self.track_deleted.emit(track_number))

        menu.exec(screen_pos.toPoint())

    def _split_region_at_center(self, track_number: int):
        for region in self._regions:
            if region.track_number == track_number:
                px_per_sec = len(self._peaks) / self._duration
                center_time = (region.start_x() + region.end_x()) / 2 / px_per_sec
                self.split_added.emit(center_time)
                break

    def _zoom_in(self):
        if self._current_zoom < 16:
            self._current_zoom *= 2
            self._apply_zoom()

    def _zoom_out(self):
        if self._current_zoom > 1:
            self._current_zoom /= 2
            self._apply_zoom()

    def _apply_zoom(self):
        if not self._peaks:
            return
        self.view.resetTransform()
        self.view.scale(self._current_zoom, 1.0)
        level = int(self._current_zoom) if self._current_zoom >= 1 else self._current_zoom
        self.zoom_label.setText(f"{level}x")

        # Center the view on the playback cursor position
        if self._cursor and self._cursor.isVisible():
            self.view.centerOn(self._cursor.pos().x(), WAVEFORM_HEIGHT / 2)
        elif self._player and self._peaks and self._duration > 0:
            position_sec = self._player.position() / 1000.0
            px_per_sec = len(self._peaks) / self._duration
            self.view.centerOn(position_sec * px_per_sec, WAVEFORM_HEIGHT / 2)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._toggle_play_pause()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _toggle_play_pause(self):
        if not self._source_path or not self._peaks:
            return
        if self._player and self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._on_pause()
        elif self._player and self._player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self._player.play()
            self._set_playback_buttons("playing")
        else:
            self._on_play()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self.view.viewport():
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    # Check if the click is on a region handle — if so, let it through
                    scene_pos = self.view.mapToScene(event.pos())
                    item = self.scene.itemAt(scene_pos, self.view.transform())
                    if not isinstance(item, RegionHandle):
                        self._seek_to_scene_pos(scene_pos)
                        self.setFocus()
                        return True
            elif event.type() == QEvent.Type.Wheel:
                delta = event.angleDelta().y()
                if delta > 0:
                    self._zoom_in()
                elif delta < 0:
                    self._zoom_out()
                return True
        return super().eventFilter(obj, event)

    def _seek_to_scene_pos(self, scene_pos):
        if not self._peaks or self._duration <= 0 or not self._source_path:
            return
        px_per_sec = len(self._peaks) / self._duration
        time_sec = max(0.0, min(scene_pos.x() / px_per_sec, self._duration))
        self.play_from_time(time_sec)

    def play_from_time(self, time_sec: float):
        """Play the source audio from the given time position."""
        if not self._source_path or not self._peaks:
            return

        was_playing = (self._player and
                       self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)

        if not self._player:
            self._init_player()
            self._player.setSource(QUrl.fromLocalFile(self._source_path))

        self._player.setPosition(int(time_sec * 1000))

        if not was_playing:
            # Need to play first, then seek (QMediaPlayer needs to be playing to seek on some backends)
            self._player.play()
            # Use a single-shot timer to seek after playback starts
            QTimer.singleShot(50, lambda: self._player.setPosition(int(time_sec * 1000)) if self._player else None)
        self._set_playback_buttons("playing")

        # Immediately update cursor position
        if self._cursor:
            px_per_sec = len(self._peaks) / self._duration
            self._cursor.setPos(time_sec * px_per_sec, 0)
            self._cursor.show()

    def clear(self):
        """Clear all waveform data."""
        self._stop_playback()
        self.scene.clear()
        self._regions = []
        self._waveform_item = None
        self._cursor = None
        self._peaks = []
        self._duration = 0
        self._source_path = None
        self.time_label.setText("")
        self._set_playback_buttons("stopped")

    def play_preview(self, mp3_path: str):
        """Play an MP3 preview file."""
        self._stop_playback()
        self._init_player()
        self._player.setSource(QUrl.fromLocalFile(mp3_path))
        self._player.play()
        self._set_playback_buttons("playing")

    def _init_player(self):
        """Create a fresh QMediaPlayer + QAudioOutput."""
        self._audio_output = QAudioOutput()
        self._audio_output.setVolume(1.0)
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)

    def _first_region_start_sec(self) -> float:
        """Return the start time of the first track region, or 0.0 if none."""
        if not self._regions or not self._peaks or self._duration <= 0:
            return 0.0
        px_per_sec = len(self._peaks) / self._duration
        starts = [r.start_x() / px_per_sec for r in self._regions]
        return max(0.0, min(starts))

    def _on_play(self):
        """Play the source audio from the first analyzed region."""
        if not self._source_path or not self._peaks:
            return

        if self._player and self._player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self._player.play()
            self._set_playback_buttons("playing")
            return

        start_sec = self._first_region_start_sec()
        self.play_from_time(start_sec)

    def _on_pause(self):
        if self._player and self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
            self._set_playback_buttons("paused")

    def _on_stop(self):
        self._stop_playback()

    def _stop_playback(self):
        self._cursor_timer.stop()
        if self._player:
            self._player.stop()
            self._player.deleteLater()
            self._player = None
        if self._audio_output:
            self._audio_output.deleteLater()
            self._audio_output = None
        if self._cursor:
            self._cursor.hide()
        self._set_playback_buttons("stopped")

    def _on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._cursor_timer.start()
            if self._cursor:
                self._cursor.show()
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self._cursor_timer.stop()
            if self._cursor:
                self._cursor.hide()
            self._set_playback_buttons("stopped")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._cursor_timer.stop()

    def _update_cursor_position(self):
        if not self._player or not self._peaks or self._duration <= 0:
            return
        position_ms = self._player.position()
        position_sec = position_ms / 1000.0
        px_per_sec = len(self._peaks) / self._duration
        cursor_x = position_sec * px_per_sec
        if self._cursor:
            self._cursor.setPos(cursor_x, 0)
        # Update time display
        mins = int(position_sec // 60)
        secs = int(position_sec % 60)
        total_mins = int(self._duration // 60)
        total_secs = int(self._duration % 60)
        self.time_label.setText(f"{mins}:{secs:02d} / {total_mins}:{total_secs:02d}")

    def _set_playback_buttons(self, state: str):
        has_source = bool(self._source_path and self._peaks)
        self.play_btn.setEnabled(has_source and state != "playing")
        self.pause_btn.setEnabled(state == "playing")
        self.stop_btn.setEnabled(state in ("playing", "paused"))
