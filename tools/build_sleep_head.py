"""Extract Calypso from the older sleep frame without its painted bed."""

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "calypso" / "sleep" / "00.png"
DESTINATION = ROOT / "assets" / "calypso" / "sleep" / "head_extracted.png"
CROP = (50, 50, 278, 210)


def build(source=SOURCE, destination=DESTINATION):
    with Image.open(source) as original:
        frame = original.convert("RGBA")
    face = Image.new("1", frame.size)
    ImageDraw.Draw(face).polygon(
        [(158, 92), (181, 97), (202, 113), (211, 141),
         (204, 171), (186, 192), (151, 195), (127, 179),
         (118, 150), (125, 117), (143, 98)], fill=1)
    face_pixels = face.load()
    pixels = frame.load()
    extracted = Image.new("RGBA", (CROP[2] - CROP[0], CROP[3] - CROP[1]))
    target = extracted.load()
    for y in range(CROP[1], CROP[3]):
        for x in range(CROP[0], CROP[2]):
            red, green, blue, alpha = pixels[x, y]
            hair = (blue >= red + 2 and green >= red - 15
                    and max(red, green, blue) < 140)
            skin = (115 <= x <= 220 and 85 <= y <= 205
                    and red - green >= 32 and green - blue >= 8)
            if not (hair or skin or face_pixels[x, y]):
                continue
            # Hair strands that reach the crop edge fade into the pillow.
            edge = min(x - CROP[0], CROP[2] - 1 - x,
                       y - CROP[1], CROP[3] - 1 - y)
            fade = min(1.0, edge / 8)
            opacity = round(alpha * fade)
            if opacity:
                target[x - CROP[0], y - CROP[1]] = (
                    red, green, blue, opacity)
    destination.parent.mkdir(parents=True, exist_ok=True)
    extracted.save(destination)
    return destination


if __name__ == "__main__":
    print(build())
