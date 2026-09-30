"""PySide6 main window: settings, engine control, system tray (v0.6–v0.8 merged)."""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QProcess, QTimer
from PySide6.QtGui import QAction
from PySide6.QtNetwork import QTcpSocket
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from windows.autostart import is_enabled as autostart_is_enabled
from windows.autostart import set_enabled as autostart_set_enabled
from windows.autostart import sync_from_config as autostart_sync
from windows.paths import CONTROL_PORT, REPO_ROOT
from windows.settings.store import (
    PROFILE_DRAWING,
    PROFILE_STANDARD,
    load_config,
    migrate_config,
    save_config,
    set_active_profile,
)
from windows.ui.advanced_dialog import AdvancedSettingsDialog
from windows.ui.widgets import JumpSlider


class MainWindow(QMainWindow):
    def __init__(self, start_hidden: bool = False):
        super().__init__()
        self.start_hidden = start_hidden
        self.config = load_config()
        try:
            save_config(self.config)  # Persist flat→nested migration once.
        except OSError:
            pass
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.started.connect(self.on_started)
        self.process.readyReadStandardOutput.connect(self.on_output)
        self.process.finished.connect(self.on_finished)
        self.process.errorOccurred.connect(self.on_process_error)

        self.control_ready = False
        self.stop_pending = False
        self.stop_acknowledged = False
        self.close_when_stopped = False
        self.output_bytes = bytearray()
        self.stop_socket = None
        self._reload_timer = None
        self._reload_socket = None

        self.quit_requested = False
        self.tray_notified = False
        self.tray = None
        self.engine_phase = "stopped"
        self.usb_phase = "unknown"
        self.tablet_phase = "disconnected"
        self.show_debug_logs = bool(
            self.config.get("general", {}).get("debug_log", False)
        )

        self.setWindowTitle("Galaxy Trackpad")
        self.resize(560, 820)
        self.setMinimumSize(420, 520)
        self.build_ui()
        self.apply_style()
        self.refresh_connection_status()

        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.timeout.connect(self.apply_changes)

        if QSystemTrayIcon.isSystemTrayAvailable():
            self.make_tray()
        else:
            self.log("System tray unavailable. Normal window behavior will be used.")

        try:
            autostart_sync(bool(self.config["general"].get("start_with_windows", True)))
        except OSError as exc:
            self.log(f"Autostart sync failed: {exc}")

        if self.config["general"].get("auto_start_engine", True):
            QTimer.singleShot(600, self.start_engine)

    # ---------- UI ----------
    def card(self):
        frame = QFrame()
        frame.setObjectName("card")
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(11)
        return frame, layout

    def section(self, text):
        item = QLabel(text)
        item.setObjectName("section")
        item.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        return item

    def action_button(self, text: str, object_name: str = "secondary") -> QPushButton:
        button = QPushButton(text)
        button.setObjectName(object_name)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(40)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return button

    def slider(self, caption, key):
        """Touchpad sensitivity slider (nested touchpad.*)."""
        outer = QWidget()
        outer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(outer)
        layout.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        row.addWidget(QLabel(caption))
        row.addStretch()
        value_label = QLabel()
        value_label.setObjectName("value")
        row.addWidget(value_label)
        bar = JumpSlider(Qt.Orientation.Horizontal)
        bar.setRange(50, 200)
        current = float(self.config["touchpad"].get(key, 1.0))
        bar.setValue(round(current * 100))
        value_label.setText(f"{bar.value() / 100:.2f}x")

        def changed(value):
            self.config["touchpad"][key] = value / 100.0
            value_label.setText(f"{value / 100:.2f}x")
            self.save_settings()

        bar.valueChanged.connect(changed)
        layout.addLayout(row)
        layout.addWidget(bar)
        return outer

    def build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        central = QWidget()
        scroll.setWidget(central)
        self.setCentralWidget(scroll)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(25, 23, 25, 22)
        layout.setSpacing(14)

        title = QLabel("Galaxy Trackpad")
        title.setObjectName("title")
        title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(title)
        hint = QLabel("Windows touchpad + S Pen  ·  USB / ADB")
        hint.setObjectName("muted")
        hint.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(hint)

        layout.addWidget(self.section("DEVICE"))
        frame, inside = self.card()
        name = QLabel("Galaxy Tab S7")
        name.setObjectName("device")
        inside.addWidget(name)
        self.status = QLabel()
        self.status.setObjectName("status")
        self.status.setWordWrap(True)
        inside.addWidget(self.status)
        self.touch_status = QLabel()
        self.pen_status = QLabel()
        inside.addWidget(self.touch_status)
        inside.addWidget(self.pen_status)
        layout.addWidget(frame)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.start_button = self.action_button("▶  START", "start")
        self.start_button.clicked.connect(self.start_engine)
        self.stop_button = self.action_button("■  STOP", "stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_engine)
        row.addWidget(self.start_button)
        row.addWidget(self.stop_button)
        layout.addLayout(row)

        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setPlaceholderText("Engine messages appear here")
        self.logs.document().setMaximumBlockCount(120)
        self.logs.setMinimumHeight(96)
        self.logs.setMaximumHeight(160)
        self.logs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.logs)

        layout.addWidget(self.section("TOUCHPAD"))
        frame, inside = self.card()
        inside.addWidget(self.slider("Cursor sensitivity", "cursor_sensitivity"))
        inside.addWidget(self.slider("Scroll sensitivity", "scroll_sensitivity"))
        layout.addWidget(frame)

        layout.addWidget(self.section("S PEN"))
        frame, inside = self.card()

        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        self.profile_group = QButtonGroup(self)
        self.radio_everyday = QRadioButton("Everyday")
        self.radio_drawing = QRadioButton("Drawing & Signature")
        self.radio_everyday.setCursor(Qt.CursorShape.PointingHandCursor)
        self.radio_drawing.setCursor(Qt.CursorShape.PointingHandCursor)
        self.profile_group.addButton(self.radio_everyday, 0)
        self.profile_group.addButton(self.radio_drawing, 1)
        self.profile_group.idToggled.connect(self.on_profile_radio)
        mode_row.addWidget(self.radio_everyday)
        mode_row.addWidget(self.radio_drawing)
        mode_row.addStretch()
        inside.addLayout(mode_row)

        self.pen_hint = QLabel()
        self.pen_hint.setObjectName("muted")
        self.pen_hint.setWordWrap(True)
        inside.addWidget(self.pen_hint)
        layout.addWidget(frame)

        layout.addWidget(self.section("GENERAL"))
        frame, inside = self.card()
        self.start_with_windows = QCheckBox("Start with Windows")
        self.start_with_windows.setChecked(
            bool(self.config["general"].get("start_with_windows", True))
        )
        self.start_with_windows.toggled.connect(self.on_start_with_windows)
        inside.addWidget(self.start_with_windows)
        self.auto_start_engine = QCheckBox("Auto-start engine when Galaxy Trackpad opens")
        self.auto_start_engine.setChecked(
            bool(self.config["general"].get("auto_start_engine", True))
        )
        self.auto_start_engine.toggled.connect(
            lambda checked: self.change_general("auto_start_engine", checked)
        )
        inside.addWidget(self.auto_start_engine)
        self.debug_logs = QCheckBox("Show debug logs")
        self.debug_logs.setChecked(self.show_debug_logs)
        self.debug_logs.toggled.connect(self.on_debug_logs_toggled)
        inside.addWidget(self.debug_logs)
        self.advanced_button = self.action_button("Advanced Settings…")
        self.advanced_button.clicked.connect(self.open_advanced)
        inside.addWidget(self.advanced_button)
        hint = QLabel("Monitor target, pen area, and connection details")
        hint.setObjectName("muted")
        inside.addWidget(hint)
        layout.addWidget(frame)

        layout.addStretch(1)

        self._pen_ui_ready = False
        self.sync_pen_controls_from_config()
        self._pen_ui_ready = True

    def sync_pen_controls_from_config(self):
        self.config = migrate_config(self.config)
        name = self.config["pen"].get("active_profile", PROFILE_STANDARD)
        self.radio_everyday.blockSignals(True)
        self.radio_drawing.blockSignals(True)
        if name == PROFILE_DRAWING:
            self.radio_drawing.setChecked(True)
        else:
            self.radio_everyday.setChecked(True)
        self.radio_everyday.blockSignals(False)
        self.radio_drawing.blockSignals(False)
        self.update_pen_hint()

    def update_pen_hint(self):
        if self.radio_drawing.isChecked():
            self.pen_hint.setText(
                "Keeps drawn proportions on the selected monitor — "
                "better for art and signatures. Change monitor/area in Advanced."
            )
        else:
            self.pen_hint.setText(
                "Default: pen follows the tablet like a normal absolute stylus "
                "on your monitor (stretch). Touchpad fingers stay relative and unchanged."
            )

    def on_profile_radio(self, button_id: int, checked: bool):
        if not checked or not getattr(self, "_pen_ui_ready", False):
            return
        name = PROFILE_DRAWING if button_id == 1 else PROFILE_STANDARD
        self.config = set_active_profile(self.config, name)
        self.update_pen_hint()
        self.save_settings()

    def on_start_with_windows(self, checked: bool):
        self.change_general("start_with_windows", checked)
        try:
            autostart_set_enabled(checked)
            state = "enabled" if checked else "disabled"
            self.log(f"Start with Windows {state}")
        except OSError as exc:
            self.log(f"Could not update Windows startup entry: {exc}")
            # Revert checkbox if registry write failed.
            self.start_with_windows.blockSignals(True)
            self.start_with_windows.setChecked(autostart_is_enabled())
            self.start_with_windows.blockSignals(False)

    def open_advanced(self):
        dialog = AdvancedSettingsDialog(self.config, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        self.config = dialog.result_config()
        self.sync_pen_controls_from_config()
        self.save_settings()
        self.log("Advanced settings saved")

    def apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QScrollArea, QScrollArea > QWidget > QWidget {
                background: #111827;
            }
            QWidget { color: #e5e7eb; font: 12px 'Segoe UI'; }
            QLabel#title { font-size: 26px; font-weight: 700; color: white; }
            QLabel#device { font-size: 16px; font-weight: 600; }
            QLabel#muted { color: #9ca3af; }
            QLabel#section {
                color: #aab4c3; font-size: 11px; font-weight: 700;
                padding-top: 4px; padding-bottom: 2px;
            }
            QLabel#status { color: #86efac; font-weight: 600; }
            QLabel#value { color: #93c5fd; font-weight: 600; }
            QFrame#card {
                background: #1f2937; border: 1px solid #374151; border-radius: 11px;
            }
            QPushButton {
                padding: 10px 14px; border-radius: 8px; font-weight: 700;
                min-height: 36px;
            }
            QPushButton#start { background: #2563eb; color: white; border: none; }
            QPushButton#start:hover { background: #3b82f6; }
            QPushButton#stop { background: #4b5563; color: white; border: none; }
            QPushButton#stop:hover { background: #6b7280; }
            QPushButton#secondary {
                background: #111827; color: #e5e7eb;
                border: 1px solid #60a5fa;
            }
            QPushButton#secondary:hover {
                background: #1e3a5f; border-color: #93c5fd; color: white;
            }
            QPushButton:disabled { background: #374151; color: #6b7280; border: none; }
            QPlainTextEdit {
                background: #0b1220; border: 1px solid #374151;
                border-radius: 7px; font: 11px Consolas; color: #d1d5db;
            }
            QSlider::groove:horizontal {
                height: 10px; background: #4b5563; border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: #60a5fa; width: 18px; height: 18px;
                margin: -5px 0; border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #3b82f6; border-radius: 5px;
            }
            QCheckBox { spacing: 9px; }
            QRadioButton {
                spacing: 8px; font-weight: 600; color: #e5e7eb;
                padding: 6px 4px;
            }
            QRadioButton::indicator {
                width: 16px; height: 16px;
            }
            QComboBox {
                background: #0b1220; color: #e5e7eb;
                border: 1px solid #4b5563; border-radius: 6px;
                padding: 6px 10px; min-height: 28px;
            }
            QComboBox:hover { border-color: #60a5fa; }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox QAbstractItemView {
                background: #0b1220; color: #e5e7eb;
                selection-background-color: #2563eb; selection-color: white;
                border: 1px solid #4b5563; outline: 0;
            }
            QScrollBar:vertical {
                background: #111827; width: 10px; margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #4b5563; border-radius: 4px; min-height: 24px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

    # ---------- Settings ----------
    def change_general(self, key, value):
        self.config = migrate_config(self.config)
        self.config["general"][key] = value
        self.save_settings()

    def change_config(self, key, value):
        self.config[key] = value
        self.save_settings()

    def save_settings(self):
        try:
            self.config = migrate_config(self.config)
            save_config(self.config)
        except OSError as exc:
            self.log(f"Settings save error: {exc}")
            return
        if (self._reload_timer is not None and self.control_ready
                and self.process.state() != QProcess.ProcessState.NotRunning):
            self._reload_timer.start(250)

    def apply_changes(self):
        if not self.control_ready or self.stop_pending:
            return
        if self._reload_socket is not None:
            self._reload_socket.abort()
            self._reload_socket.deleteLater()
        sock = QTcpSocket(self)
        self._reload_socket = sock
        sock.connected.connect(lambda: sock.write(b"RELOAD\n"))
        sock.readyRead.connect(lambda: self.reload_reply(sock))
        sock.errorOccurred.connect(lambda error: self.reload_error(sock))
        sock.connectToHost("127.0.0.1", CONTROL_PORT)
        QTimer.singleShot(2500, lambda: self.reload_timeout(sock))

    def reload_reply(self, sock):
        reply = bytes(sock.readAll()).strip()
        if reply != b"OK":
            self.log(f"Settings update response: {reply!r}")
        sock.disconnectFromHost()
        if sock is self._reload_socket:
            self._reload_socket = None
        sock.deleteLater()

    def reload_error(self, sock):
        if sock is self._reload_socket and self.control_ready:
            self.log("Settings could not be applied: " + sock.errorString())
            self._reload_socket = None
            sock.deleteLater()

    def reload_timeout(self, sock):
        if sock is self._reload_socket:
            sock.abort()
            self._reload_socket = None
            sock.deleteLater()
            if self.control_ready:
                self.log("Settings update timed out; try moving the slider again")

    def log(self, message):
        self.logs.appendPlainText(message)

    def on_debug_logs_toggled(self, checked: bool):
        self.show_debug_logs = bool(checked)
        self.change_general("debug_log", checked)

    def set_status(self, headline, touch, pen):
        self.status.setText(headline)
        self.touch_status.setText("Touchpad     " + touch)
        self.pen_status.setText("S Pen          " + pen)

    def refresh_connection_status(self):
        engine = self.engine_phase
        usb = self.usb_phase
        tablet = self.tablet_phase

        if engine == "stopped":
            self.set_status("●  Stopped", "Not running", "Not running")
        elif engine == "starting":
            self.set_status("●  Starting…", "Initializing", "Initializing")
        elif engine == "stopping":
            self.set_status("●  Stopping…", "Releasing", "Releasing")
        elif engine == "error":
            self.set_status("●  Error", "Stopped", "Stopped")
        elif tablet == "connected":
            self.set_status("●  Connected", "Active", "Available")
        elif usb == "unauthorized":
            self.set_status("●  Unlock tablet USB debugging", "Ready", "Ready")
        elif usb == "waiting":
            self.set_status("●  Waiting for device", "Ready", "Ready")
        elif usb == "connecting":
            self.set_status("●  Connecting USB…", "Ready", "Ready")
        elif usb == "ready":
            self.set_status("●  USB ready · open tablet page", "Ready", "Ready")
        elif usb == "multiple":
            self.set_status("●  Multiple ADB devices", "Ready", "Ready")
        elif usb == "error":
            self.set_status("●  USB/ADB issue · retrying", "Ready", "Ready")
        else:
            self.set_status("●  Running · waiting for tablet", "Ready", "Ready")

    # ---------- Engine ----------
    def start_engine(self):
        if self.quit_requested:
            return
        if self.process.state() != QProcess.ProcessState.NotRunning:
            return
        self.output_bytes.clear()
        self.control_ready = False
        self.stop_pending = False
        self.stop_acknowledged = False
        self.engine_phase = "starting"
        self.usb_phase = "unknown"
        self.tablet_phase = "disconnected"
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.refresh_connection_status()
        self.log("---- Starting engine ----")
        self.process.setWorkingDirectory(str(REPO_ROOT))
        self.process.start(sys.executable, ["-u", "-m", "windows", "--engine"])
        QTimer.singleShot(20000, self.warn_if_not_ready)
        self.update_tray()

    def on_started(self):
        self.log("Engine process started")

    def warn_if_not_ready(self):
        if (self.process.state() != QProcess.ProcessState.NotRunning
                and not self.control_ready):
            self.log("Engine not ready after 20s. Check messages above.")
            self.engine_phase = "error"
            self.refresh_connection_status()

    def on_output(self):
        self.output_bytes.extend(bytes(self.process.readAllStandardOutput()))
        while b"\n" in self.output_bytes:
            raw, _, remaining = self.output_bytes.partition(b"\n")
            self.output_bytes = bytearray(remaining)
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            self.inspect_engine_line(line)
            if line.startswith("[DEBUG]") and not self.show_debug_logs:
                continue
            if line.startswith("[STATE]"):
                continue
            self.log(line)

    def inspect_engine_line(self, line):
        if line.startswith("[STATE]"):
            fields = {}
            for part in line[7:].split():
                if "=" in part:
                    key, value = part.split("=", 1)
                    fields[key] = value
            if "engine" in fields:
                self.engine_phase = fields["engine"]
            if "usb" in fields:
                self.usb_phase = fields["usb"]
            if "tablet" in fields:
                self.tablet_phase = fields["tablet"]
            if self.engine_phase == "running" and not self.control_ready:
                # control-ready print may arrive slightly after first STATE
                pass
            self.refresh_connection_status()
        elif "[OK] GUI control ready: 8767" in line or "GUI control ready on" in line:
            self.control_ready = True
            self.engine_phase = "running"
            self.stop_button.setEnabled(not self.stop_pending)
            self.refresh_connection_status()
        elif line.startswith("[ERROR]"):
            if self.engine_phase == "starting":
                self.engine_phase = "error"
                self.refresh_connection_status()

        if self.quit_requested and self.control_ready and not self.stop_pending:
            self.stop_engine()
        self.update_tray()

    def stop_engine(self):
        if self.process.state() == QProcess.ProcessState.NotRunning:
            return
        if self.stop_pending:
            return
        if not self.control_ready:
            self.log("Control server is not ready; can't send STOP yet.")
            return
        self.stop_pending = True
        self.stop_acknowledged = False
        self.engine_phase = "stopping"
        self.stop_button.setEnabled(False)
        self.refresh_connection_status()
        self.stop_socket = QTcpSocket(self)
        sock = self.stop_socket
        sock.connected.connect(lambda: sock.write(b"STOP\n"))
        sock.readyRead.connect(lambda: self.on_stop_reply(sock))
        sock.errorOccurred.connect(lambda err: self.on_stop_error(sock))
        sock.connectToHost("127.0.0.1", CONTROL_PORT)
        QTimer.singleShot(4000, lambda: self.check_stop_timeout(sock))
        self.update_tray()

    def on_stop_reply(self, sock):
        response = bytes(sock.readAll()).strip()
        if response == b"OK":
            self.stop_acknowledged = True
            self.log("STOP accepted; waiting for engine cleanup...")
        else:
            self.log(f"Unexpected STOP response: {response!r}")
        sock.disconnectFromHost()

    def on_stop_error(self, sock):
        if sock is not self.stop_socket or self.stop_acknowledged:
            return
        self.log(f"STOP socket error: {sock.errorString()}")
        self.stop_pending = False
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.stop_button.setEnabled(self.control_ready)
            self.engine_phase = "running"
            self.refresh_connection_status()
        self.stop_failed_during_quit()

    def check_stop_timeout(self, sock):
        if (sock is self.stop_socket
                and self.stop_pending
                and not self.stop_acknowledged
                and self.process.state() != QProcess.ProcessState.NotRunning):
            self.log("STOP timed out; retry STOP. Do not force-close yet.")
            self.stop_pending = False
            self.stop_button.setEnabled(self.control_ready)
            self.engine_phase = "running"
            self.refresh_connection_status()
            self.stop_failed_during_quit()

    def on_process_error(self, error):
        self.log(f"Process error: {self.process.errorString()}")
        if error == QProcess.ProcessError.FailedToStart:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.engine_phase = "error"
            self.refresh_connection_status()
            if self.quit_requested:
                QApplication.instance().quit()
        self.update_tray()

    def on_finished(self, code, exit_status):
        if self.output_bytes:
            self.log(self.output_bytes.decode("utf-8", errors="replace").strip())
            self.output_bytes.clear()
        self.log(f"Engine exited (code {code})")
        self.control_ready = False
        self.stop_pending = False
        if self.stop_acknowledged or code == 0:
            self.engine_phase = "stopped"
        else:
            self.engine_phase = "error"
        self.stop_acknowledged = False
        self.usb_phase = "unknown"
        self.tablet_phase = "disconnected"
        if self.stop_socket is not None:
            self.stop_socket.abort()
            self.stop_socket.deleteLater()
            self.stop_socket = None
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.refresh_connection_status()
        self.update_tray()
        if self.close_when_stopped:
            self.close_when_stopped = False
            self.close()
        if self.quit_requested:
            if self.tray:
                self.tray.hide()
            QApplication.instance().quit()

    # ---------- Tray ----------
    def make_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        )
        self.tray.setToolTip("Galaxy Trackpad - Stopped")
        menu = QMenu(self)
        self.open_action = QAction("Open settings", self)
        self.start_action = QAction("Start", self)
        self.stop_action = QAction("Stop", self)
        self.quit_action = QAction("Quit", self)
        self.open_action.triggered.connect(self.show_settings)
        self.start_action.triggered.connect(self.start_engine)
        self.stop_action.triggered.connect(self.stop_engine)
        self.quit_action.triggered.connect(self.quit_safely)
        menu.addAction(self.open_action)
        menu.addSeparator()
        menu.addAction(self.start_action)
        menu.addAction(self.stop_action)
        menu.addSeparator()
        menu.addAction(self.quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.tray_clicked)
        self.tray.show()
        self.update_tray()

    def tray_clicked(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_settings()

    def show_settings(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def update_tray(self):
        if self.tray is None:
            return
        running = self.process.state() != QProcess.ProcessState.NotRunning
        self.start_action.setEnabled(not running and not self.quit_requested)
        self.stop_action.setEnabled(self.control_ready and not self.stop_pending)
        if self.stop_pending:
            state = "Stopping"
        elif self.control_ready:
            state = "Running"
        elif running:
            state = "Starting"
        else:
            state = "Stopped"
        self.tray.setToolTip(f"Galaxy Trackpad - {state}")

    def quit_safely(self):
        if self.process.state() == QProcess.ProcessState.NotRunning:
            if self.tray:
                self.tray.hide()
            QApplication.instance().quit()
            return
        self.quit_requested = True
        self.log("Quit requested. Waiting for safe engine shutdown...")
        if self.control_ready and not self.stop_pending:
            self.stop_engine()
        else:
            self.log(
                "Waiting for the engine control port or an existing STOP request..."
            )
        self.update_tray()

    def stop_failed_during_quit(self):
        if not self.quit_requested:
            return
        self.quit_requested = False
        self.show_settings()
        QMessageBox.warning(
            self,
            "Could not quit safely",
            "The engine is still running. Please retry STOP.",
        )
        self.update_tray()

    def closeEvent(self, event):
        if self.tray is None:
            if self.process.state() == QProcess.ProcessState.NotRunning:
                event.accept()
                return
            answer = QMessageBox.question(
                self, "Galaxy Trackpad", "Stop the touchpad engine and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.close_when_stopped = True
                self.stop_engine()
            event.ignore()
            return

        if not self.quit_requested:
            event.ignore()
            self.hide()
            if not self.tray_notified:
                self.tray.showMessage(
                    "Galaxy Trackpad remains active",
                    "Open it from the system tray. Choose Quit to exit.",
                    QSystemTrayIcon.MessageIcon.Information,
                    2500,
                )
                self.tray_notified = True
        elif self.process.state() == QProcess.ProcessState.NotRunning:
            event.accept()
        else:
            event.ignore()


def run_gui(start_hidden: bool = False) -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    if QSystemTrayIcon.isSystemTrayAvailable():
        app.setQuitOnLastWindowClosed(False)
    window = MainWindow(start_hidden=start_hidden)
    if start_hidden and QSystemTrayIcon.isSystemTrayAvailable():
        window.hide()
        window.log("Started in tray mode")
    else:
        window.show()
    return app.exec()
