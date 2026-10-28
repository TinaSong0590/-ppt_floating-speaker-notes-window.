"""Application controller: load deck, track slide index, drive UI."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

from . import privacy
from .bridges import wps_mac
from .notes_loader import DeckNotes, load_deck


class NotesApp:
    def __init__(self) -> None:
        self.deck: DeckNotes | None = None
        self.index = 1
        self.peek = False
        self.forward_keys = False  # was True: osascript keystrokes re-entered overlay and auto-flipped
        self.ui = None  # set by runner

    # --- mutations ---
    def open_path(self, path: str) -> None:
        try:
            self.deck = load_deck(path)
        except (OSError, ValueError) as exc:
            self.ui.error("无法打开", str(exc))
            return
        self.index = 1
        self.refresh()

    def reload(self) -> None:
        if not self.deck:
            self.ui.alert("提示", "还没有打开文稿。")
            return
        path = self.deck.path
        try:
            self.deck = load_deck(path)
        except (OSError, ValueError) as exc:
            self.ui.error("重载失败", str(exc))
            return
        self.index = min(self.index, self.deck.count)
        self.refresh()

    def prev(self) -> None:
        if not self.deck:
            return
        if self.index <= 1:
            return
        self.index -= 1
        self.refresh()
        if self.forward_keys:
            self._nudge_wps("prev")

    def next(self) -> None:
        if not self.deck:
            return
        if self.index >= self.deck.count:
            return
        self.index += 1
        self.refresh()
        if self.forward_keys:
            self._nudge_wps("next")

    def goto(self, index: int) -> None:
        """Jump to 1-based slide index (for random page picks / typed jump)."""
        if not self.deck:
            return
        try:
            i = int(index)
        except (TypeError, ValueError):
            return
        i = max(1, min(self.deck.count, i))
        if i == self.index:
            return
        self.index = i
        self.refresh()

    def sync_from_host(self) -> None:
        """Pull current slide from PowerPoint (WPS cannot reliably report jumps)."""
        if not self.deck:
            return
        try:
            from .slide_sync import poll_current_slide
        except Exception:
            return
        hit = poll_current_slide()
        if not hit:
            return
        if not (1 <= hit.index <= self.deck.count) or hit.index == self.index:
            return
        target = hit.index

        def _apply() -> None:
            if not self.deck:
                return
            if target != self.index and 1 <= target <= self.deck.count:
                self.index = target
                self.refresh()

        # Marshal onto UI thread when possible
        if self.ui is not None and hasattr(self.ui, "after"):
            self.ui.after(0, _apply)
        else:
            _apply()

    def _nudge_wps(self, direction: str) -> None:
        """Best-effort: send arrow key to WPS so deck and overlay stay aligned."""
        if platform.system() != "Darwin":
            return
        import subprocess

        key_code = "123" if direction == "prev" else "124"
        script = f'''
tell application "System Events"
  repeat with procName in {{"wpsoffice", "WPS Office"}}
    if exists process procName then
      tell process procName
        -- Do not steal focus aggressively; keystroke to WPS process
        try
          key code {key_code}
        end try
      end tell
      return
    end if
  end repeat
end tell
'''
        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=2,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass

    def font(self, delta: int) -> None:
        self.ui.adjust_font(delta)

    def toggle_peek(self) -> None:
        self.peek = not self.peek
        self.ui.toggle_peek_ui(self.peek)
        self.refresh()

    def privacy_info(self) -> None:
        lines = [privacy.GUIDANCE_ZH, "", "模式一览："]
        for m in privacy.MODES:
            flag = "✓ 相对安全" if m.is_safe else "⚠ 需注意"
            lines.append(f"• {m.title_zh} [{flag}]")
            lines.append(f"  {m.detail_zh}")
        self.ui.alert("投屏隐私说明", "\n".join(lines))

    def probe_wps(self) -> None:
        if platform.system() != "Darwin":
            self.ui.alert(
                "WPS 探测",
                "当前不在 macOS 上。到 Mac 上运行后可探测 WPS 进程 / 打开的文件。\n"
                "也可直接「打开」samples/demo-notes.pptx 试用界面。",
            )
            return
        st = wps_mac.probe()
        msg = st.notes
        if st.guessed_paths:
            path = st.guessed_paths[0]
            self.ui.alert("WPS 探测", msg + f"\n\n将尝试加载:\n{path}")
            self.open_path(path)
        else:
            self.ui.alert("WPS 探测", msg)

    def refresh(self) -> None:
        if not self.deck:
            self.ui.set_status("未加载文稿 · 在 WPS/PPT 里翻页，备注会跟着走")
            self.ui.set_notes("请打开与 WPS 正在放映的同一份 .pptx（含演讲者备注）。")
            return
        slide = self.deck.get(self.index)
        assert slide is not None
        title = slide.title_hint or ""
        status = (
            f"{self.deck.path.name}  ·  第 {self.index}/{self.deck.count} 页"
            + (f"  ·  {title}" if title else "")
            + "  ·  隐私：已开启防截屏隐身（推荐配合窗口放映）"
        )
        self.ui.set_status(status)
        self.ui.set_notes(slide.notes)
        if hasattr(self.ui, "set_index"):
            self.ui.set_index(self.index)
        if self.peek:
            prev_s = self.deck.get(self.index - 1)
            next_s = self.deck.get(self.index + 1)
            self.ui.set_peek(
                (prev_s.notes[:120] if prev_s and prev_s.notes else "（无）")
                if prev_s
                else None,
                (next_s.notes[:120] if next_s and next_s.notes else "（无）")
                if next_s
                else None,
            )

    def try_autoload_sample(self, repo_root: Path) -> None:
        sample = repo_root / "samples" / "demo-notes.pptx"
        if sample.is_file():
            try:
                self.deck = load_deck(sample)
                self.index = 1
            except (OSError, ValueError):
                return


def run_tk(initial_path: str | None = None) -> None:
    try:
        from .overlay_tk import NotesOverlayTk
    except ModuleNotFoundError as exc:
        if "tkinter" in str(exc).lower() or getattr(exc, "name", "") == "tkinter":
            raise SystemExit(
                "需要 Tkinter。\n"
                "macOS：用 python.org 安装包，或 brew install python-tk。\n"
                "Debian/Ubuntu：sudo apt install python3-tk。"
            ) from exc
        raise

    app = NotesApp()

    ui = NotesOverlayTk(
        on_open=app.open_path,
        on_prev=app.prev,
        on_next=app.next,
        on_reload=app.reload,
        on_probe_wps=app.probe_wps,
        on_font=app.font,
        on_toggle_peek=app.toggle_peek,
        on_privacy_info=app.privacy_info,
    )
    app.ui = ui

    if initial_path:
        app.ui.set_status(f"正在加载备注… {Path(initial_path).name}")
        app.ui.set_notes("正在读取演讲者备注，请稍候…")

        def _load() -> None:
            app.open_path(initial_path)

        ui.after(50, _load)
    else:
        app.refresh()

    ui.run()


def run_appkit(initial_path: str | None = None) -> None:
    from .overlay_appkit import NotesOverlayAppKit

    app = NotesApp()
    ui = NotesOverlayAppKit(
        on_open=app.open_path,
        on_prev=app.prev,
        on_next=app.next,
        on_reload=app.reload,
        on_probe_wps=app.probe_wps,
        on_font=app.font,
        on_toggle_peek=app.toggle_peek,
        on_privacy_info=app.privacy_info,
        on_goto=app.goto,
    )
    app.ui = ui
    if initial_path:
        app.ui.set_status(f"正在加载备注… {Path(initial_path).name}")
        app.ui.set_notes("正在读取演讲者备注，请稍候…")

        def _load() -> None:
            app.open_path(initial_path)

        ui.after(80, _load)
    else:
        app.refresh()

    # PowerPoint auto-follow runs off the UI thread — System Events can hang
    # on some Macs if polled on the main thread.
    import threading
    import time

    def _sync_loop() -> None:
        while True:
            try:
                app.sync_from_host()
            except Exception:
                pass
            time.sleep(1.0)

    threading.Thread(target=_sync_loop, daemon=True).start()
    ui.run()


def run(initial_path: str | None = None, prefer_appkit: bool = True) -> None:
    if prefer_appkit and platform.system() == "Darwin":
        from .overlay_appkit import available as appkit_available

        if not appkit_available():
            raise SystemExit("需要 PyObjC（pip install -e '.[mac]'）才能在 Mac 上显示悬浮窗。")
        # Do not fall back to Tk: after a failed AppKit NSApp init, Tk crashes hard.
        run_appkit(initial_path)
        return
    run_tk(initial_path)
