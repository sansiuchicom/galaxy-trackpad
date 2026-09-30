"""
Galaxy Trackpad v0.7
Windows GUI + System Tray

Requires:
    galaxytrackpad_gui_v06.py
    launch_v05.py

Existing v0.6 functions are reused.
"""

import sys

from PySide6.QtCore import QProcess
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QMessageBox,
    QStyle,
    QSystemTrayIcon,
)

from galaxytrackpad_gui_v06 import TrackpadWindow


# ==========================================
# 1. Main window with system tray
# ==========================================

class GalaxyTrackpadTrayWindow(TrackpadWindow):

    def __init__(self):

        # Reuse the existing v0.6 GUI.
        super().__init__()

        self.quit_requested = False
        self.tray_notified = False
        self.tray = None

        if QSystemTrayIcon.isSystemTrayAvailable():
            self.make_tray()
        else:
            self.log(
                "System tray unavailable. "
                "Normal window behavior will be used."
            )


    # ======================================
    # 2. Create system tray
    # ======================================

    def make_tray(self):

        self.tray = QSystemTrayIcon(self)

        # Built-in Windows-style icon.
        self.tray.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_ComputerIcon
            )
        )

        self.tray.setToolTip(
            "Galaxy Trackpad - Stopped"
        )

        menu = QMenu(self)

        self.open_action = QAction(
            "Open settings",
            self
        )

        self.start_action = QAction(
            "Start",
            self
        )

        self.stop_action = QAction(
            "Stop",
            self
        )

        self.quit_action = QAction(
            "Quit",
            self
        )

        # Connect menu actions.
        self.open_action.triggered.connect(
            self.show_settings
        )

        self.start_action.triggered.connect(
            self.start_engine
        )

        self.stop_action.triggered.connect(
            self.stop_engine
        )

        self.quit_action.triggered.connect(
            self.quit_safely
        )

        # Build menu.
        menu.addAction(self.open_action)
        menu.addSeparator()

        menu.addAction(self.start_action)
        menu.addAction(self.stop_action)

        menu.addSeparator()
        menu.addAction(self.quit_action)

        self.tray.setContextMenu(menu)

        self.tray.activated.connect(
            self.tray_clicked
        )

        self.tray.show()

        self.update_tray()


    # ======================================
    # 3. Tray interactions
    # ======================================

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


    # ======================================
    # 4. Update tray status
    # ======================================

    def update_tray(self):

        if self.tray is None:
            return

        running = (
            self.process.state()
            != QProcess.ProcessState.NotRunning
        )

        self.start_action.setEnabled(
            not running
            and not self.quit_requested
        )

        self.stop_action.setEnabled(
            self.control_ready
            and not self.stop_pending
        )

        if self.stop_pending:
            state = "Stopping"

        elif self.control_ready:
            state = "Running"

        elif running:
            state = "Starting"

        else:
            state = "Stopped"

        self.tray.setToolTip(
            f"Galaxy Trackpad - {state}"
        )


    # ======================================
    # 5. Engine START
    # ======================================

    def start_engine(self):

        if self.quit_requested:
            return

        # Use the existing v0.6 function.
        super().start_engine()

        self.update_tray()


    # ======================================
    # 6. Engine STOP
    # ======================================

    def stop_engine(self):

        # Use the existing v0.6 function.
        super().stop_engine()

        self.update_tray()


    # ======================================
    # 7. Monitor engine messages
    # ======================================

    def inspect_engine_line(self, line):

        super().inspect_engine_line(line)

        # If Quit was requested during startup,
        # wait until the control port is ready.
        if (
            self.quit_requested
            and self.control_ready
            and not self.stop_pending
        ):

            self.stop_engine()

        self.update_tray()


    # ======================================
    # 8. Safe application shutdown
    # ======================================

    def quit_safely(self):

        # Engine is already stopped.
        if (
            self.process.state()
            == QProcess.ProcessState.NotRunning
        ):

            if self.tray:
                self.tray.hide()

            QApplication.instance().quit()
            return

        self.quit_requested = True

        self.log(
            "Quit requested. "
            "Waiting for safe engine shutdown..."
        )

        if (
            self.control_ready
            and not self.stop_pending
        ):

            self.stop_engine()

        else:

            self.log(
                "Waiting for the engine control port "
                "or an existing STOP request..."
            )

        self.update_tray()


    # ======================================
    # 9. Handle STOP errors
    # ======================================

    def stop_failed_during_quit(self):

        if not self.quit_requested:
            return

        self.quit_requested = False

        self.show_settings()

        QMessageBox.warning(
            self,
            "Could not quit safely",
            "The engine is still running. "
            "Please retry STOP."
        )

        self.update_tray()


    def on_stop_error(self, sock):

        super().on_stop_error(sock)

        if (
            not self.stop_pending
            and not self.stop_acknowledged
        ):

            self.stop_failed_during_quit()


    def check_stop_timeout(self, sock):

        super().check_stop_timeout(sock)

        if (
            not self.stop_pending
            and not self.stop_acknowledged
        ):

            self.stop_failed_during_quit()


    # ======================================
    # 10. Handle process errors
    # ======================================

    def on_process_error(self, error):

        super().on_process_error(error)

        self.update_tray()

        if (
            error == QProcess.ProcessError.FailedToStart
            and self.quit_requested
        ):

            QApplication.instance().quit()


    # ======================================
    # 11. Engine finished
    # ======================================

    def on_finished(self, code, exit_status):

        super().on_finished(
            code,
            exit_status
        )

        self.update_tray()

        if self.quit_requested:

            if self.tray:
                self.tray.hide()

            QApplication.instance().quit()


    # ======================================
    # 12. Window close behavior
    # ======================================

    def closeEvent(self, event):

        # Fall back to v0.6 if system tray
        # is unavailable.
        if self.tray is None:

            super().closeEvent(event)
            return

        # Clicking X hides the window.
        if not self.quit_requested:

            event.ignore()

            self.hide()

            if not self.tray_notified:

                self.tray.showMessage(
                    "Galaxy Trackpad remains active",
                    "Open it from the system tray. "
                    "Choose Quit to exit.",
                    QSystemTrayIcon.MessageIcon.Information,
                    2500
                )

                self.tray_notified = True

        elif (
            self.process.state()
            == QProcess.ProcessState.NotRunning
        ):

            event.accept()

        else:

            # Never close before engine cleanup.
            event.ignore()


# ==========================================
# 13. Application
# ==========================================

def main():

    app = QApplication(sys.argv)

    app.setStyle("Fusion")

    # Closing the main window must not
    # terminate the tray application.
    if QSystemTrayIcon.isSystemTrayAvailable():

        app.setQuitOnLastWindowClosed(False)

    window = GalaxyTrackpadTrayWindow()

    window.show()

    return app.exec()


if __name__ == "__main__":

    sys.exit(main())