"""Keypad symbol pages in settings migrate / normalize."""
from __future__ import annotations

import unittest

from windows.settings.store import (
    DEFAULT_KEYPAD_SYMBOL_PAGES,
    KEYPAD_SYMBOL_SLOTS,
    migrate_config,
)
from windows.transport.state_sync import build_client_state
from windows.settings import store


class KeypadSettingsTests(unittest.TestCase):
    def test_defaults_have_two_pages_of_20(self):
        cfg = migrate_config({})
        pages = cfg["touchpad"]["keypad"]["pages"]
        self.assertEqual(len(pages), 2)
        for i, page in enumerate(pages):
            self.assertEqual(len(page["symbols"]), KEYPAD_SYMBOL_SLOTS)
            self.assertEqual(page["symbols"], DEFAULT_KEYPAD_SYMBOL_PAGES[i])

    def test_custom_symbol_and_empty_fallback(self):
        cfg = migrate_config({
            "touchpad": {
                "keypad": {
                    "pages": [
                        {"symbols": ["A"] + [""] * 19},
                        {"symbols": ["₩"] * 20},
                    ]
                }
            }
        })
        p0 = cfg["touchpad"]["keypad"]["pages"][0]["symbols"]
        self.assertEqual(p0[0], "A")
        self.assertEqual(p0[1], DEFAULT_KEYPAD_SYMBOL_PAGES[0][1])
        self.assertEqual(cfg["touchpad"]["keypad"]["pages"][1]["symbols"][0], "₩")

    def test_state_includes_keypad(self):
        cfg = migrate_config({
            "touchpad": {
                "keypad": {
                    "pages": [
                        {"symbols": ["X"] * 20},
                        {"symbols": ["Y"] * 20},
                    ]
                }
            }
        })
        store.apply_runtime_settings(cfg)
        state = build_client_state()
        self.assertEqual(state["keypad"]["pages"][0]["symbols"][0], "X")
        self.assertEqual(state["keypad"]["pages"][1]["symbols"][0], "Y")

if __name__ == "__main__":
    unittest.main()
