"""Apply NSWindow.sharingType=.none to the front Tk window on macOS (best-effort).

Tk on macOS is backed by an NSWindow. After the UI is up, call
``protect_tk_window(tk_root)`` to set sharingType. This helps against *legacy*
capture only; see ``privacy.py``.
"""

from __future__ import annotations

import sys


def protect_tk_window(tk_root) -> str:
    if sys.platform != "darwin":
        return "not-darwin"
    try:
        from AppKit import NSApp, NSWindowSharingNone
    except ImportError:
        return "no-pyobjc"

    tk_root.update_idletasks()
    # Tk window id → Quartz window id is fragile; iterate NSApp windows by title.
    title = tk_root.title()
    matched = 0
    for win in NSApp.windows():
        try:
            if str(win.title()) == title or "备注" in str(win.title()):
                win.setSharingType_(NSWindowSharingNone)
                win.setLevel_(3)  # floating
                matched += 1
        except Exception:
            continue
    if matched:
        return f"protected:{matched}"
    return "no-window-matched"
