"""
VinylFlow - Settings Dialog

Configurable audio processing parameters and output directory.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QDoubleSpinBox, QSpinBox, QLineEdit, QPushButton,
    QFileDialog, QGroupBox,
)

from ui.styles import AMBER, TEXT_SECONDARY


class SettingsDialog(QDialog):
    """Settings dialog for audio processing parameters."""

    settings_changed = Signal(dict)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("VinylFlow Settings")
        self.setMinimumSize(480, 520)
        self.setModal(True)
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel("Settings")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {AMBER};")
        layout.addWidget(title)

        # Audio Processing Group
        audio_group = QGroupBox("Audio Processing")
        audio_form = QFormLayout(audio_group)
        audio_form.setSpacing(12)
        audio_form.setContentsMargins(16, 24, 16, 16)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(-80, -10)
        self.threshold_spin.setSuffix(" dB")
        self.threshold_spin.setDecimals(0)
        audio_form.addRow("Silence Threshold:", self.threshold_spin)

        self.min_silence_spin = QDoubleSpinBox()
        self.min_silence_spin.setRange(0.1, 10.0)
        self.min_silence_spin.setSuffix(" s")
        self.min_silence_spin.setSingleStep(0.1)
        audio_form.addRow("Min Silence Duration:", self.min_silence_spin)

        self.min_track_spin = QDoubleSpinBox()
        self.min_track_spin.setRange(5, 300)
        self.min_track_spin.setSuffix(" s")
        self.min_track_spin.setDecimals(0)
        audio_form.addRow("Min Track Length:", self.min_track_spin)

        self.flac_spin = QSpinBox()
        self.flac_spin.setRange(0, 8)
        audio_form.addRow("FLAC Compression:", self.flac_spin)

        layout.addWidget(audio_group)

        # Output Group
        output_group = QGroupBox("Output")
        output_form = QFormLayout(output_group)
        output_form.setSpacing(12)
        output_form.setContentsMargins(16, 24, 16, 16)

        dir_row = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setReadOnly(True)
        dir_row.addWidget(self.output_dir_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.setFixedWidth(90)
        browse_btn.clicked.connect(self._browse_output_dir)
        dir_row.addWidget(browse_btn)

        output_form.addRow("Output Folder:", dir_row)
        layout.addWidget(output_group)

        # Discogs Group
        discogs_group = QGroupBox("Discogs API")
        discogs_form = QFormLayout(discogs_group)
        discogs_form.setSpacing(12)
        discogs_form.setContentsMargins(16, 24, 16, 16)

        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText("Personal Access Token")
        discogs_form.addRow("Token:", self.token_edit)

        layout.addWidget(discogs_group)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def _load_values(self):
        self.threshold_spin.setValue(self.config.default_silence_threshold)
        self.min_silence_spin.setValue(self.config.default_min_silence_duration)
        self.min_track_spin.setValue(self.config.default_min_track_length)
        self.flac_spin.setValue(self.config.default_flac_compression)
        self.output_dir_edit.setText(self.config.default_output_dir)
        self.token_edit.setText(self.config.discogs_token)

    def _browse_output_dir(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", self.output_dir_edit.text()
        )
        if folder:
            self.output_dir_edit.setText(folder)

    def _on_save(self):
        settings = {
            "silence_threshold": self.threshold_spin.value(),
            "min_silence_duration": self.min_silence_spin.value(),
            "min_track_length": self.min_track_spin.value(),
            "flac_compression": self.flac_spin.value(),
            "output_dir": self.output_dir_edit.text(),
            "discogs_token": self.token_edit.text().strip(),
        }
        self.settings_changed.emit(settings)
        self.accept()
