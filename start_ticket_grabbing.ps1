# start_ticket_grabbing.ps1 - Windows PowerShell 版本
# 大麦抢票 - 抢票启动脚本
# 使用方法: .\start_ticket_grabbing.ps1

Write-Host "🎫 启动大麦抢票脚本..." -ForegroundColor Cyan

# 设置 Android 环境变量
$androidSdk = $env:ANDROID_HOME
if (-not $androidSdk) {
    $androidSdk = "$env:LOCALAPPDATA\Android\Sdk"
}
$env:ANDROID_HOME = $androidSdk
$env:ANDROID_SDK_ROOT = $androidSdk

# 检查 Appium 服务器
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:4723/status" -UseBasicParsing -TimeoutSec 5
    Write-Host "✅ Appium服务器运行正常" -ForegroundColor Green
} catch {
    Write-Host "❌ Appium服务器未运行" -ForegroundColor Red
    Write-Host "   请先运行: .\start_appium.ps1"
    exit 1
}

# 检查配置文件
$configFile = "damai_appium\config.jsonc"
if (-not (Test-Path $configFile)) {
    Write-Host "❌ 配置文件不存在: $configFile" -ForegroundColor Red
    exit 1
}
Write-Host "✅ 配置文件存在" -ForegroundColor Green

# 显示当前配置（通过 Python 解析 JSONC）
Write-Host "`n📋 当前配置:" -ForegroundColor Cyan
try {
    $configJson = python -c @"
import sys; sys.path.insert(0,'damai_appium')
from config import Config; c=Config.load_config()
import json
print(json.dumps({'keyword':c.keyword,'city':c.city,'users':c.users,'date':c.date,'price':c.price,'if_commit_order':c.if_commit_order,'auto_buy_time':c.auto_buy_time,'device_name':c.device_name,'platform_version':c.platform_version}, ensure_ascii=False))
"@ 2>$null
    $config = $configJson | ConvertFrom-Json
    Write-Host "   关键词: $($config.keyword)"
    Write-Host "   城市: $($config.city)"
    Write-Host "   观众: $($config.users -join ', ')"
    Write-Host "   日期: $($config.date)"
    Write-Host "   价格: $($config.price)"
    Write-Host "   设备: $($config.device_name) (Android $($config.platform_version))"
    Write-Host "   提交订单: $($config.if_commit_order)"
    Write-Host "   定时抢票: $($config.auto_buy_time)"
} catch {
    Write-Host "   ⚠️ 无法解析配置文件: $_" -ForegroundColor Yellow
}

# 确认
Write-Host ""
$confirm = Read-Host "🤔 确认开始抢票？(y/N)"
if ($confirm -notmatch '^[Yy]') {
    Write-Host "❌ 已取消" -ForegroundColor Red
    exit 1
}

# 进入脚本目录
Push-Location "damai_appium"

Write-Host "`n🚀 开始抢票..." -ForegroundColor Cyan
Write-Host "   请确保："
Write-Host "   1. 大麦APP已打开"
Write-Host "   2. 已搜索到目标演出"
Write-Host "   3. 已进入演出详情页面"
Write-Host ""

# 运行抢票脚本
python damai_app_v2.py

Pop-Location
