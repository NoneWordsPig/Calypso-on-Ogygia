import argparse, sys, time, logging
from logging.handlers import RotatingFileHandler
from .config import PROJECT_ROOT
from .desktop.dpi import enable_per_monitor_v2
from .desktop.coordinate_mapper import ScreenTransform
from .character.animator import Animator

def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument('--smoke',type=int,default=None); mode=parser.add_mutually_exclusive_group(); mode.add_argument('--debug-overlay',action='store_true'); mode.add_argument('--desktop',action='store_true'); parser.add_argument('--fake-task',action='store_true')
    ns=parser.parse_args(argv)
    enable_per_monitor_v2()
    logdir=PROJECT_ROOT/'logs'; logdir.mkdir(parents=True,exist_ok=True); logger=logging.getLogger('calypso'); logger.setLevel(logging.INFO)
    if not logger.handlers: logger.addHandler(RotatingFileHandler(logdir/'calypso.log',maxBytes=1_000_000,backupCount=2,encoding='utf-8'))
    logger.info('app start')
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer, Qt
    except ImportError as exc: raise RuntimeError('PySide6 is required; install requirements.txt') from exc
    from .runtime import Runtime
    from .character.sprite_window import SpriteWindow
    from .objects.computer_window import ComputerWindow
    from .desktop.desktop_host import DesktopHost, DesktopHostError
    qt_args=list(argv) if argv is not None else sys.argv[1:]
    app=QApplication([sys.argv[0]]); runtime=Runtime(); animator=Animator()
    screen=app.primaryScreen(); geo=screen.geometry(); dpr=screen.devicePixelRatio()
    transform=ScreenTransform(actual_primary_physical=(round(geo.width()*dpr),round(geo.height()*dpr)),dpi=dpr)
    window=SpriteWindow(transform=transform, interactive=ns.debug_overlay); window.setFocusPolicy(Qt.StrongFocus if ns.debug_overlay else Qt.NoFocus); window.show()
    computer_window=ComputerWindow(transform=transform, navigation=runtime.navigation); computer_window.show()
    host = DesktopHost() if ns.desktop else None
    if host:
        attached = True
        for child in (window, computer_window):
            try: host.attach(int(child.winId()))
            except DesktopHostError as exc:
                attached = False; logger.warning('desktop attach failed: %s', exc); break
        logger.info('desktop attached %s', attached)
        if not attached: host.cleanup()
        app.aboutToQuit.connect(host.cleanup)
    try:
        from PySide6.QtGui import QShortcut, QKeySequence
        QShortcut(QKeySequence('F9'), window, activated=runtime.fake_task_start)
        QShortcut(QKeySequence('F10'), window, activated=runtime.fake_task_finish)
    except Exception:
        pass
    timer=QTimer(); last=time.perf_counter(); ticks=0
    shortcuts=[]
    def tick():
        nonlocal last,ticks
        now=time.perf_counter(); dt=min(.25,now-last); last=now
        try: runtime.tick(dt)
        except Exception: logger.exception('timer exception'); app.quit(); return
        c=runtime.character; state=getattr(runtime.behavior,'state',None); value=getattr(state,'value',str(state)).lower()
        if value in ('working','sleeping'): animator.set_state('work' if value=='working' else 'sleep')
        else: animator.select(getattr(c,'direction','down'),bool(getattr(c,'path',None)))
        animator.tick(dt,getattr(c,'running',False)); path=animator.frame_path()
        if path: window.sync(c.feet_position,path)
        computer_window.sync_state(getattr(runtime.computer,'on',False))
        ticks+=1
        if ns.fake_task and ticks==5: runtime.fake_task_start()
        if ns.fake_task and ticks==100: runtime.fake_task_finish()
        if ns.smoke is not None and ticks>=ns.smoke: logger.info('app exit'); print('smoke:',ticks,'ticks'); app.quit()
    timer.timeout.connect(tick); timer.start(33)
    return app.exec()
