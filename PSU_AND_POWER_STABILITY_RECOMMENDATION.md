# Hardware Power Stability & Incident Analysis Report

**Date:** 2026-09-27  
**System:** `PCLOUNGE` (Windows 11 Pro)  
**Primary Workload:** Local High-Throughput LLM Inference (NInfer / Qwen 3.8 27B NVFP4 / DFlash-2)

---

## 1. Incident Breakdown (09:17:00 AM Sudden Reboot)

### Telemetry & Log Findings
* **Task State:** Turn 13 of 15 (`req#13`, 46 messages) in Scenario 3 (Combiner Mech Long-Horizon Benchmark).
* **Context Size:** Context reached **58,791 tokens** with response-replay KV cache enabled and DFlash-2 speculative decoding running at ~350 tok/s.
* **Failure Mode:** Windows logged **Event ID 41 (Kernel-Power Critical)** on restart with **Bugcheck Code `0`** (all parameters `0x0`).
* **Meaning:** The system experienced a sudden, hard hardware-level power loss / reset before the OS kernel could execute a crash dump handler or write a blue-screen dump.

```
Total Sustained Power Draw under 60k Token Prefill:
- NVIDIA GeForce RTX 5090 (Full Load):        ~600W
- AMD Ryzen 9 7950X3D (PPT Max):              ~162W
- ASRock X670E Pro RS + 64GB DDR5 + NVMe:     ~60W–80W
------------------------------------------------------
Baseline Continuous System Draw:              ~820W–850W
Instantaneous Transient Peak (Tensor Spike):  ~1,100W–1,250W
Current PSU Rated Capacity (Corsair RM1000e): 1,000W
Continuous Load Utilization:                  ~85%–88% (Danger Zone)
```

---

## 2. Hardware Diagnostics

### A. Current Power Supply: Corsair RM1000e (1000W 80+ Gold)
* **The Constraint:** The **RMe** series is Corsair’s compact-footprint (140mm) mainstream Gold tier. Compared to Japanese-capacitor high-hold-up designs (RMx / HX / AX), the RMe has smaller bulk storage capacitors.
* **The Trigger:** When already operating at ~85% continuous capacity, the instantaneous prefill spike of an RTX 5090 at 60,000 tokens depleted the unit’s hold-up reservoir and tripped the PSU's internal **Over-Power / Over-Current Protection (OPP/OCP)**.

### B. Aqua Computer AMPINEL: Capabilities & Limitations
* **What it Does:** The AMPINEL features an active 6-channel load balancer that redistributes current across all six 12V lines of the 12V-2x6 (16-pin) connector to ensure no single pin exceeds 7.5A–8A. It monitors per-pin resistance, voltage drop, and thermals.
* **Why it is Recommended for your RTX 5090:** Under sustained 600W AI inference workloads, it is the best physical safeguard against 12VHPWR connector melting and pin burnout.
* **What it Cannot Do:** It balances current *across connector pins*, but it does not reduce or absorb whole-system power draw. A whole-system transient trip on a 1000W PSU will still occur even with the AMPINEL installed.

---

## 3. Recommended PSU Upgrades (ATX 3.1 / 1200W – 1600W)

For heavy AI/LLM workloads on an RTX 5090, upgrading to an **ATX 3.1 certified 1200W–1600W** unit places continuous load at ~50%–55% (the peak efficiency sweet spot) and provides massive transient excursion headroom (>2,400W peak tolerance for 100µs).

### Top Tier Recommendations:
1. **Corsair HX1500i / AX1600i (1500W / 1600W Platinum/Titanium)**
   * Digital DSP power control, GaN FETs (AX1600i), 100% Japanese 105°C capacitors, USB telemetry for real-time wattage/current monitoring in iCUE / HWiNFO.
2. **Seasonic Vertex PX-1200 / GX-1300 or Prime TX-1300 / TX-1600 (ATX 3.0 / 3.1)**
   * Market-leading transient suppression, ultra-low ripple (<20mV), 12-year warranty, dedicated native 12V-2x6 cabling.
3. **be quiet! Dark Power Pro 13 (1300W / 1600W Titanium)**
   * Digital regulation, individual rail OCP/OPP overclocking key, massive bulk capacitance.
4. **Corsair RM1200x SHIFT (1200W Gold ATX 3.1)**
   * High-capacity Japanese capacitors, side-cable interface, excellent transient budget.

---

## 4. Immediate Zero-Cost Software Mitigation (Right Now)

Until you upgrade your PSU, you can completely eliminate power trips during long-context benchmarks by capping the RTX 5090’s maximum continuous power draw to **480W** (a 120W reduction from the 600W ceiling).

### Why There Is Zero Real Performance Penalty:
* LLM autoregressive generation (decode) and KV-cache lookups are **memory-bandwidth bound**, not core-clock bound.
* Capping power from 600W to 480W drops total system peak draw by ~150W, keeping the RM1000e well under 700W total baseline without noticeable impact on tok/s.

### Commands:

#### To apply for the current Windows session:
```powershell
nvidia-smi -pl 480
```

#### To revert back to factory default (600W):
```powershell
nvidia-smi -pl 600
```
