# Title:
Empirical benchmark and parameter optimization of Qwen 3.8 27B (NVFP4, DFlash-2, MTP) in multi-turn coding environments

# Body:
I've been trying to select the best model variant and sampling configuration for local multi-turn agentic coding (tool use, multi-file inspection, and refactoring on an RTX 5090 using NInfer). 

Standard static benchmarks don't reflect how reasoning models behave over 10–15 conversational turns. At default parameters ($T \ge 0.90$, open thinking budgets), I ran into two consistent issues:
1. **Reasoning loops:** Models would periodically enter circular deliberation loops in their `<think>` blocks, pushing turn times from ~3s out to 30s–200s+.
2. **Premise hallucination:** When prompted with false premises (referencing non-existent structs or functions), higher temperatures often led the model to invent code rather than check the workspace.

I put together an automated harness to run a 75-run factorial sweep across 5 model variants (Swift 1.5, Swift 1.0, and Base variants with DFlash-2 vs. 3-token MTP) and 5 parameter profiles over 3 multi-turn scenarios (bug investigation, adversarial trap evasion, and 60k-token long-horizon architecture synthesis).

### Summary of observations:
* **Thinking Budget:** Across several thousand requests, median thinking was ~79 tokens (p90 at ~748). Clamping the thinking budget to `1200` eliminated the runaway tail without harming fix quality or trap detection.
* **Presence Penalty:** A small presence penalty (`0.05`) stopped self-referential deliberation loops when tool outputs were ambiguous.
* **Temperature:** Lowering from `0.90` to `0.65` cleaned up structured JSON tool calling schema errors without restricting problem-solving accuracy.
* **Speculative Decoding:** DFlash-2 (7 draft tokens) sustained 250–370+ tok/s with a ~58% acceptance rate across context lengths reaching 60k+ tokens.

### Current configuration:
Based on the optimization loss surface, I am currently using `qwen3.8-27b-swift15-nvfp4full-dflash2` with the following parameters:

```text
Model:              qwen3.8-27b-swift15-nvfp4full-dflash2.ninfer (18.4 GiB, W8G32 embeddings)
Engine:             NInfer (CUDA 13.1, SM 12.0)
Speculative:        dflash2 (7 draft tokens + LM head draft)
Temperature:        0.65
Min-P:              0.05
Presence Penalty:   0.05
Thinking Budget:    1200
Preserve Thinking:  true
Context / Cache:    240,000 tokens (k8v4 KV cache, 8GB pinned host arena)
```

The test runner, methodology writeup, and an interactive Plotly dashboard (with parallel coordinates, loss landscapes, and draft token decay curves) are here:

* **Interactive Dashboard:** https://chupaty.github.io/ninfer-bench/
* **Repository & Data:** https://github.com/chupaty/ninfer-bench

Happy to hear what parameters or speculative configurations others are finding effective for multi-turn local workflows.
