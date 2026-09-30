"""Galaxy Trackpad v0.6 – first Windows GUI -> engine integration.

Requires PySide6 and the existing, working launch_v05.py in the same folder.
Settings are saved but sensitivity / pen toggles are NOT applied to the engine yet.
"""
import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QProcess, QTimer
from PySide6.QtNetwork import QTcpSocket
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QSlider,
    QVBoxLayout, QWidget,
)

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / "launch_v05.py"
CONFIG_FILE = ROOT / "galaxytrackpad_settings.json"
DEFAULTS = {
    "cursor_sensitivity": 1.0,
    "scroll_sensitivity": 1.0,
    "pen_enabled": True,
    "pen_monitor": "Primary Monitor",
    "auto_connect": True,
}


def load_config():
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            saved = json.load(file)
        return {**DEFAULTS, **saved} if isinstance(saved, dict) else DEFAULTS.copy()
    except (FileNotFoundError, OSError, ValueError):
        return DEFAULTS.copy()


class TrackpadWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
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

        self.setWindowTitle("Galaxy Trackpad")
        self.resize(535, 830)
        self.setMinimumSize(460, 720)
        self.build_ui()
        self.apply_style()
        self.set_status("●  Engine stopped", "Not running", "Not running")

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
        bar.setValue(round(float(self.config.get(key, 1.0)) * 100))
        value_label.setText(f"{bar.value() / 100:.2f}x")

        def changed(value):
            self.config[key] = value / 100.0
            value_label.setText(f"{value / 100:.2f}x")
            self.save_settings()

        bar.valueChanged.connect(changed)
        layout.addLayout(row)
        layout.addWidget(bar)
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
        hint = QLabel("Windows touchpad + S Pen  ·  GUI integration test")
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

        layout.addWidget(self.section("TOUCHPAD  ·  SETTINGS PREVIEW"))
        frame, inside = self.card()
        inside.addWidget(self.slider("Cursor sensitivity", "cursor_sensitivity"))
        inside.addWidget(self.slider("Scroll sensitivity", "scroll_sensitivity"))
        layout.addWidget(frame)

        layout.addWidget(self.section("S PEN  ·  SETTINGS PREVIEW"))
        frame, inside = self.card()
        pen_check = QCheckBox("Enable S Pen")
        pen_check.setChecked(bool(self.config.get("pen_enabled", True)))
        pen_check.toggled.connect(lambda checked: self.change_config("pen_enabled", checked))
        inside.addWidget(pen_check)
        row = QHBoxLayout()
        row.addWidget(QLabel("Target display"))
        row.addStretch()
        monitor = QComboBox()
        monitor.addItem("Primary Monitor")
        monitor.setEnabled(False)  # Actual monitor selection will be added later.
        row.addWidget(monitor)
        inside.addLayout(row)
        layout.addWidget(frame)

        auto = QCheckBox("Connect automatically (saved for future version)")
        auto.setChecked(bool(self.config.get("auto_connect", True)))
        auto.toggled.connect(lambda checked: self.change_config("auto_connect", checked))
        layout.addWidget(auto)
        footer = QLabel("v0.6  ·  Settings are saved but do not affect the engine yet")
        footer.setObjectName("muted")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

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
        """)

    def change_config(self, key, value):
        self.config[key] = value
        self.save_settings()

    def save_settings(self):
        try:
            with CONFIG_FILE.open("w", encoding="utf-8") as file:
                json.dump(self.config, file, indent=4, ensure_ascii=False)
        except OSError as exc:
            self.log(f"Settings save error: {exc}")

    def log(self, message):
        self.logs.appendPlainText(message)

    def set_status(self, headline, touch, pen):
        self.status.setText(headline)
        self.touch_status.setText("Touchpad     " + touch)
        self.pen_status.setText("S Pen          " + pen)

    # ------------- Engine control -------------
    def start_engine(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            return
        if not ENGINE.is_file():
            QMessageBox.critical(self, "Missing engine", f"Cannot find:\n{ENGINE}")
            return
        self.output_bytes.clear()
        self.control_ready = False
        self.stop_pending = False
        self.stop_acknowledged = False
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)  # Enabled once port 8767 is ready.
        self.set_status("●  Starting...", "Initializing", "Initializing")
        self.log("---- Starting engine ----")
        self.process.setWorkingDirectory(str(ROOT))
        self.process.start(sys.executable, ["-u", str(ENGINE)])
        QTimer.singleShot(20000, self.warn_if_not_ready)

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
        sock.connectToHost("127.0.0.1", 8767)
        QTimer.singleShot(4000, lambda: self.check_stop_timeout(sock))

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

    def check_stop_timeout(self, sock):
        if (sock is self.stop_socket
                and self.stop_pending
                and not self.stop_acknowledged
                and self.process.state() != QProcess.ProcessState.NotRunning):
            self.log("STOP timed out; retry STOP. Do not force-close yet.")
            self.stop_pending = False
            self.stop_button.setEnabled(self.control_ready)
            self.status.setText("●  STOP timed out · retry")

    def on_process_error(self, error):
        self.log(f"Process error: {self.process.errorString()}")
        if error == QProcess.ProcessError.FailedToStart:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.set_status("●  Start failed", "Stopped", "Stopped")

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
        if self.close_when_stopped:
            self.close_when_stopped = False
            self.close()

    def closeEvent(self, event):
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
        event.ignore()  # Wait for the engine to confirm clean shutdown.


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = TrackpadWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
