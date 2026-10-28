"""Best-effort bridges to WPS Presentation on macOS.

Findings (2026 research):
- WPS Mac (bundle com.kingsoft.wpsoffice.mac, process often ``wpsoffice``)
  does **not** ship a usable AppleScript dictionary for slides/notes.
- Reliable approach: parse the .pptx on disk; sync page turns via hotkeys
  (user presses ←/→/Space in the overlay, mirroring WPS).
- Optional: use Accessibility / System Events to read front window title
  (sometimes contains file name) and ``lsof`` to guess the open file path.
- Live ``current slide index`` from WPS UI is unreliable across versions;
  we do not claim auto page-sync unless AX finds a clear slide indicator.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


WPS_PROCESS_CANDIDATES = ("wpsoffice", "WPS Office", "wpsoffice.localized")
WPS_BUNDLE_ID = "com.kingsoft.wpsoffice.mac"


@dataclass
class WpsStatus:
    running: bool
    process_names: list[str]
    window_titles: list[str]
    guessed_paths: list[str]
    notes: str


def _run(cmd: list[str], timeout: float = 5.0) -> str:
    try:
        out = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return out.stdout or ""
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return ""


def is_wps_running() -> bool:
    # pgrep -fl matches command line
    text = _run(["pgrep", "-fl", "wpsoffice"])
    if not text.strip():
        text = _run(["pgrep", "-fl", "WPS"])
    lines = [
        ln
        for ln in text.splitlines()
        if "wpsoffice" in ln.lower() or "/WPS" in ln
    ]
    # Filter common helpers
    helpers = ("wpscloudsvr", "WPSFinderMenu", "recentfiles", "wpsupdate")
    mains = [ln for ln in lines if not any(h in ln for h in helpers)]
    return bool(mains or lines)


def list_wps_window_titles() -> list[str]:
    script = """
    tell application "System Events"
      set titles to {}
      repeat with procName in {"wpsoffice", "WPS Office"}
        if exists process procName then
          tell process procName
            try
              set titles to titles & (name of every window)
            end try
          end tell
        end if
      end repeat
      return titles
    end tell
    """
    out = _run(["osascript", "-e", script])
    if not out.strip():
        return []
    # osascript list → comma separated
    parts = [p.strip() for p in out.replace("\n", ",").split(",") if p.strip()]
    return parts


def guess_open_presentation_paths() -> list[str]:
    """Use lsof on wpsoffice PIDs to find open .pptx/.dps paths."""
    pids_text = _run(["pgrep", "-f", "wpsoffice"])
    pids = [p for p in pids_text.split() if p.isdigit()]
    found: list[str] = []
    for pid in pids[:8]:
        lsof = _run(["lsof", "-p", pid, "-Fn"])
        for line in lsof.splitlines():
            if not line.startswith("n"):
                continue
            path = line[1:]
            lower = path.lower()
            if lower.endswith((".pptx", ".ppsx", ".pptm", ".dps", ".ppt")):
                if path not in found and Path(path).is_file():
                    found.append(path)
    return found


def probe() -> WpsStatus:
    running = is_wps_running()
    titles = list_wps_window_titles() if running else []
    paths = guess_open_presentation_paths() if running else []
    note_bits = [
        "WPS Mac 无公开的幻灯片/备注 AppleScript API。",
        "推荐：把当前文稿另存为 .pptx 后用本工具「打开文件」加载备注；翻页用本工具快捷键与 WPS 同步。",
    ]
    if paths:
        note_bits.append("lsof 猜到可能打开的文件: " + "; ".join(paths[:3]))
    if titles:
        note_bits.append("窗口标题: " + "; ".join(titles[:3]))
    return WpsStatus(
        running=running,
        process_names=["wpsoffice"] if running else [],
        window_titles=titles,
        guessed_paths=paths,
        notes="\n".join(note_bits),
    )


def try_parse_slide_index_from_title(title: str) -> int | None:
    """Heuristic only — WPS titles rarely include slide numbers."""
    m = re.search(r"(?:幻灯片|Slide)\s*[#:：]?\s*(\d+)", title, re.I)
    if m:
        return int(m.group(1))
    return None
