"""macOS AppKit floating notes window (primary UI on Mac)."""

from __future__ import annotations

from typing import Callable, Optional

try:
    from AppKit import (
        NSApp,
        NSApplication,
        NSApplicationActivationPolicyRegular,
        NSBackingStoreBuffered,
        NSButton,
        NSColor,
        NSFont,
        NSMakeRect,
        NSObject,
        NSScrollView,
        NSTextField,
        NSTextView,
        NSView,
        NSWindow,
        NSWindowStyleMaskNonactivatingPanel,
        NSWindowStyleMaskUtilityWindow,
        NSPanel,
        NSFloatingWindowLevel,
        NSScreenSaverWindowLevel,
        NSPopUpMenuWindowLevel,
        NSStatusWindowLevel,
        NSWindowStyleMaskTitled,
        NSWindowStyleMaskClosable,
        NSWindowStyleMaskResizable,
        NSWindowSharingNone,
        NSWindowCollectionBehaviorCanJoinAllSpaces,
        NSWindowCollectionBehaviorFullScreenAuxiliary,
        NSWindowCollectionBehaviorStationary,
        NSViewWidthSizable,
        NSViewHeightSizable,
        NSViewMinYMargin,
        NSOpenPanel,
        NSAlert,
        NSBezelStyleRounded,
        NSEvent,
        NSKeyDownMask,
        NSWorkspace,
    )
    import objc

    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False


def available() -> bool:
    return HAS_APPKIT


if HAS_APPKIT:

    class NotesOverlayAppKit:
        """Thin Python wrapper around the AppKit controller."""

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
            on_goto=None,
        ) -> None:
            self._on_open = on_open
            self._on_prev = on_prev
            self._on_next = on_next
            self._on_reload = on_reload
            self._on_probe = on_probe_wps
            self._on_font = on_font
            self._on_peek = on_toggle_peek
            self._on_privacy = on_privacy_info
            self._on_goto = on_goto or (lambda _n: None)
            self._font_size = 18.0
            self._controller = None
            self._pending: list[Callable[[], None]] = []

        def _ensure(self):
            if self._controller is None:
                raise RuntimeError("AppKit UI not started")

        def set_status(self, text: str) -> None:
            if self._controller:
                self._controller.setStatus_(str(text))

        def set_index(self, index: int) -> None:
            if self._controller:
                self._controller.setIndex_(int(index))

        def set_notes(self, body: str) -> None:
            shown = body if (body and str(body).strip()) else "（本页无备注）"
            if self._controller:
                self._controller.setNotes_(shown)

        def set_peek(self, prev_text, next_text) -> None:
            return

        def toggle_peek_ui(self, visible: bool) -> None:
            return

        def adjust_font(self, delta: int) -> None:
            self._font_size = max(10.0, min(48.0, self._font_size + float(delta)))
            if self._controller:
                self._controller.setFontSize_(self._font_size)

        def alert(self, title: str, message: str) -> None:
            alert = NSAlert.alloc().init()
            alert.setMessageText_(title)
            alert.setInformativeText_(message[:4000])
            alert.runModal()

        def error(self, title: str, message: str) -> None:
            self.alert(title, message)

        def after(self, ms: int, cb: Callable[[], None]) -> None:
            # Run soon on main runloop via performSelector
            delay = max(0.01, ms / 1000.0)
            if self._controller:
                self._controller.scheduleCallback_after_(cb, delay)
            else:
                self._pending.append(cb)

        def run(self) -> None:
            app = NSApplication.sharedApplication()
            app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
            self._controller = OverlayController.alloc().initWithOwner_(self)
            for cb in self._pending:
                self.after(50, cb)
            self._pending.clear()
            app.activateIgnoringOtherApps_(True)
            app.run()

        # called from ObjC buttons
        def goto_page(self, text: str) -> None:
            raw = (text or "").strip()
            if not raw:
                return
            # accept "12" or "12/39"
            raw = raw.split("/", 1)[0].strip()
            try:
                n = int(raw)
            except ValueError:
                self.alert("跳转", "请输入页码数字，例如 12")
                return
            if hasattr(self, "_on_goto"):
                self._on_goto(n)

        def _pick_file(self) -> None:
            panel = NSOpenPanel.openPanel()
            panel.setCanChooseFiles_(True)
            panel.setCanChooseDirectories_(False)
            panel.setAllowsMultipleSelection_(False)
            panel.setTitle_("选择带备注的演示文稿")
            panel.setAllowedFileTypes_(["pptx", "ppsx", "pptm"])
            if panel.runModal():
                url = panel.URLs()[0]
                path = url.path()
                self._on_open(path)

    class OverlayController(NSObject):
        def initWithOwner_(self, owner):
            self = objc.super(OverlayController, self).init()
            if self is None:
                return None
            self.owner = owner
            self._build()
            return self

        def _build(self):
            style = (
                NSWindowStyleMaskTitled
                | NSWindowStyleMaskClosable
                | NSWindowStyleMaskResizable
            )
            frame = NSMakeRect(120, 180, 560, 440)
            style = style | NSWindowStyleMaskUtilityWindow | NSWindowStyleMaskNonactivatingPanel
            self.window = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
                frame, style, NSBackingStoreBuffered, False
            )
            self.window.setFloatingPanel_(True)
            self.window.setBecomesKeyOnlyIfNeeded_(True)
            self.window.setWorksWhenModal_(True)
            self.window.setTitle_("WPS 备注悬浮窗")
            self.window.setLevel_(2147483628)  # near CG max, above WPS/Feishu fullscreen
            self.window.setCollectionBehavior_(
                NSWindowCollectionBehaviorCanJoinAllSpaces
                | NSWindowCollectionBehaviorFullScreenAuxiliary
                | NSWindowCollectionBehaviorStationary
            )
            self.window.setHidesOnDeactivate_(False)
            self.window.setOpaque_(True)
            self.window.setBackgroundColor_(NSColor.whiteColor())
            self.window.setSharingType_(NSWindowSharingNone)
            self.window.setReleasedWhenClosed_(False)

            content = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 560, 440))
            content.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
            self.window.setContentView_(content)

            # Toolbar
            x = 10
            y = 400
            specs = [
                ("打开…", "onOpen:"),
                ("←", "onPrev:"),
                ("→", "onNext:"),
                ("重载", "onReload:"),
                ("A-", "onFontDown:"),
                ("A+", "onFontUp:"),
                ("隐私", "onPrivacy:"),
                ("置顶", "onPin:"),
                ("关闭", "onQuit:"),
            ]
            for title, action in specs:
                btn = NSButton.alloc().initWithFrame_(NSMakeRect(x, y, 70, 28))
                btn.setTitle_(title)
                btn.setBezelStyle_(NSBezelStyleRounded)
                btn.setTarget_(self)
                btn.setAction_(action)
                btn.setAutoresizingMask_(NSViewMinYMargin)
                content.addSubview_(btn)
                x += 74

            self.status = NSTextField.alloc().initWithFrame_(NSMakeRect(12, 372, 536, 22))
            self.status.setStringValue_("未加载文稿 · ← → 翻页")
            self.status.setBezeled_(False)
            self.status.setDrawsBackground_(False)
            self.status.setEditable_(False)
            self.status.setSelectable_(False)
            self.status.setTextColor_(NSColor.darkGrayColor())
            self.status.setFont_(NSFont.systemFontOfSize_(12))
            self.status.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
            content.addSubview_(self.status)

            self.jump_label = NSTextField.alloc().initWithFrame_(NSMakeRect(12, 348, 40, 22))
            self.jump_label.setStringValue_("页码")
            self.jump_label.setBezeled_(False)
            self.jump_label.setDrawsBackground_(False)
            self.jump_label.setEditable_(False)
            self.jump_label.setTextColor_(NSColor.darkGrayColor())
            self.jump_label.setAutoresizingMask_(NSViewMinYMargin)
            content.addSubview_(self.jump_label)

            self.jump_field = NSTextField.alloc().initWithFrame_(NSMakeRect(52, 346, 70, 24))
            self.jump_field.setStringValue_("1")
            self.jump_field.setAutoresizingMask_(NSViewMinYMargin)
            content.addSubview_(self.jump_field)

            self.jump_btn = NSButton.alloc().initWithFrame_(NSMakeRect(128, 344, 70, 28))
            self.jump_btn.setTitle_("跳转")
            self.jump_btn.setBezelStyle_(NSBezelStyleRounded)
            self.jump_btn.setTarget_(self)
            self.jump_btn.setAction_("onJump:")
            self.jump_btn.setAutoresizingMask_(NSViewMinYMargin)
            content.addSubview_(self.jump_btn)

            # Shrink notes area to leave room for jump row

            self.notes_scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(12, 12, 536, 320))
            self.notes_scroll.setHasVerticalScroller_(True)
            self.notes_scroll.setBorderType_(1)
            self.notes_scroll.setDrawsBackground_(True)
            self.notes_scroll.setBackgroundColor_(NSColor.whiteColor())
            self.notes_scroll.setAutoresizingMask_(
                NSViewWidthSizable | NSViewHeightSizable
            )

            self.notes_view = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, 520, 350))
            self.notes_view.setEditable_(False)
            self.notes_view.setRichText_(False)
            self.notes_view.setDrawsBackground_(True)
            self.notes_view.setBackgroundColor_(NSColor.whiteColor())
            self.notes_view.setTextColor_(NSColor.blackColor())
            self.notes_view.setFont_(NSFont.systemFontOfSize_(18))
            self.notes_view.setString_("（打开 .pptx 以显示备注）")
            self.notes_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
            self.notes_scroll.setDocumentView_(self.notes_view)
            content.addSubview_(self.notes_scroll)

            # Keys: local only when overlay focused (and not editing jump field).
            # Global only when frontmost app is WPS / PowerPoint — never while typing elsewhere.
            self._nav_lock = False
            self._closed = False
            self._reassert_enabled = True
            self.window.setDelegate_(self)

            def _editing_jump():
                fr = self.window.firstResponder()
                if fr is None:
                    return False
                if fr == self.jump_field:
                    return True
                try:
                    # Field editor while typing in jump_field
                    if hasattr(fr, "delegate") and fr.delegate() == self.jump_field:
                        return True
                except Exception:
                    pass
                return False

            def _should_next(event):
                if event.isARepeat():
                    return False
                keycode = int(event.keyCode())
                chars = event.charactersIgnoringModifiers() or ""
                return keycode in (124, 49, 121) or chars in (" ",)

            def _should_prev(event):
                if event.isARepeat():
                    return False
                keycode = int(event.keyCode())
                return keycode in (123, 116)

            def _safe_next():
                if self._nav_lock or self._closed:
                    return
                self._nav_lock = True
                try:
                    self.owner._on_next()
                finally:
                    self._nav_lock = False

            def _safe_prev():
                if self._nav_lock or self._closed:
                    return
                self._nav_lock = True
                try:
                    self.owner._on_prev()
                finally:
                    self._nav_lock = False

            def _front_is_presenter():
                try:
                    app = NSWorkspace.sharedWorkspace().frontmostApplication()
                    if app is None:
                        return False
                    name = (app.localizedName() or "").lower()
                    bid = (app.bundleIdentifier() or "").lower()
                    blob = name + " " + bid
                    needles = (
                        "wps",
                        "wpsoffice",
                        "kingsoft",
                        "powerpoint",
                        "microsoft powerpoint",
                        "com.microsoft.powerpoint",
                        "com.kingsoft",
                    )
                    return any(n in blob for n in needles)
                except Exception:
                    return False

            def local_handler(event):
                if _editing_jump():
                    return event
                if _should_next(event):
                    _safe_next()
                    return None  # consume so it does not bounce
                if _should_prev(event):
                    _safe_prev()
                    return None
                return event

            def global_handler(event):
                # Only while WPS / PowerPoint is frontmost — not Feishu chat, Notes, etc.
                if not _front_is_presenter():
                    return
                if _should_next(event):
                    _safe_next()
                elif _should_prev(event):
                    _safe_prev()

            self._local_monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
                NSKeyDownMask, local_handler
            )
            try:
                self._global_monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
                    NSKeyDownMask, global_handler
                )
            except Exception:
                self._global_monitor = None

            self.window.makeKeyAndOrderFront_(None)
            NSApp.activateIgnoringOtherApps_(True)
            self.performSelector_withObject_afterDelay_("reassertTop:", None, 1.5)

        def setStatus_(self, text):
            self.status.setStringValue_(str(text))

        def setIndex_(self, index):
            try:
                self.jump_field.setStringValue_(str(int(index)))
            except Exception:
                pass

        def setNotes_(self, text):
            self.notes_view.setTextColor_(NSColor.blackColor())
            self.notes_view.setBackgroundColor_(NSColor.whiteColor())
            self.notes_view.setString_(str(text))
            self.notes_view.scrollRangeToVisible_((0, 0))

        def setFontSize_(self, size):
            self.notes_view.setFont_(NSFont.systemFontOfSize_(float(size)))

        def scheduleCallback_after_(self, cb, delay):
            # Use NSObject performSelector after delay via objc
            self._cb = cb
            self.performSelector_withObject_afterDelay_("firePending:", None, float(delay))

        def firePending_(self, _):
            cb = getattr(self, "_cb", None)
            if cb:
                cb()

        def onOpen_(self, sender):
            self.owner._pick_file()

        def onPrev_(self, sender):
            self.owner._on_prev()

        def onNext_(self, sender):
            self.owner._on_next()

        def onReload_(self, sender):
            self.owner._on_reload()

        def onFontDown_(self, sender):
            self.owner._on_font(-2)

        def onFontUp_(self, sender):
            self.owner._on_font(+2)

        def onPrivacy_(self, sender):
            self.owner._on_privacy()

        def onJump_(self, sender):
            self.owner.goto_page(self.jump_field.stringValue())

        def onQuit_(self, sender):
            self._teardown()
            NSApp.terminate_(None)

        def onPin_(self, sender):
            if self._closed:
                return
            self._reassert_enabled = True
            self.reassertTop_(sender)

        def reassertTop_(self, _sender=None):
            if self._closed or not self._reassert_enabled:
                return
            try:
                if not self.window.isVisible():
                    return
                self.window.setLevel_(2147483628)
                self.window.orderFrontRegardless()
            except Exception:
                return
            # Do not steal key focus every tick — only raise level
            self.performSelector_withObject_afterDelay_("reassertTop:", None, 0.6)

        def _teardown(self):
            self._closed = True
            self._reassert_enabled = False
            try:
                NSObject.cancelPreviousPerformRequestsWithTarget_(self)
            except Exception:
                pass
            for attr in ("_local_monitor", "_global_monitor"):
                mon = getattr(self, attr, None)
                if mon is not None:
                    try:
                        NSEvent.removeMonitor_(mon)
                    except Exception:
                        pass
                    setattr(self, attr, None)

        def windowShouldClose_(self, sender):
            self._teardown()
            NSApp.terminate_(None)
            return True

        def windowWillClose_(self, notification):
            self._teardown()

else:

    class NotesOverlayAppKit:  # type: ignore
        def __init__(self, **kwargs):
            raise RuntimeError("PyObjC / AppKit 不可用")
