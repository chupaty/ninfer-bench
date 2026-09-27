# Agentic Evaluation & Hyperparameter Optimization Harness for Local Reasoning Models

An automated benchmarking and hyperparameter optimization harness designed to evaluate and tune local reasoning models (`<think>`-enabled) under multi-turn software engineering workloads.

**Live Interactive Dashboard:** [https://chupaty.github.io/ninfer-bench/](https://chupaty.github.io/ninfer-bench/)  
**Primary Engine:** NInfer (CUDA 13.1, SM 12.0 / Blackwell)  
**Target Hardware:** NVIDIA GeForce RTX 5090 (32GB GDDR7, factory 600W TDP)

---

## Motivation

Standard single-turn benchmarks (MMLU, HumanEval, SWE-bench) evaluate models in isolation. In multi-turn agentic environments (such as Antigravity, Claude Code, and Moshi), local reasoning models frequently encounter distinct operational failure modes:

1. **Reasoning Loops:** At default sampling temperatures ($T \ge 0.90$) and unconstrained token budgets, models can enter circular deliberation loops, consuming thousands of thinking tokens and accumulating turn latencies between 30s and 230s.
2. **Premise Traps & Hallucinations:** When prompted with false premises (e.g., referencing non-existent structs or functions), models often synthesize fictitious implementations rather than verifying the codebase.
3. **Long-Horizon Context Degradation:** As context expands past 60k tokens across multi-file operations, KV cache footprint, speculative decoding acceptance, and prompt cache hit rates degrade.

This harness executes automated response surface sweeps across model variants and hyperparameter configurations to identify operating parameters that prevent reasoning loops while preserving task accuracy.

---

## Optimization Loss Function

Configurations are evaluated against a scalarized multi-objective loss function that penalizes task inaccuracies, reasoning token overhead, loop occurrences, and turnaround latency:

$$\mathcal{L}(\vec{X}) = 2 \cdot (100 - Q) + \frac{N_{\text{think}}}{50} + 10 \cdot N_{\text{loops}} + t_{\text{wall}}$$

* $Q \in [0, 100]$: Task Quality Score based on deterministic codebase criteria.
* $N_{\text{think}}$: Total reasoning tokens generated across all turns.
* $N_{\text{loops}}$: Detected circular reasoning or repetitive tool-call events.
* $t_{\text{wall}}$: Total wallclock turnaround time in seconds.

---

## Evaluation Scenarios

| Scenario | Identifier | Turns | Target Evaluation |
|---|---|:---:|---|
| **Scenario 1** | `springarm_bug` | 10 | **Multi-Crate Bug Investigation:** Locate, isolate, and patch an inverted transform vector bug across multiple Rust crates. |
| **Scenario 2** | `phantom_ik_solver` | 6 | **Adversarial False Premise Trap:** Prompt requests optimization of a non-existent IK solver. Evaluates workspace grounding vs. hallucination. |
| **Scenario 3** | `combiner_mech` | 15 | **Long-Horizon Architecture Synthesis:** Cross-crate entity-component synthesis with context expanding past 60,000 tokens. |

---

## 75-Run Factorial Benchmark Results

Summary across 5 model architectures and 5 sampling configurations evaluated on an RTX 5090 (32GB):

| Rank | Model Architecture | Champion Profile | Scenario 1 (Bugfix) | Scenario 2 (Trap) | Scenario 3 (Long-Horizon) | Mean Opt Loss | Peak Decode | Speculative Engine |
|:---:|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | **Swift15-DFlash2** | Tight Agentic Budget (`Config-1.4`) | 100/100 (9.7s) | 100/100 (3.1s) | 85/100 (21.6s) | **44.9** | 370+ tok/s | DFlash-2 (7 Draft) |
| 2 | **Base-NVFP4** | Author Baseline (`Config-5.1`) | 100/100 (21.3s) | 100/100 (5.8s) | 70/100 (17.9s) | **53.1** | 205 tok/s | MTP (3 Draft) |
| 3 | **Swift10-MTP** | Tuned Local Minima (`Config-2.5`) | 100/100 (23.0s) | 100/100 (5.1s) | 70/100 (16.2s) | **59.6** | 210 tok/s | MTP (3 Draft) |
| 4 | **Base-DFlash2** | Tight Agentic Budget (`Config-4.4`) | 100/100 (17.0s) | 75/100 (6.5s) | 85/100 (22.6s) | **60.4** | 340+ tok/s | DFlash-2 (7 Draft) |
| 5 | **Swift15-MTP** | Tight Agentic Budget (`Config-3.4`) | 90/100 (19.6s) | 75/100 (8.0s) | 70/100 (15.5s) | **74.1** | 200 tok/s | MTP (3 Draft) |

---

## Recommended Sampling Configuration

For daily-driver agentic workflows with `qwen3.8-27b-swift15-nvfp4full-dflash2`:

```powershell
-ModelId "qwen3.8-27b-swift15-nvfp4full-dflash2"
-Spec "dflash2"
-DraftTokens 7
-Temperature 0.65
-MinP 0.05
-PresencePenalty 0.05
-ThinkingBudget 1200
-PreserveThinking $true
```

### Empirical Characteristics:
* **Latency:** Reduces 99th-percentile turn duration from 200s+ to under 4.5s.
* **Grounding:** Avoids speculative hallucinations in adversarial false-premise prompts.
* **Throughput:** Sustains 250–370+ tok/s decode across long-horizon sessions with DFlash-2.

---

## Interactive Analytics Dashboard

The standalone Plotly visualization dashboard is hosted live at:  
[**https://chupaty.github.io/ninfer-bench/**](https://chupaty.github.io/ninfer-bench/)

Features:
* Parallel coordinates parameter-to-loss mapping
* Loss landscape 2D contour and 3D surface visualizations
* DFlash-2 acceptance decay per draft token position
* Multi-scenario Pareto frontier trade-offs
* Interactive scorecard filtering and turn inspection

To regenerate locally from log data:
```bash
python generate_dashboard.py
```

---

## CLI Usage

### List Available Configurations
```bash
python bench_runner.py --list
```

### Run a Single Configuration
```bash
python bench_runner.py --config 1.4 --scenario 3
```

### Run a Model Sweep
```bash
python bench_runner.py --model 1 --scenario all
```

### Full Grid Sweep
```bash
python bench_runner.py --sweep --scenario all
```

---

## Repository Documentation

* [METHODOLOGY.md](METHODOLOGY.md): Mathematical formulation, scenario definitions, speculative dynamics, and power stability.
* [PSU_AND_POWER_STABILITY_RECOMMENDATION.md](PSU_AND_POWER_STABILITY_RECOMMENDATION.md): Hardware power transient analysis and ATX 3.1 PSU specifications.
* [bench_reports/SCORECARD.md](bench_reports/SCORECARD.md): Complete ledger of individual benchmark runs and turn-by-turn logs.

---

## License
MIT License.
