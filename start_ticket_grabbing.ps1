$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$configPath = Join-Path $projectRoot "damai_appium\config.jsonc"
$venvPython = Join-Path $projectRoot "venv\Scripts\python.exe"
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

if (-not (Test-Path -LiteralPath $configPath)) {
    throw "Config file not found: $configPath"
}

if (-not $env:ANDROID_HOME) { $env:ANDROID_HOME = $sdkRoot }
if (-not $env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT = $sdkRoot }
$pathEntries = $env:Path -split ";"
if ($platformTools -notin $pathEntries) {
    $env:Path = "$platformTools;$env:Path"
}

$authorizedDevices = @(
    & $adbPath devices |
        Select-String -Pattern '^\S+\s+device$'
)
if ($authorizedDevices.Count -eq 0) {
    throw "No authorized Android device found via $adbPath"
}
try {
    $null = Invoke-RestMethod -Uri "http://127.0.0.1:4723/status" -TimeoutSec 3
} catch {
    throw "Appium is not running. Run .\start_appium.ps1 in another PowerShell window first."
}

$config = Get-Content -Raw -Encoding UTF8 -LiteralPath $configPath | ConvertFrom-Json
Write-Host "Target: $($config.target_title) / $($config.city) / $($config.date) / $($config.price)"
Write-Host "Scheduled start: $($config.start_at)"
Write-Host "Submit real order: $($config.if_commit_order)"
Write-Host "ADB: $adbPath"

if ($config.if_commit_order) {
    $choices = [System.Management.Automation.Host.ChoiceDescription[]] @(
        (New-Object System.Management.Automation.Host.ChoiceDescription '&Yes', 'Continue and allow a real order to be submitted.'),
        (New-Object System.Management.Automation.Host.ChoiceDescription '&No', 'Cancel without submitting an order.')
    )
    $confirmation = $Host.UI.PromptForChoice(
        'Confirm real order',
        'This run can submit a real order and open the payment page. Continue?',
        $choices,
        1
    )
    if ($confirmation -ne 0) {
        throw "Cancelled"
    }
}

if (Test-Path -LiteralPath $venvPython) {
    $python = $venvPython
} else {
    $python = (Get-Command python -ErrorAction Stop).Source
}

Push-Location (Join-Path $projectRoot "damai_appium")
try {
    & $python -B "damai_app_v2.py"
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
