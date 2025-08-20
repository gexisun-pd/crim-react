#!/bin/bash

# 获取本机IP地址的通用脚本
get_local_ip() {
    # 尝试多种方法获取本机IP
    local ip=""
    
    # 方法1: 使用hostname命令
    if command -v hostname &> /dev/null; then
        ip=$(hostname -I | awk '{print $1}')
    fi
    
    # 方法2: 使用ip命令 (Linux)
    if [[ -z "$ip" ]] && command -v ip &> /dev/null; then
        ip=$(ip route get 1 | awk '{print $NF;exit}')
    fi
    
    # 方法3: 使用ifconfig命令
    if [[ -z "$ip" ]] && command -v ifconfig &> /dev/null; then
        ip=$(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | head -n1)
    fi
    
    echo "$ip"
}

# 设置环境变量
LOCAL_IP=$(get_local_ip)

echo "======================================"
echo "🚀 启动CRIM React应用开发环境"
echo "======================================"
echo "本地IP地址: $LOCAL_IP"
echo ""
echo "访问地址:"
echo "  - 本地访问: http://localhost:9173"
echo "  - 局域网访问: http://$LOCAL_IP:9173"
echo ""
echo "API服务器:"
echo "  - 本地访问: http://localhost:9000"
echo "  - 局域网访问: http://$LOCAL_IP:9000"
echo "======================================"

# 导出环境变量
export REACT_APP_API_BASE_URL="http://$LOCAL_IP:9000"

# 启动Flask API服务器
echo "🔧 启动API服务器..."
cd "$(dirname "$0")" || exit 1
python3 api/app.py &
API_PID=$!

# 等待API服务器启动
sleep 3

# 启动React开发服务器
echo "⚛️ 启动React开发服务器..."
cd react-pieces-app || exit 1
HOST=0.0.0.0 PORT=9173 npm run dev &
REACT_PID=$!

# 创建清理函数
cleanup() {
    echo ""
    echo "🛑 停止服务器..."
    kill $API_PID 2>/dev/null
    kill $REACT_PID 2>/dev/null
    exit 0
}

# 设置信号处理
trap cleanup SIGINT SIGTERM

echo ""
echo "✅ 服务器已启动!"
echo "按 Ctrl+C 停止服务器"
echo ""

# 等待进程结束
wait $REACT_PID
wait $API_PID
