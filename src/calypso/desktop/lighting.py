"""Shared night palette for the map and character sprites."""

from PIL import Image


NIGHT_RED = [min(255, int(value * .38 + 3)) for value in range(256)]
NIGHT_GREEN = [min(255, int(value * .50 + 5)) for value in range(256)]
NIGHT_BLUE = [min(255, int(value * .72 + 13)) for value in range(256)]


def night_grade(image):
    """Apply the map's night palette while preserving transparent sprite pixels."""
    mode = "RGBA" if "A" in image.getbands() else "RGB"
    channels = image.convert(mode).split()
    shaded = (channels[0].point(NIGHT_RED),
              channels[1].point(NIGHT_GREEN),
              channels[2].point(NIGHT_BLUE))
    if mode == "RGBA":
        return Image.merge("RGBA", (*shaded, channels[3]))
    return Image.merge("RGB", shaded)
