"""Screen-share privacy strategy for the floating notes window.

Summary (macOS, verified with Feishu Meeting & Tencent Meeting):

1. **NSWindow.sharingType = .none (NSWindowSharingNone)** + high-level NSPanel:
   - Excludes the floating window from standard window/screen capture streams
     in Feishu Meeting (飞书会议), Tencent Meeting (腾讯会议), and wireless
     room screen casting (飞书会议室投屏码/会议ID), while remaining visible
     on the presenter's own laptop screen.

2. **Window-share / Windowed Slideshow**:
   - Most reliable defence-in-depth: share **only the WPS / PowerPoint window**
     rather than the entire desktop, and use **windowed slideshow (窗口放映)**
     if WPS exclusive full-screen covers floating panels.

3. **Second display / iPad Sidecar**:
   - Put the notes overlay on a non-shared secondary display when available.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrivacyMode:
    id: str
    title_zh: str
    is_safe: bool
    detail_zh: str


MODES = [
    PrivacyMode(
        id="window_share",
        title_zh="推荐组合：防截屏隐身 + 窗口共享 / 窗口放映",
        is_safe=True,
        detail_zh=(
            "本工具已默认开启 NSWindowSharingNone（在飞书会议、腾讯会议、会议室投屏码下对观众隐身），"
            "同时建议在会议软件中选择「只共享 WPS/PPT 窗口」或使用 WPS「窗口放映」以防全屏独占遮挡。"
        ),
    ),
    PrivacyMode(
        id="sharing_type_none",
        title_zh="内置保护：NSWindow.sharingType = none",
        is_safe=True,
        detail_zh=(
            "悬浮窗已设置为不可被共享捕获（NSWindowSharingNone），并采用高优先级非抢焦点 NSPanel 置顶。"
            "实测飞书会议、腾讯会议共享时参会者看不到本悬浮窗；如遇个别底层帧缓冲抓屏，请改用「只共享应用窗口」。"
        ),
    ),
    PrivacyMode(
        id="second_display",
        title_zh="备选方案：扩展副屏提词",
        is_safe=False,
        detail_zh=(
            "把悬浮窗拖到未投屏/未镜像的副屏；主屏给观众。"
            "若系统开启了「镜像显示器」，请依赖防截屏隐身或只投 WPS 窗口。"
        ),
    ),
]


GUIDANCE_ZH = """
## 飞书会议 / 腾讯会议 / 会议室投屏安全指南

1. **内置防截屏隐身**：本悬浮窗在 macOS 上默认设置 `NSWindowSharingNone`，飞书会议、腾讯会议共享屏幕时，观众看不到备注悬浮窗，只有你自己能看到。
2. **避免全屏遮挡**：如果点击 WPS「幻灯片放映」后独占全屏挡住了悬浮窗，请将 WPS 设为「窗口放映 / 浏览视图」，或在飞书中「只共享 WPS 窗口」。
3. **会议室投屏码 / 会议 ID 投屏**：同样支持隐身提词；为求稳妥，建议优先选择「窗口放映 + 只投 WPS 窗口」。
""".strip()
