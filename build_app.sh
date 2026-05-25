#!/bin/bash
set -e
cd "$(dirname "$0")"

echo ">>> 检查环境..."
if [ ! -d "venv" ]; then
    echo "请先运行 ./start.sh 初始化环境"
    exit 1
fi

source venv/bin/activate

echo ">>> 开始构建 .app..."
pyinstaller \
    --name "音频转文字" \
    --windowed \
    --noconfirm \
    --clean \
    --add-data "cleaner:cleaner" \
    --add-data "engine:engine" \
    --add-data "gui:gui" \
    --add-data "output:output" \
    --add-data "config.py:." \
    --hidden-import PyQt6 \
    --hidden-import openai \
    main.py

echo ">>> 构建完成!"
echo ">>> App 位置: dist/音频转文字.app"
echo ">>> 已复制到桌面: ~/Desktop/音频转文字.app"

cp -R dist/音频转文字.app ~/Desktop/音频转文字.app
