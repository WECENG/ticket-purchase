$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
function Resolve-AdbPath {
    param([string]$Root)

    $candidates = @((Join-Path $Root "platform-tools\adb.exe"))
    foreach ($sdkRoot in @($env:ANDROID_SDK_ROOT, $env:ANDROID_HOME)) {
        if ($sdkRoot) {
            $candidates += Join-Path $sdkRoot "platform-tools\adb.exe"
        }
    }
    $pathAdb = Get-Command adb.exe -ErrorAction SilentlyContinue
    if ($pathAdb) {
        $candidates += $pathAdb.Source
    }
    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw "adb.exe not found. Install Android platform-tools or place it in .\platform-tools."
}

$adbPath = Resolve-AdbPath -Root $projectRoot
$platformTools = Split-Path -Parent $adbPath
$sdkRoot = Split-Path -Parent $platformTools
if (-not $env:ANDROID_HOME) { $env:ANDROID_HOME = $sdkRoot }
if (-not $env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT = $sdkRoot }
$pathEntries = $env:Path -split ";"
if ($platformTools -notin $pathEntries) {
    $env:Path = "$platformTools;$env:Path"
}

$appium = Get-Command appium.cmd -ErrorAction SilentlyContinue
if (-not $appium) {
    $appium = Get-Command appium -ErrorAction Stop
}

$authorizedDevices = @(
    & $adbPath devices |
        Select-String -Pattern '^\S+\s+device$'
)
if ($authorizedDevices.Count -eq 0) {
    throw "No authorized Android device found. Connect the phone and allow USB debugging."
}

Write-Host "Android device detected. Starting Appium at http://127.0.0.1:4723"
Write-Host "ADB: $adbPath"
Write-Host "Keep this window open. Press Ctrl+C to stop the server."
& $appium.Source --address 127.0.0.1 --port 4723
