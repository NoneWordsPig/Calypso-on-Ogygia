"""PyQt6 desktop-pet window for Calypso's Ogygia.

Mirrors the reference hermes-pet presentation (frameless, always-on-top,
sprite-sheet animation driven by a polled status source) while rendering the
draft's map and walking its road network.
"""
from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QFont, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QWidget

from app.behavior import Behavior
from app.config import Config, ROOT
from app.hermes_status import make_provider
from app.navigation import Navigation
from app.sprites import AnimationPlayer, SpriteSheet
from app.time_system import GameTime

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None


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
    col_sum = [alpha.getpixel((x, 0)) for x in range(w)]
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
    for (x0, x1) in segs:
        strip = image.crop((x0, 0, x1, h))
        alpha_arr = strip.getchannel("A")
        bbox = alpha_arr.getbbox()
        if bbox:
            strip = strip.crop(bbox)
        frames.append(QPixmap.fromImage(_pil_to_qimage(strip)))
    return frames


class PetWindow(QWidget):
    def __init__(self, config: Config, smoke_frames: int = 0) -> None:
        super().__init__()
        self.config = config
        self.smoke_frames = smoke_frames
        self._smoke_count = 0

        self.setWindowTitle("Calypso's Ogygia")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._load_assets()
        self._build_ui_state()
        self._apply_geometry()

        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._on_tick)
        self._tick_timer.start(16)  # ~60 fps

        self._last_frame_at = time.perf_counter()
        self._last_poll_at = 0.0
        self._snapshot = None
        self._drag_offset: Optional[QPoint] = None

    # -- setup -----------------------------------------------------------
    def _load_assets(self) -> None:
        map_path = self.config.resource_path("map")
        self.map_pixmap = QPixmap(str(map_path))
        if self.map_pixmap.isNull():
            raise RuntimeError(f"cannot load map {map_path}")

        layout = self.config.get("resources", "spritesheet_layout", {})
        sheet_path = self.config.resource_path("spritesheet")
        self.sheet = SpriteSheet(sheet_path, layout)
        fps_cfg = self.config.get("movement", "fps", {})
        fps_map = {name: float(fps_cfg.get(name, 6.0)) for name in
                   ("idle", "walk", "work", "celebrate", "sleep", "waiting", "review", "failed")}
        self.player = AnimationPlayer(self.sheet, fps_map)

        self.computer_frames = _load_computer_frames(self.config.resource_path("computer"))
        self.computer_on = False

        self.nav = Navigation(self.config.resource_path("navigation"))
        self.time = GameTime(self.config)

        speed = float(self.config.get("movement", "speed", 67.5))
        arrive = float(self.config.get("movement", "arrive_radius", 12.0))
        spawn = self.nav.poi("spawn")
        from app.behavior import Actor
        self.actor = Actor(spawn, speed, arrive)
        self.behavior = Behavior(self.nav, self.actor, self.time, self.config)

        self.provider = make_provider(self.config)
        self.poll_interval = float(self.config.get("hermes", "poll_interval_seconds", 1.0))

        self.character_scale = self._character_scale()
        self.computer_scale = float(self.config.get("display", "computer_scale", 0.12))
        self.show_hud = bool(self.config.get("display", "show_hud", True))

    def _build_ui_state(self) -> None:
        self.font = QFont("Microsoft YaHei UI", 9)
        self.font_small = QFont("Microsoft YaHei UI", 8)
        self._zz_offset = 0.0

    def _character_scale(self) -> float:
        road_width = float(self.config.get("display", "road_width", 14.0))
        multiplier = float(self.config.get("display", "character_scale_multiplier", 2.0))
        frame_w = float(self.config.get("resources", "spritesheet_layout", {}).get("frame_width", 192))
        return road_width / frame_w * multiplier

    def _apply_geometry(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        mw, mh = self.map_pixmap.width(), self.map_pixmap.height()
        ratio = float(self.config.get("display", "fit_height_ratio", 0.82))
        scale = min(screen.width() / mw, screen.height() * ratio / mh)
        self.map_scale = scale
        self.window_w = int(mw * scale)
        self.window_h = int(mh * scale)
        self.resize(self.window_w, self.window_h)

        pos_mode = str(self.config.get("display", "start_position", "bottom_right"))
        if pos_mode == "bottom_right":
            self.move(screen.right() - self.window_w, screen.bottom() - self.window_h)
        elif pos_mode == "center":
            self.move(screen.center().x() - self.window_w // 2,
                      screen.center().y() - self.window_h // 2)
        else:
            self.move(screen.left(), screen.top())

    # -- coordinate helpers ----------------------------------------------
    def _world_to_screen(self, wx: float, wy: float) -> QPointF:
        mw, mh = self.map_pixmap.width(), self.map_pixmap.height()
        ox = (self.width() - mw * self.map_scale) / 2.0
        oy = (self.height() - mh * self.map_scale) / 2.0
        return QPointF(ox + wx * self.map_scale, oy + wy * self.map_scale)

    # -- main loop -------------------------------------------------------
    def _on_tick(self) -> None:
        now = time.perf_counter()
        dt = min(now - self._last_frame_at, 0.1)
        self._last_frame_at = now

        self.time.update(dt)

        if now - self._last_poll_at >= self.poll_interval:
            self._last_poll_at = now
            try:
                self._snapshot = self.provider.poll()
            except Exception as exc:  # provider must never crash the loop
                print(f"[hermes] poll error: {exc}")

        snapshot = self._snapshot
        if snapshot is None:
            from app.hermes_status import HermesSnapshot
            snapshot = HermesSnapshot()
            self._snapshot = snapshot

        self.behavior.update(dt, snapshot)
        self.player.set_state(self.behavior.animation_name())
        self.player.update(dt)
        self._zz_offset = (self._zz_offset + dt * 1.2) % (2 * math.pi)

        self.computer_on = self.behavior.state == "WORKING"
        self.update()

        if self.smoke_frames > 0:
            self._smoke_count += 1
            if self._smoke_count >= self.smoke_frames:
                print(f"[smoke] frames={self._smoke_count} time={self.time.format_time()} "
                      f"state={self.behavior.state} {self.behavior.debug_summary()}")
                QApplication.instance().quit()

    # -- painting --------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)

        mw, mh = self.map_pixmap.width(), self.map_pixmap.height()
        ox = (self.width() - mw * self.map_scale) / 2.0
        oy = (self.height() - mh * self.map_scale) / 2.0
        painter.drawPixmap(QRectF(ox, oy, mw * self.map_scale, mh * self.map_scale),
                           self.map_pixmap, QRectF(0, 0, mw, mh))

        self._draw_computer(painter)
        self._draw_character(painter)
        if self.behavior.state == "SLEEPING":
            self._draw_zzz(painter)
        if self.show_hud:
            self._draw_hud(painter)

    def _draw_computer(self, painter: QPainter) -> None:
        if not self.computer_frames:
            return
        frame = self.computer_frames[1 if self.computer_on and len(self.computer_frames) > 1 else 0]
        pos = self.nav.poi("computer")
        w = frame.width() * self.computer_scale * self.map_scale
        h = frame.height() * self.computer_scale * self.map_scale
        origin = self._world_to_screen(pos[0], pos[1])
        rect = QRectF(origin.x() - w / 2.0, origin.y() - h, w, h)
        painter.drawPixmap(rect, frame, QRectF(0, 0, frame.width(), frame.height()))

    def _draw_character(self, painter: QPainter) -> None:
        frame = self.player.current_pixmap()
        if frame.isNull():
            return
        w = frame.width() * self.character_scale * self.map_scale
        h = frame.height() * self.character_scale * self.map_scale
        origin = self._world_to_screen(self.actor.pos[0], self.actor.pos[1])
        rect = QRectF(origin.x() - w / 2.0, origin.y() - h, w, h)
        painter.drawPixmap(rect, frame, QRectF(0, 0, frame.width(), frame.height()))

        if self.behavior.state == "WORKING":
            # small working indicator above head
            head = QPointF(origin.x(), origin.y() - h)
            self._draw_bubble(painter, head, "工作", QColor(70, 130, 230, 220))

    def _draw_zzz(self, painter: QPainter) -> None:
        origin = self._world_to_screen(self.actor.pos[0], self.actor.pos[1])
        h = 208 * self.character_scale * self.map_scale
        painter.setFont(self.font)
        painter.setPen(QColor(120, 140, 190, 230))
        for i, ch in enumerate("zzz"):
            off = 10 + i * 12
            bob = math.sin(self._zz_offset + i * 1.1) * 3
            pt = QPointF(origin.x() + 14 + i * 6, origin.y() - h - off - bob)
            painter.drawText(pt.toPoint(), ch.upper() if i == 2 else ch)

    def _draw_bubble(self, painter: QPainter, at: QPointF, text: str, color: QColor) -> None:
        painter.setFont(self.font_small)
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(text) + 14
        th = fm.height() + 6
        rect = QRectF(at.x() - tw / 2, at.y() - th - 6, tw, th)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(QColor("white"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_hud(self, painter: QPainter) -> None:
        lines = [
            f"第 {self.time.day} 天  {self.time.format_time()}",
            f"状态：{self.behavior.state_zh()}",
            f"Hermes：{self._hermes_zh()}",
            f"优先级：{self.behavior.priorities[self.behavior.state]}",
        ]
        painter.setFont(self.font)
        fm = painter.fontMetrics()
        pad = 10
        w = max(fm.horizontalAdvance(line) for line in lines) + pad * 2
        h = fm.height() * len(lines) + pad * 2 + 4
        hud_rect = QRectF(10, 10, w, h)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(20, 24, 34, 185))
        painter.drawRoundedRect(hud_rect, 10, 10)
        painter.setPen(QColor(235, 238, 245))
        for i, line in enumerate(lines):
            painter.drawText(QPointF(10 + pad, 10 + pad + fm.ascent() + i * fm.height()), line)

        # reference-style badge with active session count
        if self._snapshot and self._snapshot.active_count > 0:
            cx = self.width() - 22
            cy = 22
            painter.setBrush(QColor(8, 177, 83))
            painter.drawEllipse(QPointF(cx, cy), 13, 13)
            painter.setPen(QColor("white"))
            painter.setFont(self.font_small)
            painter.drawText(QRectF(cx - 13, cy - 10, 26, 20),
                             Qt.AlignmentFlag.AlignCenter, str(self._snapshot.active_count))

    def _hermes_zh(self) -> str:
        if not self._snapshot:
            return "未知"
        labels = {
            "idle": "空闲", "working": "工作", "success": "成功",
            "waiting": "等待", "review": "审查", "failed": "失败",
        }
        return labels.get(self._snapshot.status, self._snapshot.status)

    # -- interaction -----------------------------------------------------
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_offset = None

    def keyPressEvent(self, event) -> None:  # noqa: N802
        key = event.key()
        if key == Qt.Key.Key_F5:
            self.show_hud = not self.show_hud
        elif key == Qt.Key.Key_F8:
            self.time.jump_hours(3.0)
        elif key == Qt.Key.Key_F9:
            self.behavior.request_work()
        elif key == Qt.Key.Key_F10:
            self.behavior.go_sleep()
        elif key == Qt.Key.Key_F11:
            self.behavior.wake_up()
        elif key == Qt.Key.Key_F12:
            self.behavior.reset()
        elif key == Qt.Key.Key_Escape:
            self.close()

    def _show_menu(self, global_pos: QPoint) -> None:
        menu = QMenu(self)
        actions = [
            ("显示/隐藏 HUD (F5)", Qt.Key.Key_F5),
            ("快进 3 小时 (F8)", Qt.Key.Key_F8),
            ("强制工作 (F9)", Qt.Key.Key_F9),
            ("强制睡觉 (F10)", Qt.Key.Key_F10),
            ("强制起床 (F11)", Qt.Key.Key_F11),
            ("重置空闲 (F12)", Qt.Key.Key_F12),
        ]
        for label, key in actions:
            act = QAction(label, self)
            act.triggered.connect(lambda _=False, k=key: self.keyPressEvent(
                _FakeKeyEvent(k)))
            menu.addAction(act)
        menu.addSeparator()
        quit_act = QAction("退出", self)
        quit_act.triggered.connect(self.close)
        menu.addAction(quit_act)
        menu.exec(global_pos)


class _FakeKeyEvent:
    def __init__(self, key) -> None:
        self._key = key

    def key(self):
        return self._key


def create_window(config: Config, smoke_frames: int = 0) -> PetWindow:
    return PetWindow(config, smoke_frames)
