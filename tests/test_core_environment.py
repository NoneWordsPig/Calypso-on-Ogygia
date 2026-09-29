"""Independent sprites move over a tree-free, water-free wallpaper."""

import os
import json
import unittest

from PIL import Image

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from calypso.desktop.coordinate_mapper import ScreenTransform
    from calypso.desktop.environment import ASSETS, EnvironmentAnimator, WallpaperPlacement
    from calypso.desktop.wallpaper import DAY_MAP, LEGACY_MAP
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
            self.assertEqual(len(animator.windows), 9)
            self.assertEqual(sum(w.step == 2 for w in animator.windows), 6)
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
            for name, tick in (("west_trees", 6), ("east_trees", 6),
                               ("upper_fall", 5), ("lower_fall", 5),
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

    def test_bare_map_removes_static_trees_and_falling_water(self):
        with Image.open(DAY_MAP) as source:
            bare = source.convert("RGB")
        with Image.open(LEGACY_MAP) as source:
            original = source.convert("RGB")
        self.assertEqual(bare.size, original.size)
        for point in ((561, 125), (481, 180), (1124, 420),
                      (819, 120), (1028, 640)):
            self.assertNotEqual(bare.getpixel(point), original.getpixel(point))
        # The cliff is visible beneath both independently animated falls.
        for point in ((819, 120), (1028, 640)):
            red, _, blue = bare.getpixel(point)
            self.assertGreater(red, blue)

    def test_sprite_frames_leave_ground_and_cliffs_transparent(self):
        manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], 2)
        self.assertEqual(manifest["source"], "assets/map/map_bare.png")
        static_points = {
            "west_trees": [(550, 300), (600, 350)],
            "north_trees": [(625, 90), (940, 100)],
            "east_trees": [(920, 205), (1205, 205)],
            "bed_tree": [(1050, 520), (1198, 520)],
            "south_pines": [(790, 650), (890, 680)],
            "fruit_tree": [(695, 400), (793, 400)],
            "upper_fall": [(796, 120), (843, 120), (796, 165)],
            "lower_fall": [(1003, 660), (1056, 660), (1003, 714)],
            "campfire": [(1060, 220), (1074, 237), (1090, 220)],
        }
        for spec in manifest["effects"]:
            name = spec["name"]
            x, y, width, height = spec["rect"]
            for palette in ("day", "night"):
                with Image.open(ASSETS / palette / f"{name}.png") as source:
                    strip = source.convert("RGBA")
                tile = strip.crop((0, 0, width, height))
                self.assertEqual(tile.getchannel("A").getextrema(), (0, 255), name)
                for px, py in static_points[name]:
                    for frame in range(spec["frames"]):
                        self.assertEqual(strip.getpixel((frame * width + px - x,
                                                         py - y))[3], 0,
                                         f"{name} {palette} static point {(px, py)}")

    def test_waterfall_highlight_moves_downward(self):
        for name, width, height in (("upper_fall", 48, 106),
                                    ("lower_fall", 54, 109)):
            with Image.open(ASSETS / "day" / f"{name}.png") as source:
                strip = source.convert("RGBA")
            centers = []
            for frame in range(8):
                tile = strip.crop((frame * width, 0, (frame + 1) * width, height))
                bright_rows = []
                for y in range(int(height * .16), int(height * .83)):
                    for x in range(int(width * .25), int(width * .75)):
                        red, green, blue, alpha = tile.getpixel((x, y))
                        if alpha > 180 and red > 145 and green > 185 and blue > 205:
                            bright_rows.append(y)
                self.assertTrue(bright_rows, name)
                centers.append(sum(bright_rows) / len(bright_rows))
            self.assertTrue(all(before < after for before, after in
                                zip(centers, centers[1:])), name)


if __name__ == "__main__":
    unittest.main()
