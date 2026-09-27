<#
.SYNOPSIS
    Starts NInfer High-Performance Server with Swift-Qwen3.8-27B on Windows (RTX 5090).

.DESCRIPTION
    Launches ninfer-serve on Windows with 0.0.0.0 host binding for LAN visibility,
    FP8 KV caching, speculative decoding (MTP/DFlash2), official Swift sampling parameters,
    and the built-in WebUI.
#>

[CmdletBinding()]
param (
    [Parameter(Position = 0)]
    [string]$ModelPath,

    [int]$Port = 8080,
    [string]$HostAddress = "0.0.0.0",
    [int]$MaxContext = 240000,
    [string]$ModelId = "qwen3.8-27b-nvfp4-swift",
    [string]$Spec = "mtp",
    [int]$DraftTokens = 3,
    [double]$Temperature = 1.0,
    [double]$MinP = 0.0,
    [double]$PresencePenalty = 0.0,
    [int]$ThinkingBudget = 4096,
    [bool]$PreserveThinking = $true,
    [string]$RequestLogFile = (Join-Path $PSScriptRoot "requests.jsonl"),
    [switch]$NoRequestLog,
    [switch]$Vision,
    [switch]$DFlash2,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Locate ninfer-serve binary (prefer newest version)
$binaryCandidates = @(
    (Join-Path $ScriptDir "ninfer-windows-0.8.0-win64-cuda131\ninfer-serve.exe"),
    (Join-Path $ScriptDir "ninfer-windows-0.7.1-win64-cuda131\ninfer-serve.exe"),
    (Join-Path $ScriptDir "ninfer-serve.exe")
) + (Get-ChildItem -Path $ScriptDir -Filter "ninfer-serve.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)

$bin = $binaryCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $bin) {
    Write-Error "[ERROR] ninfer-serve.exe not found under $ScriptDir"
    exit 1
}

# 2. Check if another instance is running
$running = Get-Process -Name "ninfer-serve" -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "[ERROR] ninfer-serve is already running (PID: $($running.Id -join ', '))" -ForegroundColor Red
    Write-Host "Only one server fits in VRAM at a time. Stop it first: Stop-Process -Id $($running.Id -join ',')" -ForegroundColor Yellow
    exit 1
}

# 3. Resolve Model Path
if (-not $ModelPath) {
    $modelCandidates = @(
        (Join-Path $ScriptDir "models\qwen3_8_27b_nvfp4swift15.ninfer"),
        (Join-Path $ScriptDir "ninfer-windows-0.8.0-win64-cuda131\models\qwen3_8_27b_nvfp4swift15.ninfer"),
        "\\wsl.localhost\Ubuntu\home\simon\models\qwen3_8_27b_nvfp4swift15.ninfer",
        "\\wsl$\Ubuntu\home\simon\models\qwen3_8_27b_nvfp4swift15.ninfer",
        (Join-Path $ScriptDir "models\qwen3_8_27b_nvfp4swift.ninfer"),
        (Join-Path $ScriptDir "ninfer-windows-0.8.0-win64-cuda131\models\qwen3_8_27b_nvfp4swift.ninfer"),
        (Join-Path $ScriptDir "ninfer-windows-0.7.1-win64-cuda131\models\qwen3_8_27b_nvfp4swift.ninfer"),
        "\\wsl.localhost\Ubuntu\home\simon\models\qwen3_8_27b_nvfp4swift.ninfer",
        "\\wsl$\Ubuntu\home\simon\models\qwen3_8_27b_nvfp4swift.ninfer"
    )
    $ModelPath = $modelCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $ModelPath -or -not (Test-Path $ModelPath)) {
    Write-Host "[ERROR] Model artifact not found!" -ForegroundColor Red
    Write-Host "Checked paths:"
    Write-Host "  - $ScriptDir\models\qwen3_8_27b_nvfp4swift.ninfer"
    Write-Host "  - \\wsl.localhost\Ubuntu\home\simon\models\qwen3_8_27b_nvfp4swift.ninfer"
    Write-Host "Provide path: .\start_ninfer_swift.ps1 -ModelPath 'C:\path\to\model.ninfer'" -ForegroundColor Yellow
    exit 1
}

# 4. Resolve Speculative decoding mode
if ($DFlash2) {
    $Spec = "dflash2"
    if ($DraftTokens -eq 3) { $DraftTokens = 7 }
}

# 5. Detect LAN IP for display
$lanIp = $null
try {
    $defaultRoute = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -AddressFamily IPv4 -ErrorAction Stop |
        Sort-Object RouteMetric |
        Select-Object -First 1
    if ($defaultRoute) {
        $lanIp = (Get-NetIPAddress -InterfaceIndex $defaultRoute.InterfaceIndex -AddressFamily IPv4 -ErrorAction Stop |
            Where-Object { $_.IPAddress -notlike "169.254.*" -and $_.IPAddress -notlike "127.*" } |
            Select-Object -ExpandProperty IPAddress -First 1)
    }
} catch {}

if (-not $lanIp) {
    $lanIp = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { 
            $_.IPAddress -notmatch '^(127\.|169\.254\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)'
        } |
        Select-Object -ExpandProperty IPAddress -First 1)
}

if (-not $lanIp) { $lanIp = "127.0.0.1" }

# 6. Banner
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting NInfer High-Performance Server (Swift-Qwen3.8)" -ForegroundColor Green
Write-Host " GPU:             NVIDIA GeForce RTX 5090 (32GB)" -ForegroundColor White
Write-Host " Model:           $ModelPath" -ForegroundColor White
Write-Host " Model ID:        $ModelId" -ForegroundColor White
Write-Host " Context:         $MaxContext tokens (FP8 KV Cache)" -ForegroundColor White
Write-Host " Spec:            $Spec ($DraftTokens draft tokens + LM head draft)" -ForegroundColor White
Write-Host " Sampling:        temp=$Temperature min_p=$MinP presence_penalty=$PresencePenalty" -ForegroundColor White
Write-Host " Thinking:        preserve_thinking=$PreserveThinking (budget=$ThinkingBudget tokens)" -ForegroundColor White
if (-not $NoRequestLog) {
    Write-Host " Request Log:     $RequestLogFile" -ForegroundColor White
} else {
    Write-Host " Request Log:     disabled" -ForegroundColor White
}
Write-Host " Vision:          $(if ($Vision) { 'enabled' } else { 'disabled' })" -ForegroundColor White
Write-Host " Local URL:       http://localhost:$Port" -ForegroundColor Yellow
Write-Host " LAN URL:         http://${lanIp}:$Port" -ForegroundColor Yellow
Write-Host " API Base:        http://${lanIp}:$Port/v1" -ForegroundColor Yellow
Write-Host " WebUI:           http://${lanIp}:$Port/ (interactive chat UI)" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

# 7. Start Keep-Awake Watcher
$logPath = Join-Path $ScriptDir "ninfer.log"
$keepAwakeScript = Join-Path $ScriptDir "keep_awake.ps1"
if (Test-Path $keepAwakeScript) {
    Start-Process -FilePath "powershell.exe" -ArgumentList "-WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File `"$keepAwakeScript`" -LogFile `"$logPath`"" -WindowStyle Hidden
}

# 8. Build Arguments
$argsList = @(
    $ModelPath,
    "--model-id", $ModelId,
    "--host", $HostAddress,
    "--port", $Port,
    "--max-context", $MaxContext,
    "--kv-capacity", $MaxContext,
    "--max-concurrency", "1",
    "--max-pending-requests", "50",
    "--pending-timeout-ms", "3000000",
    "--kv-dtype", "fp8",
    "--spec", $Spec,
    "--draft-tokens", $DraftTokens,
    "--lm-head-draft",
    "--temperature", $Temperature,
    "--min-p", $MinP,
    "--presence-penalty", $PresencePenalty,
    "--default-thinking-budget", $ThinkingBudget,
    "--cors",
    "--webui"
)

if ($PreserveThinking) {
    $argsList += "--preserve-thinking"
}

if (-not $NoRequestLog) {
    $argsList += @("--request-log-jsonl", $RequestLogFile)
}

if ($Vision) {
    $argsList += "--vision"
}

if ($ExtraArgs) {
    $argsList += $ExtraArgs
}

# 9. Start Engine with live tee to log file
& $bin @argsList 2>&1 | Tee-Object -FilePath $logPath
