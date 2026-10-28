"""Cross-platform floating notes UI (Tk). Used on Linux/Windows and as fallback."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox
from typing import Callable


class NotesOverlayTk:
    def __init__(
        self,
        *,
        on_open: Callable[[str], None],
        on_prev: Callable[[], None],
        on_next: Callable[[], None],
        on_reload: Callable[[], None],
        on_probe_wps: Callable[[], None],
        on_font: Callable[[int], None],
        on_toggle_peek: Callable[[], None],
        on_privacy_info: Callable[[], None],
    ) -> None:
        self.root = tk.Tk()
        self.root.title("WPS 备注悬浮窗")
        self.root.geometry("520x420+80+80")
        self.root.configure(bg="#FFFFFF")
        self.root.attributes("-topmost", True)
        try:
            # Slightly opaque so text stays readable on any wallpaper
            self.root.attributes("-alpha", 0.97)
        except tk.TclError:
            pass
        self._bg = "#FFFFFF"
        self._fg = "#111111"
        self._muted = "#555555"

        self._on_open = on_open
        self._on_prev = on_prev
        self._on_next = on_next
        self._on_reload = on_reload
        self._on_probe = on_probe_wps
        self._on_font = on_font
        self._on_peek = on_toggle_peek
        self._on_privacy = on_privacy_info

        self._build()
        self._bind_keys()

    def _build(self) -> None:
        toolbar = tk.Frame(self.root, bg=self._bg)
        toolbar.pack(fill=tk.X, padx=6, pady=4)

        for text, cmd in [
            ("打开…", self._pick),
            ("←", self._on_prev),
            ("→", self._on_next),
            ("重载", self._on_reload),
            ("探测 WPS", self._on_probe),
            ("A-", lambda: self._on_font(-2)),
            ("A+", lambda: self._on_font(+2)),
            ("前后页", self._on_peek),
            ("隐私说明", self._on_privacy),
        ]:
            tk.Button(
                toolbar,
                text=text,
                command=cmd,
                bg="#EEEEEE",
                fg=self._fg,
                activebackground="#DDDDDD",
                activeforeground=self._fg,
                relief=tk.FLAT,
                padx=6,
            ).pack(side=tk.LEFT, padx=2)

        self.status = tk.StringVar(value="未加载文稿 · 快捷键 ← → Space")
        tk.Label(
            self.root,
            textvariable=self.status,
            anchor="w",
            bg=self._bg,
            fg=self._muted,
        ).pack(fill=tk.X, padx=8)

        self.peek_prev = tk.StringVar(value="")
        self.peek_next = tk.StringVar(value="")
        self.peek_frame = tk.Frame(self.root)
        tk.Label(
            self.peek_frame,
            textvariable=self.peek_prev,
            fg="#666",
            wraplength=400,
            justify="left",
            anchor="w",
        ).pack(fill=tk.X)
        tk.Label(
            self.peek_frame,
            textvariable=self.peek_next,
            fg="#666",
            wraplength=400,
            justify="left",
            anchor="w",
        ).pack(fill=tk.X)

        self.text = tk.Text(
            self.root,
            wrap=tk.WORD,
            padx=12,
            pady=10,
            bg="#FFFFFF",
            fg=self._fg,
            insertbackground=self._fg,
            highlightthickness=0,
            borderwidth=0,
            relief=tk.FLAT,
        )
        self.text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self._base_font = tkfont.Font(family="Helvetica", size=18)
        try:
            self.text.configure(font=self._base_font)
        except tk.TclError:
            self._base_font = tkfont.Font(size=18)
            self.text.configure(font=self._base_font)
        self.text.configure(state=tk.DISABLED)

        self._peek_visible = False

    def _try_mac_protect(self) -> None:
        try:
            from .mac_protect import protect_tk_window
            result = protect_tk_window(self.root)
            if result.startswith("protected"):
                cur = self.status.get()
                if "sharingType" not in cur:
                    self.status.set(cur + " · sharingType=none(尽力)")
        except Exception:
            pass

    def _bind_keys(self) -> None:
        self.root.bind("<Left>", lambda e: self._on_prev())
        self.root.bind("<Right>", lambda e: self._on_next())
        self.root.bind("<space>", lambda e: self._on_next())
        self.root.bind("<Prior>", lambda e: self._on_prev())
        self.root.bind("<Next>", lambda e: self._on_next())
        self.root.bind("<Command-o>", lambda e: self._pick())
        self.root.bind("<Control-o>", lambda e: self._pick())

    def _pick(self) -> None:
        path = filedialog.askopenfilename(
            title="选择带备注的演示文稿",
            filetypes=[
                ("PowerPoint / WPS OOXML", "*.pptx *.ppsx *.pptm"),
                ("All", "*.*"),
            ],
        )
        if path:
            self._on_open(path)

    def set_status(self, text: str) -> None:
        self.status.set(text)

    def set_notes(self, body: str) -> None:
        shown = body if (body and body.strip()) else "（本页无备注）"
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", shown)
        self.text.see("1.0")
        self.text.configure(state=tk.DISABLED)
        try:
            self.root.update_idletasks()
        except tk.TclError:
            pass

    def set_peek(self, prev_text: str | None, next_text: str | None) -> None:
        if not self._peek_visible:
            return
        self.peek_prev.set(
            ("上一页预览: " + (prev_text or "—")) if prev_text is not None else ""
        )
        self.peek_next.set(
            ("下一页预览: " + (next_text or "—")) if next_text is not None else ""
        )

    def toggle_peek_ui(self, visible: bool) -> None:
        self._peek_visible = visible
        if visible:
            self.peek_frame.pack(fill=tk.X, padx=8, before=self.text)
        else:
            self.peek_frame.pack_forget()

    def adjust_font(self, delta: int) -> None:
        size = max(10, min(48, int(self._base_font.cget("size")) + delta))
        self._base_font.configure(size=size)

    def alert(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message)

    def error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message)

    def run(self) -> None:
        self.root.mainloop()

    def after(self, ms: int, cb: Callable[[], None]) -> None:
        self.root.after(ms, cb)
