"""Unit tests for S Pen mapping math (no Windows UI required)."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from windows.core.pen_mapping import (
    DEFAULT_TABLET_ASPECT,
    NormRect,
    PenMapConfig,
    PixelRect,
    active_tablet_rect,
    letterbox_rect,
    map_uv_to_monitor,
    norm_region_to_pixels,
    parse_norm_region,
    scale_about_center,
)
from windows.settings.store import migrate_config


class MappingMathTests(unittest.TestCase):
    def test_stretch_full_area(self):
        rect = active_tablet_rect("stretch", 1.0, monitor_aspect=16 / 9)
        self.assertEqual(rect, NormRect(0.0, 0.0, 1.0, 1.0))

    def test_area_size_scales_center(self):
        rect = active_tablet_rect("stretch", 0.8, monitor_aspect=16 / 9)
        self.assertAlmostEqual(rect.width, 0.8)
        self.assertAlmostEqual(rect.height, 0.8)
        self.assertAlmostEqual((rect.left + rect.right) / 2, 0.5)
        self.assertAlmostEqual((rect.top + rect.bottom) / 2, 0.5)

    def test_preserve_aspect_letterbox_uv(self):
        # Monitor 16:9, tablet 16:10 → UV aspect = (16/9)/(16/10) = 10/9
        mon_aspect = 16 / 9
        tab_aspect = 16 / 10
        rect = active_tablet_rect(
            "preserve_aspect_ratio",
            1.0,
            monitor_aspect=mon_aspect,
            tablet_aspect=tab_aspect,
        )
        self.assertAlmostEqual(rect.width / rect.height, mon_aspect / tab_aspect, places=5)
        self.assertLessEqual(rect.width, 1.0 + 1e-9)
        self.assertLessEqual(rect.height, 1.0 + 1e-9)

    def test_outside_returns_none(self):
        active = NormRect(0.25, 0.25, 0.75, 0.75)
        monitor = PixelRect(0, 0, 1920, 1080)
        self.assertIsNone(map_uv_to_monitor(0.1, 0.5, active, monitor))

    def test_corners_map_to_monitor(self):
        active = NormRect(0.0, 0.0, 1.0, 1.0)
        monitor = PixelRect(100, 200, 100 + 1920, 200 + 1080)
        self.assertEqual(map_uv_to_monitor(0.0, 0.0, active, monitor), (100, 200))
        self.assertEqual(map_uv_to_monitor(1.0, 1.0, active, monitor), (100 + 1919, 200 + 1079))

    def test_negative_monitor_origin(self):
        cfg = PenMapConfig(
            mapping="stretch",
            area_size=1.0,
            monitor=PixelRect(-1920, 0, 0, 1080),
            tablet_aspect=DEFAULT_TABLET_ASPECT,
        )
        self.assertEqual(cfg.map_point(0.0, 0.0), (-1920, 0))
        self.assertEqual(cfg.map_point(1.0, 1.0), (-1, 1079))

    def test_pixel_isotropy_intent(self):
        """Equal tablet-pixel steps map to equal monitor-pixel steps under preserve."""
        mon = PixelRect(0, 0, 1920, 1080)
        tab_aspect = 2560 / 1600
        cfg = PenMapConfig(
            "preserve_aspect_ratio",
            1.0,
            mon,
            tablet_aspect=tab_aspect,
        )
        active = cfg.active_rect()
        # Small step equal in tablet pixels ⇒ Δu * Tw = Δv * Th ⇒ Δu/Δv = Th/Tw
        du = 0.01 * (1600 / 2560)
        dv = 0.01
        # Pick a point inside active, apply deltas still inside
        u0 = (active.left + active.right) / 2
        v0 = (active.top + active.bottom) / 2
        p0 = cfg.map_point(u0, v0)
        p1 = cfg.map_point(u0 + du, v0 + dv)
        self.assertIsNotNone(p0)
        self.assertIsNotNone(p1)
        dx = abs(p1[0] - p0[0])
        dy = abs(p1[1] - p0[1])
        self.assertGreater(dx, 0)
        self.assertGreater(dy, 0)
        self.assertLess(abs(dx - dy) / max(dx, dy), 0.15)


class MigrationTests(unittest.TestCase):
    def test_flat_v08_migrates(self):
        cfg = migrate_config({
            "cursor_sensitivity": 1.22,
            "scroll_sensitivity": 1.24,
            "pen_enabled": False,
            "pen_monitor": "Primary Monitor",
            "auto_connect": True,
        })
        self.assertAlmostEqual(cfg["touchpad"]["cursor_sensitivity"], 1.22)
        self.assertAlmostEqual(cfg["touchpad"]["scroll_sensitivity"], 1.24)
        self.assertEqual(cfg["pen"]["profiles"]["standard"]["monitor_id"], "primary")
        self.assertEqual(cfg["pen"]["profiles"]["drawing"]["mapping"], "preserve_aspect_ratio")
        self.assertTrue(cfg["general"]["auto_start_engine"])

    def test_nested_roundtrip_shape(self):
        cfg = migrate_config({
            "touchpad": {"cursor_sensitivity": 1.5, "scroll_sensitivity": 0.8},
            "pen": {
                "active_profile": "drawing",
                "profiles": {
                    "drawing": {
                        "monitor_id": "\\\\.\\DISPLAY2",
                        "mapping": "preserve_aspect_ratio",
                        "area_size": 0.7,
                    }
                },
            },
        })
        self.assertEqual(cfg["pen"]["active_profile"], "drawing")
        self.assertEqual(cfg["pen"]["profiles"]["drawing"]["area_size"], 0.7)


class SessionPadAspectTests(unittest.TestCase):
    def tearDown(self):
        from windows.settings.pad_aspect import set_session_pad_aspect

        set_session_pad_aspect(None)

    def test_session_overrides_stored_aspect(self):
        from windows.settings.pad_aspect import set_session_pad_aspect
        from windows.settings.store import active_pen_profile

        set_session_pad_aspect(1.25)
        profile = active_pen_profile()
        self.assertAlmostEqual(profile["tablet_aspect"], 1.25)

    def test_preserve_uses_narrower_pad_aspect(self):
        """Menu-on pad is taller than full-tablet 1.6 → different letterbox than 1.6."""
        mon = PixelRect(0, 0, 3840, 2160)
        cfg_pad = PenMapConfig(
            "preserve_aspect_ratio",
            1.0,
            mon,
            tablet_aspect=1.25,
        )
        cfg_tab = PenMapConfig(
            "preserve_aspect_ratio",
            1.0,
            mon,
            tablet_aspect=1.6,
        )
        self.assertNotEqual(cfg_pad.active_rect(), cfg_tab.active_rect())
        # Active corners still cover the full monitor.
        self.assertEqual(
            cfg_pad.map_point(cfg_pad.active_rect().left, cfg_pad.active_rect().top),
            (0, 0),
        )
        br = cfg_pad.map_point(cfg_pad.active_rect().right, cfg_pad.active_rect().bottom)
        self.assertEqual(br, (3839, 2159))


class RegionMappingTests(unittest.TestCase):
    def test_parse_rejects_tiny_and_inverted(self):
        self.assertIsNone(parse_norm_region({"left": 0, "top": 0, "right": 0.01, "bottom": 1}))
        self.assertIsNone(parse_norm_region({"left": 0.8, "top": 0.1, "right": 0.2, "bottom": 0.9}))
        self.assertIsNone(parse_norm_region(None))

    def test_norm_region_to_pixels(self):
        mon = PixelRect(0, 0, 3840, 2160)
        region = parse_norm_region({"left": 0.25, "top": 0.25, "right": 0.75, "bottom": 0.75})
        self.assertIsNotNone(region)
        pix = norm_region_to_pixels(region, mon)
        self.assertEqual(pix, PixelRect(960, 540, 2880, 1620))

    def test_stretch_onto_region_maps_full_pad(self):
        mon = PixelRect(0, 0, 3840, 2160)
        region = parse_norm_region({"left": 0.1, "top": 0.2, "right": 0.5, "bottom": 0.6})
        target = norm_region_to_pixels(region, mon)
        cfg = PenMapConfig("stretch", 1.0, target, DEFAULT_TABLET_ASPECT)
        self.assertEqual(cfg.active_rect(), NormRect(0.0, 0.0, 1.0, 1.0))
        self.assertEqual(cfg.map_point(0.0, 0.0), (target.left, target.top))
        self.assertEqual(cfg.map_point(1.0, 1.0), (target.right - 1, target.bottom - 1))

    def test_preserve_onto_region_letterboxes_pad(self):
        """Region aspect ≠ pad aspect → S Pen Area is a band, corners hit region box."""
        mon = PixelRect(0, 0, 3840, 2160)
        # Wide short region on a 16:10-ish pad (aspect 1.6).
        region = parse_norm_region({"left": 0.1, "top": 0.4, "right": 0.9, "bottom": 0.6})
        target = norm_region_to_pixels(region, mon)
        pad_aspect = 1.6
        cfg = PenMapConfig("preserve_aspect_ratio", 1.0, target, pad_aspect)
        active = cfg.active_rect()
        self.assertLess(active.height, 1.0 - 1e-6)
        self.assertAlmostEqual(active.width, 1.0, places=5)
        self.assertEqual(
            cfg.map_point(active.left, active.top),
            (target.left, target.top),
        )
        self.assertEqual(
            cfg.map_point(active.right, active.bottom),
            (target.right - 1, target.bottom - 1),
        )

    def test_migrate_keeps_valid_drawing_region(self):
        cfg = migrate_config({
            "pen": {
                "active_profile": "drawing",
                "profiles": {
                    "drawing": {
                        "mapping": "preserve_aspect_ratio",
                        "region": {"left": 0.1, "top": 0.2, "right": 0.4, "bottom": 0.5},
                    },
                    "standard": {
                        "region": {"left": 0.1, "top": 0.2, "right": 0.4, "bottom": 0.5},
                    },
                },
            }
        })
        self.assertEqual(
            cfg["pen"]["profiles"]["drawing"]["region"],
            {"left": 0.1, "top": 0.2, "right": 0.4, "bottom": 0.5},
        )
        # Everyday never stores a capture region.
        self.assertIsNone(cfg["pen"]["profiles"]["standard"]["region"])

    def test_migrate_drops_invalid_region(self):
        cfg = migrate_config({
            "pen": {
                "profiles": {
                    "drawing": {"region": {"left": 0.9, "top": 0.1, "right": 0.2, "bottom": 0.3}},
                }
            }
        })
        self.assertIsNone(cfg["pen"]["profiles"]["drawing"]["region"])

    def test_active_profile_region_only_for_drawing(self):
        import copy

        from windows.settings.store import (
            DEFAULTS,
            SETTINGS,
            active_pen_profile,
            apply_runtime_settings,
            set_drawing_region,
        )

        cfg = set_drawing_region(
            copy.deepcopy(DEFAULTS),
            {"left": 0.2, "top": 0.2, "right": 0.8, "bottom": 0.8},
        )
        cfg["pen"]["active_profile"] = "drawing"
        apply_runtime_settings(cfg)
        drawing = active_pen_profile()
        self.assertTrue(drawing["region_active"])
        self.assertAlmostEqual(drawing["region"]["left"], 0.2)

        SETTINGS["pen"]["active_profile"] = "standard"
        everyday = active_pen_profile()
        self.assertFalse(everyday["region_active"])
        self.assertIsNone(everyday["region"])


if __name__ == "__main__":
    unittest.main()
