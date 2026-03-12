"""
VinylFlow - First-Run Setup Dialog

Prompts the user for their Discogs API token on first launch.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox,
)

from ui.styles import AMBER, TEXT_SECONDARY


class SetupDialog(QDialog):
    """First-run dialog to configure Discogs API token."""

    token_saved = Signal(str, str)  # token, user_agent

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VinylFlow Setup")
        self.setFixedSize(500, 340)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 32)

        # Title
        title = QLabel("Welcome to VinylFlow")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {AMBER};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "To search for album metadata, VinylFlow needs a Discogs API token.\n\n"
            "1. Go to discogs.com/settings/developers\n"
            "2. Click 'Generate new token'\n"
            "3. Copy the token and paste it below"
        )
        desc.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        layout.addSpacing(8)

        # Token input
        token_label = QLabel("Discogs Personal Access Token:")
        token_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(token_label)

        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Paste your token here...")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.token_input)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        skip_btn = QPushButton("Skip for Now")
        skip_btn.clicked.connect(self.reject)
        btn_row.addWidget(skip_btn)

        save_btn = QPushButton("Save && Connect")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def _on_save(self):
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "Missing Token", "Please enter a Discogs API token.")
            return

        # Validate token
        try:
            import discogs_client
            client = discogs_client.Client("VinylFlow/1.0", user_token=token)
            identity = client.identity()
            username = identity.username
        except Exception as e:
            QMessageBox.critical(
                self, "Invalid Token",
                f"Could not connect to Discogs:\n{e}\n\nPlease check your token."
            )
            return

        self.token_saved.emit(token, "VinylFlow/1.0")
        QMessageBox.information(
            self, "Connected",
            f"Successfully connected as: {username}"
        )
        self.accept()
