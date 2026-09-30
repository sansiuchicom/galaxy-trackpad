"""PySide6 main window: settings, engine control, system tray (v0.6–v0.8 merged)."""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QProcess, QTimer
from PySide6.QtGui import QAction
from PySide6.QtNetwork import QTcpSocket
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from windows.paths import CONTROL_PORT, REPO_ROOT
from windows.core.displays import list_monitors
from windows.settings.store import (
    PROFILE_DRAWING,
    PROFILE_STANDARD,
    load_config,
    migrate_config,
    save_config,
    set_active_profile,
    update_active_profile_fields,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
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

        self.setWindowTitle("Galaxy Trackpad · Phase 2A")
        self.resize(535, 900)
        self.setMinimumSize(460, 760)
        self.build_ui()
        self.apply_style()
        self.set_status("●  Engine stopped", "Not running", "Not running")

        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.timeout.connect(self.apply_changes)

        if QSystemTrayIcon.isSystemTrayAvailable():
            self.make_tray()
        else:
            self.log("System tray unavailable. Normal window behavior will be used.")

    # ---------- UI ----------
    def card(self):
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(11)
        return frame, layout

    def section(self, text):
        item = QLabel(text)
        item.setObjectName("section")
        return item

    def slider(self, caption, key):
        """Touchpad sensitivity slider (nested touchpad.*)."""
        outer = QWidget()
        layout = QVBoxLayout(outer)
        layout.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        row.addWidget(QLabel(caption))
        row.addStretch()
        value_label = QLabel()
        value_label.setObjectName("value")
        row.addWidget(value_label)
        bar = QSlider(Qt.Orientation.Horizontal)
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

    def area_slider(self):
        outer = QWidget()
        layout = QVBoxLayout(outer)
        layout.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        row.addWidget(QLabel("Active area size"))
        row.addStretch()
        self.area_value = QLabel()
        self.area_value.setObjectName("value")
        row.addWidget(self.area_value)
        self.area_bar = QSlider(Qt.Orientation.Horizontal)
        self.area_bar.setRange(50, 100)
        layout.addLayout(row)
        layout.addWidget(self.area_bar)

        def changed(value):
            self.area_value.setText(f"{value}%")
            self.config = update_active_profile_fields(
                self.config, area_size=value / 100.0
            )
            self.save_settings()

        self.area_bar.valueChanged.connect(changed)
        return outer

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(25, 23, 25, 22)
        layout.setSpacing(13)

        title = QLabel("Galaxy Trackpad")
        title.setObjectName("title")
        layout.addWidget(title)
        hint = QLabel("Windows touchpad + S Pen  ·  USB / ADB")
        hint.setObjectName("muted")
        layout.addWidget(hint)

        layout.addWidget(self.section("DEVICE"))
        frame, inside = self.card()
        name = QLabel("Galaxy Tab S7")
        name.setObjectName("device")
        inside.addWidget(name)
        self.status = QLabel()
        self.status.setObjectName("status")
        inside.addWidget(self.status)
        self.touch_status = QLabel()
        self.pen_status = QLabel()
        inside.addWidget(self.touch_status)
        inside.addWidget(self.pen_status)
        layout.addWidget(frame)

        row = QHBoxLayout()
        self.start_button = QPushButton("▶  START")
        self.start_button.setObjectName("start")
        self.start_button.clicked.connect(self.start_engine)
        self.stop_button = QPushButton("■  STOP")
        self.stop_button.setObjectName("stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_engine)
        row.addWidget(self.start_button)
        row.addWidget(self.stop_button)
        layout.addLayout(row)

        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setPlaceholderText("Engine messages appear here")
        self.logs.document().setMaximumBlockCount(120)
        self.logs.setFixedHeight(120)
        layout.addWidget(self.logs)

        layout.addWidget(self.section("TOUCHPAD  ·  LIVE SETTINGS"))
        frame, inside = self.card()
        inside.addWidget(self.slider("Cursor sensitivity", "cursor_sensitivity"))
        inside.addWidget(self.slider("Scroll sensitivity", "scroll_sensitivity"))
        layout.addWidget(frame)

        layout.addWidget(self.section("S PEN  ·  LIVE PROFILES"))
        frame, inside = self.card()

        row = QHBoxLayout()
        row.addWidget(QLabel("Active profile"))
        row.addStretch()
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("Standard", PROFILE_STANDARD)
        self.profile_combo.addItem("Drawing & Signature", PROFILE_DRAWING)
        self.profile_combo.currentIndexChanged.connect(self.on_profile_changed)
        row.addWidget(self.profile_combo)
        inside.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Target display"))
        row.addStretch()
        self.monitor_combo = QComboBox()
        self.monitor_combo.currentIndexChanged.connect(self.on_monitor_changed)
        row.addWidget(self.monitor_combo)
        inside.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Mapping"))
        row.addStretch()
        self.mapping_combo = QComboBox()
        self.mapping_combo.addItem("Stretch", "stretch")
        self.mapping_combo.addItem("Preserve aspect ratio", "preserve_aspect_ratio")
        self.mapping_combo.currentIndexChanged.connect(self.on_mapping_changed)
        row.addWidget(self.mapping_combo)
        inside.addLayout(row)

        inside.addWidget(self.area_slider())
        note = QLabel(
            "Pen tip always draws when detected · mapping reloads live "
            "(queued until tip up if pen is down)"
        )
        note.setObjectName("muted")
        note.setWordWrap(True)
        inside.addWidget(note)
        layout.addWidget(frame)

        auto = QCheckBox("Auto-start engine (Phase 2B wires login start)")
        auto.setChecked(bool(self.config["general"].get("auto_start_engine", True)))
        auto.toggled.connect(
            lambda checked: self.change_general("auto_start_engine", checked)
        )
        layout.addWidget(auto)
        footer = QLabel("Phase 2A  ·  Touchpad unchanged  ·  Pen mapping via RELOAD")
        footer.setObjectName("muted")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

        self._pen_ui_ready = False
        self.refresh_monitor_list()
        self.sync_pen_controls_from_config()
        self._pen_ui_ready = True

    def refresh_monitor_list(self):
        self.monitor_combo.blockSignals(True)
        self.monitor_combo.clear()
        self.monitor_combo.addItem("Primary", "primary")
        try:
            for mon in list_monitors():
                self.monitor_combo.addItem(mon.name, mon.id)
        except OSError as exc:
            self.log(f"Monitor list error: {exc}")
        self.monitor_combo.blockSignals(False)

    def sync_pen_controls_from_config(self):
        self.config = migrate_config(self.config)
        pen = self.config["pen"]
        name = pen.get("active_profile", PROFILE_STANDARD)
        idx = self.profile_combo.findData(name)
        self.profile_combo.blockSignals(True)
        self.profile_combo.setCurrentIndex(max(0, idx))
        self.profile_combo.blockSignals(False)

        profile = pen["profiles"][name]
        mid = profile.get("monitor_id", "primary")
        midx = self.monitor_combo.findData(mid)
        if midx < 0:
            midx = 0
        self.monitor_combo.blockSignals(True)
        self.monitor_combo.setCurrentIndex(midx)
        self.monitor_combo.blockSignals(False)

        mapping = profile.get("mapping", "stretch")
        map_idx = self.mapping_combo.findData(mapping)
        self.mapping_combo.blockSignals(True)
        self.mapping_combo.setCurrentIndex(max(0, map_idx))
        self.mapping_combo.blockSignals(False)

        area = int(round(float(profile.get("area_size", 1.0)) * 100))
        self.area_bar.blockSignals(True)
        self.area_bar.setValue(area)
        self.area_value.setText(f"{area}%")
        self.area_bar.blockSignals(False)

    def on_profile_changed(self, _index):
        if not getattr(self, "_pen_ui_ready", False):
            return
        name = self.profile_combo.currentData()
        self.config = set_active_profile(self.config, name)
        self.sync_pen_controls_from_config()
        self.save_settings()

    def on_monitor_changed(self, _index):
        if not getattr(self, "_pen_ui_ready", False):
            return
        self.config = update_active_profile_fields(
            self.config, monitor_id=self.monitor_combo.currentData()
        )
        self.save_settings()

    def on_mapping_changed(self, _index):
        if not getattr(self, "_pen_ui_ready", False):
            return
        self.config = update_active_profile_fields(
            self.config, mapping=self.mapping_combo.currentData()
        )
        self.save_settings()

    def apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background: #111827; }
            QWidget { color: #e5e7eb; font: 12px 'Segoe UI'; }
            QLabel#title { font-size: 26px; font-weight: 700; color: white; }
            QLabel#device { font-size: 16px; font-weight: 600; }
            QLabel#muted { color: #9ca3af; }
            QLabel#section { color: #aab4c3; font-size: 11px; font-weight: 700; }
            QLabel#status { color: #86efac; font-weight: 600; }
            QLabel#value { color: #93c5fd; font-weight: 600; }
            QFrame#card { background: #1f2937; border: 1px solid #374151; border-radius: 11px; }
            QPushButton { padding: 11px; border-radius: 7px; font-weight: 700; }
            QPushButton#start { background: #2563eb; color: white; }
            QPushButton#stop { background: #4b5563; color: white; }
            QPushButton:disabled { background: #374151; color: #6b7280; }
            QPlainTextEdit { background: #0b1220; border: 1px solid #374151;
                             border-radius: 7px; font: 11px Consolas; }
            QSlider::groove:horizontal { height: 5px; background: #4b5563; }
            QSlider::handle:horizontal { background: #60a5fa; width: 15px; margin: -5px 0; }
            QCheckBox { spacing: 9px; }
            QComboBox { background: #111827; border: 1px solid #374151; padding: 4px 8px; }
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

    def set_status(self, headline, touch, pen):
        self.status.setText(headline)
        self.touch_status.setText("Touchpad     " + touch)
        self.pen_status.setText("S Pen          " + pen)

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
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.set_status("●  Starting...", "Initializing", "Initializing")
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

    def on_output(self):
        self.output_bytes.extend(bytes(self.process.readAllStandardOutput()))
        while b"\n" in self.output_bytes:
            raw, _, remaining = self.output_bytes.partition(b"\n")
            self.output_bytes = bytearray(remaining)
            line = raw.decode("utf-8", errors="replace").strip()
            if line:
                self.log(line)
                self.inspect_engine_line(line)

    def inspect_engine_line(self, line):
        if "[OK] GUI control ready: 8767" in line:
            self.control_ready = True
            self.stop_button.setEnabled(not self.stop_pending)
            self.set_status("●  Running · waiting for tablet", "Ready", "Ready")
        elif "[USB] Reverse ports 8765 and 8766 ready" in line:
            self.set_status("●  USB ready · waiting for tablet", "Ready", "Ready")
        elif "Galaxy Tab connected" in line:
            self.set_status("●  Tablet connected", "Active", "Available")
        elif "Galaxy Tab disconnected" in line:
            self.set_status("●  Waiting for tablet", "Ready", "Ready")
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
        self.stop_button.setEnabled(False)
        self.status.setText("●  Stopping...")
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
            self.status.setText("●  STOP failed · retry")
        self.stop_failed_during_quit()

    def check_stop_timeout(self, sock):
        if (sock is self.stop_socket
                and self.stop_pending
                and not self.stop_acknowledged
                and self.process.state() != QProcess.ProcessState.NotRunning):
            self.log("STOP timed out; retry STOP. Do not force-close yet.")
            self.stop_pending = False
            self.stop_button.setEnabled(self.control_ready)
            self.status.setText("●  STOP timed out · retry")
            self.stop_failed_during_quit()

    def on_process_error(self, error):
        self.log(f"Process error: {self.process.errorString()}")
        if error == QProcess.ProcessError.FailedToStart:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.set_status("●  Start failed", "Stopped", "Stopped")
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
        self.stop_acknowledged = False
        if self.stop_socket is not None:
            self.stop_socket.abort()
            self.stop_socket.deleteLater()
            self.stop_socket = None
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.set_status("●  Engine stopped", "Not running", "Not running")
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


def run_gui() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    if QSystemTrayIcon.isSystemTrayAvailable():
        app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()
    return app.exec()
