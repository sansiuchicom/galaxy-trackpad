"""GestureScaler cursor / scroll / pinch gains."""
from __future__ import annotations

import unittest

from windows.core.sensitivity import GestureScaler
from windows.settings import store


def _touch(cid: int, x: float, y: float) -> dict:
    return {"id": cid, "tool": "touch", "x": x, "y": y}


class PinchSensitivityTests(unittest.TestCase):
    def setUp(self) -> None:
        store.SETTINGS["cursor_sensitivity"] = 1.0
        store.SETTINGS["scroll_sensitivity"] = 1.0
        store.SETTINGS["pinch_sensitivity"] = 1.0

    def _spread_distance(self, pinch: float) -> float:
        store.SETTINGS["pinch_sensitivity"] = pinch
        s = GestureScaler()
        # Establish two contacts near center.
        s.convert([_touch(1, 0.40, 0.50), _touch(2, 0.60, 0.50)])
        out = s.convert([_touch(1, 0.30, 0.50), _touch(2, 0.70, 0.50)])
        by_id = {int(c["id"]): c for c in out}
        dx = by_id[2]["x"] - by_id[1]["x"]
        dy = by_id[2]["y"] - by_id[1]["y"]
        return (dx * dx + dy * dy) ** 0.5

    def test_pinch_1_matches_raw_separation_ratio(self):
        d1 = self._spread_distance(1.0)
        # Raw separation went from 0.20 to 0.40 → distance 0.40 in norm space.
        self.assertAlmostEqual(d1, 0.40, places=3)

    def test_pinch_2_doubles_separation(self):
        d1 = self._spread_distance(1.0)
        d2 = self._spread_distance(2.0)
        self.assertGreater(d2, d1 * 1.5)

    def test_pinch_default_migrates(self):
        cfg = store.migrate_config({"touchpad": {"cursor_sensitivity": 1.1}})
        self.assertAlmostEqual(cfg["touchpad"]["pinch_sensitivity"], 1.0)

    def test_pinch_nested_migrates(self):
        cfg = store.migrate_config({
            "touchpad": {"pinch_sensitivity": 1.5, "scroll_sensitivity": 0.9},
        })
        self.assertAlmostEqual(cfg["touchpad"]["pinch_sensitivity"], 1.5)
        self.assertAlmostEqual(cfg["touchpad"]["scroll_sensitivity"], 0.9)


if __name__ == "__main__":
    unittest.main()
