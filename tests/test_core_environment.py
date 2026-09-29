"""The desktop effects stay local and move without changing the wallpaper."""

import os
import unittest

from PIL import Image

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from calypso.desktop.coordinate_mapper import ScreenTransform
    from calypso.desktop.environment import ASSETS, EnvironmentAnimator, WallpaperPlacement
    from calypso.desktop.wallpaper import DAY_MAP, night_map_image
    QT = True
except ImportError:
    QT = False


@unittest.skipUnless(QT, "PySide6 unavailable")
class EnvironmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_wallpaper_fill_centers_the_map_and_respects_dpi(self):
        transform = ScreenTransform(actual_primary_physical=(1920, 1080), dpi=1.5)
        placement = WallpaperPlacement(transform, style=10)
        center = placement.point(656, 408)
        self.assertAlmostEqual(center[0], 640)
        self.assertAlmostEqual(center[1], 360)
        self.assertFalse(WallpaperPlacement(transform, style="tile").supported)
        self.assertFalse(WallpaperPlacement(transform, style=22).supported)

    def test_effects_have_small_click_through_windows_and_pause(self):
        animator = EnvironmentAnimator(ScreenTransform())
        try:
            self.assertEqual(len(animator.windows), 8)
            self.assertEqual(sum(w.step == 2 for w in animator.windows), 5)
            self.assertTrue(all(w.width() < 750 and w.height() < 700
                                for w in animator.windows))
            self.assertTrue(all(w.windowFlags() & Qt.WindowTransparentForInput
                                for w in animator.windows))
            self.assertTrue(animator.source_matches)
            animator.set_active(True)
            self.assertTrue(animator.timer.isActive())
            animator.set_active(False)
            self.assertFalse(animator.timer.isActive())
            self.assertTrue(all(not w.isVisible() for w in animator.windows))
        finally:
            animator.close()

    def test_tree_water_fire_and_night_frames_change(self):
        animator = EnvironmentAnimator(
            ScreenTransform(actual_primary_physical=(1312, 816)))
        try:
            animator.set_active(True)
            self.app.processEvents()
            for name, tick in (("west_trees", 6), ("upper_fall", 5),
                               ("campfire", 5)):
                window = next(w for w in animator.windows if w.name == name)
                before = window.grab().toImage()
                window.advance(tick)
                self.app.processEvents()
                self.assertNotEqual(before, window.grab().toImage(), name)
                day = window.grab().toImage()
                window.set_night(True)
                self.app.processEvents()
                self.assertNotEqual(day, window.grab().toImage(), name)
        finally:
            animator.close()

    def test_baked_night_tiles_use_the_actual_night_wallpaper_pixels(self):
        with Image.open(DAY_MAP) as source:
            day = source.convert("RGB")
        night = night_map_image(day)
        for name, x, y in (("west_trees", 350, 40),
                           ("upper_fall", 788, 49),
                           ("campfire", 1046, 185)):
            with Image.open(ASSETS / "night" / f"{name}.png") as source:
                tile = source.convert("RGBA")
            self.assertEqual(tile.getpixel((7, 7))[:3],
                             night.getpixel((x + 7, y + 7)))


if __name__ == "__main__":
    unittest.main()
