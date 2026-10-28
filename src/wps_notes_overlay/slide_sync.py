"""Poll host apps for current slide index (best-effort)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .bridges import powerpoint_mac, wps_mac


@dataclass
class SyncHit:
    source: str
    index: int  # 1-based
    detail: str = ""


def poll_current_slide() -> Optional[SyncHit]:
    """Return current 1-based slide index from PowerPoint if available.

    WPS Mac does not expose a reliable current-slide API for random thumbnail
    clicks; callers should offer a manual jump control for WPS.
    """
    ppt = powerpoint_mac.probe()
    if ppt.running and ppt.slide_index and ppt.slide_index > 0:
        return SyncHit("PowerPoint", ppt.slide_index, ppt.mode)

    # Best-effort WPS title parse (rarely works)
    try:
        for title in wps_mac.list_wps_window_titles():
            idx = wps_mac.try_parse_slide_index_from_title(title)
            if idx:
                return SyncHit("WPS", idx, title)
    except Exception:
        pass
    return None
