"""Resize the edited, tree-free and water-free map to the game's source grid."""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "source" / "environment" / "bare_map_donor.png"
DESTINATION = ROOT / "assets" / "map" / "map_bare.png"


def build():
    with Image.open(SOURCE) as image:
        bare = image.convert("RGB").resize((1312, 816), Image.Resampling.BOX)
    bare.save(DESTINATION, optimize=True)


if __name__ == "__main__":
    build()
