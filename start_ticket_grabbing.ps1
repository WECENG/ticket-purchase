# 大麦抢票 - 抢票启动脚本 (Windows PowerShell)
# 用法: .\start_ticket_grabbing.ps1

$ErrorActionPreference = 'Stop'

Write-Host "🎫 启动大麦抢票脚本..."

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

# 设置 Android 环境变量（便于 adb 查找）
$sdkPath = Resolve-AndroidSdkPath
if ($sdkPath) {
  $env:ANDROID_HOME = $sdkPath
  $env:ANDROID_SDK_ROOT = $sdkPath
}

# 检查 Appium 服务器是否运行
$serverRunning = $false
try {
  $null = Invoke-RestMethod -Uri 'http://127.0.0.1:4723/status' -TimeoutSec 2
  $serverRunning = $true
} catch { $serverRunning = $false }
if (-not $serverRunning) {
  Write-Host "❌ Appium服务器未运行"
  Write-Host "   请先运行: .\start_appium.ps1"
  exit 1
}
Write-Host "✅ Appium服务器运行正常"

# 检查配置文件
$configPath = Join-Path $PSScriptRoot 'damai_appium\config.jsonc'
if (-not (Test-Path $configPath)) {
  Write-Host "❌ 配置文件不存在: damai_appium\\config.jsonc"
  exit 1
}
Write-Host "✅ 配置文件存在"

# 显示当前配置（部分）
Write-Host "📋 当前配置(部分):"
(Get-Content $configPath | Select-String '"keyword"|"city"|"users"' | Select-Object -First 3) |
  ForEach-Object { Write-Host ("   " + $_.Line) }

# 确认是否继续
$reply = Read-Host "🤔 确认开始抢票？(y/N)"
if ($reply -notmatch '^[Yy]$') {
  Write-Host "❌ 已取消"
  exit 1
}

# 进入脚本目录
Set-Location (Join-Path $PSScriptRoot 'damai_appium')

Write-Host "🚀 开始抢票..."
Write-Host "   请确保："
Write-Host "   1. 大麦APP已打开"
Write-Host "   2. 已搜索到目标演出"
Write-Host "   3. 已进入演出详情页面"
Write-Host ""

# 运行抢票脚本
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
$pyCmd = Get-Command py -ErrorAction SilentlyContinue
if ($pythonCmd) {
  & $pythonCmd.Source 'damai_app_v2.py'
} elseif ($pyCmd) {
  & $pyCmd.Source '-3' 'damai_app_v2.py'
} else {
  Write-Host "❌ 未检测到Python，请安装 Python 3.10+"
  exit 1
}
