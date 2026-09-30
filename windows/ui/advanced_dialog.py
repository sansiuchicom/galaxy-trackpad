"""Advanced Settings dialog (touchpad placeholders, pen profiles, connection)."""
from __future__ import annotations

import platform

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
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

        bt_box = QGroupBox("Bluetooth")
        bt_layout = QVBoxLayout(bt_box)
        tip = QLabel(
            f"While the engine runs, this PC waits for a tablet as '{platform.node()}'. "
            "Pair the tablet in Windows Bluetooth settings once, then on the tablet "
            "choose Bluetooth and pick this PC."
        )
        tip.setWordWrap(True)
        tip.setObjectName("muted")
        bt_layout.addWidget(tip)
        layout.addWidget(bt_box)

        box = QGroupBox("USB / ADB")
        form = QFormLayout(box)
        form.addRow("ADB", QLabel(str(ADB)))
        form.addRow("ADB present", QLabel("Yes" if ADB.is_file() else "Missing"))
        form.addRow("HTTP", QLabel(f"127.0.0.1:{HTTP_PORT}"))
        form.addRow("WebSocket", QLabel(f"127.0.0.1:{WS_PORT}"))
        form.addRow("GUI control", QLabel(f"127.0.0.1:{CONTROL_PORT}"))
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
        return migrate_config(cfg)
