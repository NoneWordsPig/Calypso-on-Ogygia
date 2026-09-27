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
                    self.assertEqual(image.size, (384, 320) if name.startswith("fish_")
                                     else (256, 256))
                    self.assertTrue(all(pixel[:3] == (0, 0, 0)
                                        for pixel in image.getdata() if pixel[3] == 0))
                bottoms = [image.getchannel("A").getbbox()[3] for image in frames]
                self.assertEqual(len(set(bottoms)), 1)
                if name.startswith("fish_"):
                    self.assertEqual(bottoms[0], 308)

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


if __name__ == "__main__":
    unittest.main()
