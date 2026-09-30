"""Advanced Settings dialog (touchpad placeholders, pen profiles, connection)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from windows.core.displays import list_monitors
from windows.paths import ADB, HTTP_PORT, WS_PORT, CONTROL_PORT
from windows.settings.store import (
    PROFILE_DRAWING,
    PROFILE_STANDARD,
    migrate_config,
)
from windows.ui.monitor_picker import MonitorPicker
from windows.ui.widgets import JumpSlider


class AdvancedSettingsDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Settings")
        self.resize(520, 640)
        self.config = migrate_config(config)
        self._profile_widgets: dict[str, dict] = {}

        root = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._touchpad_tab(), "Touchpad")
        tabs.addTab(self._pen_tab(), "S Pen")
        tabs.addTab(self._connection_tab(), "Connection")
        root.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _touchpad_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        box = QGroupBox("Input area")
        form = QFormLayout(box)
        combo = QComboBox()
        combo.addItem("Full Screen", "fullscreen")
        combo.addItem("Show Menu (Phase 3)", "show_menu")
        current = self.config["touchpad"].get("input_area", "fullscreen")
        idx = combo.findData(current)
        combo.setCurrentIndex(max(0, idx))
        combo.setEnabled(False)
        form.addRow("Tablet touchpad area", combo)
        note = QLabel(
            "Full Screen / Show Menu is configured here for Phase 3. "
            "The Android app will honor this later; Windows relative touchpad "
            "motion does not need aspect matching."
        )
        note.setWordWrap(True)
        note.setObjectName("muted")
        layout.addWidget(box)
        layout.addWidget(note)
        layout.addStretch()
        self._input_area_combo = combo
        return page

    def _pen_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        tabs = QTabWidget()
        tabs.addTab(self._profile_editor(PROFILE_STANDARD, "Standard"), "Standard")
        tabs.addTab(
            self._profile_editor(PROFILE_DRAWING, "Drawing & Signature"),
            "Drawing & Signature",
        )
        layout.addWidget(tabs)
        return page

    def _profile_editor(self, key: str, title: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(f"{title} profile"))
        picker = MonitorPicker()
        profile = self.config["pen"]["profiles"][key]
        picker.set_selected_id(profile.get("monitor_id", "primary"))
        layout.addWidget(picker)

        mapping = QComboBox()
        mapping.addItem("Stretch", "stretch")
        mapping.addItem("Preserve aspect ratio", "preserve_aspect_ratio")
        midx = mapping.findData(profile.get("mapping", "stretch"))
        mapping.setCurrentIndex(max(0, midx))
        form = QFormLayout()
        form.addRow("Mapping", mapping)
        layout.addLayout(form)

        area_row = QHBoxLayout()
        area_row.addWidget(QLabel("Active area size"))
        area_value = QLabel()
        area_row.addStretch()
        area_row.addWidget(area_value)
        area = JumpSlider(Qt.Orientation.Horizontal)
        area.setRange(50, 100)
        area_pct = int(round(float(profile.get("area_size", 1.0)) * 100))
        area.setValue(area_pct)
        area_value.setText(f"{area_pct}%")
        area.valueChanged.connect(lambda v, label=area_value: label.setText(f"{v}%"))
        layout.addLayout(area_row)
        layout.addWidget(area)
        layout.addStretch()

        self._profile_widgets[key] = {
            "picker": picker,
            "mapping": mapping,
            "area": area,
        }
        return page

    def _connection_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        mode_box = QGroupBox("Connection mode")
        mode_layout = QVBoxLayout(mode_box)
        self._mode_group = QButtonGroup(self)
        current = str(self.config["general"].get("connection_mode", "auto")).lower()
        options = [
            ("auto", "Automatic — prefer USB when connected, else Bluetooth"),
            ("usb", "USB only — classic Galaxy Trackpad cable path"),
            ("bluetooth", "Bluetooth only — no USB pad (Tab must Listen / BT pad)"),
        ]
        self._mode_radios: dict[str, QRadioButton] = {}
        for key, label in options:
            radio = QRadioButton(label)
            self._mode_group.addButton(radio)
            self._mode_radios[key] = radio
            mode_layout.addWidget(radio)
            if key == current or (current in ("bt",) and key == "bluetooth"):
                radio.setChecked(True)
        if not any(r.isChecked() for r in self._mode_radios.values()):
            self._mode_radios["auto"].setChecked(True)
        tip = QLabel(
            "Automatic never switches mid-gesture. Pair the Tab in Windows Bluetooth "
            "settings once. Restart the engine after changing mode."
        )
        tip.setWordWrap(True)
        tip.setObjectName("muted")
        mode_layout.addWidget(tip)
        layout.addWidget(mode_box)

        box = QGroupBox("USB / ADB")
        form = QFormLayout(box)
        form.addRow("ADB", QLabel(str(ADB)))
        form.addRow("ADB present", QLabel("Yes" if ADB.is_file() else "Missing"))
        form.addRow("HTTP", QLabel(f"127.0.0.1:{HTTP_PORT}"))
        form.addRow("WebSocket", QLabel(f"127.0.0.1:{WS_PORT}"))
        form.addRow("GUI control", QLabel(f"127.0.0.1:{CONTROL_PORT}"))
        mac = self.config["general"].get("bluetooth_mac") or "(auto from paired Tab)"
        form.addRow("Bluetooth MAC", QLabel(str(mac)))
        form.addRow(
            "Bluetooth channel",
            QLabel(str(self.config["general"].get("bluetooth_channel", 5))),
        )
        try:
            mons = list_monitors()
            mon_text = "\n".join(
                f"{m.name}  [{m.left},{m.top} {m.width}x{m.height}]" for m in mons
            ) or "(none)"
        except OSError as exc:
            mon_text = f"Error: {exc}"
        monitors = QLabel(mon_text)
        monitors.setWordWrap(True)
        form.addRow("Monitors", monitors)
        layout.addWidget(box)
        layout.addStretch()
        return page

    def result_config(self) -> dict:
        cfg = migrate_config(self.config)
        # Touchpad area stored for Phase 3 even while UI is disabled.
        cfg["touchpad"]["input_area"] = self._input_area_combo.currentData() or "fullscreen"
        for key, widgets in self._profile_widgets.items():
            cfg["pen"]["profiles"][key]["monitor_id"] = widgets["picker"].selected_id()
            cfg["pen"]["profiles"][key]["mapping"] = widgets["mapping"].currentData()
            cfg["pen"]["profiles"][key]["area_size"] = widgets["area"].value() / 100.0
        mode = "auto"
        for key, radio in self._mode_radios.items():
            if radio.isChecked():
                mode = key
                break
        cfg["general"]["connection_mode"] = mode
        return migrate_config(cfg)
