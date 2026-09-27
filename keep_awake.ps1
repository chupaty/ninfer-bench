param(
    [string]$ProcessName = "ninfer-serve",
    [int]$IdleTimeoutMinutes = 60,
    [int]$PollIntervalSeconds = 10,
    [string]$LogFile = "",
    [switch]$NoAutoSleep
)

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $scriptDir) { $scriptDir = "C:\dev\ninfer" }
$lockFile = Join-Path $scriptDir ".keep_awake.pid"
if (-not $LogFile) { $LogFile = Join-Path $scriptDir "ninfer.log" }

# Check if an existing monitor is already running
if (Test-Path $lockFile) {
    try {
        $oldPid = Get-Content $lockFile -ErrorAction SilentlyContinue
        if ($oldPid -and (Get-Process -Id ([int]$oldPid) -ErrorAction SilentlyContinue)) {
            exit 0
        }
    } catch {}
}

try {
    $PID | Set-Content $lockFile -Force -ErrorAction SilentlyContinue
} catch {}

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class SleepBlocker {
    [Flags]
    public enum EXECUTION_STATE : uint {
        ES_CONTINUOUS        = 0x80000000,
        ES_SYSTEM_REQUIRED   = 0x00000001
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern EXECUTION_STATE SetThreadExecutionState(EXECUTION_STATE esFlags);

    [DllImport("PowrProf.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern bool SetSuspendState(bool hibernate, bool forceCritical, bool disableWakeEvent);

    public static void PreventSleep() {
        SetThreadExecutionState(EXECUTION_STATE.ES_CONTINUOUS | EXECUTION_STATE.ES_SYSTEM_REQUIRED);
    }

    public static void AllowSleep() {
        SetThreadExecutionState(EXECUTION_STATE.ES_CONTINUOUS);
    }

    public static void TriggerSleep() {
        SetSuspendState(false, false, false);
    }
}
"@ -ErrorAction SilentlyContinue

$isKeepingAwake = $false
$lastActiveTime = Get-Date
$lastLogLength = -1
$lastCpuTime = $null
$hasSeenProcess = $false
$missCount = 0

try {
    while ($true) {
        $proc = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue | Select-Object -First 1

        if ($proc) {
            $hasSeenProcess = $true
            $missCount = 0

            # 1. Check Log file write activity if log exists
            if (Test-Path $LogFile) {
                try {
                    $item = Get-Item $LogFile -ErrorAction SilentlyContinue
                    if ($item) {
                        if ($lastLogLength -eq -1) {
                            # First check: record baseline size, but start active timer from NOW (not stale log file date)
                            $lastLogLength = $item.Length
                            $lastActiveTime = Get-Date
                        } elseif ($item.Length -ne $lastLogLength) {
                            # New activity detected in log
                            $lastLogLength = $item.Length
                            $lastActiveTime = Get-Date
                        }
                    }
                } catch {}
            } else {
                # Fallback: CPU delta threshold (requiring at least 0.5s CPU within 10s window to avoid idle ticks)
                $currentCpu = $proc.CPU
                if ($null -eq $lastCpuTime) {
                    $lastCpuTime = $currentCpu
                    $lastActiveTime = Get-Date
                }
                elseif ($currentCpu -gt ($lastCpuTime + 0.5)) {
                    $lastCpuTime = $currentCpu
                    $lastActiveTime = Get-Date
                }
            }

            $elapsedMinutes = ((Get-Date) - $lastActiveTime).TotalMinutes

            if ($elapsedMinutes -le $IdleTimeoutMinutes) {
                if (-not $isKeepingAwake) {
                    [SleepBlocker]::PreventSleep()
                    $isKeepingAwake = $true
                }
            } else {
                # Idle threshold exceeded
                if ($isKeepingAwake) {
                    [SleepBlocker]::AllowSleep()
                    $isKeepingAwake = $false
                }
                if (-not $NoAutoSleep) {
                    # Reset active time to current moment so on resume we wait another idle window
                    $lastActiveTime = Get-Date
                    [SleepBlocker]::AllowSleep()
                    [SleepBlocker]::TriggerSleep()
                }
            }
        } else {
            # If ninfer-serve was previously running and is now stopped, exit cleanly
            if ($hasSeenProcess) {
                $missCount++
                if ($missCount -ge 3) {
                    break
                }
            } else {
                # If launched slightly before ninfer-serve starts up, wait up to 30s
                $missCount++
                if ($missCount -gt 6) {
                    break
                }
            }
        }

        Start-Sleep -Seconds $PollIntervalSeconds
    }
}
finally {
    [SleepBlocker]::AllowSleep()
    Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
}
