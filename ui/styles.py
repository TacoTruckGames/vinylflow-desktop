"""
VinylFlow - QSS Stylesheet & Color Constants

Dark theme with amber/gold accents matching the VinylFlow brand.
"""

# Color palette
BG_DARK = "#0f0f0f"
BG_MEDIUM = "#1a1a1a"
BG_LIGHT = "#242424"
BG_LIGHTER = "#2e2e2e"
BG_HOVER = "#383838"
BORDER = "#333333"
BORDER_LIGHT = "#444444"

TEXT_PRIMARY = "#e5e5e5"
TEXT_SECONDARY = "#a0a0a0"
TEXT_MUTED = "#666666"

AMBER = "#f59e0b"
AMBER_DARK = "#d97706"
AMBER_DARKER = "#b45309"
AMBER_LIGHT = "#fbbf24"
AMBER_MUTED = "#92400e"

RED = "#ef4444"
RED_DARK = "#dc2626"
GREEN = "#22c55e"
GREEN_DARK = "#16a34a"
BLUE = "#3b82f6"

# Track region colors (translucent)
TRACK_COLORS = [
    "#f59e0b",  # amber
    "#3b82f6",  # blue
    "#22c55e",  # green
    "#ef4444",  # red
    "#a855f7",  # purple
    "#ec4899",  # pink
    "#06b6d4",  # cyan
    "#f97316",  # orange
]


def get_stylesheet() -> str:
    return f"""
    /* Global */
    QWidget {{
        background-color: {BG_DARK};
        color: {TEXT_PRIMARY};
        font-size: 13px;
    }}

    /* Main Window */
    QMainWindow {{
        background-color: {BG_DARK};
    }}

    QMainWindow::separator {{
        background: {BORDER};
        width: 1px;
        height: 1px;
    }}

    /* Scroll Areas */
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}

    QScrollBar:vertical {{
        background: {BG_MEDIUM};
        width: 8px;
        margin: 0;
        border-radius: 4px;
    }}

    QScrollBar::handle:vertical {{
        background: {BORDER_LIGHT};
        min-height: 30px;
        border-radius: 4px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {TEXT_MUTED};
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QScrollBar:horizontal {{
        background: {BG_MEDIUM};
        height: 8px;
        margin: 0;
        border-radius: 4px;
    }}

    QScrollBar::handle:horizontal {{
        background: {BORDER_LIGHT};
        min-width: 30px;
        border-radius: 4px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {TEXT_MUTED};
    }}

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* Labels */
    QLabel {{
        background-color: transparent;
        padding: 0;
    }}

    /* Buttons */
    QPushButton {{
        background-color: {BG_LIGHTER};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: bold;
    }}

    QPushButton:hover {{
        background-color: {BG_HOVER};
        border-color: {BORDER_LIGHT};
    }}

    QPushButton:pressed {{
        background-color: {BG_LIGHT};
    }}

    QPushButton:disabled {{
        color: {TEXT_MUTED};
        background-color: {BG_MEDIUM};
        border-color: {BORDER};
    }}

    QPushButton#primaryButton {{
        background-color: {AMBER};
        color: #000000;
        border: none;
        font-weight: bold;
    }}

    QPushButton#primaryButton:hover {{
        background-color: {AMBER_LIGHT};
    }}

    QPushButton#primaryButton:pressed {{
        background-color: {AMBER_DARK};
    }}

    QPushButton#primaryButton:disabled {{
        background-color: {AMBER_MUTED};
        color: {TEXT_MUTED};
    }}

    QPushButton#dangerButton {{
        background-color: {RED_DARK};
        color: white;
        border: none;
    }}

    QPushButton#dangerButton:hover {{
        background-color: {RED};
    }}

    /* Line Edit */
    QLineEdit {{
        background-color: {BG_LIGHT};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 8px 12px;
        selection-background-color: {AMBER_DARK};
    }}

    QLineEdit:focus {{
        border-color: {AMBER};
    }}

    /* Spin Boxes */
    QSpinBox, QDoubleSpinBox {{
        background-color: {BG_LIGHT};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 6px 10px;
    }}

    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {AMBER};
    }}

    QSpinBox::up-button, QDoubleSpinBox::up-button,
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        background-color: {BG_LIGHTER};
        border: none;
        width: 20px;
    }}

    /* Combo Box */
    QComboBox {{
        background-color: {BG_LIGHT};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 6px 10px;
        min-width: 100px;
    }}

    QComboBox:focus {{
        border-color: {AMBER};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {BG_LIGHT};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        selection-background-color: {AMBER_DARK};
    }}

    /* Check Box */
    QCheckBox {{
        spacing: 8px;
        background-color: transparent;
    }}

    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {BORDER_LIGHT};
        border-radius: 4px;
        background-color: {BG_LIGHT};
    }}

    QCheckBox::indicator:checked {{
        background-color: {AMBER};
        border-color: {AMBER};
    }}

    /* Progress Bar */
    QProgressBar {{
        background-color: {BG_LIGHT};
        border: 1px solid {BORDER};
        border-radius: 6px;
        text-align: center;
        color: {TEXT_PRIMARY};
        min-height: 20px;
    }}

    QProgressBar::chunk {{
        background-color: {AMBER};
        border-radius: 5px;
    }}

    /* Group Box */
    QGroupBox {{
        border: 1px solid {BORDER};
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 20px;
        font-weight: bold;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        color: {AMBER};
    }}

    /* Tab Widget */
    QTabWidget::pane {{
        border: 1px solid {BORDER};
        border-radius: 0 0 8px 8px;
        background-color: {BG_MEDIUM};
    }}

    QTabBar::tab {{
        background-color: {BG_LIGHTER};
        color: {TEXT_SECONDARY};
        border: 1px solid {BORDER};
        border-bottom: none;
        padding: 8px 20px;
        margin-right: 2px;
        border-radius: 6px 6px 0 0;
    }}

    QTabBar::tab:selected {{
        background-color: {BG_MEDIUM};
        color: {AMBER};
        border-color: {BORDER};
    }}

    QTabBar::tab:hover {{
        color: {TEXT_PRIMARY};
    }}

    /* List Widget */
    QListWidget {{
        background-color: {BG_MEDIUM};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 4px;
    }}

    QListWidget::item {{
        padding: 8px;
        border-radius: 4px;
    }}

    QListWidget::item:selected {{
        background-color: {AMBER_MUTED};
        color: {TEXT_PRIMARY};
    }}

    QListWidget::item:hover {{
        background-color: {BG_HOVER};
    }}

    /* Table Widget */
    QTableWidget {{
        background-color: {BG_MEDIUM};
        border: 1px solid {BORDER};
        border-radius: 6px;
        gridline-color: {BORDER};
    }}

    QTableWidget::item {{
        padding: 6px;
    }}

    QTableWidget::item:selected {{
        background-color: {AMBER_MUTED};
    }}

    QHeaderView::section {{
        background-color: {BG_LIGHTER};
        color: {TEXT_SECONDARY};
        border: none;
        border-right: 1px solid {BORDER};
        border-bottom: 1px solid {BORDER};
        padding: 6px 10px;
        font-weight: bold;
    }}

    /* Splitter */
    QSplitter::handle {{
        background-color: {BORDER};
    }}

    QSplitter::handle:horizontal {{
        width: 2px;
    }}

    QSplitter::handle:vertical {{
        height: 2px;
    }}

    /* Dialog */
    QDialog {{
        background-color: {BG_DARK};
    }}

    /* Menu */
    QMenu {{
        background-color: {BG_LIGHT};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 4px;
    }}

    QMenu::item {{
        padding: 6px 24px;
        border-radius: 4px;
    }}

    QMenu::item:selected {{
        background-color: {AMBER_MUTED};
    }}

    QMenu::separator {{
        height: 1px;
        background-color: {BORDER};
        margin: 4px 8px;
    }}

    /* Tooltip */
    QToolTip {{
        background-color: {BG_LIGHTER};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 4px 8px;
    }}

    /* Frame */
    QFrame#separator {{
        background-color: {BORDER};
        max-height: 1px;
    }}
    """
