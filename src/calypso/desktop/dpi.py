import ctypes, logging
def enable_per_monitor_v2():
    if hasattr(ctypes,'windll'):
        try: return bool(ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)))
        except Exception as exc: logging.getLogger(__name__).warning('DPI awareness unavailable: %s',exc)
    return False
set_process_dpi_awareness = enable_per_monitor_v2
