# 技术架构与实现说明（WPS / PowerPoint Mac 悬浮备注）

## 1. 为什么做这个工具？

在单屏笔记本上用飞书会议、腾讯会议或会议室投屏码演示 PPT 时，经常遇到两个痛点：
1. 开启 WPS / PowerPoint 自带的「演讲者视图」会占用双屏或把备注直接暴露在共享画面里；
2. 普通笔记窗口一旦点击幻灯片播放就会被挡在后面，或者切到聊天窗口打字时误触翻页。

本工具使用 macOS 原生 `AppKit`（`NSPanel`）实现了一个**防截屏隐身、高优先级置顶、智能按键同步**的演讲者备注悬浮窗。

## 2. 核心设计对比

| 能力项 | 实现方案 | 说明 |
|------|------|------|
| **备注解析** | 轻量级 OOXML (`zipfile` + `ElementTree`) | 只读取 `ppt/presentation.xml` 与 `ppt/notesSlides/*.xml`，不解压图片/视频流，200MB+ 大型 `.pptx` 也可在 ~1 秒内完成加载，内存占用仅数 MB。 |
| **投屏隐身** | `NSWindowSharingNone` (`window.setSharingType_`) | 将悬浮窗标记为不可被屏幕录制/共享捕获。在飞书会议、腾讯会议及无线投屏中，观众看不到悬浮窗，仅演讲者本机可见。 |
| **防遮挡置顶** | `NSPanel` + 高窗口层级 + 定时保活 | 使用 `NSWindowStyleMaskUtilityWindow | NSWindowStyleMaskNonactivatingPanel` 配合高窗口层级与非抢焦点 `orderFrontRegardless`，确保幻灯片播放时不被压在底层。 |
| **智能翻页监听** | 本地监听 + 宿主前台限定全局监听 | 当焦点在悬浮窗本身，或当前前台应用是 **WPS / PowerPoint** 时，`Space` / `←` / `→` / `PageUp` / `PageDown` 同步翻页；当切到飞书、微信、浏览器打字时，绝不误触翻页。 |
| **PowerPoint 自动跟页** | AppleScript 后台轮询 | 若使用 Microsoft PowerPoint for Mac，后台线程每秒读取当前放映/编辑页码，即便在缩略图随机跳页也能自动同步。 |
| **WPS 跳页支持** | 工具栏「页码 + 跳转」 | WPS Mac 无公开 AppleScript 页码接口；顺序翻页通过快捷键自动同步，随机跳页可在悬浮窗输入页码一键跳转。 |

## 3. 大体积演示文稿性能基准

测试样本：约 200MB+、包含 39 页高清图表与多媒体的 `.pptx` 演示文稿：

| 指标 | 结果 |
|----|------|
| 总页数 | 39 页（严格遵循 `presentation.xml` 中 `sldId` 顺序） |
| 解析方式 | `load_deck_light`（仅读取 slide rels + notesSlide XML） |
| 解析耗时 | ~1.0 秒 |
| 峰值内存分配 | ~3 MB（`tracemalloc`） |
