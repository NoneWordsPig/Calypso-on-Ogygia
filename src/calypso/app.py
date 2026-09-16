"""Application entry point for the production PySide6 companion."""
import argparse
import atexit
import json
import logging
import os
import secrets
import signal
import sys
import time
from logging.handlers import RotatingFileHandler

from .config import PROJECT_ROOT
from .desktop.coordinate_mapper import ScreenTransform
from .desktop.dpi import enable_per_monitor_v2
from .character.animator import Animator
from .config import load_config


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", type=int, default=None)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--debug-overlay", action="store_true")
    modes.add_argument("--desktop", action="store_true")
    parser.add_argument("--fake-task", action="store_true")
    ns = parser.parse_args(argv)
    enable_per_monitor_v2()
    logdir = PROJECT_ROOT / "logs"
    logdir.mkdir(parents=True, exist_ok=True)
    pid_file = logdir / "calypso.pid"
    stop_file = logdir / "calypso.stop"
    ack_file = logdir / "calypso.stop.ack"
    stop_file.unlink(missing_ok=True)
    ack_file.unlink(missing_ok=True)
    control_token = secrets.token_hex(16)
    marker_payload = json.dumps({"pid": os.getpid(), "token": control_token})
    pid_file.write_text(marker_payload, encoding="ascii")
    def remove_control_files():
        try:
            if pid_file.exists() and pid_file.read_text(encoding="ascii").strip() == marker_payload:
                pid_file.unlink(missing_ok=True)
            stop_file.unlink(missing_ok=True)
            ack_file.unlink(missing_ok=True)
        except OSError:
            pass
    atexit.register(remove_control_files)
    logger = logging.getLogger("calypso")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(RotatingFileHandler(logdir / "calypso.log", maxBytes=1_000_000,
                                              backupCount=2, encoding="utf-8"))
    try:
        from PySide6.QtCore import QTimer, Qt
        from PySide6.QtGui import QIcon, QKeySequence, QShortcut
        from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon
    except ImportError as exc:
        raise RuntimeError("PySide6 is required; install requirements.txt") from exc
    from .runtime import Runtime
    from .character.sprite_window import SpriteWindow
    from .objects.computer_window import ComputerWindow
    from .desktop.desktop_host import DesktopHost, DesktopHostError

    logger.info("app start")
    app = QApplication([sys.argv[0]])
    cfg = load_config()
    runtime = Runtime(config=cfg)
    animator = Animator(cfg.sprite_manifest)
    screen = app.primaryScreen()
    geo = screen.geometry()
    dpr = screen.devicePixelRatio()
    transform = ScreenTransform(actual_primary_physical=(round(geo.width() * dpr),
                                                         round(geo.height() * dpr)), dpi=dpr)
    window = SpriteWindow(transform=transform, interactive=ns.debug_overlay, target_height=cfg.character_height)
    window.setFocusPolicy(Qt.StrongFocus if ns.debug_overlay else Qt.NoFocus)
    window.show()
    computer_window = ComputerWindow(transform=transform, navigation=runtime.navigation, target_height=cfg.computer_height)
    computer_window.show()
    host = DesktopHost() if ns.desktop else None
    if host:
        attached = True
        for child in (window, computer_window):
            try:
                host.attach(int(child.winId()))
            except DesktopHostError as exc:
                attached = False
                logger.warning("desktop attach failed: %s", exc)
                break
        logger.info("desktop attached %s", attached)
        if not attached:
            host.cleanup()
    tray = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        icon = PROJECT_ROOT / "assets" / "calypso" / "idle_down" / "00.png"
        tray = QSystemTrayIcon(QIcon(str(icon)), app)
        menu = QMenu()
        menu.addAction("Exit Calypso", app.quit)
        tray.setContextMenu(menu)
        tray.show()
    timer = QTimer(app)
    last = time.perf_counter()
    ticks = 0
    cleaned = False
    exit_logged = False

    def cleanup():
        nonlocal cleaned, exit_logged
        if cleaned:
            return
        cleaned = True
        timer.stop()
        stop_file.unlink(missing_ok=True)
        if tray is not None:
            tray.hide()
        if host is not None:
            host.cleanup()
        runtime.close()
        window.close()
        computer_window.close()
        if not exit_logged:
            logger.info("app exit")
            exit_logged = True

    app.aboutToQuit.connect(cleanup)

    def request_quit(*_args):
        app.quit()

    signal.signal(signal.SIGINT, request_quit)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_quit)
    shortcuts = [QShortcut(QKeySequence("F9"), window, activated=runtime.fake_task_start),
                 QShortcut(QKeySequence("F10"), window, activated=runtime.fake_task_finish),
                 QShortcut(QKeySequence("Escape"), window, activated=app.quit),
                 QShortcut(QKeySequence("Ctrl+Q"), window, activated=app.quit)]
    window._calypso_shortcuts = shortcuts

    def tick():
        nonlocal last, ticks
        now = time.perf_counter()
        dt = min(0.25, now - last)
        last = now
        try:
            if stop_file.exists():
                request_token = stop_file.read_text(encoding="ascii").strip()
                if request_token == control_token:
                    ack_file.write_text(control_token, encoding="ascii")
                    app.quit()
                    return
                stop_file.unlink(missing_ok=True)
            runtime.tick(dt)
            value = getattr(getattr(runtime.behavior, "state", None), "value", "").lower()
            if value in ("working", "sleeping"):
                animator.set_state("work" if value == "working" else "sleep")
            else:
                animator.select(getattr(runtime.character, "direction", "down"),
                                bool(getattr(runtime.character, "path", None)))
            animator.tick(dt, getattr(runtime.character, "running", False))
            path = animator.frame_path()
            if path:
                height = cfg.sleep_height if value == "sleeping" else cfg.character_height
                window.sync_target_height_world(runtime.character.feet_position, path, height)
            computer_window.sync_state(getattr(runtime.computer, "on", False))
        except Exception:
            logger.exception("timer exception")
            app.quit()
            return
        ticks += 1
        if ns.fake_task and ticks == 5:
            runtime.fake_task_start()
        if ns.fake_task and ticks == 100:
            runtime.fake_task_finish()
        if ns.smoke is not None and ticks >= ns.smoke:
            print("smoke:", ticks, "ticks")
            app.quit()

    timer.timeout.connect(tick)
    timer.start(33)
    return app.exec()
