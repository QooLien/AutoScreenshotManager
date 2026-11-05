def ensure_interactive_desktop():
    """Reject a locked / secure desktop instead of recording unreliable pixels."""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    user32.OpenInputDesktop.restype = wintypes.HANDLE
    user32.SwitchDesktop.argtypes = [wintypes.HANDLE]
    user32.SwitchDesktop.restype = wintypes.BOOL
    user32.CloseDesktop.argtypes = [wintypes.HANDLE]
    desktop = user32.OpenInputDesktop(0, False, 0x0100)
    if not desktop:
        raise RuntimeError("無法存取互動桌面：可能已鎖定、顯示 UAC 或處於不同登入工作階段。")
    try:
        if not user32.SwitchDesktop(desktop):
            raise RuntimeError("桌面目前無法擷取：請解鎖 Windows 並關閉安全桌面提示。")
    finally:
        user32.CloseDesktop(desktop)
