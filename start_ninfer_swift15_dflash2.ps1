<#
.SYNOPSIS
    Starts NInfer High-Performance Server with kaushikvira's Swift 1.5 NVFP4-Full + DFlash2 build on Windows (RTX 5090).

.DESCRIPTION
    Launches ninfer-serve with recommended settings from the model card:
    - All-NVFP4 text + W8G32 embeddings
    - DFlash2 speculative decoding (7 draft tokens + LM head draft)
    - 262,144 token context with k8v4 KV caching & 48GB pinned host-KV arena
    - Sampling: temp 0.9, min_p 0.05, preserve_thinking (budget 16,384)
    - Built-in WebUI and LAN 0.0.0.0 binding
#>

[CmdletBinding()]
param (
    [Parameter(Position = 0)]
    [string]$ModelPath,

    [int]$Port = 8080,
    [string]$HostAddress = "0.0.0.0",
    [int]$MaxContext = 131072,
    [string]$ModelId = "qwen3.8-27b-swift15-nvfp4full-dflash2",
    [string]$Spec = "dflash2",
    [int]$DraftTokens = 7,
    [string]$KvDtype = "k8v4",
    [double]$Temperature = 0.65,
    [double]$MinP = 0.05,
    [double]$PresencePenalty = 0.05,
    [int]$ThinkingBudget = 1200,
    [bool]$PreserveThinking = $true,
    [int]$PrefillChunk = 4096,
    [int]$HostKvMib = 8192,
    [int]$MaxConcurrency = 2,
    [int]$MaxPendingRequests = 64,
    [int]$PendingTimeoutMs = 600000,
    [string]$RequestLogFile = "",
    [switch]$NoRequestLog,
    [bool]$Vision = $true,
    [switch]$NoVision,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $RequestLogFile) {
    $RequestLogFile = Join-Path $ScriptDir "requests.jsonl"
}

# 1. Resolve Model Path
if (-not $ModelPath) {
    $modelCandidates = @(
        (Join-Path $ScriptDir "models\qwen3_8_27b_swift15_nvfp4full-dflash2.ninfer"),
        (Join-Path $ScriptDir "ninfer-windows-0.8.0-win64-cuda131\models\qwen3_8_27b_swift15_nvfp4full-dflash2.ninfer"),
        "\\wsl.localhost\Ubuntu\home\simon\models\qwen3_8_27b_swift15_nvfp4full-dflash2.ninfer",
        "\\wsl$\Ubuntu\home\simon\models\qwen3_8_27b_swift15_nvfp4full-dflash2.ninfer"
    )
    $ModelPath = $modelCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}

if (-not $ModelPath -or -not (Test-Path $ModelPath)) {
    Write-Host "[ERROR] Model artifact not found!" -ForegroundColor Red
    Write-Host "Checked paths:"
    Write-Host "  - $ScriptDir\models\qwen3_8_27b_swift15_nvfp4full-dflash2.ninfer"
    Write-Host "  - \\wsl.localhost\Ubuntu\home\simon\models\qwen3_8_27b_swift15_nvfp4full-dflash2.ninfer"
    Write-Host "Provide path: .\start_ninfer_swift15_dflash2.ps1 -ModelPath 'C:\path\to\model.ninfer'" -ForegroundColor Yellow
    exit 1
}

# 2. Check if another instance is running
$running = Get-Process -Name "ninfer-serve" -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "[ERROR] ninfer-serve is already running (PID: $($running.Id -join ', '))" -ForegroundColor Red
    Write-Host "Only one server fits in VRAM at a time. Stop it first: Stop-Process -Id $($running.Id -join ',')" -ForegroundColor Yellow
    exit 1
}

# 3. Locate ninfer-serve binary (auto-detecting v2 vs v3 artifact version)
$isV2 = $false
try {
    $stream = [System.IO.File]::OpenRead($ModelPath)
    $bytes = New-Object byte[] 16
    $read = $stream.Read($bytes, 0, 16)
    $stream.Close()
    if ($read -ge 8 -and $bytes[0] -eq 78 -and $bytes[1] -eq 73 -and $bytes[2] -eq 78 -and $bytes[3] -eq 70 -and $bytes[4] -eq 69 -and $bytes[5] -eq 82 -and $bytes[7] -eq 2) {
        $isV2 = $true
    }
} catch {}

if ($isV2) {
    $binaryCandidates = @(
        (Join-Path $ScriptDir "ninfer-windows-0.7.1-win64-cuda131\ninfer-serve.exe"),
        (Join-Path $ScriptDir "ninfer-windows-0.8.0-win64-cuda131\ninfer-serve.exe")
    )
} else {
    $binaryCandidates = @(
        (Join-Path $ScriptDir "ninfer-windows-0.8.0-win64-cuda131\ninfer-serve.exe"),
        (Join-Path $ScriptDir "ninfer-windows-0.7.1-win64-cuda131\ninfer-serve.exe")
    )
}

$bin = $binaryCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $bin) {
    Write-Error "[ERROR] ninfer-serve.exe not found under $ScriptDir"
    exit 1
}

# 4. Detect LAN IP for display
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

# 5. Banner
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting NInfer Server (Swift-1.5 NVFP4-Full + DFlash2)" -ForegroundColor Green
Write-Host " GPU:             NVIDIA GeForce RTX 5090 (32GB)" -ForegroundColor White
Write-Host " Model:           $ModelPath" -ForegroundColor White
Write-Host " Model ID:        $ModelId" -ForegroundColor White
Write-Host " Context:         $MaxContext tokens ($KvDtype KV Cache)" -ForegroundColor White
Write-Host " Speculative:     $Spec ($DraftTokens draft tokens + LM head draft)" -ForegroundColor White
Write-Host " Sampling:        temp=$Temperature min_p=$MinP presence_penalty=$PresencePenalty" -ForegroundColor White
Write-Host " Thinking:        preserve_thinking=$PreserveThinking (budget=$ThinkingBudget tokens)" -ForegroundColor White
Write-Host " Concurrency:     $MaxConcurrency (Host KV Arena: ${HostKvMib} MiB)" -ForegroundColor White
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

# 6. Start Keep-Awake Watcher
$logPath = Join-Path $ScriptDir "ninfer.log"
$keepAwakeScript = Join-Path $ScriptDir "keep_awake.ps1"
if (Test-Path $keepAwakeScript) {
    Start-Process -FilePath "powershell.exe" -ArgumentList "-WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File `"$keepAwakeScript`" -LogFile `"$logPath`"" -WindowStyle Hidden
}

# 7. Build Arguments
$argsList = @(
    $ModelPath,
    "--model-id", $ModelId,
    "--host", $HostAddress,
    "--port", $Port,
    "--max-context", $MaxContext,
    "--kv-capacity", "auto",
    "--kv-dtype", $KvDtype,
    "--max-concurrency", $MaxConcurrency,
    "--max-pending-requests", $MaxPendingRequests,
    "--pending-timeout-ms", $PendingTimeoutMs,
    "--default-max-tokens", "32768",
    "--prefill-chunk", $PrefillChunk,
    "--temperature", $Temperature,
    "--min-p", $MinP,
    "--presence-penalty", $PresencePenalty,
    "--default-thinking-budget", $ThinkingBudget,
    "--host-kv-mib", $HostKvMib,
    "--cors",
    "--webui"
)

if ($Spec -and $Spec -ne "none") {
    $argsList += @("--spec", $Spec)
    if ($DraftTokens -gt 0) {
        $argsList += @("--draft-tokens", $DraftTokens)
    }
    if ($Spec -eq "dflash2") {
        $argsList += "--lm-head-draft"
    }
}

if ($PreserveThinking) {
    $argsList += "--preserve-thinking"
}

if (-not $NoRequestLog) {
    $argsList += @("--request-log-jsonl", $RequestLogFile)
}

if ($Vision -and -not $NoVision) {
    $argsList += "--vision"
}

if ($ExtraArgs) {
    $argsList += $ExtraArgs
}

# 8. Start Engine with live tee to log file
$ErrorActionPreference = "Continue"
& $bin @argsList 2>&1 | Tee-Object -FilePath $logPath
