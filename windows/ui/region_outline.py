"""Always-on thin border for the active Drawing pen region."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from windows.core.pen_mapping import PixelRect

_outline: "RegionOutlineWindow | None" = None


class RegionOutlineWindow(QWidget):
    """Click-through rectangle border on the virtual desktop."""

    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        # Outer bright edge + inner dim edge so it reads on light and dark UIs.
        pen = QPen(QColor(64, 180, 255, 210))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(1, 1, self.width() - 3, self.height() - 3)
        pen = QPen(QColor(0, 0, 0, 120))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)


def show_region_outline(rect: PixelRect) -> None:
    """Show or move the outline to cover ``rect`` (virtual-screen pixels)."""
    global _outline
    if rect.width < 2 or rect.height < 2:
        hide_region_outline()
        return
    if _outline is None:
        _outline = RegionOutlineWindow()
    _outline.setGeometry(rect.left, rect.top, rect.width, rect.height)
    _outline.show()
    _outline.raise_()


def hide_region_outline() -> None:
    global _outline
    if _outline is not None:
        _outline.hide()


def outline_is_visible() -> bool:
    return _outline is not None and _outline.isVisible()
