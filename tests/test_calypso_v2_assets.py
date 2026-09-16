import json
import unittest
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parents[1]; BASE = ROOT / "assets/calypso_v2"
class CalypsoV2AssetTests(unittest.TestCase):
    def test_manifest_and_frames(self):
        manifest = json.loads((BASE / "manifest.json").read_text())
        for name, spec in manifest["animations"].items():
            expected = 2 if name.startswith("idle") else 4
            self.assertEqual(spec["count"], expected)
            self.assertEqual(len(spec["frames"]), spec["count"])
            frames = [Image.open(BASE / rel).convert("RGBA") for rel in spec["frames"]]
            if name.startswith(("walk_", "idle_")):
                for image in frames:
                    self.assertEqual(image.size, (256, 256))
                    self.assertTrue(all(pixel[:3] == (0, 0, 0)
                                        for pixel in image.getdata() if pixel[3] == 0))
                bottoms = [image.getchannel("A").getbbox()[3] for image in frames]
                self.assertEqual(len(set(bottoms)), 1)


if __name__ == "__main__":
    unittest.main()
