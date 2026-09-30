"""Small shared UI widgets."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSlider


class JumpSlider(QSlider):
    """Horizontal slider: click groove to jump; mouse wheel does not change value."""

    def wheelEvent(self, event):
        event.ignore()

    def _value_at(self, pos) -> int:
        span = self.maximum() - self.minimum()
        x = max(0.0, min(float(pos.x()), float(max(self.width() - 1, 1))))
        return self.minimum() + round((x / max(self.width() - 1, 1)) * span)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.setSliderDown(True)
            self.setValue(self._value_at(event.position()))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.isSliderDown() and event.buttons() & Qt.MouseButton.LeftButton:
            self.setValue(self._value_at(event.position()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isSliderDown():
            self.setSliderDown(False)
            self.sliderReleased.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)
