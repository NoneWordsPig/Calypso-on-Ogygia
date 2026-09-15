"""Desktop overlay + control panel for Calypso's Ogygia.

The map is the desktop wallpaper, so the main window is a transparent,
click-through, always-on-top overlay covering the screen and drawing ONLY the
character and the computer. A small control panel provides interaction (time,
state, debug actions, exit).

This is the native Windows path (Qt layered windows on Win32); the same logic
can be ported to a Tauri/WebView shell later if desired.
"""
from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.behavior import Actor, Behavior
from app.config import Config
from app.hermes_status import HermesSnapshot, make_provider
from app.navigation import Navigation
from app.sprites import AnimationPlayer, SpriteSheet
from app.time_system import GameTime
from app.wallpaper import WallpaperPlacement

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

FONT = "Microsoft YaHei UI"


def _pil_to_qimage(pil_image) -> QImage:
    img = pil_image.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, img.width, img.height, img.width * 4, QImage.Format.Format_RGBA8888)
    return qimg.copy()


def _load_computer_frames(path: Path) -> list[QPixmap]:
    """Split assets/object/computer.png into off/on frames via transparent gutters."""
    image = Image.open(path).convert("RGBA")
    w, h = image.size
    alpha = image.split()[3]
    col_content = [any(alpha.getpixel((x, y)) > 0 for y in range(0, h, 4)) for x in range(w)]
    segs: list[tuple[int, int]] = []
    in_seg = False
    start = 0
    for x in range(w):
        if col_content[x] and not in_seg:
            in_seg, start = True, x
        elif not col_content[x] and in_seg:
            in_seg = False
            if x - start > 8:
                segs.append((start, x))
    if in_seg and w - start > 8:
        segs.append((start, w))
    if not segs:
        return [QPixmap.fromImage(_pil_to_qimage(image))]
    frames: list[QPixmap] = []
    for x0, x1 in segs:
        strip = image.crop((x0, 0, x1, h))
        bbox = strip.getchannel("A").getbbox()
        if bbox:
            strip = strip.crop(bbox)
        frames.append(QPixmap.fromImage(_pil_to_qimage(strip)))
    return frames


class PetCore:
    """Non-GUI simulation core shared by the overlay and the control panel."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.nav = Navigation(config.resource_path("navigation"))
        self.time = GameTime(config)
        speed = float(config.get("movement", "speed", 67.5))
        arrive = float(config.get("movement", "arrive_radius", 12.0))
        self.actor = Actor(self.nav.poi("spawn"), speed, arrive)
        self.behavior = Behavior(self.nav, self.actor, self.time, config)
        self.provider = make_provider(config)
        self.poll_interval = float(config.get("hermes", "poll_interval_seconds", 1.0))
        self.fps_map = dict(config.get("movement", "fps", {}))
        self.snapshot = HermesSnapshot()
        self.animation_name = "idle"
        self.animation_fps = 4.0
        self.computer_on = False
        self._last_poll = 0.0

    def update(self, dt: float) -> None:
        self.time.update(dt)
        now = time.perf_counter()
        if now - self._last_poll >= self.poll_interval:
            self._last_poll = now
            try:
                self.snapshot = self.provider.poll()
            except Exception as exc:  # provider must never crash the loop
                print(f"[hermes] poll error: {exc}")
        self.behavior.update(dt, self.snapshot)
        self.animation_name = self.behavior.animation_name()
        self.animation_fps = self.behavior.fps(self.fps_map)
        self.computer_on = self.behavior.state == "WORKING"

    # -- panel-facing helpers -------------------------------------------
    def hermes_zh(self) -> str:
        labels = {
            "idle": "空闲", "working": "工作", "success": "成功",
            "waiting": "等待", "review": "审查", "failed": "失败",
        }
        return labels.get(self.snapshot.status, self.snapshot.status)

    def status_lines(self) -> list[str]:
        return [
            f"第 {self.time.day} 天  {self.time.format_time()}",
            f"状态：{self.behavior.state_zh()}（{self.behavior.state}）",
            f"Hermes：{self.hermes_zh()}",
            f"位置：({self.actor.pos[0]:.0f}, {self.actor.pos[1]:.0f})",
            f"动画：{self.animation_name}  {self.animation_fps:.0f}fps",
        ]


class DesktopOverlay(QWidget):
    """Transparent always-on-top overlay drawing the pet over the wallpaper."""

    def __init__(self, config: Config, core: PetCore) -> None:
        super().__init__()
        self.config = config
        self.core = core
        self.smoke_frames = 0
        self._smoke_count = 0

        self.setWindowTitle("Calypso's Ogygia")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                          bool(config.get("display", "click_through", True)))

        self.screen = QApplication.primaryScreen()
        self.setGeometry(self.screen.geometry())

        self.draw_debug_map = bool(config.get("display", "draw_debug_map", False))
        self.show_shadow = bool(config.get("display", "show_shadow", True))
        self.show_status_bubble = bool(config.get("display", "show_status_bubble", False))

        self._load_visuals()
        self._zz_offset = 0.0
        self._last_frame_at = time.perf_counter()

        self._tick = QTimer(self)
        self._tick.timeout.connect(self._on_tick)
        self._tick.start(16)

    # -- visuals ---------------------------------------------------------
    def _load_visuals(self) -> None:
        layout = self.config.get("resources", "spritesheet_layout", {})
        self.sheet = SpriteSheet(self.config.resource_path("spritesheet"), layout)
        self.player = AnimationPlayer(self.sheet, dict(self.core.fps_map))
        self.computer_frames = _load_computer_frames(self.config.resource_path("computer"))

        mw = float(self.config.get("display", "wallpaper", {}).get("map_width", 1312))
        mh = float(self.config.get("display", "wallpaper", {}).get("map_height", 816))
        geo = self.screen.geometry()
        self.core.placement = WallpaperPlacement(self.config, geo.width(), geo.height(), int(mw), int(mh))

        road_width = float(self.config.get("display", "road_width", 14.0))
        multiplier = float(self.config.get("display", "character_scale_multiplier", 2.0))
        frame_w = float(layout.get("frame_width", 192))
        self.character_scale = road_width / frame_w * multiplier  # map px per sprite px
        self.computer_scale = float(self.config.get("display", "computer_scale", 0.12))

        if self.draw_debug_map:
            self.map_pixmap = QPixmap(str(self.config.resource_path("map")))

    # -- loop ------------------------------------------------------------
    def _on_tick(self) -> None:
        now = time.perf_counter()
        dt = min(now - self._last_frame_at, 0.1)
        self._last_frame_at = now

        self.core.update(dt)
        self.player.set_state(self.core.animation_name)
        self.player.update(dt)
        self._zz_offset = (self._zz_offset + dt * 1.2) % (2 * math.pi)
        self.update()

        if self.smoke_frames > 0:
            self._smoke_count += 1
            if self._smoke_count >= self.smoke_frames:
                print(f"[smoke] frames={self._smoke_count} time={self.core.time.format_time()} "
                      f"state={self.core.behavior.state} "
                      f"{self.core.behavior.debug_summary()}")
                QApplication.instance().quit()

    # -- painting --------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)

        if self.draw_debug_map:
            self._paint_debug_map(painter)

        self._draw_computer(painter)
        self._draw_character(painter)
        if self.core.behavior.state == "SLEEPING":
            self._draw_zzz(painter)
        if self.show_status_bubble and self.core.behavior.state not in ("WALKING", "IDLE"):
            self._draw_status_bubble(painter)

    def _paint_debug_map(self, painter: QPainter) -> None:
        pm = self.map_pixmap
        if pm.isNull():
            return
        p = self.core.placement
        painter.drawPixmap(QRectF(p.offset_x, p.offset_y, pm.width() * p.scale_x, pm.height() * p.scale_y),
                           pm, QRectF(0, 0, pm.width(), pm.height()))

    def _char_rect(self) -> QRectF:
        frame = self.player.current_pixmap()
        w = frame.width() * self.character_scale * self.core.placement.scale
        h = frame.height() * self.character_scale * self.core.placement.scale
        sx, sy = self.core.placement.map_to_screen(*self.core.actor.pos)
        return QRectF(sx - w / 2.0, sy - h, w, h)

    def _draw_shadow(self, painter: QPainter, rect: QRectF) -> None:
        cx = rect.center().x()
        bottom = rect.bottom()
        painter.setBrush(QColor(0, 0, 0, 70))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(cx - rect.width() * 0.28, bottom - 4,
                                   rect.width() * 0.56, rect.height() * 0.10))

    def _draw_character(self, painter: QPainter) -> None:
        frame = self.player.current_pixmap()
        if frame.isNull():
            return
        rect = self._char_rect()
        if self.show_shadow:
            self._draw_shadow(painter, rect)
        painter.drawPixmap(rect, frame, QRectF(0, 0, frame.width(), frame.height()))

    def _draw_computer(self, painter: QPainter) -> None:
        if not self.computer_frames:
            return
        frame = self.computer_frames[1 if self.core.computer_on and len(self.computer_frames) > 1 else 0]
        p = self.core.placement
        sx, sy = p.map_to_screen(*self.core.nav.poi("computer"))
        w = frame.width() * self.computer_scale * p.scale
        h = frame.height() * self.computer_scale * p.scale
        painter.drawPixmap(QRectF(sx - w / 2.0, sy - h, w, h), frame,
                           QRectF(0, 0, frame.width(), frame.height()))

    def _draw_zzz(self, painter: QPainter) -> None:
        p = self.core.placement
        sx, sy = p.map_to_screen(*self.core.actor.pos)
        h = 208 * self.character_scale * p.scale
        painter.setFont(QFont(FONT, 9))
        painter.setPen(QColor(120, 140, 190, 230))
        for i, ch in enumerate("zzz"):
            off = 8 + i * 12
            bob = math.sin(self._zz_offset + i * 1.1) * 3
            painter.drawText(QPointF(sx + 12 + i * 6, sy - h - off - bob).toPoint(),
                             ch.upper() if i == 2 else ch)

    def _draw_status_bubble(self, painter: QPainter) -> None:
        rect = self._char_rect()
        text = self.core.behavior.state_zh()
        painter.setFont(QFont(FONT, 9))
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(text) + 14
        th = fm.height() + 6
        bubble = QRectF(rect.center().x() - tw / 2, rect.top() - th - 6, tw, th)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(20, 24, 34, 190))
        painter.drawRoundedRect(bubble, 6, 6)
        painter.setPen(QColor(235, 238, 245))
        painter.drawText(bubble, Qt.AlignmentFlag.AlignCenter, text)


class ControlPanel(QWidget):
    """Small interactive panel for status + debug actions."""

    def __init__(self, config: Config, core: PetCore) -> None:
        super().__init__()
        self.core = core
        self.setWindowTitle("Calypso 控制面板")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet(_PANEL_QSS)
        self._build_ui()
        self._position(config)

        self._refresh = QTimer(self)
        self._refresh.timeout.connect(self._update_labels)
        self._refresh.start(200)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        self.title = QLabel("Calypso's Ogygia")
        self.title.setObjectName("title")
        root.addWidget(self.title)

        self.labels: list[QLabel] = []
        for _ in range(5):
            lab = QLabel("")
            lab.setObjectName("line")
            root.addWidget(lab)
            self.labels.append(lab)

        rows = [
            ("+3小时", self._jump_3h), ("工作", self._work),
            ("睡觉", self._sleep), ("起床", self._wake),
            ("空闲", self._reset), ("庆祝", self._celebrate),
            ("隐藏面板", self.hide), ("退出", QApplication.instance().quit),
        ]
        grid = QHBoxLayout()
        for i in range(0, len(rows), 2):
            col = QVBoxLayout()
            for label, fn in rows[i:i + 2]:
                btn = QPushButton(label)
                btn.clicked.connect(fn)
                col.addWidget(btn)
            grid.addLayout(col)
        root.addLayout(grid)
        self.setFixedWidth(236)

    def _position(self, config: Config) -> None:
        pos = str(config.get("display", "control_panel", {}).get("position", "top_right"))
        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        if pos == "top_right":
            self.move(screen.right() - self.width() - 16, screen.top() + 16)
        elif pos == "bottom_right":
            self.move(screen.right() - self.width() - 16, screen.bottom() - self.height() - 16)
        else:
            self.move(screen.left() + 16, screen.top() + 16)

    def _update_labels(self) -> None:
        for lab, line in zip(self.labels, self.core.status_lines()):
            if lab.text() != line:
                lab.setText(line)

    def _jump_3h(self) -> None:
        self.core.time.jump_hours(3.0)

    def _work(self) -> None:
        self.core.behavior.request_work()

    def _sleep(self) -> None:
        self.core.behavior.go_sleep()

    def _wake(self) -> None:
        self.core.behavior.wake_up()

    def _reset(self) -> None:
        self.core.behavior.reset()

    def _celebrate(self) -> None:
        self.core.behavior.request_celebrate()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        key = event.key()
        if key == Qt.Key.Key_F8:
            self._jump_3h()
        elif key == Qt.Key.Key_F9:
            self._work()
        elif key == Qt.Key.Key_F10:
            self._sleep()
        elif key == Qt.Key.Key_F11:
            self._wake()
        elif key == Qt.Key.Key_F12:
            self._reset()
        elif key == Qt.Key.Key_Escape:
            self.hide()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif event.button() == Qt.MouseButton.RightButton:
            self.hide()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if getattr(self, "_drag", None) is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag = None


_PANEL_QSS = """
QWidget { background: #20242c; color: #eef1f6; font-family: "Microsoft YaHei UI"; font-size: 12px; }
QLabel#title { font-size: 13px; font-weight: 700; color: #9fd0ff; }
QLabel#line { color: #cdd4e0; }
QPushButton { background: #2e3542; border: 1px solid #3c4556; border-radius: 6px; padding: 4px 10px; }
QPushButton:hover { background: #3a4354; }
QPushButton:pressed { background: #232a35; }
"""
