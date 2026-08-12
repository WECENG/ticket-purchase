#!/bin/bash
# 大麦抢票 - 抢票启动脚本
# 使用方法: ./start_ticket_grabbing.sh

echo "🎫 启动大麦抢票脚本..."

# 可通过环境变量覆盖 Python；默认优先使用 python3。
PYTHON_BIN="${PYTHON_BIN:-python3}"

# 检查Appium服务器是否运行
if ! curl -s http://127.0.0.1:4723/status > /dev/null; then
    echo "❌ Appium服务器未运行"
    echo "   请先运行: ./start_appium.sh"
    exit 1
fi

echo "✅ Appium服务器运行正常"

# 检查配置文件
if [ ! -f "damai_appium/config.jsonc" ]; then
    echo "❌ 配置文件不存在: damai_appium/config.jsonc"
    exit 1
fi

echo "✅ 配置文件存在"

# 显示当前配置
echo "📋 当前配置:"
echo "   $(cat damai_appium/config.jsonc | grep -E '"keyword"|"city"|"users"' | head -3)"

# 确认是否继续
read -p "🤔 确认开始抢票？(y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 已取消"
    exit 1
fi

# 进入脚本目录
cd damai_appium

echo "🚀 开始抢票..."
echo "   请确保："
echo "   1. 大麦APP已打开"
echo "   2. 已搜索到目标演出"
echo "   3. 已进入演出详情页面"
echo ""

# 运行抢票脚本
"$PYTHON_BIN" damai_app_v2.py
