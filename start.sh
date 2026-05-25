#!/bin/bash
set -e
cd "$(dirname "$0")"

# 优先使用 Homebrew 安装的 Python（Apple Silicon 原生支持）
if [ -x "/opt/homebrew/bin/python3.12" ]; then
    PYTHON="/opt/homebrew/bin/python3.12"
elif [ -x "/opt/homebrew/bin/python3" ]; then
    PYTHON="/opt/homebrew/bin/python3"
else
    PYTHON="python3"
fi

echo ">>> 使用 Python: $($PYTHON --version)"

if [ ! -d "venv" ]; then
    echo ">>> 正在创建虚拟环境..."
    $PYTHON -m venv venv
    source venv/bin/activate
    echo ">>> 正在安装依赖（首次需下载约 2-3GB，请耐心等待）..."
    pip install -r requirements.txt
    echo ">>> 环境初始化完成"
else
    source venv/bin/activate
fi

python main.py
