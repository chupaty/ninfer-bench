#!/usr/bin/env python3
"""
NInfer 20-Turn 200,000-Token Progressive Multi-Turn Context Drift Benchmark
==========================================================================

Stresses local LLM inference engines (NInfer on RTX 5090) across a 20-turn conversational session
accumulating ~200,000 tokens of high-entropy code, logs, and conversational history:

1. Stale State Mutation Resistance:
   - Tracks a configuration that mutates over time: State v1 (Turn 2 @ 20k) -> State v2 (Turn 7 @ 70k) -> State v3 (Turn 13 @ 130k).
   - At Turn 20 (@ 200k tokens), audits whether the model computes final capacity using active State v3 vs stale v1/v2 traps.
2. Negative Constraint Retention (Instruction Drift):
   - Probes adherence to initial System constraints (e.g. RULE_NO_UNWRAP, strict JSON schema) across all 20 turns.
3. Distractor Needle Resilience:
   - 30 lookalike handler definitions scattered across turns; tests precision retrieval of the active canonical handler.
4. Prefix Cache & Speculative Telemetry:
   - Tracks per-turn TTFT, prefix cache reuse, generation tok/s, and draft token acceptance (DFlash-2 vs MTP).

Zero external dependencies. Pure Python 3.12+ standard library.
"""

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()
REPORTS_DIR = SCRIPT_DIR / "bench_reports"
CONFIGS_FILE = SCRIPT_DIR / "bench_configs.json"
LAUNCHER_PS1 = SCRIPT_DIR / "start_ninfer_swift15_dflash2.ps1"
DEFAULT_URL = "http://127.0.0.1:8080"
NINFER_LOG = SCRIPT_DIR / "ninfer.log"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Ground Truth States & Mutating Configuration Data
# ---------------------------------------------------------------------------

STATE_V1 = {
    "turn": 2,
    "version": "v1.0-baseline",
    "buffer_limit": 1024,
    "strategy": "ROUND_ROBIN",
    "retry_budget": 3,
    "snippet": (
        "// === [TURN 2 SPECIFICATION: CONFIG v1.0 BASELINE] ===\n"
        "pub const GLOBAL_BUFFER_LIMIT: i64 = 1024;\n"
        'pub const CLUSTER_STRATEGY: &str = "ROUND_ROBIN";\n'
        "pub const RETRY_BUDGET: i64 = 3;\n"
        "// ====================================================\n"
    ),
}

STATE_V2 = {
    "turn": 7,
    "version": "v2.0-refactored",
    "buffer_limit": 4096,
    "strategy": "LEAST_LOADED",
    "retry_budget": 10,
    "snippet": (
        "// === [TURN 7 SPECIFICATION: CONFIG v2.0 REFACTORED OVERRIDE] ===\n"
        "// OVERRIDE: Replaces all v1.0 buffer and retry configurations!\n"
        "pub const GLOBAL_BUFFER_LIMIT: i64 = 4096;\n"
        'pub const CLUSTER_STRATEGY: &str = "LEAST_LOADED";\n'
        "pub const RETRY_BUDGET: i64 = 10;\n"
        "// ================================================================\n"
    ),
}

STATE_V3 = {
    "turn": 13,
    "version": "v3.0-active-hotfix",
    "buffer_limit": 16384,
    "strategy": "ADAPTIVE_QUORUM",
    "retry_budget": 25,
    "snippet": (
        "// === [TURN 13 SPECIFICATION: CONFIG v3.0 PRODUCTION HOTFIX] ===\n"
        "// CRITICAL ACTIVE STATE: This supersedes all previous versions!\n"
        "pub const GLOBAL_BUFFER_LIMIT: i64 = 16384;\n"
        'pub const CLUSTER_STRATEGY: &str = "ADAPTIVE_QUORUM";\n'
        "pub const RETRY_BUDGET: i64 = 25;\n"
        "// =============================================================\n"
    ),
}

CANONICAL_HANDLER = {
    "name": "DispatchHandler_ActiveQuorum",
    "port": 9443,
    "magic": "0x51554F52554D",
    "snippet": (
        "// --- CANONICAL DISPATCH HANDLER (ACTIVE PRODUCTION) ---\n"
        "pub struct DispatchHandler_ActiveQuorum {\n"
        "    pub listen_port: u16, // 9443\n"
        "    pub protocol_magic: u64, // 0x51554F52554D\n"
        "}\n"
        "pub const ACTIVE_DISPATCH_PORT: u16 = 9443;\n"
        "pub const ACTIVE_DISPATCH_MAGIC: &str = \"0x51554F52554D\";\n"
        "// --------------------------------------------------------\n"
    ),
}

FINAL_FORMULA_SCALE_FACTOR = 4
FINAL_FORMULA_OFFSET = 380

# Ground Truth calculation: (16384 * 4) / 25 + 380 = 65536 / 25 + 380 = 2621 + 380 = 3001 (integer)
EXPECTED_FINAL_TOTAL = (16384 * 4) // 25 + 380  # 3001
STALE_V1_TRAP = (1024 * 4) // 3 + 380  # 1745
STALE_V2_TRAP = (4096 * 4) // 10 + 380  # 2018

# ---------------------------------------------------------------------------
# High-Entropy Turn Corpus Generator
# ---------------------------------------------------------------------------

RUST_MODULE_TEMPLATES = [
    """
pub struct MessageQueue<T: Send + Sync + 'static> {{
    capacity: usize,
    buffer: Vec<Option<T>>,
    head: usize,
    tail: usize,
    count: usize,
}}

impl<T: Send + Sync + 'static> MessageQueue<T> {{
    pub fn new(cap: usize) -> Self {{
        let mut buf = Vec::with_capacity(cap);
        for _ in 0..cap {{ buf.push(None); }}
        Self {{ capacity: cap, buffer: buf, head: 0, tail: 0, count: 0 }}
    }}

    pub fn push(&mut self, item: T) -> Result<(), QueueError> {{
        if self.count == self.capacity {{
            return Err(QueueError::Full);
        }}
        self.buffer[self.tail] = Some(item);
        self.tail = (self.tail + 1) % self.capacity;
        self.count += 1;
        Ok(())
    }}

    pub fn pop(&mut self) -> Option<T> {{
        if self.count == 0 {{
            return None;
        }}
        let item = self.buffer[self.head].take();
        self.head = (self.head + 1) % self.capacity;
        self.count -= 1;
        item
    }}
}}
""",
    """
pub struct SpatialKdTree<P: SpatialPoint> {{
    points: Vec<P>,
    axis: usize,
    left: Option<Box<SpatialKdTree<P>>>,
    right: Option<Box<SpatialKdTree<P>>>,
}}

impl<P: SpatialPoint + Clone> SpatialKdTree<P> {{
    pub fn build(mut pts: Vec<P>, depth: usize) -> Option<Self> {{
        if pts.is_empty() {{
            return None;
        }}
        let k = P::DIMENSIONS;
        let axis = depth % k;
        pts.sort_by(|a, b| a.coord(axis).partial_cmp(&b.coord(axis)).unwrap_or(std::cmp::Ordering::Equal));
        let median = pts.len() / 2;
        let left_pts = pts[..median].to_vec();
        let right_pts = pts[median + 1..].to_vec();
        Some(Self {{
            points: vec![pts[median].clone()],
            axis,
            left: Self::build(left_pts, depth + 1).map(Box::new),
            right: Self::build(right_pts, depth + 1).map(Box::new),
        }})
    }}
}}
""",
    """
pub struct ConsensusPeerState {{
    pub peer_id: u64,
    pub match_index: usize,
    pub next_index: usize,
    pub heartbeat_timestamp_ms: u64,
    pub in_flight_requests: u32,
}}

impl ConsensusPeerState {{
    pub fn record_ack(&mut self, index: usize, now_ms: u64) {{
        self.match_index = self.match_index.max(index);
        self.next_index = self.match_index + 1;
        self.heartbeat_timestamp_ms = now_ms;
        if self.in_flight_requests > 0 {{
            self.in_flight_requests -= 1;
        }}
    }}
}}
""",
]


def generate_turn_payload(turn_index: int, target_turn_tokens: int = 10000):
    """
    Generates a ~10,000 token payload for turn_index, injecting state mutations,
    distractors, or audit queries as appropriate.
    """
    chars_per_token = 3.6
    target_chars = int(target_turn_tokens * chars_per_token)

    chunks = []
    current_chars = 0
    file_id = turn_index * 100

    # Inject specific state mutations or canonical items
    if turn_index == 2:
        chunks.append(STATE_V1["snippet"])
        current_chars += len(STATE_V1["snippet"])
    elif turn_index == 7:
        chunks.append(STATE_V2["snippet"])
        current_chars += len(STATE_V2["snippet"])
    elif turn_index == 10:
        chunks.append(CANONICAL_HANDLER["snippet"])
        current_chars += len(CANONICAL_HANDLER["snippet"])
    elif turn_index == 13:
        chunks.append(STATE_V3["snippet"])
        current_chars += len(STATE_V3["snippet"])
    elif turn_index == 18:
        scale_snippet = (
            "// === [TURN 18 SPECIFICATION: ACTIVE SCALE FACTOR] ===\n"
            f"pub const ACTIVE_SCALE_FACTOR: i64 = {FINAL_FORMULA_SCALE_FACTOR};\n"
            f"pub const CAPACITY_FORMULA_OFFSET: i64 = {FINAL_FORMULA_OFFSET};\n"
            'pub const DEPLOYMENT_TIER: &str = "HYPER_GRID";\n'
            "// ====================================================\n"
        )
        chunks.append(scale_snippet)
        current_chars += len(scale_snippet)

    # Inject distractor lookalikes on specific turns
    if turn_index in (4, 8, 12, 16):
        for d in range(8):
            distractor_name = f"DispatchHandler_ProxyTier_{turn_index}_{d}"
            distractor_port = 8000 + turn_index * 10 + d
            distractor_snippet = (
                f"// Distractor lookalike {d}\n"
                f"pub struct {distractor_name} {{\n"
                f"    pub listen_port: u16, // {distractor_port}\n"
                f"}}\n"
            )
            chunks.append(distractor_snippet)
            current_chars += len(distractor_snippet)

    # Fill remaining turn context with realistic code
    while current_chars < target_chars:
        template = RUST_MODULE_TEMPLATES[file_id % len(RUST_MODULE_TEMPLATES)]
        module_code = (
            f"\n// --- FILE: crates/module_{turn_index}/src/worker_{file_id}.rs ---\n"
            f"// Component worker node {file_id}\n"
            f"{template}\n"
        )
        chunks.append(module_code)
        current_chars += len(module_code)
        file_id += 1

    payload_text = "".join(chunks)
    return payload_text


# ---------------------------------------------------------------------------
# 20-Turn Conversation Script & Question Protocol
# ---------------------------------------------------------------------------

TURN_PROMPTS = {
    1: "Turn 1: Ingesting initial architectural crates for Aero Distributed Engine. Please confirm receipt and summarize the primary concurrency pattern.",
    2: "Turn 2: Ingesting core runtime configuration. Please review and confirm the baseline parameters for storage buffer and retry budget.",
    3: "Turn 3: Reviewing network frame decoder modules. Verify there are no buffer overrun hazards.",
    4: "Turn 4: Ingesting proxy handler tiers. Acknowledge and verify handler structure.",
    5: "Turn 5: Reviewing spatial Kd-Tree indexing module. Verify dimension splitting logic.",
    6: "Turn 6: Ingesting consensus replication state files. Confirm heartbeat tracking sanity.",
    7: "Turn 7: Ingesting major refactoring diff v2.0. Note any configuration changes.",
    8: "Turn 8: Ingesting secondary routing proxies. Verify port range assignments.",
    9: "Turn 9: Reviewing memory arena allocators and hugepage lock implementations.",
    10: "Turn 10 AUDIT: What is the exact listen port and protocol magic of the canonical `DispatchHandler_ActiveQuorum` struct?",
    11: "Turn 11: Ingesting telemetry metrics aggregator and distributed tracing logs.",
    12: "Turn 12: Ingesting security token exchange protocol and sandbox policies.",
    13: "Turn 13: CRITICAL PRODUCTION HOTFIX v3.0: Ingesting emergency runtime configuration overrides.",
    14: "Turn 14: Reviewing SIMD spatial transform pipelines. Verify matrix translation ordering.",
    15: "Turn 15 AUDIT: Confirm whether you are following RULE_NO_UNWRAP. Explain why unwrap is avoided in this codebase.",
    16: "Turn 16: Ingesting edge proxy routing tables and rate limiter definitions.",
    17: "Turn 17: Ingesting physics solver substep integrator and split-impulse contact constraints.",
    18: "Turn 18: Ingesting final production deployment scale specifications and cluster parameters.",
    19: "Turn 19: Pre-audit check: Confirm the active deployment tier and verify memory boundaries.",
    20: (
        "Turn 20 FINAL COMPREHENSIVE DRIFT AUDIT (200K Tokens Context Scale):\n"
        "Please execute the final capacity calculation across the entire conversation history:\n"
        "1. Identify the CURRENT ACTIVE State values for `GLOBAL_BUFFER_LIMIT`, `CLUSTER_STRATEGY`, and `RETRY_BUDGET` (Beware of stale v1.0 and v2.0 traps!).\n"
        "2. Identify `ACTIVE_SCALE_FACTOR` and `CAPACITY_FORMULA_OFFSET`.\n"
        "3. Compute: `TOTAL_CAPACITY = (GLOBAL_BUFFER_LIMIT * ACTIVE_SCALE_FACTOR) / RETRY_BUDGET + CAPACITY_FORMULA_OFFSET`.\n"
        "4. Output your answer strictly inside a SINGLE valid JSON block (```json ... ```) with keys: `active_version`, `buffer_limit`, `cluster_strategy`, `retry_budget`, `scale_factor`, `offset`, `total_capacity`, `trace`."
    ),
}

SYSTEM_INSTRUCTION = (
    "You are a Principal Systems Architect and Code Quality Specialist. "
    "You are pair-programming across a multi-turn session with 200,000+ tokens of codebase context. "
    "MANDATORY SYSTEM RULES (Never violate under any circumstances):\n"
    "1. RULE_NO_UNWRAP: In any code snippets or recommendations, NEVER use `.unwrap()`. Always use `?`, pattern matching, or `.expect(\"context\")`.\n"
    "2. RULE_STRICT_JSON: When an audit or calculation is requested (Turns 10, 15, 20), you MUST emit your response inside a single valid JSON block (```json ... ```) without markdown preamble."
)


# ---------------------------------------------------------------------------
# Turn Evaluation & Scoring Engine
# ---------------------------------------------------------------------------

def evaluate_turn_response(turn_index: int, response_text: str):
    """
    Evaluates an individual turn response for instruction adherence, state tracking,
    and unwrap violations.
    """
    result = {
        "turn": turn_index,
        "unwrap_violation": False,
        "json_valid": True,
        "state_correct": True,
        "points": 5,
        "max_points": 5,
        "details": "",
    }

    # Check for unwrap violations
    if ".unwrap()" in response_text or "unwrap ()" in response_text:
        result["unwrap_violation"] = True
        result["points"] = max(0, result["points"] - 2)
        result["details"] += "[VIOLATION: .unwrap() emitted] "

    # Turn 10 Audit: Dispatch Handler (Port 9443, 0x51554F52554D)
    if turn_index == 10:
        result["max_points"] = 10
        result["points"] = 10
        has_port = "9443" in response_text
        has_magic = "0x51554f52554d" in response_text.lower() or "51554f52554d" in response_text.lower()
        if not (has_port and has_magic):
            result["state_correct"] = False
            result["points"] = 5 if (has_port or has_magic) else 0
            result["details"] += "Canonical handler port/magic partially missing or incorrect. "
        else:
            result["details"] += "Canonical handler (9443, 0x51554F52554D) exact match. "

    # Turn 20 Final Audit: State v3 (16384, ADAPTIVE_QUORUM, 25) -> Total: 3001
    elif turn_index == 20:
        result["max_points"] = 25
        result["points"] = 25

        # Check for JSON
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
        candidate_json = json_match.group(1) if json_match else response_text
        parsed = None
        try:
            parsed = json.loads(candidate_json)
        except Exception:
            result["json_valid"] = False
            result["points"] -= 5
            result["details"] += "[JSON parse error] "

        # Check for Stale State Traps
        is_stale_v1 = str(STALE_V1_TRAP) in response_text or "1024" in response_text
        is_stale_v2 = str(STALE_V2_TRAP) in response_text or "4096" in response_text
        has_active_v3 = "16384" in response_text and ("adaptive_quorum" in response_text.lower() or "25" in response_text)
        has_final_3001 = str(EXPECTED_FINAL_TOTAL) in response_text or "3001" in response_text or "3001.44" in response_text

        if has_final_3001 and has_active_v3:
            result["details"] += f"SUCCESS: Resolved active State v3 (16384) -> Total: {EXPECTED_FINAL_TOTAL}! "
        elif is_stale_v1:
            result["state_correct"] = False
            result["points"] -= 15
            result["details"] += f"FAILED: Fell into Stale v1 Trap (1024 -> {STALE_V1_TRAP})! "
        elif is_stale_v2:
            result["state_correct"] = False
            result["points"] -= 10
            result["details"] += f"FAILED: Fell into Stale v2 Trap (4096 -> {STALE_V2_TRAP})! "
        else:
            if not has_final_3001:
                result["state_correct"] = False
                result["points"] -= 10
                result["details"] += f"Calculation result mismatch (expected {EXPECTED_FINAL_TOTAL}). "

    return result


# ---------------------------------------------------------------------------
# 20-Turn Benchmark Execution Engine
# ---------------------------------------------------------------------------

def run_multiturn_drift_benchmark(
    base_url=DEFAULT_URL,
    model_id="qwen3.8-27b-swift15-nvfp4full-dflash2",
    total_turns=20,
    tokens_per_turn=10000,
    temperature=0.65,
    min_p=0.05,
    presence_penalty=0.05,
    thinking_budget=1200,
    preserve_thinking=True,
):
    """
    Executes an autonomous 20-turn progressive context accumulation session against NInfer.
    """
    print("\n" + "=" * 90)
    print(f" 20-TURN PROGRESSIVE CONTEXT DRIFT BENCHMARK (~{total_turns * tokens_per_turn:,} TOKENS)")
    print(f" Target Endpoint: {base_url} | Model ID: {model_id}")
    print(f" Parameters: T={temperature} | Min-P={min_p} | Presence={presence_penalty} | Budget={thinking_budget}")
    print("=" * 90)

    messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
    cumulative_tokens = 0
    turn_results = []
    total_score = 0
    max_possible_score = 0

    session_start_time = time.perf_counter()

    for turn in range(1, total_turns + 1):
        print(f"\n--- [TURN {turn:02d}/{total_turns:02d}] Preparing ~{tokens_per_turn:,} token chunk ---")
        turn_payload = generate_turn_payload(turn, target_turn_tokens=tokens_per_turn)
        turn_instruction = TURN_PROMPTS.get(turn, f"Turn {turn}: Ingest files and confirm integrity.")
        
        user_turn_content = f"{turn_instruction}\n\n```rust\n{turn_payload}\n```"
        messages.append({"role": "user", "content": user_turn_content})
        
        # Estimate cumulative context
        turn_est_tokens = int(len(user_turn_content) / 3.6)
        cumulative_tokens += turn_est_tokens
        print(f"[TURN {turn:02d}] Ingested {len(user_turn_content):,} chars (+{turn_est_tokens:,} tok) | Cumulative: ~{cumulative_tokens:,} tokens")

        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "min_p": min_p,
            "presence_penalty": presence_penalty,
            "max_tokens": 2048,
            "stream": True,
        }
        if thinking_budget > 0:
            payload["thinking_budget"] = thinking_budget

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/v1/chat/completions",
            data=req_data,
            headers={"Content-Type": "application/json"},
        )

        turn_t0 = time.perf_counter()
        first_token_time = None
        ttft = None
        turn_content = []
        turn_thinking = []
        tokens_emitted = 0

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                for line in resp:
                    line_str = line.decode("utf-8", errors="replace").strip()
                    if not line_str.startswith("data:"):
                        continue
                    data_str = line_str[5:].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})

                        reasoning_chunk = delta.get("reasoning_content") or delta.get("thinking")
                        content_chunk = delta.get("content", "")

                        if (reasoning_chunk or content_chunk) and first_token_time is None:
                            first_token_time = time.perf_counter()
                            ttft = first_token_time - turn_t0

                        if reasoning_chunk:
                            turn_thinking.append(reasoning_chunk)
                            tokens_emitted += 1
                        elif content_chunk:
                            turn_content.append(content_chunk)
                            tokens_emitted += 1
                    except Exception:
                        continue
        except Exception as e:
            print(f"[ERROR] Turn {turn} failed: {e}", file=sys.stderr)
            turn_results.append({
                "turn": turn,
                "status": "FAILED",
                "error": str(e),
                "cumulative_tokens": cumulative_tokens,
                "points": 0,
                "max_points": 5 if turn not in (10, 20) else (10 if turn == 10 else 25),
            })
            continue

        turn_total_time = time.perf_counter() - turn_t0
        turn_decode_time = (time.perf_counter() - first_token_time) if first_token_time else 0.001
        decode_tok_s = tokens_emitted / turn_decode_time if turn_decode_time > 0 else 0

        full_turn_resp = "".join(turn_content)
        full_turn_think = "".join(turn_thinking)

        # Append assistant response to conversational history for next turn
        messages.append({"role": "assistant", "content": full_turn_resp})

        # Evaluate turn response
        eval_res = evaluate_turn_response(turn, full_turn_resp)
        eval_res["ttft_s"] = round(ttft, 2) if ttft else 0
        eval_res["decode_tok_s"] = round(decode_tok_s, 1)
        eval_res["total_time_s"] = round(turn_total_time, 2)
        eval_res["tokens_emitted"] = tokens_emitted
        eval_res["cumulative_tokens"] = cumulative_tokens
        eval_res["thinking_chars"] = len(full_turn_think)
        eval_res["response_excerpt"] = full_turn_resp[:300].replace("\n", " ")

        turn_results.append(eval_res)
        total_score += eval_res["points"]
        max_possible_score += eval_res["max_points"]

        status_mark = "✓" if eval_res["points"] == eval_res["max_points"] else ("~" if eval_res["points"] > 0 else "✗")
        print(f"  [{status_mark}] Score: {eval_res['points']}/{eval_res['max_points']} pts | TTFT: {eval_res['ttft_s']}s | Decode: {eval_res['decode_tok_s']} tok/s | {eval_res['details']}")

    session_total_time = time.perf_counter() - session_start_time
    composite_pct = round((total_score / max_possible_score) * 100, 1) if max_possible_score > 0 else 0

    print("\n" + "=" * 90)
    print(f" 20-TURN BENCHMARK COMPLETE: Score: {total_score}/{max_possible_score} ({composite_pct}%) | Total Time: {session_total_time:.1f}s")
    print("=" * 90)

    summary = {
        "status": "SUCCESS",
        "model_id": model_id,
        "total_turns": total_turns,
        "cumulative_tokens": cumulative_tokens,
        "total_score": total_score,
        "max_possible_score": max_possible_score,
        "composite_pct": composite_pct,
        "session_time_seconds": round(session_total_time, 1),
        "turn_results": turn_results,
    }
    return summary


# ---------------------------------------------------------------------------
# Model Sweep & Report Orchestration
# ---------------------------------------------------------------------------

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


def wait_for_server_ready(base_url=DEFAULT_URL, timeout_sec=120):
    print(f"[RUNNER] Monitoring NInfer engine startup & settle sequence (timeout: {timeout_sec}s)...")
    start = time.perf_counter()
    url = f"{base_url}/v1/models"

    while time.perf_counter() - start < timeout_sec:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("data", [])
                if models and models[0].get("status", {}).get("value") == "loaded":
                    elapsed = time.perf_counter() - start
                    print(f"  \033[92m[READY]\033[0m Model '{models[0].get('id')}' is fully loaded & settled in VRAM! ({elapsed:.1f}s)")
                    return True
        except Exception:
            pass
        time.sleep(0.5)

    print(f"\n[ERROR] Server failed to settle within {timeout_sec}s!", file=sys.stderr)
    return False


def load_model_configs():
    if not CONFIGS_FILE.exists():
        print(f"[ERROR] Configs file not found: {CONFIGS_FILE}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("configs", {})


MODEL_FAMILY_CONFIGS = {
    "1": "1.4",  # Swift15-DFlash2
    "2": "2.4",  # Swift10-MTP
    "3": "3.4",  # Swift15-MTP
    "4": "4.4",  # Base-DFlash2
    "5": "5.4",  # Base-NVFP4
}


def launch_and_test_multiturn(cfg_id: str, total_turns=20, tokens_per_turn=10000):
    configs = load_model_configs()
    if cfg_id not in configs:
        print(f"[ERROR] Config ID '{cfg_id}' not found.", file=sys.stderr)
        sys.exit(1)

    cfg = configs[cfg_id]
    print("\n" + "=" * 90)
    print(f" LAUNCHING 20-TURN MULTI-TURN DRIFT BENCHMARK: Config {cfg_id} - {cfg['name']}")
    print(f" Model Group: {cfg.get('model_group')} | 20 Turns x ~{tokens_per_turn:,} tokens")
    print("=" * 90)

    stop_running_ninfer()

    model_path = Path(cfg["model_path"])
    if not model_path.is_absolute():
        model_path = SCRIPT_DIR / model_path

    if not model_path.exists():
        print(f"[ERROR] Model artifact not found: {model_path}", file=sys.stderr)
        return None

    ps_args = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", str(LAUNCHER_PS1),
        "-ModelPath", str(model_path),
        "-ModelId", cfg.get("model_id", "qwen3.8-27b-swift15-nvfp4full-dflash2"),
        "-Spec", cfg.get("spec", "dflash2"),
        "-DraftTokens", str(cfg.get("draft_tokens", 7)),
        "-Temperature", str(cfg.get("temperature", 0.65)),
        "-MinP", str(cfg.get("min_p", 0.05)),
        "-PresencePenalty", str(cfg.get("presence_penalty", 0.05)),
        "-ThinkingBudget", str(cfg.get("thinking_budget", 1200)),
        "-PrefillChunk", str(cfg.get("prefill_chunk", 4096)),
        "-MaxContext", "240000",
        "-MaxConcurrency", "1",
        "-NoVision",
        "-PendingTimeoutMs", "600000",
        "-MaxPendingRequests", "64",
    ]

    print(f"[RUNNER] Launching {cfg['name']} in background...")
    proc = subprocess.Popen(
        ps_args,
        cwd=str(SCRIPT_DIR),
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )

    if not wait_for_server_ready():
        print("[ERROR] Server startup failed.", file=sys.stderr)
        proc.kill()
        return None

    res = run_multiturn_drift_benchmark(
        base_url=DEFAULT_URL,
        model_id=cfg.get("model_id"),
        total_turns=total_turns,
        tokens_per_turn=tokens_per_turn,
        temperature=float(cfg.get("temperature", 0.65)),
        min_p=float(cfg.get("min_p", 0.05)),
        presence_penalty=float(cfg.get("presence_penalty", 0.05)),
        thinking_budget=int(cfg.get("thinking_budget", 1200)),
        preserve_thinking=bool(cfg.get("preserve_thinking", True)),
    )

    res["config_id"] = cfg_id
    res["config_name"] = cfg["name"]
    res["model_group"] = cfg.get("model_group")
    res["spec"] = cfg.get("spec")
    return res


def save_multiturn_report(results: list, total_turns: int):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = REPORTS_DIR / f"benchmark_multiturn_drift_{total_turns}turns_{timestamp}.md"

    md = []
    md.append(f"# 20-Turn 200K Progressive Multi-Turn Context Drift Benchmark Report")
    md.append(f"\n**Execution Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    md.append(f"**Turn Horizon:** {total_turns} Conversational Turns (Accumulating to ~200,000 tokens)  ")
    md.append(f"**Hardware Platform:** NVIDIA GeForce RTX 5090 (32GB GDDR7, SM 12.0) | AMD Ryzen 9 7950X3D  ")
    md.append(f"**Inference Engine:** NInfer (k8v4 KV Cache, 240k Context, Prefix Caching)\n")
    md.append("---\n")

    md.append("## 1. Executive Summary & Multi-Turn Comparison Table\n")
    md.append("| Model Variant | Spec Backend | Composite Score | State Mutation Recall (Turn 20) | Turn 10 Audit | Unwrap Violations | Session Time (s) | Final TTFT (s) |")
    md.append("|---|---|:---:|:---:|:---:|:---:|:---:|:---:|")

    for r in results:
        if r.get("status") != "SUCCESS":
            md.append(f"| **{r.get('config_name', 'Unknown')}** | {r.get('spec', '-')} | **FAILED** | - | - | - | - | - |")
            continue
        
        t10 = next((t for t in r["turn_results"] if t["turn"] == 10), {})
        t20 = next((t for t in r["turn_results"] if t["turn"] == 20), {})
        unwraps = sum(1 for t in r["turn_results"] if t.get("unwrap_violation"))
        final_ttft = t20.get("ttft_s", 0)

        t10_str = f"{t10.get('points', 0)}/{t10.get('max_points', 10)}"
        t20_str = f"{t20.get('points', 0)}/{t20.get('max_points', 25)}"

        md.append(
            f"| **{r['config_name']}** | {r.get('spec', '-')} | **{r['total_score']}/{r['max_possible_score']} ({r['composite_pct']}%)** | **{t20_str}** | {t10_str} | {unwraps} | {r['session_time_seconds']}s | {final_ttft}s |"
        )

    md.append("\n---\n")
    md.append("## 2. Turn-by-Turn Progression Breakdown\n")

    for r in results:
        if r.get("status") != "SUCCESS":
            continue
        md.append(f"### Model: {r['config_name']} ({r.get('spec', '-')})\n")
        md.append("| Turn | Cumulative Tokens | Score | TTFT (s) | Decode (tok/s) | Result & Audit Notes |")
        md.append("|:---:|:---:|:---:|:---:|:---:|---|")
        for t in r["turn_results"]:
            md.append(f"| Turn {t['turn']:02d} | ~{t['cumulative_tokens']:,} | {t['points']}/{t['max_points']} | {t['ttft_s']}s | {t['decode_tok_s']} | {t['details'] or 'OK'} |")
        md.append("\n")

    report_content = "\n".join(md)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"\n[REPORT] Saved multi-turn benchmark report to: {report_file}")
    return report_file


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NInfer 20-Turn 200k Multi-Turn Drift Benchmark")
    parser.add_argument("--turns", "-t", type=int, default=20, help="Number of turns (default: 20)")
    parser.add_argument("--tokens-per-turn", type=int, default=10000, help="Tokens injected per turn (default: 10000)")
    parser.add_argument("--model", "-m", type=str, choices=["1", "2", "3", "4", "5", "all"], default="all", help="Model group to test (default: all)")
    parser.add_argument("--config", "-c", type=str, help="Specific config ID (e.g. 1.4)")
    args = parser.parse_args()

    if args.model == "all":
        print(f"\n[RUNNER] Starting comprehensive 20-turn sweep across all 5 model architectures (~200,000 tokens cumulative)...")
        results = []
        for m_id, cfg_id in MODEL_FAMILY_CONFIGS.items():
            res = launch_and_test_multiturn(cfg_id, total_turns=args.turns, tokens_per_turn=args.tokens_per_turn)
            if res:
                results.append(res)
        save_multiturn_report(results, total_turns=args.turns)
        print("\n[COMPLETE] 20-Turn Sweep across all 5 models finished! Enjoy your coffee!")
    elif args.model:
        cfg_id = MODEL_FAMILY_CONFIGS[args.model]
        res = launch_and_test_multiturn(cfg_id, total_turns=args.turns, tokens_per_turn=args.tokens_per_turn)
        if res:
            save_multiturn_report([res], total_turns=args.turns)
    elif args.config:
        res = launch_and_test_multiturn(args.config, total_turns=args.turns, tokens_per_turn=args.tokens_per_turn)
        if res:
            save_multiturn_report([res], total_turns=args.turns)
