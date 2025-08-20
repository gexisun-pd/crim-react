#!/bin/bash

echo "🚀 启动 FastAPI 服务器..."
echo "📖 API 文档: http://localhost:9000/docs"  
echo "📚 ReDoc 文档: http://localhost:9000/redoc"
echo "🌐 局域网访问: http://10.113.82.229:9000"
echo ""

cd "$(dirname "$0")/.."
source .venv/bin/activate

# 使用 uvicorn 命令行启动（推荐方式）
uvicorn api.fastapi_app:app --host 0.0.0.0 --port 9000 --reload
