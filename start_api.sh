#!/bin/bash
# API 伺服器啟動腳本

echo "🔧 Clang-Tidy API Server Setup"
echo "================================"

# 檢查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

# 檢查模組
if [ ! -f "build/libMiscTidyModule.so" ]; then
    echo "❌ libMiscTidyModule.so not found"
    echo "Please build the module first:"
    echo "  mkdir -p build && cd build"
    echo "  cmake .. && cmake --build . --config Release"
    exit 1
fi

# 安裝依賴
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# 啟動伺服器
echo ""
echo "🚀 Starting API server (uvicorn)..."
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
echo "API server started."
