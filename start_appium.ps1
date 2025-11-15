# 大麦抢票 - Appium 启动脚本 (Windows PowerShell)
# 用法: .\start_appium.ps1

$ErrorActionPreference = 'Stop'

Write-Host "🚀 启动大麦抢票环境..."

function Resolve-AndroidSdkPath {
  if ($env:ANDROID_HOME) { return $env:ANDROID_HOME }
  if ($env:ANDROID_SDK_ROOT) { return $env:ANDROID_SDK_ROOT }
  $candidates = @(
    (Join-Path $env:LOCALAPPDATA 'Android\Sdk'),
    (Join-Path $env:USERPROFILE 'AppData\Local\Android\Sdk')
  )
  foreach ($p in $candidates) { if (Test-Path $p) { return $p } }
  return $null
}

# 设置 Android 环境变量
$sdkPath = Resolve-AndroidSdkPath
if (-not $sdkPath) {
  Write-Host "❌ 未找到 Android SDK，请安装并配置 SDK"
  exit 1
}
$env:ANDROID_HOME = $sdkPath
$env:ANDROID_SDK_ROOT = $sdkPath
Write-Host "✅ 环境变量已设置"
Write-Host "   ANDROID_HOME: $env:ANDROID_HOME"
Write-Host "   ANDROID_SDK_ROOT: $env:ANDROID_SDK_ROOT"

# 检查 Node.js 版本
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($nodeCmd) {
  $nodeVer = (& $nodeCmd.Source --version)
  Write-Host "📦 Node.js版本: $nodeVer"
} else {
  Write-Host "❌ 未检测到 Node.js，请安装 Node.js 20+"
  exit 1
}

# 检查 Appium 是否安装
$appiumCmd = Get-Command appium -ErrorAction SilentlyContinue
if (-not $appiumCmd) {
  Write-Host "❌ Appium未安装，请先安装 Appium"
  Write-Host "   运行: npm install -g appium"
  exit 1
}

# 解析 ADB 路径
$adbCmd = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adbCmd) {
  $adbCandidate = Join-Path $sdkPath 'platform-tools\adb.exe'
  if (Test-Path $adbCandidate) { $adbCmdPath = $adbCandidate } else { $adbCmdPath = $null }
} else {
  $adbCmdPath = $adbCmd.Source
}
if (-not $adbCmdPath) {
  Write-Host "❌ 未找到ADB (platform-tools)"
  Write-Host "   请通过 Android Studio 的 SDK Manager 安装 platform-tools"
  exit 1
}

# 检查 Android 设备
Write-Host "📱 检查Android设备..."
$adbOutput = & $adbCmdPath devices 2>$null
$deviceCount = ($adbOutput | Select-String '^[^\s]+\s+device$').Count
if ($deviceCount -eq 0) {
  Write-Host "⚠️  未检测到Android设备"
  Write-Host "   请启动模拟器或连接真机"
  $emuExe = Join-Path $sdkPath 'emulator\emulator.exe'
  if (Test-Path $emuExe) { Write-Host "   启动模拟器示例: `"$emuExe`" -avd <你的AVD名称>" }
  exit 1
} else {
  Write-Host "✅ 检测到 $deviceCount 个Android设备"
}

# 检查大麦APP是否安装
$pkgInstalled = (& $adbCmdPath shell pm list packages | Select-String -Quiet 'cn\.damai')
if (-not $pkgInstalled) {
  Write-Host "⚠️  大麦APP未安装，请在设备上安装后再继续"
  exit 1
} else {
  Write-Host "✅ 大麦APP已安装"
}

# 启动 Appium 服务器（前台运行，Ctrl+C 停止）
Write-Host "🚀 启动Appium服务器..."
Write-Host "   服务器地址: http://127.0.0.1:4723"
Write-Host "   按 Ctrl+C 停止服务器"
Write-Host ""

& $appiumCmd.Source --port 4723
