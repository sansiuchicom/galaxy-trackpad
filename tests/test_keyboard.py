"""Unit tests for keypad key-name mapping (no live SendInput)."""
from __future__ import annotations

import ctypes
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from windows.core import keyboard as kb


class KeyboardMappingTests(unittest.TestCase):
    def test_input_struct_size_x64(self):
        self.assertEqual(ctypes.sizeof(kb.INPUT), 40)

    def test_vk_names_cover_numpad(self):
        for name in (
            "backspace",
            "enter",
            "comma",
            "divide",
            "multiply",
            "subtract",
            "add",
            "decimal",
            *[f"num{i}" for i in range(10)],
        ):
            self.assertIn(name, kb.VK_NAMED)

    def test_digits_use_main_row_not_numpad_vk(self):
        # NumLock-off safe: '0'..'9' on the main keyboard row.
        for i in range(10):
            self.assertEqual(kb.VK_NAMED[f"num{i}"], 0x30 + i)
        self.assertEqual(kb.VK_NAMED["decimal"], kb.VK_OEM_PERIOD)

    def test_apply_key_packet_ignores_other_types(self):
        self.assertFalse(kb.apply_key_packet({"type": "hello"}))
        self.assertFalse(kb.apply_key_packet({"event": "move", "contacts": []}))

    def test_text_too_long_rejected(self):
        with self.assertRaises(ValueError):
            kb.tap_text("x" * 9)


if __name__ == "__main__":
    unittest.main()
