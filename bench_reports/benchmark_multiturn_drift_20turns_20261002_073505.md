# 20-Turn 200K Progressive Multi-Turn Context Drift Benchmark Report

**Execution Timestamp:** 2026-10-02 07:35:05  
**Turn Horizon:** 20 Conversational Turns (Accumulating to ~200,000 tokens)  
**Hardware Platform:** NVIDIA GeForce RTX 5090 (32GB GDDR7, SM 12.0) | AMD Ryzen 9 7950X3D  
**Inference Engine:** NInfer (k8v4 KV Cache, 240k Context, Prefix Caching)

---

## 1. Executive Summary & Multi-Turn Comparison Table

| Model Variant | Spec Backend | Composite Score | State Mutation Recall (Turn 20) | Turn 10 Audit | Unwrap Violations | Session Time (s) | Final TTFT (s) |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Swift15-DFlash2 Tight Agentic Budget** | dflash2 | **118/125 (94.4%)** | **20/25** | 10/10 | 1 | 208.3s | 6.55s |
| **Swift10-MTP Tight Agentic Budget** | mtp | **121/125 (96.8%)** | **25/25** | 10/10 | 2 | 256.0s | 6.52s |
| **Swift15-MTP Tight Agentic Budget** | mtp | **119/125 (95.2%)** | **25/25** | 10/10 | 3 | 346.1s | 7.08s |
| **Base-DFlash2 Tight Agentic Budget** | dflash2 | **123/125 (98.4%)** | **25/25** | 10/10 | 2 | 233.3s | 6.77s |
| **Base-NVFP4 Tight Agentic Budget** | mtp | **121/125 (96.8%)** | **25/25** | 10/10 | 2 | 292.9s | 6.78s |

---

## 2. Turn-by-Turn Progression Breakdown

### Model: Swift15-DFlash2 Tight Agentic Budget (dflash2)

| Turn | Cumulative Tokens | Score | TTFT (s) | Decode (tok/s) | Result & Audit Notes |
|:---:|:---:|:---:|:---:|:---:|---|
| Turn 01 | ~10,095 | 5/5 | 0.91s | 69.1 | OK |
| Turn 02 | ~20,277 | 5/5 | 1.27s | 68.2 | OK |
| Turn 03 | ~30,484 | 5/5 | 1.49s | 66.9 | OK |
| Turn 04 | ~40,624 | 5/5 | 1.82s | 66.8 | OK |
| Turn 05 | ~50,727 | 5/5 | 2.03s | 65.3 | OK |
| Turn 06 | ~60,933 | 5/5 | 2.35s | 64.8 | OK |
| Turn 07 | ~71,100 | 5/5 | 2.67s | 64.1 | OK |
| Turn 08 | ~81,137 | 5/5 | 2.85s | 63.4 | OK |
| Turn 09 | ~91,340 | 5/5 | 3.11s | 62.5 | OK |
| Turn 10 | ~101,387 | 10/10 | 3.46s | 61.9 | Canonical handler (9443, 0x51554F52554D) exact match.  |
| Turn 11 | ~111,522 | 5/5 | 3.6s | 60.8 | OK |
| Turn 12 | ~121,721 | 5/5 | 4.04s | 60.0 | OK |
| Turn 13 | ~131,756 | 5/5 | 4.49s | 59.1 | OK |
| Turn 14 | ~141,894 | 5/5 | 4.81s | 58.4 | OK |
| Turn 15 | ~152,141 | 3/5 | 5.27s | 57.6 | [VIOLATION: .unwrap() emitted]  |
| Turn 16 | ~162,315 | 5/5 | 5.35s | 56.9 | OK |
| Turn 17 | ~172,454 | 5/5 | 5.75s | 56.2 | OK |
| Turn 18 | ~182,490 | 5/5 | 6.05s | 55.5 | OK |
| Turn 19 | ~192,604 | 5/5 | 6.19s | 55.0 | OK |
| Turn 20 | ~202,913 | 20/25 | 6.55s | 54.7 | [JSON parse error] SUCCESS: Resolved active State v3 (16384) -> Total: 3001!  |


### Model: Swift10-MTP Tight Agentic Budget (mtp)

| Turn | Cumulative Tokens | Score | TTFT (s) | Decode (tok/s) | Result & Audit Notes |
|:---:|:---:|:---:|:---:|:---:|---|
| Turn 01 | ~10,095 | 5/5 | 1.16s | 58.5 | OK |
| Turn 02 | ~20,277 | 5/5 | 1.5s | 57.2 | OK |
| Turn 03 | ~30,484 | 5/5 | 1.76s | 56.2 | OK |
| Turn 04 | ~40,624 | 5/5 | 2.06s | 56.0 | OK |
| Turn 05 | ~50,727 | 5/5 | 2.29s | 55.0 | OK |
| Turn 06 | ~60,933 | 5/5 | 2.59s | 54.5 | OK |
| Turn 07 | ~71,100 | 5/5 | 2.84s | 54.0 | OK |
| Turn 08 | ~81,137 | 5/5 | 3.09s | 53.1 | OK |
| Turn 09 | ~91,340 | 5/5 | 3.37s | 52.5 | OK |
| Turn 10 | ~101,387 | 10/10 | 3.62s | 51.8 | Canonical handler (9443, 0x51554F52554D) exact match.  |
| Turn 11 | ~111,522 | 5/5 | 3.85s | 51.2 | OK |
| Turn 12 | ~121,721 | 5/5 | 4.27s | 50.0 | OK |
| Turn 13 | ~131,756 | 5/5 | 4.43s | 49.4 | OK |
| Turn 14 | ~141,894 | 5/5 | 4.82s | 49.3 | OK |
| Turn 15 | ~152,141 | 5/5 | 5.13s | 48.6 | OK |
| Turn 16 | ~162,315 | 5/5 | 5.42s | 47.5 | OK |
| Turn 17 | ~172,454 | 3/5 | 5.68s | 47.7 | [VIOLATION: .unwrap() emitted]  |
| Turn 18 | ~182,490 | 3/5 | 5.92s | 47.0 | [VIOLATION: .unwrap() emitted]  |
| Turn 19 | ~192,604 | 5/5 | 6.22s | 46.5 | OK |
| Turn 20 | ~202,913 | 25/25 | 6.52s | 46.1 | SUCCESS: Resolved active State v3 (16384) -> Total: 3001!  |


### Model: Swift15-MTP Tight Agentic Budget (mtp)

| Turn | Cumulative Tokens | Score | TTFT (s) | Decode (tok/s) | Result & Audit Notes |
|:---:|:---:|:---:|:---:|:---:|---|
| Turn 01 | ~10,095 | 5/5 | 1.15s | 57.5 | OK |
| Turn 02 | ~20,277 | 5/5 | 1.57s | 56.1 | OK |
| Turn 03 | ~30,484 | 5/5 | 1.83s | 55.8 | OK |
| Turn 04 | ~40,624 | 5/5 | 2.16s | 55.3 | OK |
| Turn 05 | ~50,727 | 5/5 | 2.44s | 54.2 | OK |
| Turn 06 | ~60,933 | 5/5 | 2.7s | 51.7 | OK |
| Turn 07 | ~71,100 | 5/5 | 3.15s | 50.6 | OK |
| Turn 08 | ~81,137 | 5/5 | 3.3s | 51.0 | OK |
| Turn 09 | ~91,340 | 5/5 | 3.6s | 49.7 | OK |
| Turn 10 | ~101,387 | 10/10 | 4.07s | 50.3 | Canonical handler (9443, 0x51554F52554D) exact match.  |
| Turn 11 | ~111,522 | 5/5 | 3.87s | 49.8 | OK |
| Turn 12 | ~121,721 | 5/5 | 4.44s | 49.4 | OK |
| Turn 13 | ~131,756 | 5/5 | 4.91s | 46.9 | OK |
| Turn 14 | ~141,894 | 5/5 | 5.14s | 48.2 | OK |
| Turn 15 | ~152,141 | 3/5 | 5.53s | 47.3 | [VIOLATION: .unwrap() emitted]  |
| Turn 16 | ~162,315 | 5/5 | 5.56s | 47.2 | OK |
| Turn 17 | ~172,454 | 5/5 | 5.86s | 45.9 | OK |
| Turn 18 | ~182,490 | 3/5 | 5.95s | 46.1 | [VIOLATION: .unwrap() emitted]  |
| Turn 19 | ~192,604 | 3/5 | 6.76s | 45.6 | [VIOLATION: .unwrap() emitted]  |
| Turn 20 | ~202,913 | 25/25 | 7.08s | 44.2 | SUCCESS: Resolved active State v3 (16384) -> Total: 3001!  |


### Model: Base-DFlash2 Tight Agentic Budget (dflash2)

| Turn | Cumulative Tokens | Score | TTFT (s) | Decode (tok/s) | Result & Audit Notes |
|:---:|:---:|:---:|:---:|:---:|---|
| Turn 01 | ~10,095 | 5/5 | 1.32s | 57.2 | OK |
| Turn 02 | ~20,277 | 5/5 | 1.72s | 56.1 | OK |
| Turn 03 | ~30,484 | 5/5 | 1.93s | 55.6 | OK |
| Turn 04 | ~40,624 | 5/5 | 2.23s | 55.1 | OK |
| Turn 05 | ~50,727 | 5/5 | 2.46s | 54.8 | OK |
| Turn 06 | ~60,933 | 5/5 | 2.8s | 54.2 | OK |
| Turn 07 | ~71,100 | 5/5 | 3.07s | 53.6 | OK |
| Turn 08 | ~81,137 | 5/5 | 3.36s | 53.2 | OK |
| Turn 09 | ~91,340 | 5/5 | 3.56s | 52.7 | OK |
| Turn 10 | ~101,387 | 10/10 | 3.79s | 51.0 | [VIOLATION: .unwrap() emitted] Canonical handler (9443, 0x51554F52554D) exact match.  |
| Turn 11 | ~111,522 | 5/5 | 4.05s | 51.3 | OK |
| Turn 12 | ~121,721 | 5/5 | 4.48s | 50.3 | OK |
| Turn 13 | ~131,756 | 5/5 | 4.96s | 49.9 | OK |
| Turn 14 | ~141,894 | 5/5 | 5.3s | 49.6 | OK |
| Turn 15 | ~152,141 | 3/5 | 5.36s | 49.0 | [VIOLATION: .unwrap() emitted]  |
| Turn 16 | ~162,315 | 5/5 | 5.59s | 47.5 | OK |
| Turn 17 | ~172,454 | 5/5 | 5.9s | 47.2 | OK |
| Turn 18 | ~182,490 | 5/5 | 6.38s | 44.2 | OK |
| Turn 19 | ~192,604 | 5/5 | 6.44s | 46.1 | OK |
| Turn 20 | ~202,913 | 25/25 | 6.77s | 47.0 | SUCCESS: Resolved active State v3 (16384) -> Total: 3001!  |


### Model: Base-NVFP4 Tight Agentic Budget (mtp)

| Turn | Cumulative Tokens | Score | TTFT (s) | Decode (tok/s) | Result & Audit Notes |
|:---:|:---:|:---:|:---:|:---:|---|
| Turn 01 | ~10,095 | 5/5 | 1.33s | 55.5 | OK |
| Turn 02 | ~20,277 | 5/5 | 1.62s | 54.3 | OK |
| Turn 03 | ~30,484 | 5/5 | 1.94s | 53.7 | OK |
| Turn 04 | ~40,624 | 5/5 | 2.3s | 52.9 | OK |
| Turn 05 | ~50,727 | 5/5 | 2.45s | 52.4 | OK |
| Turn 06 | ~60,933 | 5/5 | 2.78s | 51.7 | OK |
| Turn 07 | ~71,100 | 5/5 | 3.07s | 51.1 | OK |
| Turn 08 | ~81,137 | 5/5 | 3.34s | 50.7 | OK |
| Turn 09 | ~91,340 | 5/5 | 3.57s | 50.2 | OK |
| Turn 10 | ~101,387 | 10/10 | 3.79s | 49.5 | Canonical handler (9443, 0x51554F52554D) exact match.  |
| Turn 11 | ~111,522 | 5/5 | 4.08s | 48.7 | OK |
| Turn 12 | ~121,721 | 5/5 | 4.46s | 48.2 | OK |
| Turn 13 | ~131,756 | 5/5 | 4.77s | 47.5 | OK |
| Turn 14 | ~141,894 | 5/5 | 5.3s | 47.1 | OK |
| Turn 15 | ~152,141 | 3/5 | 5.35s | 46.4 | [VIOLATION: .unwrap() emitted]  |
| Turn 16 | ~162,315 | 5/5 | 5.65s | 46.0 | OK |
| Turn 17 | ~172,454 | 3/5 | 6.21s | 45.1 | [VIOLATION: .unwrap() emitted]  |
| Turn 18 | ~182,490 | 5/5 | 6.02s | 44.8 | OK |
| Turn 19 | ~192,604 | 5/5 | 6.83s | 43.9 | OK |
| Turn 20 | ~202,913 | 25/25 | 6.78s | 44.0 | SUCCESS: Resolved active State v3 (16384) -> Total: 3001!  |

