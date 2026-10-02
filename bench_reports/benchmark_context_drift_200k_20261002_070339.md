# 200K Context Drift & Needle Degradation Benchmark Report

**Execution Timestamp:** 2026-10-02 07:03:39  
**Target Sequence Length:** ~200,000 tokens  
**Hardware Platform:** NVIDIA GeForce RTX 5090 (32GB GDDR7, SM 12.0) | AMD Ryzen 9 7950X3D  
**Inference Engine:** NInfer (C++/CUDA Runtime, k8v4 KV Cache, 240k Context)

---

## 1. Executive Summary & Comparison Table

| Model Variant | Spec Backend | Spec Acceptance | Quality Score | Retrieval (/50) | Multi-Hop (/35) | TTFT (s) | Prefill (tok/s) | Decode (tok/s) | Total (s) |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Swift15-DFlash2 Tight Agentic Budget** | dflash2 | N/A | **100/100** | 50/50 | 35/35 | 57.69s | 3,469 | 54.4 | 62.36s |
| **Swift10-MTP Tight Agentic Budget** | mtp | N/A | **100/100** | 50/50 | 35/35 | 63.01s | 3,176 | 46.0 | 69.65s |
| **Swift15-MTP Tight Agentic Budget** | mtp | N/A | **100/100** | 50/50 | 35/35 | 65.26s | 3,067 | 44.3 | 74.04s |
| **Base-DFlash2 Tight Agentic Budget** | dflash2 | N/A | **100/100** | 50/50 | 35/35 | 67.92s | 2,947 | 48.3 | 74.05s |
| **Base-NVFP4 Tight Agentic Budget** | mtp | N/A | **100/100** | 50/50 | 35/35 | 65.13s | 3,073 | 45.5 | 71.96s |

---

## 2. Needle-in-a-Haystack (M-NIAH) Depth Breakdown

| Model Variant | Alpha (10%) | Beta (30%) | Gamma (50% - Middle) | Delta (75%) | Epsilon (92% - RoPE) | Multi-Hop Final (5450) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Swift15-DFlash2 Tight Agentic Budget** | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 15/15 |
| **Swift10-MTP Tight Agentic Budget** | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 15/15 |
| **Swift15-MTP Tight Agentic Budget** | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 15/15 |
| **Base-DFlash2 Tight Agentic Budget** | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 15/15 |
| **Base-NVFP4 Tight Agentic Budget** | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 15/15 |

---

## 3. Detailed Model Telemetry & Responses

### Model: Swift15-DFlash2 Tight Agentic Budget

* **Quality Score:** 100/100
* **TTFT Latency:** 57.69s (3,469 tok/s prefill)
* **Decoding Speed:** 54.4 tok/s (254 tokens in 4.67s)
* **Thinking Overhead:** ~399 tokens

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

### Model: Swift10-MTP Tight Agentic Budget

* **Quality Score:** 100/100
* **TTFT Latency:** 63.01s (3,176 tok/s prefill)
* **Decoding Speed:** 46.0 tok/s (305 tokens in 6.63s)
* **Thinking Overhead:** ~288 tokens

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
    "resolution_trace": "TOTAL_EFFECTIVE_CAPACITY = (GLOBAL_CAPACITY_BASE * TIER_SCALE_MULTIPLIER_HYPER) / (UNIT_WEIGHT_DIVISOR - UNIT_WEIGHT_DISCOUNT) + BUFFER_HEADROOM = (2400 * 4) / (3 - 1) + 650 = 9600 / 2 + 650 = 4800 + 650 = 5450."
  }
}
`
```

### Model: Swift15-MTP Tight Agentic Budget

* **Quality Score:** 100/100
* **TTFT Latency:** 65.26s (3,067 tok/s prefill)
* **Decoding Speed:** 44.3 tok/s (389 tokens in 8.78s)
* **Thinking Overhead:** ~439 tokens

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

### Model: Base-DFlash2 Tight Agentic Budget

* **Quality Score:** 100/100
* **TTFT Latency:** 67.92s (2,947 tok/s prefill)
* **Decoding Speed:** 48.3 tok/s (296 tokens in 6.13s)
* **Thinking Overhead:** ~508 tokens

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

### Model: Base-NVFP4 Tight Agentic Budget

* **Quality Score:** 100/100
* **TTFT Latency:** 65.13s (3,073 tok/s prefill)
* **Decoding Speed:** 45.5 tok/s (311 tokens in 6.83s)
* **Thinking Overhead:** ~351 tokens

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
