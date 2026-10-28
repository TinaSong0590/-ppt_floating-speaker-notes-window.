"""Microsoft PowerPoint for Mac — read current slide index via AppleScript."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class PowerPointState:
    running: bool
    slide_index: Optional[int]  # 1-based
    slide_count: Optional[int]
    mode: str  # slideshow | edit | unknown
    error: str = ""


_SCRIPT = r'''
tell application "Microsoft PowerPoint"
  try
    set i to slide index of slide show view of slide show window 1
    try
      set c to count of slides of active presentation
    on error
      set c to -1
    end try
    return "SHOW|" & i & "|" & c
  on error
    try
      set i to slide index of slide of view of document window 1
      try
        set c to count of slides of active presentation
      on error
        set c to -1
      end try
      return "EDIT|" & i & "|" & c
    on error errMsg
      return "ERR|" & errMsg
    end try
  end try
end tell
'''


def _powerpoint_running() -> bool:
    try:
        r = subprocess.run(
            ["pgrep", "-x", "Microsoft PowerPoint"],
            capture_output=True,
            timeout=0.5,
            check=False,
        )
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def probe() -> PowerPointState:
    if not _powerpoint_running():
        return PowerPointState(False, None, None, "unknown")
    try:
        r = subprocess.run(
            ["osascript", "-e", _SCRIPT],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return PowerPointState(True, None, None, "unknown", str(exc))
    out = (r.stdout or "").strip()
    if out.startswith("SHOW|") or out.startswith("EDIT|"):
        kind, rest = out.split("|", 1)
        parts = rest.split("|")
        try:
            idx = int(parts[0])
        except ValueError:
            idx = None
        count = None
        if len(parts) > 1:
            try:
                c = int(parts[1])
                if c > 0:
                    count = c
            except ValueError:
                pass
        return PowerPointState(True, idx, count, "slideshow" if kind == "SHOW" else "edit")
    return PowerPointState(True, None, None, "unknown", out)
