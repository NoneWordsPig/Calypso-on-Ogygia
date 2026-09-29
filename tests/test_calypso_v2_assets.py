import json
import unittest
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parents[1]; BASE = ROOT / "assets/calypso_v2"
class CalypsoV2AssetTests(unittest.TestCase):
    def test_manifest_and_frames(self):
        manifest = json.loads((BASE / "manifest.json").read_text())
        for name, spec in manifest["animations"].items():
            expected = (1 if name in ("sleep", "fish_cast", "fish_pull")
                        else 2 if name.startswith("idle") or name in ("work", "fish_wait")
                        else 4)
            self.assertEqual(spec["count"], expected)
            self.assertEqual(len(spec["frames"]), spec["count"])
            frames = [Image.open(BASE / rel).convert("RGBA") for rel in spec["frames"]]
            if name.startswith(("walk_", "idle_", "fish_")):
                for image in frames:
                    self.assertEqual(image.size, (640, 520) if name.startswith("fish_")
                                     else (256, 256))
                    self.assertTrue(all(pixel[:3] == (0, 0, 0)
                                        for pixel in image.getdata() if pixel[3] == 0))
                bottoms = [image.getchannel("A").getbbox()[3] for image in frames]
                self.assertEqual(len(set(bottoms)), 1)
                if name.startswith("fish_"):
                    self.assertEqual(bottoms[0], 479 if name == "fish_wait" else 308)

    def test_side_walk_sandals_have_a_visible_stride(self):
        def sandal(pixel):
            r, g, b, alpha = pixel
            return alpha > 128 and r > g * 1.2 and r > b * 1.4 and r > 70

        for direction in ("left", "right"):
            widths = []
            for i in range(4):
                image = Image.open(BASE / f"walk_{direction}/{i:02d}.png").convert("RGBA")
                shoe_x = [x for y in range(190, 245) for x in range(256)
                          if sandal(image.getpixel((x, y)))]
                widths.append(max(shoe_x) - min(shoe_x))
            self.assertGreater(max(widths) - min(widths), 25, direction)

    def test_fishing_float_projects_into_water(self):
        map_image = Image.open(ROOT / "assets/map/map.png").convert("RGBA")
        wait = Image.open(BASE / "fishing/wait/00.png").convert("RGBA")
        self.assertGreater(wait.getpixel((49, 475))[3], 0)
        scale = (245 * 816 / 1600) / 520  # world height -> source map pixels
        water = (round(455 + (49 - 342) * scale),
                 round(610 + (475 - 308) * scale))
        self.assertEqual(water, (385, 650))
        red, _, blue, _ = map_image.getpixel(water)
        self.assertGreater(blue, red)

    def test_sleep_head_projects_over_pillow(self):
        head = Image.open(ROOT / "assets/calypso/sleep/head_extracted.png").convert("RGBA")
        self.assertGreater(head.getpixel((114, 80))[3], 0)
        scale = (40 * 816 / 1600) / head.height
        face = (round(1074 + (114 - head.width / 2) * scale),
                round(503 + (80 - head.height) * scale))
        self.assertEqual(face, (1074, 493))
        pillow = Image.open(ROOT / "assets/map/map.png").convert("RGBA")
        red, green, blue, _ = pillow.getpixel((1074, 490))
        self.assertTrue(red > green > blue)


if __name__ == "__main__":
    unittest.main()
