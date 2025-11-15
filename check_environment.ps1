# 大麦抢票 - 环境检查脚本 (Windows PowerShell)
# 用法: .\check_environment.ps1

$ErrorActionPreference = 'Stop'

Write-Host "🔍 检查大麦抢票环境..."
Write-Host "================================"

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

# 检查 Python
Write-Host "🐍 检查Python环境..."
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
$pyCmd = Get-Command py -ErrorAction SilentlyContinue
if ($pythonCmd) {
  $pythonVersion = (& $pythonCmd.Source --version) 2>&1
  Write-Host "✅ Python: $pythonVersion"
} elseif ($pyCmd) {
  $pythonVersion = (& $pyCmd.Source -V) 2>&1
  Write-Host "✅ Python: $pythonVersion"
} else {
  Write-Host "❌ 未检测到Python，请安装 Python 3.9+"
  exit 1
}

# 检查 Node.js
Write-Host ""
Write-Host "📦 检查Node.js环境..."
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($nodeCmd) {
  $nodeVerRaw = (& $nodeCmd.Source --version)
  Write-Host "✅ Node.js: $nodeVerRaw"
  $nodeVer = $nodeVerRaw -replace '^v',''
  try {
    $nodeMajor = [int]($nodeVer.Split('.')[0])
    if ($nodeMajor -ge 20) {
      Write-Host "✅ Node.js版本兼容"
    } else {
      Write-Host "⚠️  Node.js版本可能不兼容，建议升级到 20.19.0+"
    }
  } catch {
    Write-Host "⚠️  无法解析 Node.js 主版本号"
  }
} else {
  Write-Host "❌ Node.js未安装"
  exit 1
}

# 检查 Appium
Write-Host ""
Write-Host "🤖 检查Appium..."
$appiumCmd = Get-Command appium -ErrorAction SilentlyContinue
if ($appiumCmd) {
  $appiumVer = (& $appiumCmd.Source --version)
  Write-Host "✅ Appium: $appiumVer"
} else {
  Write-Host "❌ Appium未安装"
  Write-Host "   安装命令: npm install -g appium"
  exit 1
}

# 检查 Android SDK
Write-Host ""
Write-Host "📱 检查Android SDK..."
$sdkPath = Resolve-AndroidSdkPath
if ($null -ne $sdkPath -and (Test-Path $sdkPath)) {
  Write-Host "✅ Android SDK路径存在: $sdkPath"
  $env:ANDROID_HOME = $sdkPath
  $env:ANDROID_SDK_ROOT = $sdkPath
} else {
  Write-Host "❌ Android SDK路径不存在"
  Write-Host "   请安装 Android Studio 并确保 SDK 已安装"
  Write-Host "   常见路径: $env:LOCALAPPDATA\Android\Sdk"
  exit 1
}

# 检查 ADB
Write-Host ""
Write-Host "🔧 检查ADB..."
$adbCmd = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adbCmd) {
  $adbCandidate = Join-Path $sdkPath 'platform-tools\adb.exe'
  if (Test-Path $adbCandidate) { $adbCmdPath = $adbCandidate } else { $adbCmdPath = $null }
} else {
  $adbCmdPath = $adbCmd.Source
}
if ($adbCmdPath) {
  Write-Host "✅ ADB路径: $adbCmdPath"
} else {
  Write-Host "❌ 未找到ADB (platform-tools)"
  Write-Host "   请通过 Android Studio 的 SDK Manager 安装 platform-tools"
  exit 1
}

# 检查 Android 设备
Write-Host ""
Write-Host "📱 检查Android设备..."
$adbOutput = & $adbCmdPath devices 2>$null
$deviceCount = ($adbOutput | Select-String '^[^\s]+\s+device$').Count
if ($deviceCount -eq 0) {
  Write-Host "⚠️  未检测到Android设备"
  Write-Host "   请启动模拟器或连接真机"
  $emuExe = Join-Path $sdkPath 'emulator\emulator.exe'
  if (Test-Path $emuExe) { Write-Host "   启动模拟器示例: `"$emuExe`" -avd <你的AVD名称>" }
} else {
  Write-Host "✅ 检测到 $deviceCount 个Android设备"
  $pkgInstalled = (& $adbCmdPath shell pm list packages | Select-String -Quiet 'cn\.damai')
  if ($pkgInstalled) {
    Write-Host "✅ 大麦APP已安装"
  } else {
    Write-Host "⚠️  大麦APP未安装，请在设备上安装"
  }
}

# 检查 Appium 服务器
Write-Host ""
Write-Host "🌐 检查Appium服务器..."
$serverRunning = $false
try {
  $null = Invoke-RestMethod -Uri 'http://127.0.0.1:4723/status' -TimeoutSec 2
  $serverRunning = $true
} catch { $serverRunning = $false }
if ($serverRunning) {
  Write-Host "✅ Appium服务器正在运行"
} else {
  Write-Host "⚠️  Appium服务器未运行"
  Write-Host "   启动命令: .\start_appium.ps1"
}

# 检查配置文件
Write-Host ""
Write-Host "📋 检查配置文件..."
$configPath = Join-Path $PSScriptRoot 'damai_appium\config.jsonc'
if (Test-Path $configPath) {
  Write-Host "✅ 配置文件存在"
  Write-Host "   当前配置(部分):"
  (Get-Content $configPath | Select-String '"keyword"|"city"|"users"' | Select-Object -First 3) |
    ForEach-Object { Write-Host ("   " + $_.Line) }
} else {
  Write-Host "❌ 配置文件不存在"
  Write-Host "   请创建 damai_appium\\config.jsonc 文件"
}

Write-Host ""
Write-Host "================================"
Write-Host "🎯 环境检查完成！"
Write-Host ""
Write-Host "📝 使用说明:"
Write-Host "   1. 启动Appium: .\\start_appium.ps1"
Write-Host "   2. 开始抢票: .\\start_ticket_grabbing.ps1"
