#!/usr/bin/env python3
"""
NInfer Standalone Benchmark Harness
Tests any running NInfer model against standardized real-world dev tasks:
  - Test 1 (Empty/Short Context: ~1.2k tokens): Clinical data pipeline refactor (c:\tmp\bloods)
  - Test 2 (Half-Full Context: ~81k tokens): Full AIMS Rust multi-crate architecture audit (dev/aims)

Zero external dependencies (pure Python standard library).
Logs full outputs and marks scorecard as [PENDING QUALITY REVIEW] for agent inspection.
"""

import argparse
import glob
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_URL = "http://127.0.0.1:8080"
SCRIPT_DIR = Path(__file__).parent.resolve()
REPORTS_DIR = SCRIPT_DIR / "bench_reports"
BLOODS_FILE = Path(r"C:\tmp\bloods\analyze_clinical_trends.py")
AIMS_DIR = Path(r"\\wsl.localhost\Ubuntu\home\simon\dev\aims")
if not AIMS_DIR.exists():
    AIMS_DIR = Path(r"\\wsl$\Ubuntu\home\simon\dev\aims")


def get_active_model(base_url):
    try:
        req = urllib.request.Request(f"{base_url}/v1/models")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = data.get("data", [])
            if models:
                return models[0].get("id", "unknown-model")
    except Exception as e:
        print(f"[WARN] Could not query /v1/models ({e}). Using fallback ID.", file=sys.stderr)
    return "qwen3.8-27b-nvfp4"


def build_test1_prompt():
    """Short context dev test: code review & refactor"""
    code_content = ""
    if BLOODS_FILE.exists():
        code_content = BLOODS_FILE.read_text(encoding="utf-8", errors="ignore")
    else:
        code_content = """import pandas as pd
import numpy as np

def calculate_patient_trajectory(df, patient_id, marker_cols):
    sub = df[df['patient_id'] == patient_id].sort_values('timestamp')
    results = {}
    for col in marker_cols:
        vals = sub[col].dropna().values
        if len(vals) < 2:
            results[col] = {'slope': 0.0, 'variance': 0.0}
            continue
        x = np.arange(len(vals))
        slope, intercept = np.polyfit(x, vals, 1)
        results[col] = {'slope': float(slope), 'variance': float(np.var(vals))}
    return results
"""

    prompt = f"""You are an expert Python systems and data engineer.
Review the following clinical data processing script:

```python
{code_content}
```

Please perform the following:
1. Identify any performance bottlenecks, missing edge cases (e.g. empty inputs, division by zero, null/NaN handling), and type safety issues.
2. Provide a fully refactored, robust, and vectorized/optimized version with Python 3.12+ type annotations, docstrings, error handling, and unit test examples.
"""
    return prompt


def build_test2_prompt():
    """Half-full context dev test: full codebase ingestion & architectural review"""
    collected_files = []
    total_chars = 0

    if AIMS_DIR.exists():
        pattern = str(AIMS_DIR / "**" / "*")
        for f in glob.glob(pattern, recursive=True):
            p = Path(f)
            if p.is_file() and p.suffix in (".rs", ".toml", ".sql", ".md") and "target" not in p.parts:
                try:
                    rel_path = p.relative_to(AIMS_DIR)
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    collected_files.append((str(rel_path), content))
                    total_chars += len(content)
                except Exception:
                    continue

    if not collected_files:
        print("[WARN] AIMS repository not found at WSL path; using synthetic codebase context.")
        synthetic = "// Synthetic module\npub struct ServiceState { pub id: u64, pub active: bool }\n" * 15000
        collected_files = [("crates/synthetic/src/lib.rs", synthetic)]

    repo_text = []
    for path, content in collected_files:
        repo_text.append(f"--- FILE: {path} ---\n{content}\n")
    all_code = "\n".join(repo_text)

    prompt = f"""You are a Principal Rust Architect. Below is the full source code and configuration of the AIMS project ({len(collected_files)} files):

{all_code}

Based on the complete repository provided above, provide a thorough architectural audit:
1. **End-to-End Data Flow**: Trace the lifecycle of a request from the API layer through the database migrations/queries.
2. **Concurrency & Resilience Audit**: Identify any potential deadlocks, async cancellation hazards, unchecked unwrap calls, or transaction rollback edge cases.
3. **Telemetry & Healthcheck Design**: Propose a concrete Rust implementation plan (including structs and handlers) to add structured tracing, metrics, and deep health check probes across all crates.
"""
    return prompt


def send_chat_completion(base_url, model_id, prompt, temperature=1.0, max_tokens=8192, thinking_budget=2048, stream=True):
    url = f"{base_url}/v1/chat/completions"
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "thinking": {"budget_tokens": thinking_budget},
        "stream": stream,
    }

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    t_start = time.perf_counter()
    t_first_token = None
    chunks = []
    thinking_chunks = []
    answer_chunks = []
    in_think = False

    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            for line in resp:
                line = line.decode("utf-8", errors="replace").strip()
                if not line or line.startswith(":"):
                    continue
                if line == "data: [DONE]":
                    break
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        chunk_obj = json.loads(data_str)
                        delta = chunk_obj.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        reasoning = delta.get("reasoning_content", "") or delta.get("thinking", "")

                        if t_first_token is None and (content or reasoning):
                            t_first_token = time.perf_counter()

                        if reasoning:
                            thinking_chunks.append(reasoning)

                        if content:
                            if "<think>" in content:
                                in_think = True
                            if "</think>" in content:
                                in_think = False
                            
                            if in_think:
                                thinking_chunks.append(content)
                            else:
                                answer_chunks.append(content)

                        chunks.append(content)
                    except json.JSONDecodeError:
                        continue
    except urllib.error.URLError as e:
        print(f"[ERROR] Request failed: {e}", file=sys.stderr)
        return None

    t_end = time.perf_counter()

    ttft = (t_first_token - t_start) if t_first_token else 0.0
    total_time = t_end - t_start
    full_text = "".join(chunks)
    thinking_text = "".join(thinking_chunks)
    answer_text = "".join(answer_chunks)

    return {
        "ttft_sec": ttft,
        "total_time_sec": total_time,
        "full_text": full_text,
        "thinking_text": thinking_text,
        "answer_text": answer_text,
    }


def get_last_server_telemetry(log_path):
    if not os.path.exists(log_path):
        return {}
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = [l.strip() for l in f if l.strip()]
            for line in reversed(lines):
                try:
                    obj = json.loads(line)
                    if obj.get("event") == "request_done":
                        return obj
                except Exception:
                    continue
    except Exception:
        pass
    return {}


def run_benchmark(selected_test=None, base_url=DEFAULT_URL, temp=1.0, max_tokens=8192, thinking_budget=2048):
    model_id = get_active_model(base_url)
    REPORTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = REPORTS_DIR / f"benchmark_{model_id}_{ts}.md"
    log_file = SCRIPT_DIR / "requests.jsonl"

    print("=" * 75)
    print(f" NInfer Benchmark Suite")
    print(f" Target Server:  {base_url}")
    print(f" Active Model:   {model_id}")
    print(f" Sampling Temp:  {temp}")
    print(f" Think Budget:   {thinking_budget} tokens | Max Output: {max_tokens} tokens")
    print(f" Report Target:  {report_file.name}")
    print("=" * 75)

    tests_to_run = []
    if selected_test in (None, "1", "all", "short"):
        tests_to_run.append(("Test 1: Empty Context (Dev Short Refactor)", build_test1_prompt))
    if selected_test in (None, "2", "all", "long"):
        tests_to_run.append(("Test 2: Half-Full Context (AIMS ~81k Repo Audit)", build_test2_prompt))

    results = []

    for name, prompt_fn in tests_to_run:
        print(f"\n[RUNNING] {name}...")
        prompt = prompt_fn()
        approx_prompt_tokens = len(prompt) // 4
        print(f"          Context Size: ~{approx_prompt_tokens:,} tokens")

        res = send_chat_completion(base_url, model_id, prompt, temperature=temp, max_tokens=max_tokens, thinking_budget=thinking_budget)
        if not res:
            print(f"[FAILED] {name} encountered an error.")
            continue

        telem = get_last_server_telemetry(log_file)
        result_telem = telem.get("result", {})
        spec_telem = telem.get("speculative", {})
        timing_telem = telem.get("timings_seconds", {})

        actual_prompt_tokens = result_telem.get("prompt_tokens", approx_prompt_tokens)
        thinking_tokens = result_telem.get("model_thinking_tokens", len(res["thinking_text"]) // 4)
        completion_tokens = result_telem.get("completion_tokens", len(res["full_text"]) // 4)
        server_ttft = timing_telem.get("ttft", res["ttft_sec"])
        server_decode_tps = result_telem.get("decode_tokens_per_second", 0.0)

        if server_decode_tps == 0.0 and res["total_time_sec"] > res["ttft_sec"]:
            decode_time = res["total_time_sec"] - res["ttft_sec"]
            server_decode_tps = completion_tokens / max(decode_time, 0.001)

        drafted = spec_telem.get("drafted_tokens", 0)
        accepted = spec_telem.get("accepted_tokens", 0)
        mtp_rate = (accepted / drafted * 100.0) if drafted > 0 else 0.0

        summary = {
            "test_name": name,
            "model_id": model_id,
            "prompt_tokens": actual_prompt_tokens,
            "thinking_tokens": thinking_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": actual_prompt_tokens + completion_tokens,
            "ttft_sec": server_ttft,
            "total_time_sec": res["total_time_sec"],
            "decode_tps": server_decode_tps,
            "mtp_acceptance_pct": mtp_rate,
            "quality_status": "PENDING REVIEW",
        }
        results.append((summary, res, prompt))

        print(f"  [OK] Completed in {res['total_time_sec']:.2f}s (TTFT: {server_ttft:.3f}s, Decode: {server_decode_tps:.1f} tok/s)")
        print(f"    Tokens: {actual_prompt_tokens:,} in + {thinking_tokens:,} think + {completion_tokens:,} out | MTP Accept: {mtp_rate:.1f}%")

    # Console Scorecard
    print("\n" + "=" * 90)
    print(f"{'Test Name':<36} | {'Prompt':<7} | {'Think':<6} | {'Out':<6} | {'TTFT':<5} | {'Tok/s':<5} | {'Scorecard'}")
    print("-" * 90)
    for s, _, _ in results:
        print(f"{s['test_name']:<36} | {s['prompt_tokens']:<7} | {s['thinking_tokens']:<6} | {s['completion_tokens']:<6} | {s['ttft_sec']:<4.2f}s | {s['decode_tps']:<5.1f} | [PENDING QUALITY REVIEW]")
    print("=" * 90)

    # Write Markdown Report
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"# NInfer Benchmark & Quality Report\n\n")
        f.write(f"- **Model ID:** `{model_id}`\n")
        f.write(f"- **Date & Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Temperature:** `{temp}`\n")
        f.write(f"- **Thinking Budget:** `{thinking_budget}` | **Max Tokens:** `{max_tokens}`\n")
        f.write(f"- **Overall Quality Status:** **`[PENDING QUALITY REVIEW]`**\n\n")
        f.write("## 1. Performance Scorecard\n\n")
        f.write("| Test | Prompt Tokens | Thinking Tokens | Out Tokens | TTFT (s) | Total Time (s) | Decode (tok/s) | MTP Accept | Quality Status |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for s, _, _ in results:
            f.write(f"| {s['test_name']} | {s['prompt_tokens']:,} | {s['thinking_tokens']:,} | {s['completion_tokens']:,} | {s['ttft_sec']:.2f} | {s['total_time_sec']:.2f} | {s['decode_tps']:.1f} | {s['mtp_acceptance_pct']:.1f}% | **`[PENDING QUALITY REVIEW]`** |\n")

        f.write("\n---\n## 2. Full Model Outputs (For Agent Quality Inspection)\n\n")
        for s, res, pr in results:
            f.write(f"### {s['test_name']}\n\n")
            f.write(f"#### Prompt Summary\n```text\n{pr[:400]}...\n```\n\n")
            if res.get("thinking_text"):
                f.write(f"#### Reasoning Trace (`<think>`)\n```text\n{res['thinking_text'].strip()}\n```\n\n")
            f.write(f"#### Final Output Response\n\n{res.get('answer_text') or res.get('full_text')}\n\n")
            f.write("\n---\n")

    print(f"\n[REPORT LOGGED] file:///{str(report_file).replace(chr(92), '/')}")
    print("Ready for quality review: you can ask the agent to inspect this report at any time.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NInfer Standalone Model Benchmark")
    parser.add_argument("--test", choices=["1", "2", "all", "short", "long"], default="all", help="Which test to run (1=short, 2=long, all=both)")
    parser.add_argument("--url", default=DEFAULT_URL, help="NInfer server base URL (default: http://127.0.0.1:8080)")
    parser.add_argument("--temp", type=float, default=1.0, help="Sampling temperature (default: 1.0)")
    parser.add_argument("--max-tokens", type=int, default=8192, help="Max total tokens (default: 8192)")
    parser.add_argument("--think-budget", type=int, default=2048, help="Thinking budget tokens (default: 2048)")
    args = parser.parse_args()

    run_benchmark(selected_test=args.test, base_url=args.url, temp=args.temp, max_tokens=args.max_tokens, thinking_budget=args.think_budget)
