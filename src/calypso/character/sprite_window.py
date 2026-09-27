"""Transparent sprite window positioned by the character's world anchor."""

try:
    from PIL import Image
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QBitmap, QImage, QPainter, QPixmap, QRegion
    from PySide6.QtWidgets import QWidget

    from ..desktop.coordinate_mapper import ScreenTransform
    from ..desktop.lighting import night_grade
    from ..desktop.window_styles import apply_native_styles


    def _night_pixmap(path):
        with Image.open(path) as source:
            shaded = night_grade(source.convert("RGBA"))
        pixels = shaded.tobytes()
        image = QImage(pixels, shaded.width, shaded.height,
                       shaded.width * 4, QImage.Format_RGBA8888)
        return QPixmap.fromImage(image.copy())


    class SpriteWindow(QWidget):
        def __init__(self, manifest=None, transform=None, parent=None,
                     interactive=False, target_height=88):
            super().__init__(parent)
            self.transform = transform or ScreenTransform()
            self._cache = {}
            self._key = None
            self._last_pos = None
            self.target_height = int(target_height)
            flags = Qt.FramelessWindowHint | Qt.Tool
            flags |= Qt.Widget if interactive else Qt.WindowDoesNotAcceptFocus
            self.setWindowFlags(flags)
            self.setAttribute(Qt.WA_TranslucentBackground)
            apply_native_styles(self, interactive)

        def sync(self, world_pos, frame, night=False):
            logical_h = max(1, round(
                self.target_height * self.transform.actual_primary_physical[1]
                / self.transform.world_size[1] / self.transform.dpi))
            key = (str(frame), logical_h, bool(night))
            if key not in self._cache:
                raw = _night_pixmap(key[0]) if night else QPixmap(key[0])
                width = round(raw.width() * logical_h / raw.height())
                quality = (Qt.SmoothTransformation if raw.height() > logical_h * 8
                           else Qt.FastTransformation)
                pix = raw.scaled(width, logical_h, Qt.IgnoreAspectRatio,
                                 quality)
                mask = QBitmap.fromImage(pix.toImage().createAlphaMask())
                self._cache[key] = (pix, mask)
            self._pix, self._mask = self._cache[key]
            if self.size() != self._pix.size():
                self.resize(self._pix.size())
            point = self.transform.world_to_logical(world_pos)
            pos = (round(point[0] - self.width() / 2),
                   round(point[1] - self.height()))
            if pos != self._last_pos:
                self.move(*pos)
                self._last_pos = pos
            if key != self._key:
                self.setMask(QRegion(self._mask))
                self.update()
                self._key = key

        def sync_target_height_world(self, world_pos, frame, target_height,
                                     night=False):
            self.target_height = int(target_height)
            self.sync(world_pos, frame, night=night)

        def paintEvent(self, event):
            if hasattr(self, "_pix"):
                QPainter(self).drawPixmap(0, 0, self._pix)

except ImportError:
    class SpriteWindow:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PySide6 is required for SpriteWindow")
