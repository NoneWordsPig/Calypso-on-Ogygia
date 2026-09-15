import ctypes
WS_EX_TOOLWINDOW=0x80; WS_EX_NOACTIVATE=0x8000000; WS_EX_LAYERED=0x80000; WS_EX_TRANSPARENT=0x20
def apply_native_styles(widget, interactive=False, click_through=False):
    if not hasattr(ctypes,'windll'): return
    hwnd=int(widget.winId()); u=ctypes.windll.user32; G=-20; s=u.GetWindowLongW(hwnd,G); flags=WS_EX_TOOLWINDOW|WS_EX_LAYERED|(0 if interactive else WS_EX_NOACTIVATE)|(WS_EX_TRANSPARENT if click_through else 0); u.SetWindowLongW(hwnd,G,s|flags)
