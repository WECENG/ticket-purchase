# setup_mobile.ps1 - Windows 移动端环境安装脚本
# 以管理员身份运行此脚本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  大麦抢票 - 移动端环境安装向导" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查 Node.js
Write-Host "[1/5] 检查 Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = (node --version) -replace 'v', ''
    Write-Host "  ✅ Node.js $nodeVersion 已安装" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Node.js 未安装" -ForegroundColor Red
    Write-Host "  请从 https://nodejs.org/ 下载安装 Node.js 20.19+ LTS 版本"
    Write-Host "  安装完成后重新运行此脚本"
    exit 1
}

# 2. 安装 Appium
Write-Host "`n[2/5] 安装 Appium..." -ForegroundColor Yellow
try {
    appium --version 2>$null
    Write-Host "  ✅ Appium 已安装" -ForegroundColor Green
} catch {
    Write-Host "  正在安装 Appium..." -ForegroundColor Yellow
    npm install -g appium
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Appium 安装成功" -ForegroundColor Green
    }
}

# 3. 安装 UIAutomator2 驱动
Write-Host "`n[3/5] 安装 UIAutomator2 驱动..." -ForegroundColor Yellow
$drivers = appium driver list --installed 2>$null
if ($drivers -match "uiautomator2") {
    Write-Host "  ✅ UIAutomator2 驱动已安装" -ForegroundColor Green
} else {
    appium driver install uiautomator2
    Write-Host "  ✅ UIAutomator2 驱动安装完成" -ForegroundColor Green
}

# 4. 检查 Android SDK
Write-Host "`n[4/5] 检查 Android SDK..." -ForegroundColor Yellow
$androidHome = $env:ANDROID_HOME
if (-not $androidHome) {
    $androidHome = "$env:LOCALAPPDATA\Android\Sdk"
}
$adbPath = "$androidHome\platform-tools\adb.exe"
if (Test-Path $adbPath) {
    Write-Host "  ✅ Android SDK 已配置: $androidHome" -ForegroundColor Green
} else {
    Write-Host "  ⚠️ Android SDK 未找到" -ForegroundColor Yellow
    Write-Host "  请安装 Android Studio: https://developer.android.com/studio"
    Write-Host "  或单独安装 Android SDK Platform-Tools"
    Write-Host "  默认安装路径: $androidHome"
}

# 5. 检查 Android 设备
Write-Host "`n[5/5] 检查 Android 设备..." -ForegroundColor Yellow
try {
    $devices = adb devices 2>$null | Select-String "device$"
    if ($devices) {
        Write-Host "  ✅ 检测到设备:" -ForegroundColor Green
        Write-Host "  $devices"
    } else {
        Write-Host "  ⚠️ 未检测到设备" -ForegroundColor Yellow
        Write-Host "  请确保："
        Write-Host "  1. Android 真机已通过 USB 连接"
        Write-Host "  2. 手机已开启「开发者选项」和「USB 调试」"
        Write-Host "  3. 手机上已安装大麦APP (cn.damai)"
    }
} catch {
    Write-Host "  ⚠️ adb 命令不可用" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  移动端环境安装完成！" -ForegroundColor Green
Write-Host "  运行抢票: .\start_ticket_grabbing.ps1" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
