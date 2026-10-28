#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
bash "$DIR/scripts/install_mac.sh"
echo
read -r -p "按回车键关闭窗口..." _ || true
