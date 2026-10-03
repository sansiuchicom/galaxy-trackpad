"""Edit left-side keypad symbol pages (Windows → tablet via settings state)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from windows.settings.store import (
    DEFAULT_KEYPAD_SYMBOL_PAGES,
    KEYPAD_SYMBOL_SLOTS,
    migrate_config,
)


class KeypadSymbolsDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keypad symbols")
        self.resize(420, 480)
        self.config = migrate_config(config)
        self._edits: list[list[QLineEdit]] = []

        root = QVBoxLayout(self)
        hint = QLabel(
            "Left keypad only (20 keys per page). One character per cell — "
            "paste from Win+. emoji panel if you like. Right numpad stays fixed."
        )
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        root.addWidget(hint)

        tabs = QTabWidget()
        pages = self.config["touchpad"]["keypad"]["pages"]
        for i, page in enumerate(pages):
            tabs.addTab(self._page_tab(i, page["symbols"]), f"Page {i + 1}")
        root.addWidget(tabs)

        row = QHBoxLayout()
        reset = QPushButton("Reset this page to defaults")
        reset.clicked.connect(lambda: self._reset_page(tabs.currentIndex()))
        row.addWidget(reset)
        row.addStretch()
        root.addLayout(row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _page_tab(self, page_index: int, symbols: list[str]) -> QWidget:
        page = QWidget()
        grid = QGridLayout(page)
        grid.setSpacing(8)
        edits: list[QLineEdit] = []
        for i in range(KEYPAD_SYMBOL_SLOTS):
            edit = QLineEdit(symbols[i] if i < len(symbols) else "")
            edit.setMaxLength(8)
            edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit.setFixedHeight(40)
            font = edit.font()
            font.setPointSize(14)
            edit.setFont(font)
            r, c = divmod(i, 4)
            grid.addWidget(edit, r, c)
            edits.append(edit)
        self._edits.append(edits)
        return page

    def _reset_page(self, page_index: int) -> None:
        if page_index < 0 or page_index >= len(self._edits):
            return
        defaults = DEFAULT_KEYPAD_SYMBOL_PAGES[page_index]
        for edit, ch in zip(self._edits[page_index], defaults):
            edit.setText(ch)

    def result_config(self) -> dict:
        cfg = migrate_config(self.config)
        pages = []
        for page_index, edits in enumerate(self._edits):
            defaults = DEFAULT_KEYPAD_SYMBOL_PAGES[page_index]
            symbols = []
            for i, edit in enumerate(edits):
                text = edit.text().strip()
                symbols.append(text if text else defaults[i])
            pages.append({"symbols": symbols})
        cfg["touchpad"]["keypad"] = {"pages": pages}
        return migrate_config(cfg)
