# galaxytrackpad_gui.py
# Galaxy Trackpad v0.5
# Windows GUI Prototype

import sys
import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QCheckBox,
    QComboBox,
    QFrame,
)


# ==========================================
# 1. Configuration
# ==========================================

ROOT = Path(__file__).resolve().parent

CONFIG_FILE = ROOT / "galaxytrackpad_settings.json"

DEFAULT_CONFIG = {
    "cursor_sensitivity": 1.0,
    "scroll_sensitivity": 1.0,
    "pen_enabled": True,
    "pen_monitor": "Primary Monitor",
    "auto_connect": True,
}


def load_config():

    if CONFIG_FILE.exists():

        try:

            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)

            return {
                **DEFAULT_CONFIG,
                **saved
            }

        except (OSError, ValueError):
            print("Could not load settings. Using defaults.")

    return DEFAULT_CONFIG.copy()


def save_config(config):

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(
            config,
            f,
            indent=4,
            ensure_ascii=False
        )


# ==========================================
# 2. Main Window
# ==========================================

class GalaxyTrackpadWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.config = load_config()

        self.setWindowTitle("Galaxy Trackpad")

        self.resize(520, 710)
        self.setMinimumSize(460, 650)

        self.setup_ui()
        self.apply_style()


    # ======================================
    # UI helpers
    # ======================================

    def section_title(self, text):

        label = QLabel(text)
        label.setObjectName("sectionTitle")

        return label


    def card(self):

        frame = QFrame()
        frame.setObjectName("card")

        layout = QVBoxLayout(frame)

        layout.setContentsMargins(
            20, 18, 20, 18
        )

        layout.setSpacing(13)

        return frame, layout


    def create_slider(
        self,
        title,
        key
    ):

        container = QWidget()

        layout = QVBoxLayout(container)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()

        name = QLabel(title)

        value_label = QLabel()
        value_label.setObjectName("valueLabel")

        header.addWidget(name)
        header.addStretch()
        header.addWidget(value_label)

        slider = QSlider(Qt.Orientation.Horizontal)

        slider.setMinimum(50)
        slider.setMaximum(200)

        slider.setSingleStep(5)

        current = self.config[key]

        slider.setValue(
            round(current * 100)
        )

        value_label.setText(
            f"{current:.2f}x"
        )

        def update(value):

            sensitivity = value / 100.0

            value_label.setText(
                f"{sensitivity:.2f}x"
            )

            self.config[key] = sensitivity

            self.save_settings()

        slider.valueChanged.connect(update)

        layout.addLayout(header)
        layout.addWidget(slider)

        return container


    def save_settings(self):

        try:

            save_config(self.config)

        except OSError as error:

            print(
                "Failed to save settings:",
                error
            )


    # ======================================
    # Build UI
    # ======================================

    def setup_ui(self):

        central = QWidget()

        self.setCentralWidget(central)

        main = QVBoxLayout(central)

        main.setContentsMargins(
            28, 26, 28, 25
        )

        main.setSpacing(18)


        # ----------------------------------
        # Header
        # ----------------------------------

        title = QLabel("Galaxy Trackpad")

        title.setObjectName("mainTitle")

        subtitle = QLabel(
            "Turn your Galaxy Tab into a Windows touchpad"
        )

        subtitle.setObjectName("subtitle")

        main.addWidget(title)
        main.addWidget(subtitle)


        # ----------------------------------
        # Device Status
        # ----------------------------------

        main.addWidget(
            self.section_title("DEVICE")
        )

        device_card, device_layout = self.card()

        device_name = QLabel("Galaxy Tab S7")

        device_name.setObjectName("deviceName")

        self.status_label = QLabel(
            "●  Engine not started"
        )

        self.status_label.setObjectName("statusLabel")

        device_layout.addWidget(device_name)
        device_layout.addWidget(self.status_label)

        self.touch_status = QLabel(
            "Touchpad     Not running"
        )

        self.pen_status = QLabel(
            "S Pen          Not running"
        )

        device_layout.addWidget(self.touch_status)
        device_layout.addWidget(self.pen_status)

        main.addWidget(device_card)


        # ----------------------------------
        # Start / Stop
        # ----------------------------------

        buttons = QHBoxLayout()

        self.start_button = QPushButton(
            "▶  START"
        )

        self.start_button.setObjectName(
            "startButton"
        )

        self.stop_button = QPushButton(
            "■  STOP"
        )

        self.stop_button.setObjectName(
            "stopButton"
        )

        # Engine integration comes next.
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        buttons.addWidget(
            self.start_button
        )

        buttons.addWidget(
            self.stop_button
        )

        main.addLayout(buttons)


        # ----------------------------------
        # Touchpad Settings
        # ----------------------------------

        main.addWidget(
            self.section_title("TOUCHPAD")
        )

        touch_card, touch_layout = self.card()

        touch_layout.addWidget(
            self.create_slider(
                "Cursor sensitivity",
                "cursor_sensitivity"
            )
        )

        touch_layout.addWidget(
            self.create_slider(
                "Scroll sensitivity",
                "scroll_sensitivity"
            )
        )

        main.addWidget(touch_card)


        # ----------------------------------
        # Pen Settings
        # ----------------------------------

        main.addWidget(
            self.section_title("S PEN")
        )

        pen_card, pen_layout = self.card()

        self.pen_checkbox = QCheckBox(
            "Enable S Pen"
        )

        self.pen_checkbox.setChecked(
            self.config["pen_enabled"]
        )

        self.pen_checkbox.toggled.connect(
            self.update_pen_setting
        )

        pen_layout.addWidget(
            self.pen_checkbox
        )

        monitor_row = QHBoxLayout()

        monitor_label = QLabel(
            "Target display"
        )

        self.monitor_combo = QComboBox()

        # Monitor detection will be added later.
        self.monitor_combo.addItems([
            "Primary Monitor"
        ])

        monitor_row.addWidget(
            monitor_label
        )

        monitor_row.addStretch()

        monitor_row.addWidget(
            self.monitor_combo
        )

        pen_layout.addLayout(
            monitor_row
        )

        main.addWidget(pen_card)


        # ----------------------------------
        # General Settings
        # ----------------------------------

        self.autoconnect_checkbox = QCheckBox(
            "Connect automatically"
        )

        self.autoconnect_checkbox.setChecked(
            self.config["auto_connect"]
        )

        self.autoconnect_checkbox.toggled.connect(
            self.update_autoconnect
        )

        main.addWidget(
            self.autoconnect_checkbox
        )


        # ----------------------------------
        # Footer
        # ----------------------------------

        main.addStretch()

        footer = QLabel(
            "Galaxy Trackpad v0.5  •  GUI Preview"
        )

        footer.setObjectName(
            "footer"
        )

        footer.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        main.addWidget(footer)


    # ======================================
    # Settings handlers
    # ======================================

    def update_pen_setting(self, checked):

        self.config["pen_enabled"] = checked

        self.save_settings()


    def update_autoconnect(self, checked):

        self.config["auto_connect"] = checked

        self.save_settings()


    # ======================================
    # Styling
    # ======================================

    def apply_style(self):

        self.setStyleSheet("""

            QMainWindow {
                background-color: #111827;
            }

            QWidget {
                color: #e5e7eb;
                font-family: "Segoe UI";
                font-size: 13px;
            }

            QLabel#mainTitle {
                font-size: 29px;
                font-weight: 700;
                color: #ffffff;
            }

            QLabel#subtitle {
                font-size: 12px;
                color: #9ca3af;
            }

            QLabel#sectionTitle {
                font-size: 11px;
                font-weight: 700;
                color: #9ca3af;
                padding-top: 3px;
            }

            QFrame#card {
                background-color: #1f2937;
                border: 1px solid #374151;
                border-radius: 12px;
            }

            QLabel#deviceName {
                font-size: 17px;
                font-weight: 600;
            }

            QLabel#statusLabel {
                color: #fbbf24;
                font-size: 12px;
            }

            QLabel#valueLabel {
                color: #60a5fa;
                font-weight: 600;
            }

            QPushButton {
                padding: 12px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }

            QPushButton#startButton {
                background-color: #2563eb;
                color: white;
            }

            QPushButton#startButton:hover {
                background-color: #1d4ed8;
            }

            QPushButton#stopButton {
                background-color: #374151;
                color: white;
            }

            QPushButton:disabled {
                background-color: #374151;
                color: #6b7280;
            }

            QSlider::groove:horizontal {
                height: 6px;
                background-color: #374151;
                border-radius: 3px;
            }

            QSlider::handle:horizontal {
                background-color: #60a5fa;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }

            QSlider::sub-page:horizontal {
                background-color: #2563eb;
                border-radius: 3px;
            }

            QComboBox {
                background-color: #374151;
                border: 1px solid #4b5563;
                border-radius: 6px;
                padding: 5px;
            }

            QCheckBox {
                spacing: 10px;
            }

            QLabel#footer {
                color: #6b7280;
                font-size: 11px;
            }

        """)


# ==========================================
# 3. Application
# ==========================================

def main():

    app = QApplication(sys.argv)

    app.setStyle("Fusion")

    window = GalaxyTrackpadWindow()

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()