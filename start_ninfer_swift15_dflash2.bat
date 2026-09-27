@echo off
setlocal EnableExtensions EnableDelayedExpansion

title NInfer Server (Swift-1.5 NVFP4-Full + DFlash2 / RTX 5090)

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

rem ---------------------------------------------------------------- Find ninfer-serve binary
set "BIN="
if exist "%SCRIPT_DIR%ninfer-windows-0.8.0-win64-cuda131\ninfer-serve.exe" (
    set "BIN=%SCRIPT_DIR%ninfer-windows-0.8.0-win64-cuda131\ninfer-serve.exe"
) else if exist "%SCRIPT_DIR%ninfer-windows-0.7.1-win64-cuda131\ninfer-serve.exe" (
    set "BIN=%SCRIPT_DIR%ninfer-windows-0.7.1-win64-cuda131\ninfer-serve.exe"
) else (
    for /d %%D in ("%SCRIPT_DIR%ninfer-windows-*") do (
        if exist "%%D\ninfer-serve.exe" set "BIN=%%D\ninfer-serve.exe"
    )
)

if not defined BIN (
    echo [ERROR] ninfer-serve.exe not found under %SCRIPT_DIR%
    echo Please make sure a ninfer-windows package is extracted in this folder.
    pause
    exit /b 1
)

rem ---------------------------------------------------------------- Check if already running
tasklist /FI "IMAGENAME eq ninfer-serve.exe" 2>NUL | find /I /N "ninfer-serve.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [ERROR] ninfer-serve is already running!
    echo Only one server fits in VRAM at a time. Stop the running instance first.
    tasklist /FI "IMAGENAME eq ninfer-serve.exe"
    pause
    exit /b 1
)

rem ---------------------------------------------------------------- Resolve Model Path
set "MODEL_PATH=%~1"
if not defined MODEL_PATH (
    if exist "%SCRIPT_DIR%models\qwen3_8_27b_swift15_nvfp4full-dflash2.ninfer" (
        set "MODEL_PATH=%SCRIPT_DIR%models\qwen3_8_27b_swift15_nvfp4full-dflash2.ninfer"
    ) else if exist "%SCRIPT_DIR%ninfer-windows-0.8.0-win64-cuda131\models\qwen3_8_27b_swift15_nvfp4full-dflash2.ninfer" (
        set "MODEL_PATH=%SCRIPT_DIR%ninfer-windows-0.8.0-win64-cuda131\models\qwen3_8_27b_swift15_nvfp4full-dflash2.ninfer"
    ) else if exist "\\wsl.localhost\Ubuntu\home\simon\models\qwen3_8_27b_swift15_nvfp4full-dflash2.ninfer" (
        set "MODEL_PATH=\\wsl.localhost\Ubuntu\home\simon\models\qwen3_8_27b_swift15_nvfp4full-dflash2.ninfer"
    ) else if exist "\\wsl$\Ubuntu\home\simon\models\qwen3_8_27b_swift15_nvfp4full-dflash2.ninfer" (
        set "MODEL_PATH=\\wsl$\Ubuntu\home\simon\models\qwen3_8_27b_swift15_nvfp4full-dflash2.ninfer"
    )
)

if not defined MODEL_PATH (
    echo [ERROR] Model artifact not found!
    echo Checked:
    echo   - %SCRIPT_DIR%models\qwen3_8_27b_swift15_nvfp4full-dflash2.ninfer
    echo   - \\wsl.localhost\Ubuntu\home\simon\models\qwen3_8_27b_swift15_nvfp4full-dflash2.ninfer
    echo Pass the model path as argument 1: start_ninfer_swift15_dflash2.bat "path\to\model.ninfer"
    pause
    exit /b 1
)

rem ---------------------------------------------------------------- Configuration (kaushikvira recommended settings)
if not defined PORT set "PORT=8080"
if not defined HOST set "HOST=0.0.0.0"
if not defined MAX_CONTEXT set "MAX_CONTEXT=131072"
if not defined MODEL_ID set "MODEL_ID=qwen3.8-27b-swift15-nvfp4full-dflash2"
if not defined SPEC set "SPEC=dflash2"
if not defined DRAFT_TOKENS set "DRAFT_TOKENS=7"
if not defined KV_DTYPE set "KV_DTYPE=k8v4"
if not defined TEMPERATURE set "TEMPERATURE=0.65"
if not defined MIN_P set "MIN_P=0.05"
if not defined PRESENCE_PENALTY set "PRESENCE_PENALTY=0.05"
if not defined THINKING_BUDGET set "THINKING_BUDGET=1200"
if not defined PRESERVE_THINKING set "PRESERVE_THINKING=1"
if not defined PREFILL_CHUNK set "PREFILL_CHUNK=4096"
if not defined MAX_CONCURRENCY set "MAX_CONCURRENCY=2"
if not defined MAX_PENDING set "MAX_PENDING=64"
if not defined PENDING_TIMEOUT_MS set "PENDING_TIMEOUT_MS=600000"
if not defined HOST_KV_MIB set "HOST_KV_MIB=8192"
if not defined VISION set "VISION=1"
if not defined REQUEST_LOG set "REQUEST_LOG=1"
if not defined REQUEST_LOG_FILE set "REQUEST_LOG_FILE=%SCRIPT_DIR%requests.jsonl"

rem ---------------------------------------------------------------- Detect LAN IP
set "LAN_IP=127.0.0.1"
for /f "delims=" %%a in ('powershell.exe -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex (Get-NetRoute -DestinationPrefix 0.0.0.0/0 -AddressFamily IPv4 -ErrorAction SilentlyContinue | Sort-Object RouteMetric | Select-Object -ExpandProperty InterfaceIndex -First 1) -ErrorAction SilentlyContinue).IPAddress"') do (
    if not "%%a"=="" set "LAN_IP=%%a"
)

set "EXTRA_FLAGS="
if "%VISION%"=="1" set "EXTRA_FLAGS=!EXTRA_FLAGS! --vision"
if "%PRESERVE_THINKING%"=="1" set "EXTRA_FLAGS=!EXTRA_FLAGS! --preserve-thinking"
if "%REQUEST_LOG%"=="1" set "EXTRA_FLAGS=!EXTRA_FLAGS! --request-log-jsonl ""!REQUEST_LOG_FILE!"""

echo ==========================================================
echo  Starting NInfer Server (Swift-1.5 NVFP4-Full + DFlash2)
echo  GPU:             NVIDIA GeForce RTX 5090 (32GB)
echo  Model:           !MODEL_PATH!
echo  Model ID:        !MODEL_ID!
echo  Context:         !MAX_CONTEXT! tokens (!KV_DTYPE! KV Cache)
echo  Speculative:     !SPEC! (!DRAFT_TOKENS! draft tokens + LM head draft)
echo  Sampling:        temp=!TEMPERATURE! min_p=!MIN_P! presence_penalty=!PRESENCE_PENALTY!
echo  Thinking:        preserve_thinking=%PRESERVE_THINKING% (budget=!THINKING_BUDGET!)
echo  Concurrency:     !MAX_CONCURRENCY! (Host KV Arena: !HOST_KV_MIB! MiB)
if "%REQUEST_LOG%"=="1" (
    echo  Request Log:     !REQUEST_LOG_FILE!
) else (
    echo  Request Log:     disabled
)
if "%VISION%"=="1" (
    echo  Vision:          enabled
) else (
    echo  Vision:          disabled (set VISION=1 to enable)
)
echo  Keep-Awake:      Active (prevents sleep while active)
echo  Local URL:       http://localhost:%PORT%
echo  LAN URL:         http://!LAN_IP!:%PORT%
echo  API Base:        http://!LAN_IP!:%PORT%/v1
echo  WebUI:           http://!LAN_IP!:%PORT%/ (interactive chat UI)
echo ==========================================================

rem ---------------------------------------------------------------- Shift model arg if given
if not "%~1"=="" shift

rem ---------------------------------------------------------------- Start Keep-Awake Watcher
set "LOG_FILE=%SCRIPT_DIR%ninfer.log"
start "" powershell.exe -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%keep_awake.ps1" -LogFile "%LOG_FILE%"

"%BIN%" "!MODEL_PATH!" ^
    --model-id "%MODEL_ID%" ^
    --host "%HOST%" ^
    --port "%PORT%" ^
    --max-context %MAX_CONTEXT% ^
    --kv-capacity auto ^
    --kv-dtype %KV_DTYPE% ^
    --max-concurrency %MAX_CONCURRENCY% ^
    --max-pending-requests %MAX_PENDING% ^
    --pending-timeout-ms %PENDING_TIMEOUT_MS% ^
    --default-max-tokens 32768 ^
    --prefill-chunk %PREFILL_CHUNK% ^
    --spec %SPEC% --draft-tokens %DRAFT_TOKENS% ^
    --lm-head-draft ^
    --temperature %TEMPERATURE% ^
    --min-p %MIN_P% ^
    --presence-penalty %PRESENCE_PENALTY% ^
    --default-thinking-budget %THINKING_BUDGET% ^
    --host-kv-mib %HOST_KV_MIB% ^
    --cors ^
    --webui ^
    !EXTRA_FLAGS! ^
    %1 %2 %3 %4 %5 %6 %7 %8 %9 2>&1 | powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$input | Tee-Object -FilePath '%LOG_FILE%'"

pause
