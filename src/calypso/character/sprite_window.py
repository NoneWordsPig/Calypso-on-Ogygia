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

        def sync(self, world_pos, frame, night=False, anchor=None, overlay=None):
            logical_h = max(1, round(
                self.target_height * self.transform.actual_primary_physical[1]
                / self.transform.world_size[1] / self.transform.dpi))
            key = (str(frame), logical_h, bool(night), str(overlay) if overlay else None)
            if key not in self._cache:
                raw = _night_pixmap(key[0]) if night else QPixmap(key[0])
                if overlay:
                    line = _night_pixmap(overlay) if night else QPixmap(overlay)
                    composed = QPixmap(raw.size())
                    composed.fill(Qt.transparent)
                    painter = QPainter(composed)
                    painter.drawPixmap(0, 0, line)
                    painter.drawPixmap(0, 0, raw)
                    painter.end()
                    raw = composed
                width = round(raw.width() * logical_h / raw.height())
                quality = (Qt.SmoothTransformation if raw.height() > logical_h * 8
                           else Qt.FastTransformation)
                pix = raw.scaled(width, logical_h, Qt.IgnoreAspectRatio,
                                 quality)
                mask = QBitmap.fromImage(pix.toImage().createAlphaMask())
                self._cache[key] = (pix, mask, raw.size())
            self._pix, self._mask, source_size = self._cache[key]
            if self.size() != self._pix.size():
                self.resize(self._pix.size())
            point = self.transform.world_to_logical(world_pos)
            raw_size = self._pix.size()
            if anchor is None:
                anchor = (raw_size.width() / 2, raw_size.height())
            else:
                anchor = (anchor[0] * self.width() / source_size.width(),
                          anchor[1] * self.height() / source_size.height())
            pos = (round(point[0] - anchor[0]),
                   round(point[1] - anchor[1]))
            if pos != self._last_pos:
                self.move(*pos)
                self._last_pos = pos
            if key != self._key:
                self.setMask(QRegion(self._mask))
                self.update()
                self._key = key

        def sync_target_height_world(self, world_pos, frame, target_height,
                                     night=False, anchor=None, overlay=None):
            self.target_height = int(target_height)
            self.sync(world_pos, frame, night=night, anchor=anchor, overlay=overlay)

        def paintEvent(self, event):
            if hasattr(self, "_pix"):
                QPainter(self).drawPixmap(0, 0, self._pix)

except ImportError:
    class SpriteWindow:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PySide6 is required for SpriteWindow")
