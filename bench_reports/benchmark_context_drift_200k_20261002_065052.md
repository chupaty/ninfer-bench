# 200K Context Drift & Needle Degradation Benchmark Report

**Execution Timestamp:** 2026-10-02 06:50:52  
**Target Sequence Length:** ~200,000 tokens  
**Hardware Platform:** NVIDIA GeForce RTX 5090 (32GB GDDR7, SM 12.0) | AMD Ryzen 9 7950X3D  
**Inference Engine:** NInfer (C++/CUDA Runtime, k8v4 KV Cache, 240k Context)

---

## 1. Executive Summary & Comparison Table

| Model Variant | Spec Backend | Spec Acceptance | Quality Score | Retrieval (/50) | Multi-Hop (/35) | TTFT (s) | Prefill (tok/s) | Decode (tok/s) | Total (s) |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Swift15-DFlash2 Tight Agentic Budget** | dflash2 | N/A | **100/100** | 50/50 | 35/35 | 57.06s | 3,508 | 55.7 | 61.54s |
| **Swift10-MTP Tight Agentic Budget** | mtp | N/A | **100/100** | 50/50 | 35/35 | 62.47s | 3,204 | 46.8 | 69.1s |
| **Swift15-MTP Tight Agentic Budget** | mtp | N/A | **100/100** | 50/50 | 35/35 | 62.42s | 3,206 | 46.9 | 70.08s |
| **Base-NVFP4 Tight Agentic Budget** | mtp | N/A | **100/100** | 50/50 | 35/35 | 64.72s | 3,092 | 45.8 | 72.28s |

---

## 2. Needle-in-a-Haystack (M-NIAH) Depth Breakdown

| Model Variant | Alpha (10%) | Beta (30%) | Gamma (50% - Middle) | Delta (75%) | Epsilon (92% - RoPE) | Multi-Hop Final (5450) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Swift15-DFlash2 Tight Agentic Budget** | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 15/15 |
| **Swift10-MTP Tight Agentic Budget** | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 15/15 |
| **Swift15-MTP Tight Agentic Budget** | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 15/15 |
| **Base-NVFP4 Tight Agentic Budget** | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 15/15 |

---

## 3. Detailed Model Telemetry & Responses

### Model: Swift15-DFlash2 Tight Agentic Budget

* **Quality Score:** 100/100
* **TTFT Latency:** 57.06s (3,508 tok/s prefill)
* **Decoding Speed:** 55.7 tok/s (250 tokens in 4.49s)
* **Thinking Overhead:** ~397 tokens

#### Response Excerpt:
```json
```json
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
    "resolution_trace": "GLOBAL_CAPACITY_BASE 2400 multiplied by TIER_SCALE_MULTIPLIER_HYPER 4 gives 9600. UNIT_WEIGHT_DIVISOR 3 minus UNIT_WEIGHT_DISCOUNT 1 gives effective divisor 2. 9600 divided by 2 gives 4800. Adding BUFFER_HEADROOM 650 giv
```

### Model: Swift10-MTP Tight Agentic Budget

* **Quality Score:** 100/100
* **TTFT Latency:** 62.47s (3,204 tok/s prefill)
* **Decoding Speed:** 46.8 tok/s (310 tokens in 6.63s)
* **Thinking Overhead:** ~318 tokens

#### Response Excerpt:
```json
```json
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
```
```

### Model: Swift15-MTP Tight Agentic Budget

* **Quality Score:** 100/100
* **TTFT Latency:** 62.42s (3,206 tok/s prefill)
* **Decoding Speed:** 46.9 tok/s (359 tokens in 7.66s)
* **Thinking Overhead:** ~451 tokens

#### Response Excerpt:
```json
```json
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
```
```

### Model: Base-NVFP4 Tight Agentic Budget

* **Quality Score:** 100/100
* **TTFT Latency:** 64.72s (3,092 tok/s prefill)
* **Decoding Speed:** 45.8 tok/s (346 tokens in 7.56s)
* **Thinking Overhead:** ~396 tokens

#### Response Excerpt:
```json
```json
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
    "resolution_trace": "2400 * 4 = 9600; 3 - 1 = 2; 9600 / 2 = 4800; 4800 + 650 = 5450"
  }
}
```
```
