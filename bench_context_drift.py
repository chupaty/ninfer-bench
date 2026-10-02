#!/usr/bin/env python3
"""
NInfer 200,000-Token Context Drift & Needle Degradation Benchmark
================================================================

Evaluates local LLM inference engines (NInfer on RTX 5090) at extreme context scale (~200,000 tokens):
1. Verbatim Needle-in-a-Haystack (M-NIAH) across 5 precision depth tiers (10%, 30%, 50%, 75%, 92%).
2. Interlocking Multi-Hop Reasoning & Synthesis Chain across context depths (15% -> 52% -> 88%).
3. Instruction & Schema Drift Adherence under extreme context (Strict JSON output).
4. Telemetry: TTFT, Prefill tok/s, Decode tok/s, Thinking tokens, and Speculative Decoding efficiency.

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
# Sentinel Definitions & Ground Truth Data
# ---------------------------------------------------------------------------

SENTINELS = {
    "alpha": {
        "depth_target": 0.10,
        "name": "Sentinel Alpha (Auth & Security Policy)",
        "token": "0x9F4C2A18E6B70D31",
        "policy": "STRICT_ISOLATED_SANDBOX",
        "file": "crates/aero_security/src/auth_policy.rs",
        "snippet": (
            "// --- CRITICAL SENTINEL ALPHA CONFIGURATION ---\n"
            'pub const SECURITY_TOKEN_ALPHA: &str = "0x9F4C2A18E6B70D31";\n'
            'pub const AUDIT_POLICY_ALPHA: &str = "STRICT_ISOLATED_SANDBOX";\n'
            "// -----------------------------------------------\n"
        ),
    },
    "beta": {
        "depth_target": 0.30,
        "name": "Sentinel Beta (Storage Shard Partition)",
        "key": "shard_region_apac_central_9",
        "isolation": "SERIALIZABLE_SNAPSHOT",
        "file": "crates/aero_storage/src/sharding.rs",
        "snippet": (
            "// --- CRITICAL SENTINEL BETA CONFIGURATION ---\n"
            'pub const DB_ROUTING_KEY_BETA: &str = "shard_region_apac_central_9";\n'
            'pub const ISOLATION_LEVEL_BETA: &str = "SERIALIZABLE_SNAPSHOT";\n'
            "// -----------------------------------------------\n"
        ),
    },
    "gamma": {
        "depth_target": 0.50,
        "name": "Sentinel Gamma (Memory HugePage Allocator)",
        "alignment_bytes": 16384,
        "strategy": "BUMP_HUGEPAGE_LOCK",
        "file": "crates/aero_memory/src/hugepage_arena.rs",
        "snippet": (
            "// --- CRITICAL SENTINEL GAMMA CONFIGURATION ---\n"
            "pub const ALLOC_ALIGNMENT_BYTES_GAMMA: u32 = 16384;\n"
            'pub const ARENA_STRATEGY_GAMMA: &str = "BUMP_HUGEPAGE_LOCK";\n'
            "// -----------------------------------------------\n"
        ),
    },
    "delta": {
        "depth_target": 0.75,
        "name": "Sentinel Delta (High-Speed RPC Protocol)",
        "magic": "0x5357494654",
        "timeout_ms": 4500,
        "file": "crates/aero_net/src/handshake.rs",
        "snippet": (
            "// --- CRITICAL SENTINEL DELTA CONFIGURATION ---\n"
            "pub const RPC_HANDSHAKE_MAGIC_DELTA: u64 = 0x5357494654;\n"
            "pub const HANDSHAKE_TIMEOUT_MS_DELTA: u32 = 4500;\n"
            "// -----------------------------------------------\n"
        ),
    },
    "epsilon": {
        "depth_target": 0.92,
        "name": "Sentinel Epsilon (Physics Substep Integrator)",
        "substeps": 128,
        "constraint": "PENALTY_IMPULSE_SPLIT",
        "file": "crates/aero_physics/src/solver_substep.rs",
        "snippet": (
            "// --- CRITICAL SENTINEL EPSILON CONFIGURATION ---\n"
            "pub const SOLVER_MAX_SUBSTEPS_EPSILON: u32 = 128;\n"
            'pub const CONSTRAINT_ALGORITHM_EPSILON: &str = "PENALTY_IMPULSE_SPLIT";\n'
            "// -------------------------------------------------\n"
        ),
    },
}

# Multi-Hop Interlocking Reasoning Chain
MULTIHOP_CHAIN = {
    "hop1": {
        "depth_target": 0.15,
        "file": "crates/aero_cluster/src/capacity.rs",
        "snippet": (
            "// === MULTI-HOP SYNTHESIS HOP 1 ===\n"
            "pub const GLOBAL_CAPACITY_BASE: i64 = 2400;\n"
            "pub const UNIT_WEIGHT_DIVISOR: i64 = 3;\n"
            "// =================================\n"
        ),
    },
    "hop2": {
        "depth_target": 0.52,
        "file": "crates/aero_cluster/src/rule_engine.rs",
        "snippet": (
            "// === MULTI-HOP SYNTHESIS HOP 2 ===\n"
            "pub const TIER_SCALE_MULTIPLIER_HYPER: i64 = 4;\n"
            "pub const UNIT_WEIGHT_DISCOUNT: i64 = 1;\n"
            "// =================================\n"
        ),
    },
    "hop3": {
        "depth_target": 0.88,
        "file": "crates/aero_cluster/src/deployment.rs",
        "snippet": (
            "// === MULTI-HOP SYNTHESIS HOP 3 ===\n"
            'pub const ACTIVE_TIER: &str = "HYPER_SCALE";\n'
            "pub const BUFFER_HEADROOM: i64 = 650;\n"
            "// =================================\n"
        ),
    },
    "ground_truth": {
        "active_tier": "HYPER_SCALE",
        "base_capacity": 2400,
        "tier_multiplier": 4,
        "weight_divisor": 3,
        "weight_discount": 1,
        "effective_divisor": 2,  # 3 - 1
        "headroom": 650,
        # Formula: (2400 * 4) / (3 - 1) + 650 = 9600 / 2 + 650 = 4800 + 650 = 5450
        "expected_result": 5450,
    },
}

# ---------------------------------------------------------------------------
# High-Entropy Codebase Generation Engine
# ---------------------------------------------------------------------------

CODE_BLOCK_TEMPLATES = [
    # Template A: Raft Consensus & Actor Messages
    """
pub struct RaftNode<S: StorageBackend, N: NetworkTransport> {{
    node_id: u64,
    current_term: u64,
    voted_for: Option<u64>,
    log: Vec<LogEntry>,
    commit_index: usize,
    last_applied: usize,
    state: NodeRole,
    storage: S,
    transport: N,
}}

impl<S: StorageBackend, N: NetworkTransport> RaftNode<S, N> {{
    pub async fn handle_append_entries(&mut self, req: AppendEntriesRequest) -> Result<AppendEntriesResponse, RaftError> {{
        if req.term < self.current_term {{
            return Ok(AppendEntriesResponse {{ term: self.current_term, success: false }});
        }}
        if req.term > self.current_term {{
            self.current_term = req.term;
            self.state = NodeRole::Follower;
            self.voted_for = None;
        }}
        if req.prev_log_index > 0 {{
            if let Some(entry) = self.log.get(req.prev_log_index - 1) {{
                if entry.term != req.prev_log_term {{
                    return Ok(AppendEntriesResponse {{ term: self.current_term, success: false }});
                }}
            }} else {{
                return Ok(AppendEntriesResponse {{ term: self.current_term, success: false }});
            }}
        }}
        for (i, entry) in req.entries.into_iter().enumerate() {{
            let target_idx = req.prev_log_index + i;
            if target_idx < self.log.len() {{
                self.log[target_idx] = entry;
            }} else {{
                self.log.push(entry);
            }}
        }}
        if req.leader_commit > self.commit_index {{
            self.commit_index = req.leader_commit.min(self.log.len());
        }}
        Ok(AppendEntriesResponse {{ term: self.current_term, success: true }})
    }}
}}
""",
    # Template B: SIMD Spatial Matrix Math
    """
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Transform3D {{
    pub position: [f32; 3],
    pub rotation: [f32; 4],
    pub scale: [f32; 3],
}}

impl Transform3D {{
    #[inline(always)]
    pub fn to_matrix_simd(&self) -> [f32; 16] {{
        let (qx, qy, qz, qw) = (self.rotation[0], self.rotation[1], self.rotation[2], self.rotation[3]);
        let (sx, sy, sz) = (self.scale[0], self.scale[1], self.scale[2]);
        let (tx, ty, tz) = (self.position[0], self.position[1], self.position[2]);

        let x2 = qx + qx; let y2 = qy + qy; let z2 = qz + qz;
        let xx = qx * x2; let xy = qx * y2; let xz = qx * z2;
        let yy = qy * y2; let yz = qy * z2; let zz = qz * z2;
        let wx = qw * x2; let wy = qw * y2; let wz = qw * z2;

        [
            (1.0 - (yy + zz)) * sx, (xy + wz) * sx, (xz - wy) * sx, 0.0,
            (xy - wz) * sy, (1.0 - (xx + zz)) * sy, (yz + wx) * sy, 0.0,
            (xz + wy) * sz, (yz - wx) * sz, (1.0 - (xx + yy)) * sz, 0.0,
            tx, ty, tz, 1.0,
        ]
    }}
}}
""",
    # Template C: Async Connection Multiplexer & Frame Parser
    """
pub struct FrameDecoder {{
    buffer: Vec<u8>,
    max_frame_size: usize,
}}

impl FrameDecoder {{
    pub fn new(max_size: usize) -> Self {{
        Self {{ buffer: Vec::with_capacity(65536), max_frame_size: max_size }}
    }}

    pub fn decode_next(&mut self) -> Result<Option<Frame>, FrameError> {{
        if self.buffer.len() < 8 {{
            return Ok(None);
        }}
        let magic = u32::from_be_bytes([self.buffer[0], self.buffer[1], self.buffer[2], self.buffer[3]]);
        if magic != 0x4145524F {{
            return Err(FrameError::InvalidMagic(magic));
        }}
        let length = u32::from_be_bytes([self.buffer[4], self.buffer[5], self.buffer[6], self.buffer[7]]) as usize;
        if length > self.max_frame_size {{
            return Err(FrameError::FrameTooLarge(length));
        }}
        if self.buffer.len() < 8 + length {{
            return Ok(None);
        }}
        let payload = self.buffer[8..8 + length].to_vec();
        self.buffer.drain(0..8 + length);
        Ok(Some(Frame {{ length, payload }}))
    }}
}}
""",
    # Template D: Persistent B-Tree Storage Node
    """
pub struct BTreeNode<K: Ord + Clone, V: Clone> {{
    keys: Vec<K>,
    values: Vec<V>,
    children: Vec<u64>,
    is_leaf: bool,
    node_id: u64,
}}

impl<K: Ord + Clone, V: Clone> BTreeNode<K, V> {{
    pub fn split_child(&mut self, index: usize, child: &mut BTreeNode<K, V>, degree: usize) -> BTreeNode<K, V> {{
        let mut sibling = BTreeNode {{
            keys: child.keys.split_off(degree),
            values: child.values.split_off(degree),
            children: if child.is_leaf {{ Vec::new() }} else {{ child.children.split_off(degree) }},
            is_leaf: child.is_leaf,
            node_id: child.node_id + 1000,
        }};
        let median_key = child.keys.pop().unwrap();
        let median_value = child.values.pop().unwrap();
        self.keys.insert(index, median_key);
        self.values.insert(index, median_value);
        self.children.insert(index + 1, sibling.node_id);
        sibling
    }}
}}
""",
]


def generate_codebase_corpus(target_tokens=200000):
    """
    Generates a realistic, multi-crate Rust workspace corpus calibrated to ~target_tokens.
    Injects the 5 Sentinels and 3 Multi-Hop Chain steps at precise target depth ratios.
    """
    # Character to token ratio calibrated for Qwen tokenizer on Rust code (~3.6 chars/token)
    chars_per_token = 3.6
    total_target_chars = int(target_tokens * chars_per_token)

    # Calculate target character positions for injections
    injections = []
    for key, s in SENTINELS.items():
        pos = int(total_target_chars * s["depth_target"])
        injections.append((pos, f"\n// --- FILE: {s['file']} ---\n" + s["snippet"]))

    for key, h in MULTIHOP_CHAIN.items():
        if key == "ground_truth":
            continue
        pos = int(total_target_chars * h["depth_target"])
        injections.append((pos, f"\n// --- FILE: {h['file']} ---\n" + h["snippet"]))

    # Sort injections by position
    injections.sort(key=lambda x: x[0])

    corpus_chunks = []
    current_chars = 0
    injection_idx = 0
    file_counter = 1
    tmpl_idx = 0

    while current_chars < total_target_chars:
        # Check if we should inject a sentinel or multihop step
        if injection_idx < len(injections) and current_chars >= injections[injection_idx][0]:
            _, snippet = injections[injection_idx]
            corpus_chunks.append(snippet)
            current_chars += len(snippet)
            injection_idx += 1
            continue

        # Add a simulated module file
        crate_name = f"aero_module_{file_counter % 20}"
        file_name = f"crates/{crate_name}/src/worker_{file_counter}.rs"
        template = CODE_BLOCK_TEMPLATES[tmpl_idx % len(CODE_BLOCK_TEMPLATES)]
        tmpl_idx += 1

        chunk = (
            f"\n// --- FILE: {file_name} ---\n"
            f"// Module iteration {file_counter} - Aero Distributed Engine\n"
            f"{template}\n"
        )
        corpus_chunks.append(chunk)
        current_chars += len(chunk)
        file_counter += 1

    # Flush any remaining injections
    while injection_idx < len(injections):
        _, snippet = injections[injection_idx]
        corpus_chunks.append(snippet)
        current_chars += len(snippet)
        injection_idx += 1

    full_context = "".join(corpus_chunks)
    estimated_tokens = int(len(full_context) / chars_per_token)
    return full_context, estimated_tokens


def build_benchmark_prompt(target_tokens=200000):
    """
    Constructs the complete 200,000 token prompt with explicit questions,
    retrieval targets, multi-hop reasoning requirements, and strict JSON schema.
    """
    context_text, est_tokens = generate_codebase_corpus(target_tokens=target_tokens)

    system_message = (
        "You are an expert Systems Architect and Code Audit Specialist. "
        "You have ingested the entire source tree of the Aero Distributed Engine. "
        "You must analyze the codebase, retrieve exact configuration sentinels placed across the modules, "
        "and execute a multi-hop cluster capacity calculation without hallucination."
    )

    user_query = f"""Below is the complete source code and configuration archive of the Aero Distributed Engine workspace ({est_tokens:,} tokens):

{context_text}

================================================================================
AUDIT INSTRUCTIONS & REASONING TASKS (200K CONTEXT DRIFT BENCHMARK)
================================================================================

Please perform the following audit tasks across the codebase you just ingested:

Task 1: Retrieve all 5 Sentinel configurations placed throughout the crates:
  - Alpha (Depth ~10%): `SECURITY_TOKEN_ALPHA` and `AUDIT_POLICY_ALPHA` in security module.
  - Beta (Depth ~30%): `DB_ROUTING_KEY_BETA` and `ISOLATION_LEVEL_BETA` in storage sharding module.
  - Gamma (Depth ~50%): `ALLOC_ALIGNMENT_BYTES_GAMMA` and `ARENA_STRATEGY_GAMMA` in memory arena module.
  - Delta (Depth ~75%): `RPC_HANDSHAKE_MAGIC_DELTA` and `HANDSHAKE_TIMEOUT_MS_DELTA` in network handshake module.
  - Epsilon (Depth ~92%): `SOLVER_MAX_SUBSTEPS_EPSILON` and `CONSTRAINT_ALGORITHM_EPSILON` in physics module.

Task 2: Multi-Hop Interlocking Capacity Synthesis:
  - Locate `GLOBAL_CAPACITY_BASE` and `UNIT_WEIGHT_DIVISOR` in `capacity.rs`.
  - Locate `TIER_SCALE_MULTIPLIER_HYPER` and `UNIT_WEIGHT_DISCOUNT` in `rule_engine.rs`.
  - Locate `ACTIVE_TIER` and `BUFFER_HEADROOM` in `deployment.rs`.
  - Apply the cluster capacity formula:
    `TOTAL_EFFECTIVE_CAPACITY = (GLOBAL_CAPACITY_BASE * TIER_SCALE_MULTIPLIER_HYPER) / (UNIT_WEIGHT_DIVISOR - UNIT_WEIGHT_DISCOUNT) + BUFFER_HEADROOM`
  - Show the arithmetic resolution and calculate the exact integer total.

Task 3: Output Formatting:
You MUST emit your final answer inside a SINGLE valid JSON codeblock (```json ... ```) with EXACTLY the following structure:

```json
{{
  "sentinels": {{
    "alpha": {{
      "token": "<string>",
      "policy": "<string>"
    }},
    "beta": {{
      "routing_key": "<string>",
      "isolation": "<string>"
    }},
    "gamma": {{
      "alignment_bytes": <integer>,
      "strategy": "<string>"
    }},
    "delta": {{
      "magic": "<string or hex>",
      "timeout_ms": <integer>
    }},
    "epsilon": {{
      "substeps": <integer>,
      "constraint": "<string>"
    }}
  }},
  "multihop_calculation": {{
    "active_tier": "<string>",
    "base_capacity": <integer>,
    "tier_multiplier": <integer>,
    "weight_divisor": <integer>,
    "weight_discount": <integer>,
    "effective_divisor": <integer>,
    "headroom": <integer>,
    "calculated_total": <integer>,
    "resolution_trace": "<explanation of math step>"
  }}
}}
```
"""
    return system_message, user_query, est_tokens


# ---------------------------------------------------------------------------
# Evaluator & Scoring Engine
# ---------------------------------------------------------------------------

def evaluate_response(response_text: str):
    """
    Evaluates the model's output against ground truth sentinels, multi-hop reasoning,
    and schema compliance. Returns a detailed scorecard and composite score (0 to 100).
    """
    scores = {
        "retrieval": {
            "alpha": {"points": 0, "max": 10, "details": ""},
            "beta": {"points": 0, "max": 10, "details": ""},
            "gamma": {"points": 0, "max": 10, "details": ""},
            "delta": {"points": 0, "max": 10, "details": ""},
            "epsilon": {"points": 0, "max": 10, "details": ""},
            "total": 0,
            "max": 50,
        },
        "multihop": {
            "active_tier": {"points": 0, "max": 5, "details": ""},
            "components": {"points": 0, "max": 10, "details": ""},
            "math_step": {"points": 0, "max": 5, "details": ""},
            "final_result": {"points": 0, "max": 15, "details": ""},
            "total": 0,
            "max": 35,
        },
        "schema": {
            "valid_json": {"points": 0, "max": 10, "details": ""},
            "key_completeness": {"points": 0, "max": 5, "details": ""},
            "total": 0,
            "max": 15,
        },
        "total_quality_score": 0,
    }

    # 1. Parse JSON
    parsed_json = None
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
    candidate_json = json_match.group(1) if json_match else response_text

    try:
        parsed_json = json.loads(candidate_json)
        scores["schema"]["valid_json"]["points"] = 10
        scores["schema"]["valid_json"]["details"] = "JSON successfully parsed."
    except Exception:
        # Fallback: find any { ... } block
        brace_match = re.search(r"(\{[\s\S]*\})", response_text)
        if brace_match:
            try:
                parsed_json = json.loads(brace_match.group(1))
                scores["schema"]["valid_json"]["points"] = 7
                scores["schema"]["valid_json"]["details"] = "Parsed fallback JSON block with minor wrapping issues."
            except Exception as e:
                scores["schema"]["valid_json"]["details"] = f"Failed to parse JSON: {e}"
        else:
            scores["schema"]["valid_json"]["details"] = "No JSON object found."

    # 2. Score Retrieval Sentinels
    s_alpha = SENTINELS["alpha"]
    s_beta = SENTINELS["beta"]
    s_gamma = SENTINELS["gamma"]
    s_delta = SENTINELS["delta"]
    s_epsilon = SENTINELS["epsilon"]

    text_lower = response_text.lower()

    # Alpha (10%)
    alpha_data = parsed_json.get("sentinels", {}).get("alpha", {}) if parsed_json else {}
    alpha_token = str(alpha_data.get("token", "")).lower()
    alpha_policy = str(alpha_data.get("policy", "")).lower()
    if "0x9f4c2a18e6b70d31" in alpha_token or "0x9f4c2a18e6b70d31" in text_lower:
        pts = 5
        if "strict_isolated_sandbox" in alpha_policy or "strict_isolated_sandbox" in text_lower:
            pts = 10
        scores["retrieval"]["alpha"]["points"] = pts
        scores["retrieval"]["alpha"]["details"] = f"Alpha match ({pts}/10 pts)"
    else:
        scores["retrieval"]["alpha"]["details"] = "Alpha token missing or incorrect"

    # Beta (30%)
    beta_data = parsed_json.get("sentinels", {}).get("beta", {}) if parsed_json else {}
    beta_key = str(beta_data.get("routing_key", "")).lower()
    beta_iso = str(beta_data.get("isolation", "")).lower()
    if "shard_region_apac_central_9" in beta_key or "shard_region_apac_central_9" in text_lower:
        pts = 5
        if "serializable_snapshot" in beta_iso or "serializable_snapshot" in text_lower:
            pts = 10
        scores["retrieval"]["beta"]["points"] = pts
        scores["retrieval"]["beta"]["details"] = f"Beta match ({pts}/10 pts)"
    else:
        scores["retrieval"]["beta"]["details"] = "Beta key missing or incorrect"

    # Gamma (50% - Lost in Middle)
    gamma_data = parsed_json.get("sentinels", {}).get("gamma", {}) if parsed_json else {}
    gamma_align = str(gamma_data.get("alignment_bytes", ""))
    gamma_strat = str(gamma_data.get("strategy", "")).lower()
    if "16384" in gamma_align or "16384" in response_text:
        pts = 5
        if "bump_hugepage_lock" in gamma_strat or "bump_hugepage_lock" in text_lower:
            pts = 10
        scores["retrieval"]["gamma"]["points"] = pts
        scores["retrieval"]["gamma"]["details"] = f"Gamma match ({pts}/10 pts)"
    else:
        scores["retrieval"]["gamma"]["details"] = "Gamma alignment (16384) missing or incorrect"

    # Delta (75%)
    delta_data = parsed_json.get("sentinels", {}).get("delta", {}) if parsed_json else {}
    delta_magic = str(delta_data.get("magic", "")).lower()
    delta_timeout = str(delta_data.get("timeout_ms", ""))
    if "0x5357494654" in delta_magic or "0x5357494654" in text_lower or "357945517652" in response_text:
        pts = 5
        if "4500" in delta_timeout or "4500" in response_text:
            pts = 10
        scores["retrieval"]["delta"]["points"] = pts
        scores["retrieval"]["delta"]["details"] = f"Delta match ({pts}/10 pts)"
    else:
        scores["retrieval"]["delta"]["details"] = "Delta magic/timeout missing or incorrect"

    # Epsilon (92% - Deep RoPE)
    eps_data = parsed_json.get("sentinels", {}).get("epsilon", {}) if parsed_json else {}
    eps_sub = str(eps_data.get("substeps", ""))
    eps_const = str(eps_data.get("constraint", "")).lower()
    if "128" in eps_sub or "128" in response_text:
        pts = 5
        if "penalty_impulse_split" in eps_const or "penalty_impulse_split" in text_lower:
            pts = 10
        scores["retrieval"]["epsilon"]["points"] = pts
        scores["retrieval"]["epsilon"]["details"] = f"Epsilon match ({pts}/10 pts)"
    else:
        scores["retrieval"]["epsilon"]["details"] = "Epsilon substeps/constraint missing or incorrect"

    scores["retrieval"]["total"] = sum(scores["retrieval"][k]["points"] for k in ["alpha", "beta", "gamma", "delta", "epsilon"])

    # 3. Score Multi-Hop Reasoning
    gt = MULTIHOP_CHAIN["ground_truth"]
    mh_data = parsed_json.get("multihop_calculation", {}) if parsed_json else {}

    # Active tier
    tier_val = str(mh_data.get("active_tier", "")).lower()
    if "hyper_scale" in tier_val or "hyper_scale" in text_lower:
        scores["multihop"]["active_tier"]["points"] = 5
        scores["multihop"]["active_tier"]["details"] = "Active tier HYPER_SCALE correctly identified."
    else:
        scores["multihop"]["active_tier"]["details"] = "Active tier missing or incorrect."

    # Components retrieval
    comps_found = 0
    if str(gt["base_capacity"]) in response_text:
        comps_found += 1
    if str(gt["tier_multiplier"]) in response_text:
        comps_found += 1
    if str(gt["headroom"]) in response_text:
        comps_found += 1
    scores["multihop"]["components"]["points"] = min(10, int((comps_found / 3.0) * 10))
    scores["multihop"]["components"]["details"] = f"Identified {comps_found}/3 base components in context."

    # Math step
    if "9600" in response_text or "4800" in response_text or "(2400" in response_text or "2400 * 4" in response_text:
        scores["multihop"]["math_step"]["points"] = 5
        scores["multihop"]["math_step"]["details"] = "Arithmetic steps present and logically consistent."
    else:
        scores["multihop"]["math_step"]["details"] = "Arithmetic steps missing or unclear."

    # Final result (5450)
    calc_total = str(mh_data.get("calculated_total", ""))
    if "5450" in calc_total or "5450" in response_text:
        scores["multihop"]["final_result"]["points"] = 15
        scores["multihop"]["final_result"]["details"] = "Exact final calculation (5450) achieved!"
    else:
        scores["multihop"]["final_result"]["details"] = f"Expected 5450, got '{calc_total}'."

    scores["multihop"]["total"] = (
        scores["multihop"]["active_tier"]["points"]
        + scores["multihop"]["components"]["points"]
        + scores["multihop"]["math_step"]["points"]
        + scores["multihop"]["final_result"]["points"]
    )

    # 4. Schema completeness
    if parsed_json:
        has_sentinels = "sentinels" in parsed_json and len(parsed_json["sentinels"]) >= 4
        has_mh = "multihop_calculation" in parsed_json
        if has_sentinels and has_mh:
            scores["schema"]["key_completeness"]["points"] = 5
            scores["schema"]["key_completeness"]["details"] = "All top-level keys and structures present."
        else:
            scores["schema"]["key_completeness"]["points"] = 2
            scores["schema"]["key_completeness"]["details"] = "Partial schema keys present."

    scores["schema"]["total"] = scores["schema"]["valid_json"]["points"] + scores["schema"]["key_completeness"]["points"]

    # 5. Composite Quality Score
    scores["total_quality_score"] = scores["retrieval"]["total"] + scores["multihop"]["total"] + scores["schema"]["total"]
    return scores


# ---------------------------------------------------------------------------
# Benchmark Execution & Telemetry Engine
# ---------------------------------------------------------------------------

def run_context_drift_test(
    base_url=DEFAULT_URL,
    model_id="qwen3.8-27b-swift15-nvfp4full-dflash2",
    target_tokens=200000,
    temperature=0.65,
    min_p=0.05,
    presence_penalty=0.05,
    thinking_budget=1200,
    preserve_thinking=True,
    timeout_sec=600,
):
    """
    Executes a live 200k context drift test against a running NInfer instance.
    Captures TTFT, throughput, thinking token counts, and response evaluation.
    """
    print("\n" + "=" * 80)
    print(f" NInfer Context Drift & Sentinel Benchmark (~{target_tokens:,} tokens)")
    print(f" Target Endpoint: {base_url} | Model ID: {model_id}")
    print(f" Parameters: T={temperature} | Min-P={min_p} | Presence={presence_penalty} | Budget={thinking_budget}")
    print("=" * 80)

    print(f"[BENCH] Generating high-entropy synthetic codebase corpus (~{target_tokens:,} tokens)...")
    t0_gen = time.perf_counter()
    system_prompt, user_prompt, est_tokens = build_benchmark_prompt(target_tokens=target_tokens)
    t_gen = time.perf_counter() - t0_gen
    print(f"  \033[92m[DONE]\033[0m Generated {len(user_prompt):,} characters (~{est_tokens:,} tokens) in {t_gen:.2f}s")

    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "min_p": min_p,
        "presence_penalty": presence_penalty,
        "max_tokens": 4096,
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

    print(f"[BENCH] Dispatching {est_tokens:,}-token prefill request to NInfer engine...")
    start_time = time.perf_counter()
    ttft = None
    first_token_time = None
    full_content = []
    thinking_content = []
    is_thinking = False
    tokens_emitted = 0

    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
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

                    # Check for thinking vs content
                    reasoning_chunk = delta.get("reasoning_content") or delta.get("thinking")
                    content_chunk = delta.get("content", "")

                    # Capture TTFT on first real token
                    if (reasoning_chunk or content_chunk) and first_token_time is None:
                        first_token_time = time.perf_counter()
                        ttft = first_token_time - start_time
                        prefill_tok_s = est_tokens / ttft if ttft > 0 else 0
                        print(f"  \033[92m[TTFT]\033[0m First token received in {ttft:.2f}s (Prefill Speed: ~{prefill_tok_s:,.0f} tok/s)")

                    if reasoning_chunk:
                        thinking_content.append(reasoning_chunk)
                        tokens_emitted += 1
                    elif content_chunk:
                        full_content.append(content_chunk)
                        tokens_emitted += 1

                except Exception:
                    continue

    except Exception as e:
        print(f"[ERROR] Inference failed: {e}", file=sys.stderr)
        return {
            "status": "FAILED",
            "error": str(e),
            "est_tokens": est_tokens,
            "quality_score": 0,
        }

    total_time = time.perf_counter() - start_time
    decode_time = (time.perf_counter() - first_token_time) if first_token_time else 0.001
    decode_tok_s = tokens_emitted / decode_time if decode_time > 0 else 0
    prefill_tok_s = est_tokens / ttft if ttft and ttft > 0 else 0

    complete_response = "".join(full_content)
    complete_thinking = "".join(thinking_content)
    n_think = len(complete_thinking.split()) * 1.3  # rough token count
    n_content = len(complete_response.split()) * 1.3

    print(f"  \033[92m[DECODE]\033[0m Emitted {tokens_emitted} tokens in {decode_time:.2f}s ({decode_tok_s:.1f} tok/s)")
    print(f"  \033[92m[TOTAL]\033[0m Turnaround: {total_time:.2f}s | Thinking chars: {len(complete_thinking):,}")

    # Evaluate response
    print("\n[BENCH] Scoring response against Sentinel and Multi-Hop Ground Truth...")
    scorecard = evaluate_response(complete_response)
    q_score = scorecard["total_quality_score"]

    print(f"  >>> Composite Quality Score: \033[1m{q_score}/100\033[0m <<<")
    print(f"      - Retrieval (M-NIAH):    {scorecard['retrieval']['total']}/50")
    for k in ["alpha", "beta", "gamma", "delta", "epsilon"]:
        res = scorecard["retrieval"][k]
        mark = "✓" if res["points"] == 10 else ("~" if res["points"] > 0 else "✗")
        print(f"        [{mark}] {k.capitalize():<7} ({SENTINELS[k]['depth_target']*100:.0f}% depth): {res['points']}/10 pts - {res['details']}")

    print(f"      - Multi-Hop Synthesis:   {scorecard['multihop']['total']}/35")
    print(f"        [*] Final Result (5450): {scorecard['multihop']['final_result']['points']}/15 pts - {scorecard['multihop']['final_result']['details']}")
    print(f"      - Schema Compliance:     {scorecard['schema']['total']}/15")

    # Extract exact telemetry from ninfer.log
    exact_prefill_tok_s = prefill_tok_s
    exact_decode_tok_s = decode_tok_s
    exact_ttft = ttft
    exact_spec_acc = "N/A"
    exact_prompt_tokens = est_tokens
    exact_output_tokens = tokens_emitted
    exact_thinking = int(n_think)

    if NINFER_LOG.exists():
        try:
            with open(NINFER_LOG, "r", encoding="utf-8", errors="ignore") as f:
                log_lines = f.readlines()
            for line in reversed(log_lines):
                if "done | openai-chat" in line or "done | openai-responses" in line:
                    # Parse: prompt 217,088 | output 1,232 | ... | TTFT 56.9s | ... | prefill 3.82k tok/s | decode 272.8 tok/s | dflash2 accepted 982/1,750 (56.1%) | thinking 854/1,200
                    p_match = re.search(r"prompt\s+([\d,]+)", line)
                    if p_match:
                        exact_prompt_tokens = int(p_match.group(1).replace(",", ""))

                    o_match = re.search(r"output\s+([\d,]+)", line)
                    if o_match:
                        exact_output_tokens = int(o_match.group(1).replace(",", ""))

                    ttft_match = re.search(r"TTFT\s+([\d.]+)(?:s|ms)", line)
                    if ttft_match:
                        exact_ttft = float(ttft_match.group(1))

                    pf_match = re.search(r"prefill\s+([\d.]+)(k)?\s*tok/s", line)
                    if pf_match:
                        val = float(pf_match.group(1))
                        exact_prefill_tok_s = val * 1000 if pf_match.group(2) else val

                    dec_match = re.search(r"decode\s+([\d.]+)\s*tok/s", line)
                    if dec_match:
                        exact_decode_tok_s = float(dec_match.group(1))

                    spec_match = re.search(r"(?:dflash2|mtp)\s+accepted\s+[^()]+\(([\d.]+%)\)", line)
                    if spec_match:
                        exact_spec_acc = spec_match.group(1)

                    thk_match = re.search(r"thinking\s+(\d+)/\d+", line)
                    if thk_match:
                        exact_thinking = int(thk_match.group(1))
                    break
        except Exception:
            pass

    result_summary = {
        "status": "SUCCESS",
        "model_id": model_id,
        "est_tokens": exact_prompt_tokens,
        "ttft_seconds": round(exact_ttft, 2) if exact_ttft else 0,
        "prefill_tok_s": round(exact_prefill_tok_s, 1),
        "decode_tok_s": round(exact_decode_tok_s, 1),
        "spec_acceptance": exact_spec_acc,
        "total_time_seconds": round(total_time, 2),
        "decode_time_seconds": round(decode_time, 2),
        "tokens_emitted": exact_output_tokens,
        "thinking_tokens_est": exact_thinking,
        "quality_score": q_score,
        "retrieval_score": scorecard["retrieval"]["total"],
        "multihop_score": scorecard["multihop"]["total"],
        "schema_score": scorecard["schema"]["total"],
        "scorecard": scorecard,
        "response_sample": complete_response[:1000],
        "thinking_sample": complete_thinking[:500],
    }

    return result_summary


# ---------------------------------------------------------------------------
# Server Lifecycle & Model Orchestration
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


# Standard tuned representative configurations for the 5 model families
MODEL_FAMILY_CONFIGS = {
    "1": "1.4",  # Swift15-DFlash2 (Tuned Tight Budget / Minima)
    "2": "2.4",  # Swift10-MTP
    "3": "3.4",  # Swift15-MTP
    "4": "4.4",  # Base-DFlash2
    "5": "5.4",  # Base-NVFP4
}


def launch_and_test_model(cfg_id: str, target_tokens=200000):
    configs = load_model_configs()
    if cfg_id not in configs:
        print(f"[ERROR] Config ID '{cfg_id}' not found.", file=sys.stderr)
        sys.exit(1)

    cfg = configs[cfg_id]
    print("\n" + "=" * 90)
    print(f" ORCHESTRATING CONTEXT DRIFT TEST: Config {cfg_id} - {cfg['name']}")
    print(f" Model Group: {cfg.get('model_group')} | Target Tokens: {target_tokens:,}")
    print("=" * 90)

    # 1. Stop existing instance
    stop_running_ninfer()

    # 2. Prepare launcher command
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

    # 3. Run the benchmark
    res = run_context_drift_test(
        base_url=DEFAULT_URL,
        model_id=cfg.get("model_id"),
        target_tokens=target_tokens,
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


def save_markdown_report(results: list, target_tokens: int):
    """
    Generates a consolidated Markdown benchmark report comparing all tested models.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = REPORTS_DIR / f"benchmark_context_drift_{target_tokens // 1000}k_{timestamp}.md"

    md = []
    md.append(f"# 200K Context Drift & Needle Degradation Benchmark Report")
    md.append(f"\n**Execution Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    md.append(f"**Target Sequence Length:** ~{target_tokens:,} tokens  ")
    md.append(f"**Hardware Platform:** NVIDIA GeForce RTX 5090 (32GB GDDR7, SM 12.0) | AMD Ryzen 9 7950X3D  ")
    md.append(f"**Inference Engine:** NInfer (C++/CUDA Runtime, k8v4 KV Cache, 240k Context)\n")
    md.append("---\n")

    md.append("## 1. Executive Summary & Comparison Table\n")
    md.append("| Model Variant | Spec Backend | Spec Acceptance | Quality Score | Retrieval (/50) | Multi-Hop (/35) | TTFT (s) | Prefill (tok/s) | Decode (tok/s) | Total (s) |")
    md.append("|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")

    for r in results:
        if r.get("status") != "SUCCESS":
            md.append(f"| **{r.get('config_name', 'Unknown')}** | {r.get('spec', '-')} | - | **FAILED** | - | - | - | - | - | - |")
            continue
        md.append(
            f"| **{r['config_name']}** | {r.get('spec', '-')} | {r.get('spec_acceptance', 'N/A')} | **{r['quality_score']}/100** | {r['retrieval_score']}/50 | {r['multihop_score']}/35 | {r['ttft_seconds']}s | {r['prefill_tok_s']:,.0f} | {r['decode_tok_s']} | {r['total_time_seconds']}s |"
        )

    md.append("\n---\n")
    md.append("## 2. Needle-in-a-Haystack (M-NIAH) Depth Breakdown\n")
    md.append("| Model Variant | Alpha (10%) | Beta (30%) | Gamma (50% - Middle) | Delta (75%) | Epsilon (92% - RoPE) | Multi-Hop Final (5450) |")
    md.append("|---|:---:|:---:|:---:|:---:|:---:|:---:|")

    for r in results:
        if r.get("status") != "SUCCESS":
            continue
        sc = r["scorecard"]
        ret = sc["retrieval"]
        mh = sc["multihop"]["final_result"]
        md.append(
            f"| **{r['config_name']}** | {ret['alpha']['points']}/10 | {ret['beta']['points']}/10 | {ret['gamma']['points']}/10 | {ret['delta']['points']}/10 | {ret['epsilon']['points']}/10 | {mh['points']}/15 |"
        )

    md.append("\n---\n")
    md.append("## 3. Detailed Model Telemetry & Responses\n")
    for r in results:
        md.append(f"### Model: {r.get('config_name', 'Unknown')}\n")
        if r.get("status") != "SUCCESS":
            md.append(f"> **Execution Status:** FAILED ({r.get('error', 'Unknown Error')})\n")
            continue
        md.append(f"* **Quality Score:** {r['quality_score']}/100")
        md.append(f"* **TTFT Latency:** {r['ttft_seconds']}s ({r['prefill_tok_s']:,.0f} tok/s prefill)")
        md.append(f"* **Decoding Speed:** {r['decode_tok_s']} tok/s ({r['tokens_emitted']} tokens in {r['decode_time_seconds']}s)")
        md.append(f"* **Thinking Overhead:** ~{r['thinking_tokens_est']} tokens\n")
        md.append("#### Response Excerpt:\n```json\n" + r["response_sample"] + "\n```\n")

    report_content = "\n".join(md)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"\n[REPORT] Saved benchmark report to: {report_file}")
    return report_file


# ---------------------------------------------------------------------------
# Self-Test Mode (Validates Corpus & Evaluator Logic Offline)
# ---------------------------------------------------------------------------

def run_self_test():
    """
    Validates corpus generation, needle placement, and scoring logic offline.
    """
    print("\n" + "=" * 80)
    print(" RUNNING OFFLINE SELF-TEST & VALIDATOR VERIFICATION")
    print("=" * 80)

    print("[TEST 1/3] Generating test corpus (~50,000 tokens for quick verification)...")
    corpus, est_tokens = generate_codebase_corpus(target_tokens=50000)
    print(f"  ✓ Corpus generated: {len(corpus):,} characters (~{est_tokens:,} tokens)")

    print("[TEST 2/3] Verifying Sentinel placement in corpus...")
    for key, s in SENTINELS.items():
        found = s["snippet"].strip() in corpus
        assert found, f"Sentinel {key} was not found in generated corpus!"
        print(f"  ✓ {s['name']} verified in corpus.")

    for key, h in MULTIHOP_CHAIN.items():
        if key == "ground_truth":
            continue
        found = h["snippet"].strip() in corpus
        assert found, f"Multi-hop {key} was not found in generated corpus!"
        print(f"  ✓ Multi-hop {key} verified in corpus.")

    print("[TEST 3/3] Verifying scoring engine on mock perfect response...")
    mock_perfect = """```json
{
  "sentinels": {
    "alpha": {
      "token": "0x9F4C2A18E6B70D31",
      "policy": "STRICT_ISOLATED_SANDBOX"
    },
    "beta": {
      "routing_key": "shard_region_apac_central_9",
      "isolation": "SERIALIZABLE_SNAPSHOT"
    },
    "gamma": {
      "alignment_bytes": 16384,
      "strategy": "BUMP_HUGEPAGE_LOCK"
    },
    "delta": {
      "magic": "0x5357494654",
      "timeout_ms": 4500
    },
    "epsilon": {
      "substeps": 128,
      "constraint": "PENALTY_IMPULSE_SPLIT"
    }
  },
  "multihop_calculation": {
    "active_tier": "HYPER_SCALE",
    "base_capacity": 2400,
    "tier_multiplier": 4,
    "weight_divisor": 3,
    "weight_discount": 1,
    "effective_divisor": 2,
    "headroom": 650,
    "calculated_total": 5450,
    "resolution_trace": "(2400 * 4) / (3 - 1) + 650 = 9600 / 2 + 650 = 4800 + 650 = 5450"
  }
}
```"""
    scores = evaluate_response(mock_perfect)
    assert scores["total_quality_score"] == 100, f"Expected 100/100 on perfect mock, got {scores['total_quality_score']}"
    print(f"  ✓ Evaluator scored perfect mock response as: {scores['total_quality_score']}/100")

    print("\n\033[92m[PASS] ALL SELF-TESTS PASSED SUCCESSFULLY!\033[0m\n")


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NInfer 200k Context Drift Benchmark Harness")
    parser.add_argument("--self-test", action="store_true", help="Run offline unit test on corpus and evaluator")
    parser.add_argument("--running", action="store_true", help="Run test against currently running server without restarting")
    parser.add_argument("--tokens", "-t", type=int, default=200000, help="Target context tokens (default: 200000)")
    parser.add_argument("--model", "-m", type=str, choices=["1", "2", "3", "4", "5", "all"], default=None, help="Model group to test (1=Swift15-DFlash2, 2=Swift10-MTP, 3=Swift15-MTP, 4=Base-DFlash2, 5=Base-NVFP4, all=sweep all 5)")
    parser.add_argument("--config", "-c", type=str, help="Specific config ID from bench_configs.json (e.g. 1.4)")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        sys.exit(0)

    if args.running:
        print("[INFO] Running against currently active server on http://localhost:8080...")
        res = run_context_drift_test(
            base_url=DEFAULT_URL,
            model_id="qwen3.8-27b-swift15-nvfp4full-dflash2",
            target_tokens=args.tokens,
        )
        save_markdown_report([res], target_tokens=args.tokens)
        sys.exit(0)

    if args.model == "all":
        print(f"\n[RUNNER] Starting comprehensive context drift sweep across all 5 model architectures (~{args.tokens:,} tokens)...")
        results = []
        for m_id, cfg_id in MODEL_FAMILY_CONFIGS.items():
            res = launch_and_test_model(cfg_id, target_tokens=args.tokens)
            if res:
                results.append(res)
        save_markdown_report(results, target_tokens=args.tokens)
        print("\n[COMPLETE] All 5 models evaluated! See bench_reports for full markdown scorecard.")
    elif args.model:
        cfg_id = MODEL_FAMILY_CONFIGS[args.model]
        res = launch_and_test_model(cfg_id, target_tokens=args.tokens)
        if res:
            save_markdown_report([res], target_tokens=args.tokens)
    elif args.config:
        res = launch_and_test_model(args.config, target_tokens=args.tokens)
        if res:
            save_markdown_report([res], target_tokens=args.tokens)
    else:
        # Default: run self-test then prompt
        run_self_test()
        print("Run with: python bench_context_drift.py --model all [--tokens 200000]")
