"""Convert the generated action sheets into aligned, transparent game frames.

The source sheets stay in assets/source so the selected artwork can be rebuilt.
All resizing here uses nearest-neighbor sampling and keeps a common feet anchor.
"""

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "source"
DEST = ROOT / "assets" / "calypso_v2"
BASELINE = 240


def save_frame(frame: Image.Image, path: Path, size: tuple[int, int],
               scale: float, center_x: float, feet_y: int) -> None:
    """Place an RGBA crop using one scale and one common body/feet anchor."""
    frame = frame.convert("RGBA")
    scaled = frame.resize((round(frame.width * scale), round(frame.height * scale)),
                          Image.Resampling.NEAREST)
    canvas = Image.new("RGBA", size)
    x = round(size[0] / 2 - center_x * scale)
    y = feet_y - scaled.getchannel("A").getbbox()[3]
    canvas.alpha_composite(scaled, (x, y))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, optimize=True)


def side_walk() -> None:
    side_sheet = Image.open(SOURCE / "calypso_sidewalk_sheet_v3.png").convert("RGBA")
    left_sheet = Image.open(SOURCE / "calypso_walk_left_sheet_v4.png").convert("RGBA")
    if side_sheet.size != (1774, 887) or left_sheet.size != (2172, 724):
        raise ValueError("Unexpected generated walking sheet size")
    # Keep each figure inside its own crop. The revised left strip has more
    # visible alternating leg positions than the first generated left row.
    left_x = [(60, 480), (630, 1040), (1120, 1570), (1720, 2100)]
    right_x = [(70, 350), (510, 810), (950, 1250), (1390, 1700)]
    cells = ([left_sheet.crop((x0, 0, x1, left_sheet.height)) for x0, x1 in left_x]
             + [side_sheet.crop((x0, 444, x1, side_sheet.height)) for x0, x1 in right_x])
    boxes = [cell.getchannel("A").getbbox() for cell in cells]
    for row, direction in enumerate(("left", "right")):
        for col in range(4):
            cell = cells[row * 4 + col]
            box = boxes[row * 4 + col]
            crop = cell.crop(box)
            # Generated poses vary slightly in size. Normalize the full body
            # height so the head does not bob when the feet stay planted.
            scale = 232 / crop.height
            save_frame(crop, DEST / f"walk_{direction}" / f"{col:02d}.png",
                       (256, 256), scale, crop.width / 2, BASELINE)


def fishing() -> None:
    sheet = Image.open(SOURCE / "calypso_fishing_sheet_v1.png").convert("RGBA")
    if sheet.size != (2172, 724):
        raise ValueError(f"Unexpected fishing sheet size: {sheet.size}")
    cuts = [0, 630, 1120, 1604, 2172]
    # Cast and pull keep their original artwork and action-specific curved line.
    for i, action, body_center in ((0, "cast", 460), (3, "pull", 1900)):
        crop = sheet.crop((cuts[i], 0, cuts[i + 1], sheet.height))
        path = DEST / "fishing" / action / "00.png"
        save_frame(crop, path, (384, 320), 0.42,
                   body_center - cuts[i], 308)
        frame = Image.open(path).convert("RGBA")
        canvas = Image.new("RGBA", (640, 520))
        canvas.alpha_composite(frame, (150, 0))
        canvas.save(path, optimize=True)

    # New line-free waiting poses are independent source art. Align their feet
    # at the same anchor so the only fishing line can be a separate overlay.
    placements = (((640, 520), (0, 15)), ((438, 356), (106, 26)))
    for index, (size, position) in enumerate(placements):
        source = SOURCE / f"calypso_fishing_wait_clean_{index:02d}.png"
        with Image.open(source) as original:
            if original.size != (1391, 1131):
                raise ValueError(f"Unexpected clean fishing pose size: {original.size}")
            pose = original.convert("RGBA").resize(size, Image.Resampling.NEAREST)
        # Generated transparent sprite edges use soft alpha; quantize them to
        # the same crisp transparency as the other pixel-art action frames.
        pose.putalpha(pose.getchannel("A").point(lambda value: 255 if value >= 100 else 0))
        canvas = Image.new("RGBA", (640, 520))
        canvas.alpha_composite(pose, position)
        path = DEST / "fishing" / "wait" / f"{index:02d}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(path, optimize=True)

        line = Image.new("RGBA", canvas.size)
        draw = ImageDraw.Draw(line)
        tip = (249, 154) if index == 0 else (245, 154)
        draw.line((tip, (49, 475)), fill=(42, 69, 75, 220), width=4)
        draw.ellipse((46, 472, 52, 478), fill=(112, 187, 191, 240))
        line_path = DEST / "fishing" / "line" / f"{index:02d}.png"
        line_path.parent.mkdir(parents=True, exist_ok=True)
        line.save(line_path, optimize=True)


if __name__ == "__main__":
    side_walk()
    fishing()
