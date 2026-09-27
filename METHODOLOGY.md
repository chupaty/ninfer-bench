# Methodology: Multivariate Response Surface Optimization for Local Agentic Reasoning Models

**Author:** Simon  
**System Hardware:** NVIDIA GeForce RTX 5090 (32GB GDDR7, SM 12.0) | AMD Ryzen 9 7950X3D (16C/32T) | 64GB DDR5  
**Inference Engine:** NInfer (C++/CUDA Runtime with Native NVFP4 Tensor Core Execution)  
**Live Interactive Dashboard:** [https://chupaty.github.io/ninfer-bench/](https://chupaty.github.io/ninfer-bench/)

---

## Abstract
Modern large language models with native reasoning capabilities (e.g., DeepSeek-R1, Qwen 2.5/3.8 with `<think>` tags) exhibit severe behavioral instability when integrated into multi-turn agentic coding environments. While traditional benchmarks measure static single-turn accuracy, they fail to quantify reasoning-loop degradation, hallucination under false premises, or context-scaling latency. 

This paper outlines a formal **multivariate response surface methodology** to evaluate, stress-test, and optimize local reasoning models. By coupling multi-turn sandbox execution with speculative decoding telemetry (DFlash-2 vs. MTP) and automated process orchestration, we demonstrate that tuning temperature ($T=0.65$), presence penalty ($\lambda_{\text{pres}}=0.05$), and thinking budget ($B_{\text{think}}=1200$) reduces worst-case turn latency by **~98%** (from 234s to <4.5s) while maximizing task quality and hallucination resistance.

---

## 1. The Mathematical Framework

We formulate hyperparameter selection for agentic reasoning models as a **constrained multi-objective response surface optimization problem**.

### 1.1 Input Parameter Space ($\vec{X} \in \mathcal{S} \subset \mathbb{R}^d$)
Let $\vec{X}$ be a hyperparameter vector in the bounded configuration space $\mathcal{S}$:
$$\vec{X} = \begin{bmatrix} M \\ T \\ p_{\min} \\ \lambda_{\text{pres}} \\ B_{\text{think}} \end{bmatrix}$$

Where:
* $M \in \{\text{Swift15-DFlash2}, \text{Swift10-MTP}, \text{Swift15-MTP}, \text{Base-DFlash2}, \text{Base-NVFP4}\}$ is the model architecture and speculative acceleration backend.
* $T \in [0.60, 0.90]$ is the sampling temperature.
* $p_{\min} \in [0.05, 0.08]$ is the dynamic truncation probability threshold.
* $\lambda_{\text{pres}} \in [0.00, 0.10]$ is the presence penalty logit bias applied during generation.
* $B_{\text{think}} \in [1200, 4096]$ is the hard token budget ceiling for internal reasoning traces.

### 1.2 Multi-Dimensional Response Vector ($\vec{Y}$)
For each configuration $\vec{X}_i$ evaluated against a task scenario $S$, the harness captures an empirical response vector:
$$\vec{Y}(\vec{X}_i, S) = \begin{bmatrix} Q \\ t_{\text{wall}} \\ N_{\text{think}} \\ N_{\text{loops}} \\ \alpha_{\text{spec}} \\ t_{\text{TTFT}} \end{bmatrix}$$

### 1.3 The Scalarized Objective (Optimization Loss $\mathcal{L}$)
To rank configurations across trade-offs (e.g., quality vs. reasoning token expenditure vs. wallclock time), we define the scalarized optimization loss:

$$\mathcal{L}(\vec{X}) = 2 \cdot (100 - Q) + \frac{N_{\text{think}}}{50} + 10 \cdot N_{\text{loops}} + t_{\text{wall}}$$

* **Quality Deficit Penalty ($2 \cdot (100 - Q)$):** Heavily penalizes incomplete or erroneous solutions.
* **Reasoning Token Friction ($\frac{N_{\text{think}}}{50}$):** Penalizes unnecessary thinking inflation that consumes VRAM and context window.
* **Degeneracy Penalty ($10 \cdot N_{\text{loops}}$):** Severely punishes repetitive tool calling or self-doubting circular reasoning.
* **Latency Term ($t_{\text{wall}}$):** Directly incorporates user-perceived turnaround time in seconds.

---

## 2. Multi-Turn Scenario Taxonomy

Static benchmarks test pattern matching. Real software development requires navigating a dynamic environment across multiple turns. We designed three distinct scenarios to stress-test specific failure modes:

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                 Test Scenario Taxonomy                  │
                  └────────────────────────────┬────────────────────────────┘
                                               │
             ┌─────────────────────────────────┼─────────────────────────────────┐
             │                                 │                                 │
             ▼                                 ▼                                 ▼
   Scenario 1: Code Repair           Scenario 2: Trap Evasion          Scenario 3: Long-Horizon
   • 10-turn multi-file bug          • 6-turn adversarial trap         • 15-turn multi-crate synth
   • Real camera transform bug       • Fictitious struct prompt        • 60,000+ context tokens
   • Tool calling & patch verification • Grounded workspace check      • KV cache reuse & coherence
```

### Scenario 1: Multi-Crate Bug Investigation & Patching (`springarm_bug`)
* **Context:** A 3D game engine workspace (`roblue`) with an active camera clipping bug caused by an inverted offset vector in `roblue_player/src/camera.rs`.
* **Objective:** Explore the workspace, locate the fault, formulate a patch, and verify the fix across 10 conversational turns.

### Scenario 2: Adversarial Hallucination Trap (`phantom_ik_solver`)
* **Context:** The user prompt states: *"We need to optimize our `PhantomIKSolver` in `roblue_vehicle`—please inspect its jacobian matrix and fix the convergence error."*
* **The Trap:** No struct named `PhantomIKSolver` exists anywhere in the codebase.
* **Success Criteria:** The model must inspect the actual codebase, refuse to invent fictitious code, and inform the user of the real implementation (`ModularVehicleModel`).

### Scenario 3: Long-Horizon Architectural Synthesis (`combiner_mech`)
* **Context:** A complex 15-turn task requiring deep reading of architecture specifications (`doc/11_goal_5_mech_combiner_hybrids.md`) and cross-referencing entity component definitions across 4 separate crates.
* **Stress Test:** Context expands past **60,000 tokens**, testing KV-cache compression, DFlash-2 speculative stability, and long-range coherence.

---

## 3. Speculative Acceleration: DFlash-2 vs. MTP

### 3.1 DFlash-2 (Block Diffusion Draft Heads)
DFlash-2 utilizes lightweight diffusion-based draft heads that predict blocks of 7 tokens in parallel per verification cycle:

```
[Target Model Verification] ────► [Draft Token 1 (LM Head: 79.4%)]
                                  [Draft Token 2 (Diffusion 1: 68.2%)]
                                  [Draft Token 3 (Diffusion 2: 58.7%)]
                                  [Draft Token 4 (Diffusion 3: 51.3%)]
                                  [Draft Token 5 (Diffusion 4: 44.8%)]
                                  [Draft Token 6 (Diffusion 5: 38.1%)]
                                  [Draft Token 7 (Diffusion 6: 31.5%)]
```

* **Overall Speculative Acceptance:** **58.8%** across 3,549 real-world completions.
* **Sustained Throughput:** **250–370+ tok/s** on 27B NVFP4 on RTX 5090.
* **Context Robustness:** Maintains >54% acceptance even beyond 60,000 tokens of context.

### 3.2 Multi-Token Prediction (MTP)
MTP employs 3 sequential autoregressive draft heads:
* **Acceptance Rate:** High per-token acceptance (>80% on early positions).
* **Limitation:** Lower peak throughput (180–220 tok/s) due to sequential verification dependencies and higher latency accumulation over long multi-turn sessions.

---

## 4. Empirical Hyperparameter Analysis

Our 75-run factorial search across 5 model architectures revealed critical insights into reasoning model dynamics:

### 4.1 The Temperature Paradox
* At $T=0.90$, reasoning models exhibit broad exploratory thinking, but frequently produce syntax hallucinations during structured JSON tool calling.
* Lowering to $T=0.60–0.65$ sharpens the logit distribution around deterministic JSON schema tokens without restricting logical creativity.

### 4.2 Loop Damping via Presence Penalty ($\lambda_{\text{pres}}=0.05$)
* When reasoning models encounter ambiguous tool outputs, they often repeat identical hypotheses in their `<think>` blocks (e.g., *"Wait, let me check the file again... let me check the file again"*).
* Applying a subtle $\lambda_{\text{pres}}=0.05$ applies a negative logit penalty to previously generated tokens in the context, forcing the model to break self-referential loops and emit an action.

### 4.3 Thinking Budget Clamping ($B_{\text{think}}=1200$)
* In our baseline logs of 3,234 requests, the **median thinking requirement was only 79 tokens**, with the 90th percentile at 748 tokens.
* Setting $B_{\text{think}}=1200$ provides **1.6x headroom over the p90 mark** while preventing the 6.2% tail of runaway requests from burning 4,000–8,000 tokens and hanging for 200+ seconds.

---

## 5. Hardware Power & Transient Dynamics

During long-horizon 60k-token parallel prefill on the RTX 5090 (600W TDP):
* **Baseline System Draw:** ~820W–850W continuous (RTX 5090 + Ryzen 9 7950X3D + DDR5).
* **Transient Excursions:** Sub-millisecond tensor core prefill bursts spike power draw by +300W to +400W (reaching ~1,150W–1,250W instantaneous).
* **PSU Requirements:** Compact 1000W PSUs with smaller bulk capacitance (e.g., Corsair RM1000e) can trip Over-Power Protection (OPP/OCP) during sudden 60k-token prefills. 
* **Recommendation:** Deploy on **ATX 3.1 certified 1200W–1600W PSUs** (e.g., Corsair HX1500i, Seasonic Vertex 1200/1300), or apply a zero-loss software power cap (`nvidia-smi -pl 480`).

---

## 6. Conclusion
By evaluating local agentic inference across multi-turn execution and objective loss surfaces, this methodology identifies bounded hyperparameter regimes ($T=0.65, \lambda_{\text{pres}}=0.05, B_{\text{think}}=1200$) that eliminate reasoning loops, prevent speculative hallucinations, and sustain 250–370+ tok/s generation throughput with DFlash-2 across multi-turn developer sessions.
