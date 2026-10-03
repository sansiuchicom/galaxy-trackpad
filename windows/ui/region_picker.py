"""Capture-style pen region picker on one monitor (Qt screen coords)."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QKeySequence,
    QPainter,
    QPen,
    QScreen,
    QShortcut,
)
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

from windows.core.displays import MonitorInfo
from windows.core.pen_mapping import (
    NormRect,
    PixelRect,
    norm_region_to_dict,
    norm_region_to_pixels,
    parse_norm_region,
)


def find_qscreen_for_monitor(monitor: MonitorInfo) -> QScreen | None:
    """Match a Win32 monitor to a QScreen (name first, then center proximity)."""
    screens = QGuiApplication.screens()
    if not screens:
        return None
    for screen in screens:
        name = screen.name() or ""
        if name == monitor.id:
            return screen
        # Sometimes Qt reports short names.
        if monitor.id.endswith(name) and name:
            return screen
    mx = (monitor.left + monitor.right) / 2.0
    my = (monitor.top + monitor.bottom) / 2.0
    best: QScreen | None = None
    best_d = float("inf")
    for screen in screens:
        geo = screen.geometry()
        dpr = float(screen.devicePixelRatio() or 1.0)
        # Prefer treating geometry as DIPs mapped to physical; also try native.
        for sx, sy in (
            ((geo.x() + geo.width() / 2) * dpr, (geo.y() + geo.height() / 2) * dpr),
            (geo.x() + geo.width() / 2, geo.y() + geo.height() / 2),
        ):
            d = (sx - mx) ** 2 + (sy - my) ** 2
            if d < best_d:
                best_d = d
                best = screen
    return best or QGuiApplication.primaryScreen()


class RegionPickerOverlay(QDialog):
    """Lightly dim one Qt screen and drag a rectangle; Esc cancels."""

    def __init__(self, screen: QScreen, parent=None) -> None:
        super().__init__(parent)
        self._screen = screen
        self._origin: QPoint | None = None
        self._current: QPoint | None = None
        self._norm: NormRect | None = None
        self._keyboard_grabbed = False

        # Window (not Tool): Tool overlays often never get keyboard focus on Windows,
        # so Esc never reaches keyPressEvent while the main app window is hidden.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowTitle("Select pen region")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # Use Qt's screen geometry so the overlay matches what the user sees.
        self.setGeometry(screen.geometry())
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        tip = QLabel(
            "Drag to select the pen area  ·  release to confirm  ·  Esc to cancel",
            self,
        )
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        tip.setStyleSheet(
            "color: #e8eef8; background: rgba(15, 23, 42, 160); "
            "padding: 10px 16px; border-radius: 8px; font-size: 14px;"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(tip, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)

        # Belt-and-suspenders: Esc via shortcut + keyPressEvent + keyboard grab.
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self.reject)

    def norm_region(self) -> NormRect | None:
        return self._norm

    def _rubber_rect(self) -> QRect | None:
        if self._origin is None or self._current is None:
            return None
        return QRect(self._origin, self._current).normalized()

    def _commit_from_rubber(self) -> bool:
        rubber = self._rubber_rect()
        if rubber is None or rubber.width() < 8 or rubber.height() < 8:
            return False
        # Normalize against the actual Qt widget size (not Win32 pixel size).
        w = max(self.width(), 1)
        h = max(self.height(), 1)
        left = rubber.x() / w
        top = rubber.y() / h
        right = (rubber.x() + rubber.width()) / w
        bottom = (rubber.y() + rubber.height()) / h
        parsed = parse_norm_region(
            {"left": left, "top": top, "right": right, "bottom": bottom}
        )
        if parsed is None:
            return False
        self._norm = parsed
        return True

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        # Light veil — desktop must stay readable (was too dark before).
        painter.fillRect(self.rect(), QColor(15, 23, 42, 55))
        rubber = self._rubber_rect()
        if rubber is not None:
            painter.fillRect(rubber, QColor(56, 189, 248, 70))
            pen = QPen(QColor(125, 211, 252, 230))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rubber.adjusted(0, 0, -1, -1))

    def _claim_keyboard(self) -> None:
        # PySide6 has no QGuiApplication.keyboardGrabber(); track grab ourselves.
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        if not self._keyboard_grabbed:
            self.grabKeyboard()
            self._keyboard_grabbed = True

    def _release_keyboard(self) -> None:
        if not self._keyboard_grabbed:
            return
        self._keyboard_grabbed = False
        try:
            self.releaseKeyboard()
        except Exception:
            pass

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._claim_keyboard()

    def hideEvent(self, event) -> None:
        self._release_keyboard()
        super().hideEvent(event)

    def closeEvent(self, event) -> None:
        self._release_keyboard()
        super().closeEvent(event)

    def done(self, result: int) -> None:
        self._release_keyboard()
        super().done(result)

    def mousePressEvent(self, event) -> None:
        # Keep Esc working if focus was stolen, but do not re-activate every click
        # (that was interrupting the rubber-band drag / accept path).
        if not self._keyboard_grabbed:
            self._claim_keyboard()
        else:
            self.setFocus(Qt.FocusReason.MouseFocusReason)
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.position().toPoint()
            self._current = self._origin
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._origin is not None:
            self._current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._origin is None:
            return
        self._current = event.position().toPoint()
        if self._commit_from_rubber():
            self.accept()
        else:
            self._origin = None
            self._current = None
            self.update()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)


def pick_region_on_monitor(monitor: MonitorInfo, parent=None) -> dict[str, float] | None:
    """
    Block until the user picks a region on ``monitor`` or cancels.

    Returns a monitor-normalized region dict, or None if cancelled / invalid.
    """
    screen = find_qscreen_for_monitor(monitor)
    if screen is None:
        return None
    QGuiApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)
    try:
        dlg = RegionPickerOverlay(screen, parent)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        region = dlg.norm_region()
        if region is None:
            return None
        return norm_region_to_dict(region)
    finally:
        QGuiApplication.restoreOverrideCursor()


def pixel_rect_for_region(monitor: MonitorInfo, region: dict[str, float]) -> PixelRect | None:
    """Win32/physical pixel rect for pen injection (engine)."""
    parsed = parse_norm_region(region)
    if parsed is None:
        return None
    full = PixelRect(monitor.left, monitor.top, monitor.right, monitor.bottom)
    return norm_region_to_pixels(parsed, full)


def qt_rect_for_region(monitor: MonitorInfo, region: dict[str, float]) -> QRect | None:
    """Qt screen geometry rect for the always-on outline (GUI process)."""
    parsed = parse_norm_region(region)
    if parsed is None:
        return None
    screen = find_qscreen_for_monitor(monitor)
    if screen is None:
        return None
    geo = screen.geometry()
    x = geo.x() + int(round(parsed.left * geo.width()))
    y = geo.y() + int(round(parsed.top * geo.height()))
    w = max(2, int(round((parsed.right - parsed.left) * geo.width())))
    h = max(2, int(round((parsed.bottom - parsed.top) * geo.height())))
    return QRect(x, y, w, h)
