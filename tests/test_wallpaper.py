"""Wallpaper placement tests."""
import unittest

from app.config import Config
from app.wallpaper import WallpaperPlacement


class TestWallpaper(unittest.TestCase):
    def test_fill_scales_and_centers(self):
        # emulate registry style 10 (fill)
        cfg = Config.load()
        cfg.data["display"]["wallpaper"] = {"mode": "fill"}
        p = WallpaperPlacement(cfg, 1920, 1080, 1312, 816)
        scale = max(1920 / 1312, 1080 / 816)
        self.assertAlmostEqual(p.scale, scale, places=4)
        sx, sy = p.map_to_screen(0, 0)
        self.assertAlmostEqual(sx, (1920 - 1312 * scale) / 2, places=2)
        self.assertAlmostEqual(sy, (1080 - 816 * scale) / 2, places=2)

    def test_fit(self):
        cfg = Config.load()
        cfg.data["display"]["wallpaper"] = {"mode": "fit"}
        p = WallpaperPlacement(cfg, 1920, 1080, 1312, 816)
        self.assertAlmostEqual(p.scale, min(1920 / 1312, 1080 / 816), places=4)

    def test_roundtrip(self):
        cfg = Config.load()
        cfg.data["display"]["wallpaper"] = {"mode": "fill"}
        p = WallpaperPlacement(cfg, 1920, 1080, 1312, 816)
        sx, sy = p.map_to_screen(660, 379)
        mx, my = p.screen_to_map(sx, sy)
        self.assertAlmostEqual(mx, 660, places=3)
        self.assertAlmostEqual(my, 379, places=3)


if __name__ == "__main__":
    unittest.main()
