"""Capture-style pen region picker on one monitor."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

from windows.core.displays import MonitorInfo
from windows.core.pen_mapping import (
    NormRect,
    PixelRect,
    norm_region_to_dict,
    parse_norm_region,
)


class RegionPickerOverlay(QDialog):
    """Dim one monitor and drag a rectangle; Esc cancels."""

    def __init__(self, monitor: MonitorInfo, parent=None) -> None:
        super().__init__(parent)
        self._monitor = monitor
        self._origin: QPoint | None = None
        self._current: QPoint | None = None
        self._norm: NormRect | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowTitle("Select pen region")
        self.setModal(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(monitor.left, monitor.top, monitor.width, monitor.height)
        self.setStyleSheet("background-color: rgba(8, 12, 20, 120);")

        tip = QLabel(
            "Drag to select the pen area  ·  release to confirm  ·  Esc to cancel",
            self,
        )
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        tip.setStyleSheet(
            "color: #e8eef8; background: rgba(15, 23, 42, 180); "
            "padding: 10px 16px; border-radius: 8px; font-size: 14px;"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(tip, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

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
        mon = self._monitor
        # Geometry is already the monitor; rubber is widget-local.
        left = rubber.left() / max(mon.width, 1)
        top = rubber.top() / max(mon.height, 1)
        right = rubber.right() / max(mon.width, 1)
        bottom = rubber.bottom() / max(mon.height, 1)
        # QRect.right() is inclusive in Qt; convert to exclusive-ish norm using width.
        right = (rubber.x() + rubber.width()) / max(mon.width, 1)
        bottom = (rubber.y() + rubber.height()) / max(mon.height, 1)
        parsed = parse_norm_region(
            {"left": left, "top": top, "right": right, "bottom": bottom}
        )
        if parsed is None:
            return False
        self._norm = parsed
        return True

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        rubber = self._rubber_rect()
        if rubber is None:
            return
        painter = QPainter(self)
        painter.fillRect(rubber, QColor(56, 189, 248, 55))
        pen = QPen(QColor(125, 211, 252, 230))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rubber.adjusted(0, 0, -1, -1))

    def mousePressEvent(self, event) -> None:
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
    # Ensure the overlay uses the same pixel space as Win32 monitor bounds.
    QGuiApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)
    try:
        dlg = RegionPickerOverlay(monitor, parent)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        region = dlg.norm_region()
        if region is None:
            return None
        return norm_region_to_dict(region)
    finally:
        QGuiApplication.restoreOverrideCursor()


def pixel_rect_for_region(monitor: MonitorInfo, region: dict[str, float]) -> PixelRect | None:
    from windows.core.pen_mapping import norm_region_to_pixels, parse_norm_region

    parsed = parse_norm_region(region)
    if parsed is None:
        return None
    full = PixelRect(monitor.left, monitor.top, monitor.right, monitor.bottom)
    return norm_region_to_pixels(parsed, full)
