import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from PIL import Image

from calypso.config import PROJECT_ROOT
from calypso.desktop.lighting import night_grade
from calypso.desktop.wallpaper import WallpaperSwitcher, _light_campfire


class WallpaperSwitcherTests(unittest.TestCase):
    def setUp(self):
        self.files = []
        self.prefix = f"wallpaper-test-{uuid4().hex}"

    def path(self, name):
        path = PROJECT_ROOT / "logs" / f"{self.prefix}-{name}"
        self.files.append(path)
        return path

    def tearDown(self):
        for path in self.files:
            path.unlink(missing_ok=True)

    def test_switches_matching_map_and_restores_original_path(self):
        day = self.path("day.png")
        original = self.path("selected.png")
        night = self.path("night.bmp")
        Image.new("RGB", (3, 2), (160, 210, 240)).save(day)
        shutil.copyfile(day, original)
        current = [original]
        switcher = WallpaperSwitcher(day, night, lambda: current[0],
                                     lambda path: current.__setitem__(0, Path(path)))

        self.assertTrue(switcher.sync(True))
        self.assertEqual(current[0], night)
        with Image.open(night) as image:
            self.assertEqual(image.size, (3, 2))
            self.assertNotEqual(image.getpixel((1, 1)), (160, 210, 240))
        switcher.close()
        self.assertEqual(current[0], original)

    def test_unrelated_wallpaper_is_left_alone(self):
        day, other, night = self.path("day.png"), self.path("other.png"), self.path("night.bmp")
        Image.new("RGB", (2, 2), "blue").save(day)
        Image.new("RGB", (2, 2), "red").save(other)
        calls = []
        switcher = WallpaperSwitcher(day, night, lambda: other, calls.append)
        self.assertFalse(switcher.sync(True))
        self.assertEqual(calls, [])

    def test_campfire_light_is_local_and_brighter(self):
        day = Image.new("RGB", (9, 9), (180, 120, 50))
        night = Image.new("RGB", (9, 9), (50, 40, 30))
        _light_campfire(day, night, center=(4, 4), radius=3)
        self.assertGreater(night.getpixel((4, 4))[0], 50)
        self.assertEqual(night.getpixel((0, 0)), (50, 40, 30))

    def test_shared_night_palette_preserves_sprite_transparency(self):
        sprite = Image.new("RGBA", (1, 1), (200, 150, 100, 73))
        self.assertEqual(night_grade(sprite).getpixel((0, 0)), (79, 80, 85, 73))


if __name__ == "__main__":
    unittest.main()
