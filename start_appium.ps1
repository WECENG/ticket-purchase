# start_appium.ps1 - Windows PowerShell 版本
# 大麦抢票 - Appium 启动脚本
# 使用方法: .\start_appium.ps1

Write-Host "🚀 启动大麦抢票环境..." -ForegroundColor Cyan

# 设置 Android 环境变量（请根据实际安装路径修改）
$androidSdk = $env:ANDROID_HOME
if (-not $androidSdk) {
    # 默认 Windows 路径
    $androidSdk = "$env:LOCALAPPDATA\Android\Sdk"
}
$env:ANDROID_HOME = $androidSdk
$env:ANDROID_SDK_ROOT = $androidSdk

Write-Host "✅ 环境变量已设置" -ForegroundColor Green
Write-Host "   ANDROID_HOME: $env:ANDROID_HOME"
Write-Host "   ANDROID_SDK_ROOT: $env:ANDROID_SDK_ROOT"

# 检查 Node.js
try {
    $nodeVersion = (node --version) -replace 'v', ''
    Write-Host "📦 Node.js版本: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js 未安装，请先安装 Node.js 20.19+" -ForegroundColor Red
    Write-Host "   下载: https://nodejs.org/"
    exit 1
}

# 检查 Appium
try {
    $appiumVersion = appium --version
    Write-Host "✅ Appium版本: $appiumVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Appium 未安装，正在安装..." -ForegroundColor Yellow
    npm install -g appium
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Appium 安装失败" -ForegroundColor Red
        exit 1
    }
}

# 检查 UIAutomator2 驱动
$drivers = appium driver list --installed 2>$null
if ($drivers -notmatch "uiautomator2") {
    Write-Host "⚠️ UIAutomator2 驱动未安装，正在安装..." -ForegroundColor Yellow
    appium driver install uiautomator2
}

# 检查 Android 设备
Write-Host "📱 检查Android设备..." -ForegroundColor Cyan
try {
    $devices = adb devices | Select-String "device$"
    if ($devices.Count -eq 0) {
        Write-Host "⚠️ 未检测到Android设备" -ForegroundColor Yellow
        Write-Host "   请连接 Android 真机或启动模拟器"
        Write-Host "   确保已开启 USB 调试模式"
    } else {
        Write-Host "✅ 检测到 Android 设备" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️ adb 命令不可用，请确认 Android SDK platform-tools 已安装" -ForegroundColor Yellow
    Write-Host "   路径: $androidSdk\platform-tools"
}

# 检查大麦APP
try {
    $packages = adb shell pm list packages 2>$null
    if ($packages -match "cn.damai") {
        Write-Host "✅ 大麦APP已安装" -ForegroundColor Green
    } else {
        Write-Host "⚠️ 大麦APP未安装，请在设备上安装大麦APP" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️ 无法检查大麦APP安装状态" -ForegroundColor Yellow
}

# 启动 Appium 服务器
Write-Host "`n🚀 启动Appium服务器..." -ForegroundColor Cyan
Write-Host "   服务器地址: http://127.0.0.1:4723" -ForegroundColor White
Write-Host "   按 Ctrl+C 停止服务器" -ForegroundColor White
Write-Host ""

appium --port 4723 --allow-cors
