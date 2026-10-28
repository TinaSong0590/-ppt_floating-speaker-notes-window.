#!/usr/bin/env bash
# 一键安装 WPS 备注悬浮窗 (macOS) 并在桌面生成快捷应用
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "请在 macOS 上运行本脚本。当前系统: $(uname -s)"
  exit 1
fi

echo "==> [1/3] 创建 Python 虚拟环境 (.venv) ..."
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> [2/3] 安装依赖与 PyObjC (AppKit 悬浮窗支持) ..."
pip install -U pip
pip install -e ".[mac]"

BIN_PATH="$ROOT/.venv/bin/wps-notes-overlay"
DESKTOP_DIR="$HOME/Desktop"
APP_PATH="$DESKTOP_DIR/WPS备注悬浮窗.app"
CMD_PATH="$DESKTOP_DIR/打开WPS备注悬浮窗.command"

echo "==> [3/3] 在桌面生成「WPS备注悬浮窗.app」与「打开WPS备注悬浮窗.command」..."
if [[ -d "$DESKTOP_DIR" ]]; then
  TMP_SCPT="$(mktemp /tmp/wps_notes_overlay_XXXX.applescript)"
  cat > "$TMP_SCPT" <<EOF
property binPath : "$BIN_PATH"

on run
	my launchOverlay("")
end run

on open droppedItems
	repeat with f in droppedItems
		set p to POSIX path of f
		if p ends with ".pptx" or p ends with ".PPTX" or p ends with ".ppsx" or p ends with ".pptm" then
			my launchOverlay(p)
			return
		end if
	end repeat
	my launchOverlay("")
end open

on launchOverlay(pptxPath)
	try
		do shell script "pkill -f " & quoted form of binPath & " || true"
	end try
	delay 0.3
	if pptxPath is "" then
		do shell script quoted form of binPath & " >/tmp/wps-notes-overlay.log 2>&1 &"
	else
		do shell script quoted form of binPath & " " & quoted form of pptxPath & " >/tmp/wps-notes-overlay.log 2>&1 &"
	end if
end launchOverlay
EOF

  rm -rf "$APP_PATH"
  osacompile -o "$APP_PATH" "$TMP_SCPT"
  rm -f "$TMP_SCPT"

  cat > "$CMD_PATH" <<EOF
#!/bin/bash
pkill -f "$BIN_PATH" 2>/dev/null || true
sleep 0.3
if [ \$# -ge 1 ]; then
  exec "$BIN_PATH" "\$@"
else
  exec "$BIN_PATH"
fi
EOF
  chmod +x "$CMD_PATH"
fi

echo
echo "✅ 安装完成！"
echo "--------------------------------------------------------"
echo "启动方式 1（推荐）：双击桌面上的「WPS备注悬浮窗.app」"
echo "                   或直接把任意 .pptx 文件拖到「WPS备注悬浮窗.app」图标上打开"
echo "启动方式 2：双击桌面上的「打开WPS备注悬浮窗.command」"
echo "启动方式 3（命令行）："
echo "  $BIN_PATH /path/to/your-slides.pptx"
echo "--------------------------------------------------------"
