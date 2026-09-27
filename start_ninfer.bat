@echo off
setlocal EnableExtensions EnableDelayedExpansion

title NInfer Server (RTX 5090)

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

rem ---------------------------------------------------------------- Find ninfer-serve binary
set "BIN="
if exist "%SCRIPT_DIR%ninfer-windows-0.7.1-win64-cuda131\ninfer-serve.exe" (
    set "BIN=%SCRIPT_DIR%ninfer-windows-0.7.1-win64-cuda131\ninfer-serve.exe"
) else (
    for /d %%D in ("%SCRIPT_DIR%ninfer-windows-*") do (
        if exist "%%D\ninfer-serve.exe" set "BIN=%%D\ninfer-serve.exe"
    )
)

if not defined BIN (
    echo [ERROR] ninfer-serve.exe not found under %SCRIPT_DIR%
    echo Please make sure the ninfer-windows package is extracted in this folder.
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
    if exist "%SCRIPT_DIR%models\qwen3_8_27b_nvfp4.ninfer" (
        set "MODEL_PATH=%SCRIPT_DIR%models\qwen3_8_27b_nvfp4.ninfer"
    ) else if exist "%SCRIPT_DIR%ninfer-windows-0.7.1-win64-cuda131\models\qwen3_8_27b_nvfp4.ninfer" (
        set "MODEL_PATH=%SCRIPT_DIR%ninfer-windows-0.7.1-win64-cuda131\models\qwen3_8_27b_nvfp4.ninfer"
    ) else if exist "\\wsl.localhost\Ubuntu\home\simon\models\qwen3_8_27b_nvfp4.ninfer" (
        set "MODEL_PATH=\\wsl.localhost\Ubuntu\home\simon\models\qwen3_8_27b_nvfp4.ninfer"
    ) else if exist "\\wsl$\Ubuntu\home\simon\models\qwen3_8_27b_nvfp4.ninfer" (
        set "MODEL_PATH=\\wsl$\Ubuntu\home\simon\models\qwen3_8_27b_nvfp4.ninfer"
    )
)

if not defined MODEL_PATH (
    echo [ERROR] Model artifact not found!
    echo Checked:
    echo   - %SCRIPT_DIR%models\qwen3_8_27b_nvfp4.ninfer
    echo   - \\wsl.localhost\Ubuntu\home\simon\models\qwen3_8_27b_nvfp4.ninfer
    echo Pass the model path as argument 1: start_ninfer.bat "path\to\model.ninfer"
    pause
    exit /b 1
)

rem ---------------------------------------------------------------- Configuration
if not defined PORT set "PORT=8080"
if not defined HOST set "HOST=0.0.0.0"
if not defined MAX_CONTEXT set "MAX_CONTEXT=240000"
if not defined KV_CAPACITY set "KV_CAPACITY=240000"
if not defined MODEL_ID set "MODEL_ID=qwen3.8-27b-nvfp4"
if not defined SPEC set "SPEC=mtp"
if not defined DRAFT_TOKENS set "DRAFT_TOKENS=3"

rem Anti-loop sampling & thinking controls
if not defined TEMPERATURE set "TEMPERATURE=0.6"
if not defined MIN_P set "MIN_P=0.05"
if not defined PRESENCE_PENALTY set "PRESENCE_PENALTY=0.1"
if not defined THINKING_BUDGET set "THINKING_BUDGET=4096"
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
echo  Starting NInfer High-Performance Server (Windows)
echo  GPU:             NVIDIA GeForce RTX 5090 (32GB)
echo  Model:           !MODEL_PATH!
echo  Model ID:        !MODEL_ID!
echo  Context:         !MAX_CONTEXT! tokens (FP8 KV Cache)
echo  Spec:            !SPEC! (!DRAFT_TOKENS! draft tokens + LM head draft)
echo  Sampling:        temp=!TEMPERATURE! min_p=!MIN_P! presence_penalty=!PRESENCE_PENALTY!
echo  Thinking Budget: !THINKING_BUDGET! tokens (preserve_thinking=%PRESERVE_THINKING%)
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
echo  Keep-Awake:      Active (prevents sleep if active in last 60m)
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
    --kv-capacity %KV_CAPACITY% ^
    --max-concurrency 1 ^
    --kv-dtype fp8 ^
    --spec %SPEC% --draft-tokens %DRAFT_TOKENS% ^
    --lm-head-draft ^
    --temperature %TEMPERATURE% ^
    --min-p %MIN_P% ^
    --presence-penalty %PRESENCE_PENALTY% ^
    --default-thinking-budget %THINKING_BUDGET% ^
    --cors ^
    --webui ^
    !EXTRA_FLAGS! ^
    %1 %2 %3 %4 %5 %6 %7 %8 %9 2>&1 | powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$input | Tee-Object -FilePath '%LOG_FILE%'"

pause

