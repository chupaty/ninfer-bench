#!/usr/bin/env python3
"""
NInfer Autonomous Benchmark & Lifecycle Orchestrator (Outer Layer)
Manages server startup, watchdog timeouts, settling checks, benchmark execution,
and scorecard recording.

Usage:
  python bench_runner.py --list
  python bench_runner.py --config 1
  python bench_runner.py --config 2
  python bench_runner.py --config 3
  python bench_runner.py --config 4
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIGS_FILE = SCRIPT_DIR / "bench_configs.json"
LAUNCHER_PS1 = SCRIPT_DIR / "start_ninfer_swift15_dflash2.ps1"
DEFAULT_URL = "http://127.0.0.1:8080"


def load_configs():
    if not CONFIGS_FILE.exists():
        print(f"[ERROR] Configs file not found: {CONFIGS_FILE}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("configs", {})


def stop_running_ninfer():
    print("[RUNNER] Stopping any existing ninfer-serve processes...")
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Process -Name 'ninfer-serve' -ErrorAction SilentlyContinue | Stop-Process -Force"],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass
    time.sleep(2.0)


NINFER_LOG = SCRIPT_DIR / "ninfer.log"

def wait_for_server_ready(base_url=DEFAULT_URL, timeout_sec=120, log_path=NINFER_LOG):
    print(f"[RUNNER] Monitoring NInfer engine startup & loading sequence (timeout: {timeout_sec}s)...")
    start = time.perf_counter()
    url = f"{base_url}/v1/models"
    
    log_file = None
    log_pos = 0
    if log_path and Path(log_path).exists():
        try:
            log_file = open(log_path, "r", encoding="utf-8", errors="replace")
            log_file.seek(0, os.SEEK_END)
            log_pos = log_file.tell()
        except Exception:
            pass

    while time.perf_counter() - start < timeout_sec:
        # Check and stream new lines from ninfer.log
        if log_path and Path(log_path).exists():
            try:
                if not log_file:
                    log_file = open(log_path, "r", encoding="utf-8", errors="replace")
                log_file.seek(log_pos)
                new_lines = log_file.readlines()
                log_pos = log_file.tell()
                for line in new_lines:
                    line_str = line.strip()
                    if line_str and not line_str.startswith("."):
                        print(f"  \033[90m[NInfer]\033[0m {line_str}")
            except Exception:
                pass

        # Check /v1/models readiness
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("data", [])
                if models and models[0].get("status", {}).get("value") == "loaded":
                    elapsed = time.perf_counter() - start
                    print(f"\n  \033[92m[READY]\033[0m Model '{models[0].get('id')}' is fully loaded & settled in VRAM! ({elapsed:.1f}s)")
                    if log_file:
                        log_file.close()
                    return True
        except Exception:
            pass
        time.sleep(0.5)

    if log_file:
        log_file.close()
    print(f"\n[ERROR] Server failed to settle within {timeout_sec}s!", file=sys.stderr)
    return False


def run_config(cfg_id: str, stop_after=False, scenario="1", max_turns=None):
    configs = load_configs()
    if cfg_id not in configs:
        print(f"[ERROR] Config ID '{cfg_id}' not found. Available: {list(configs.keys())}", file=sys.stderr)
        sys.exit(1)

    cfg = configs[cfg_id]
    print("\n" + "=" * 80)
    print(f" ORCHESTRATOR: Running Config {cfg_id} - {cfg['name']}")
    print(f" Scenario: {scenario} | Description: {cfg.get('description', '')}")
    print("=" * 80)

    # 1. Stop existing instance
    stop_running_ninfer()

    # 2. Prepare launcher command
    model_path = Path(cfg["model_path"])
    if not model_path.is_absolute():
        model_path = SCRIPT_DIR / model_path

    if not model_path.exists():
        print(f"[ERROR] Model artifact not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    ps_args = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", str(LAUNCHER_PS1),
        "-ModelPath", str(model_path),
        "-ModelId", cfg.get("model_id", "qwen3.8-27b-swift15-nvfp4full-dflash2"),
        "-Spec", cfg.get("spec", "dflash2"),
        "-DraftTokens", str(cfg.get("draft_tokens", 7)),
        "-Temperature", str(cfg.get("temperature", 0.9)),
        "-MinP", str(cfg.get("min_p", 0.05)),
        "-PresencePenalty", str(cfg.get("presence_penalty", 0.0)),
        "-ThinkingBudget", str(cfg.get("thinking_budget", 4096)),
        "-PrefillChunk", str(cfg.get("prefill_chunk", 4096)),
        "-MaxContext", str(cfg.get("max_context", 240000)),
        "-MaxConcurrency", str(cfg.get("max_concurrency", 2)),
        "-PendingTimeoutMs", str(cfg.get("pending_timeout_ms", 600000)),
        "-MaxPendingRequests", str(cfg.get("max_pending_requests", 64)),
    ]

    print(f"[RUNNER] Launching background server via {LAUNCHER_PS1.name}...")

    proc = subprocess.Popen(
        ps_args,
        cwd=str(SCRIPT_DIR),
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )

    # 3. Wait for server ready
    if not wait_for_server_ready():
        print("[ERROR] Server startup failed. Inspect ninfer.log for details.", file=sys.stderr)
        proc.kill()
        sys.exit(1)

    # 4. Execute the agentic benchmark harness
    print(f"\n[RUNNER] Launching inner agentic benchmark harness...")
    from bench_agentic import run_agentic_test

    scenarios_to_run = ["1", "2", "3"] if str(scenario).lower() == "all" else [str(scenario)]
    summaries = []

    for sc_key in scenarios_to_run:
        summary = run_agentic_test(
            config_name=f"Config-{cfg_id}_{cfg['name'].replace(' ', '_')}",
            scenario_key=sc_key,
            base_url=DEFAULT_URL,
            model_id=cfg.get("model_id", "qwen3.8-27b-swift15-nvfp4full-dflash2"),
            temperature=float(cfg.get("temperature", 0.9)),
            min_p=float(cfg.get("min_p", 0.05)),
            presence_penalty=float(cfg.get("presence_penalty", 0.0)),
            thinking_budget=int(cfg.get("thinking_budget", 4096)),
            preserve_thinking=bool(cfg.get("preserve_thinking", True)),
            max_turns=max_turns,
        )
        summaries.append(summary)

    if stop_after:
        stop_running_ninfer()
    else:
        print("\n[INFO] Server remains running on http://localhost:8080.")

    return summaries[-1] if len(summaries) == 1 else summaries


def list_configs():
    configs = load_configs()
    print("\n" + "=" * 110)
    print(f"{'ID':<6} | {'Model Group':<16} | {'Iteration / Name':<38} | {'Temp':<5} | {'MinP':<5} | {'Penalty':<7} | {'Budget':<6} | {'Spec'}")
    print("-" * 110)
    for cid, c in sorted(configs.items(), key=lambda x: x[0]):
        mgroup = c.get("model_group", "")
        name = c.get("name", "")
        print(f"{cid:<6} | {mgroup:<16} | {name:<38} | {c.get('temperature', 0.9):<5} | {c.get('min_p', 0.05):<5} | {c.get('presence_penalty', 0.0):<7} | {c.get('thinking_budget', 4096):<6} | {c.get('spec', 'none')} (draft={c.get('draft_tokens', 0)})")
    print("=" * 110)
    print("Run with: python bench_runner.py --config <ID> [--scenario <1|2|3|all>] OR --model <1|2|3|all> OR --sweep\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NInfer Benchmark Lifecycle Orchestrator")
    parser.add_argument("--config", "-c", type=str, help="Config ID or comma-separated list to launch and test (e.g. 1.1 or 1.1,1.2,1.3)")
    parser.add_argument("--scenario", "-sc", default="1", choices=["1", "2", "3", "all"], help="Scenario ID: 1=SpringArm Bug, 2=Phantom IK Solver, 3=Combiner Mech, all=all 3 scenarios")
    parser.add_argument("--max-turns", type=int, default=None, help="Override maximum turns per scenario")
    parser.add_argument("--model", "-m", type=str, help="Model group to sweep (1, 2, 3, or all)")
    parser.add_argument("--sweep", "-s", action="store_true", help="Run all registered configurations across all models in sequence")
    parser.add_argument("--list", "-l", action="store_true", help="List all registered test configurations")
    parser.add_argument("--stop-after", action="store_true", help="Stop server after benchmark finishes")
    args = parser.parse_args()

    configs = load_configs()

    if args.list:
        list_configs()
    elif args.sweep or args.model == "all":
        print(f"\n[RUNNER] Starting comprehensive sweep across all {len(configs)} configurations on Scenario {args.scenario}...")
        for cid in sorted(configs.keys()):
            print(f"\n================================================================================")
            print(f">>> Running Sweep Config {cid} of {len(configs)}: {configs[cid]['name']} <<<")
            print(f"================================================================================")
            run_config(cid, stop_after=False, scenario=args.scenario, max_turns=args.max_turns)
        print("\n[COMPLETE] Full configuration sweep completed! See bench_reports/SCORECARD.md")
    elif args.model:
        prefix = f"{args.model}."
        matched = [cid for cid in sorted(configs.keys()) if cid.startswith(prefix)]
        if not matched:
            print(f"[ERROR] No configs found for model group '{args.model}'. Available groups: 1, 2, 3", file=sys.stderr)
            sys.exit(1)
        print(f"\n[RUNNER] Starting sweep for Model Group {args.model} ({len(matched)} iterations) on Scenario {args.scenario}...")
        for cid in matched:
            print(f"\n>>> Running Sweep Config {cid}: {configs[cid]['name']} <<<")
            run_config(cid, stop_after=False, scenario=args.scenario, max_turns=args.max_turns)
        print(f"\n[COMPLETE] Model Group {args.model} sweep completed! See bench_reports/SCORECARD.md")
    elif args.config:
        cids = [c.strip() for c in args.config.split(",") if c.strip()]
        for cid in cids:
            run_config(cid, stop_after=args.stop_after, scenario=args.scenario, max_turns=args.max_turns)
    else:
        list_configs()
