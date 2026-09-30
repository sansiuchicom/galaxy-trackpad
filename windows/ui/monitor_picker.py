"""Visual monitor layout picker + Identify overlays."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from windows.core.displays import MonitorInfo, list_monitors


class MonitorMapWidget(QWidget):
    """Clickable map of Win32 monitors (layout only; IDs stay Win32 device names)."""

    monitorSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._monitors: list[MonitorInfo] = []
        self._selected_id = "primary"
        self.setMinimumHeight(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.refresh()

    def refresh(self) -> None:
        try:
            self._monitors = list_monitors()
        except OSError:
            self._monitors = []
        self.update()

    def set_selected_id(self, monitor_id: str | None) -> None:
        self._selected_id = monitor_id or "primary"
        self.update()

    def selected_id(self) -> str:
        return self._selected_id

    def _layout_rects(self) -> list[tuple[MonitorInfo, QRectF]]:
        if not self._monitors:
            return []
        min_x = min(m.left for m in self._monitors)
        min_y = min(m.top for m in self._monitors)
        max_x = max(m.right for m in self._monitors)
        max_y = max(m.bottom for m in self._monitors)
        world_w = max(max_x - min_x, 1)
        world_h = max(max_y - min_y, 1)
        margin = 12
        avail_w = max(self.width() - margin * 2, 1)
        avail_h = max(self.height() - margin * 2, 1)
        scale = min(avail_w / world_w, avail_h / world_h)
        used_w = world_w * scale
        used_h = world_h * scale
        ox = margin + (avail_w - used_w) / 2
        oy = margin + (avail_h - used_h) / 2
        out = []
        for mon in self._monitors:
            rect = QRectF(
                ox + (mon.left - min_x) * scale,
                oy + (mon.top - min_y) * scale,
                max(mon.width * scale, 8),
                max(mon.height * scale, 8),
            )
            out.append((mon, rect))
        return out

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0b1220"))
        primary = next((m for m in self._monitors if m.is_primary), None)
        selected = self._selected_id
        if selected in (None, "", "primary") and primary is not None:
            selected = primary.id

        for index, (mon, rect) in enumerate(self._layout_rects(), start=1):
            is_sel = mon.id == selected
            painter.setBrush(QColor("#2563eb" if is_sel else "#1f2937"))
            painter.setPen(QPen(QColor("#93c5fd" if is_sel else "#4b5563"), 2))
            painter.drawRoundedRect(rect, 8, 8)
            painter.setPen(QColor("#e5e7eb"))
            font = QFont("Segoe UI", 11)
            font.setBold(True)
            painter.setFont(font)
            label = f"{index}"
            if mon.is_primary:
                label += " ★"
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position()
        for mon, rect in self._layout_rects():
            if rect.contains(pos):
                self._selected_id = mon.id
                self.monitorSelected.emit(mon.id)
                self.update()
                break


class MonitorPicker(QWidget):
    """Map + selection label + Identify button."""

    selectionChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._overlays: list[QWidget] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.map = MonitorMapWidget()
        self.map.monitorSelected.connect(self._on_map_selected)
        layout.addWidget(self.map)
        row = QHBoxLayout()
        self.caption = QLabel("Selected: Primary")
        self.caption.setObjectName("muted")
        row.addWidget(self.caption)
        row.addStretch()
        identify = QPushButton("Identify Displays")
        identify.clicked.connect(self.identify_displays)
        row.addWidget(identify)
        layout.addLayout(row)

    def refresh(self) -> None:
        self.map.refresh()
        self._update_caption(self.map.selected_id())

    def set_selected_id(self, monitor_id: str | None) -> None:
        self.map.set_selected_id(monitor_id)
        self._update_caption(self.map.selected_id())

    def selected_id(self) -> str:
        return self.map.selected_id()

    def _on_map_selected(self, monitor_id: str) -> None:
        self._update_caption(monitor_id)
        self.selectionChanged.emit(monitor_id)

    def _update_caption(self, monitor_id: str) -> None:
        try:
            monitors = list_monitors()
        except OSError:
            monitors = []
        primary = next((m for m in monitors if m.is_primary), None)
        target_id = monitor_id
        if target_id in ("", "primary") and primary is not None:
            target_id = primary.id
        label = next((m.name for m in monitors if m.id == target_id), monitor_id)
        self.caption.setText(f"Selected: {label}")

    def identify_displays(self) -> None:
        self.clear_overlays()
        screens = QGuiApplication.screens()
        for index, screen in enumerate(screens, start=1):
            overlay = QLabel(str(index))
            overlay.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
            overlay.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
            overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            overlay.setStyleSheet(
                "background: rgba(37, 99, 235, 180); color: white;"
                "font: 700 72px 'Segoe UI'; border-radius: 16px;"
            )
            geo = screen.geometry()
            size = 180
            overlay.setGeometry(
                geo.center().x() - size // 2,
                geo.center().y() - size // 2,
                size,
                size,
            )
            overlay.show()
            self._overlays.append(overlay)
        QTimer.singleShot(2000, self.clear_overlays)

    def clear_overlays(self) -> None:
        for overlay in self._overlays:
            overlay.close()
            overlay.deleteLater()
        self._overlays.clear()
