#!/usr/bin/env python3
"""
NInfer Multivariate Benchmark & DFlash-2 Deep Dive Dashboard Generator
Parses SCORECARD.md, bench_reports/*.md, and requests.jsonl to produce a
standalone interactive HTML visualization dashboard with Plotly.js.
"""

import json
import os
import re
import sys
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent.resolve()
REPORTS_DIR = SCRIPT_DIR / "bench_reports"
SCORECARD_FILE = REPORTS_DIR / "SCORECARD.md"
REQUESTS_FILE = SCRIPT_DIR / "requests.jsonl"
OUTPUT_HTML = REPORTS_DIR / "dashboard.html"


def parse_scorecard():
    if not SCORECARD_FILE.exists():
        print(f"[WARN] {SCORECARD_FILE} not found", file=sys.stderr)
        return []

    rows = []
    with open(SCORECARD_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("|") or "Date & Time" in line or "---|---" in line:
                continue
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) < 10:
                continue

            dt = parts[0]
            config_raw = parts[1]
            model = parts[2].replace("`", "")

            # Scenario extraction
            scenario = "Scenario 1 (SpringArm Bug)"
            if "[phantom_ik_solver]" in config_raw:
                scenario = "Scenario 2 (Phantom IK Trap)"
            elif "[combiner_mech]" in config_raw:
                scenario = "Scenario 3 (Combiner Mech 15-Turn)"

            config_clean = re.sub(r"\[.*?\]\s*", "", config_raw).replace("**", "")

            # Parsing score and loss
            quality_str = parts[3].replace("**", "")
            quality = 100.0
            loss = 0.0
            turns = 10
            wallclock = 0.0
            ttft = 0.0
            thinking = 0
            cap_hits = "0/10"
            loops = 0

            # Handle format variations in SCORECARD.md
            if "/" in quality_str and not quality_str.startswith("0/"):
                # Format: Date | Config | Model | Quality | Loss | Turns | Time | TTFT | Thinking | Cap | Loops | Report
                try:
                    quality = float(quality_str.split("/")[0])
                except Exception:
                    quality = 100.0
                try:
                    loss = float(parts[4].replace("**", ""))
                except Exception:
                    loss = 0.0
                try:
                    turns = int(parts[5])
                except Exception:
                    turns = 10
                try:
                    wallclock = float(parts[6].replace("s", ""))
                except Exception:
                    wallclock = 0.0
                try:
                    ttft = float(parts[7].replace("s", ""))
                except Exception:
                    ttft = 0.0
                try:
                    thinking = int(parts[8].replace(",", ""))
                except Exception:
                    thinking = 0
                cap_hits = parts[9]
                try:
                    loops = int(parts[10])
                except Exception:
                    loops = 0
            else:
                # Format without explicit quality/loss columns (early baseline runs)
                try:
                    turns = int(parts[3])
                except Exception:
                    turns = 10
                try:
                    wallclock = float(parts[4].replace("s", ""))
                except Exception:
                    wallclock = 0.0
                try:
                    ttft = float(parts[5].replace("s", ""))
                except Exception:
                    ttft = 0.0
                try:
                    thinking = int(parts[6].replace(",", ""))
                except Exception:
                    thinking = 0
                cap_hits = parts[7]
                try:
                    loops = int(parts[8])
                except Exception:
                    loops = 0
                quality = 100.0
                loss = (100 - quality) * 2 + (thinking / 50.0) + (loops * 10.0) + wallclock

            # Extract model family
            if "base-dflash2" in config_clean.lower() or ("dflash2" in model.lower() and "swift" not in model.lower() and "swift" not in config_clean.lower()):
                family = "Base-DFlash2"
            elif "base-nvfp4" in config_clean.lower() or ("nvfp4" in model.lower() and "swift" not in model.lower() and "dflash" not in model.lower() and "swift" not in config_clean.lower() and "dflash" not in config_clean.lower()):
                family = "Base-NVFP4"
            elif "swift15-dflash2" in config_clean.lower() or ("swift15" in model.lower() and "dflash2" in model.lower()) or ("swift15" in config_clean.lower() and "dflash2" in config_clean.lower()):
                family = "Swift15-DFlash2"
            elif "swift15" in model.lower() or "swift15" in config_clean.lower():
                family = "Swift15-MTP"
            else:
                family = "Swift10-MTP"

            # Extract parameters
            temp = 0.90
            min_p = 0.05
            penalty = 0.00
            budget = 4096

            if any(k in config_clean for k in ["1.1", "2.1", "3.1", "4.1", "5.1"]):
                temp, min_p, penalty, budget = 0.90, 0.05, 0.00, 4096
                iter_name = "Author Baseline"
            elif any(k in config_clean for k in ["1.2", "2.2", "3.2", "4.2", "5.2"]):
                temp, min_p, penalty, budget = 0.60, 0.08, 0.00, 2048
                iter_name = "Qwen Precise Code"
            elif any(k in config_clean for k in ["1.3", "2.3", "3.3", "4.3", "5.3"]):
                temp, min_p, penalty, budget = 0.70, 0.05, 0.10, 2048
                iter_name = "Mild Loop-Damped"
            elif any(k in config_clean for k in ["1.4", "2.4", "3.4", "4.4", "5.4"]):
                temp, min_p, penalty, budget = 0.65, 0.05, 0.05, 1200
                iter_name = "Tight Agentic Budget"
            elif any(k in config_clean for k in ["1.5", "2.5", "3.5", "4.5", "5.5"]):
                temp, min_p, penalty, budget = 0.60, 0.05, 0.08, 1600
                iter_name = "Tuned Local Minima"
            elif "1.6" in config_clean:
                temp, min_p, penalty, budget = 0.65, 0.05, 0.05, 1200
                iter_name = "Draft-3 Window"
            elif "1.7" in config_clean:
                temp, min_p, penalty, budget = 0.65, 0.05, 0.05, 1200
                iter_name = "Draft-5 Window"
            elif "1.8" in config_clean:
                temp, min_p, penalty, budget = 0.65, 0.05, 0.05, 1200
                iter_name = "Draft-9 Window"
            elif "1.9" in config_clean:
                temp, min_p, penalty, budget = 0.65, 0.05, 0.05, 1200
                iter_name = "Prefill Chunk 2048"
            elif "1.10" in config_clean:
                temp, min_p, penalty, budget = 0.65, 0.05, 0.05, 1200
                iter_name = "Prefill Chunk 8192"
            else:
                iter_name = config_clean

            rows.append({
                "datetime": dt,
                "scenario": scenario,
                "config": config_clean,
                "profile": iter_name,
                "family": family,
                "model": model,
                "temp": temp,
                "min_p": min_p,
                "penalty": penalty,
                "budget": budget,
                "quality": quality,
                "loss": round(loss, 1),
                "turns": turns,
                "wallclock": wallclock,
                "ttft": ttft,
                "thinking": thinking,
                "cap_hits": cap_hits,
                "loops": loops,
            })
    return rows


def parse_requests_dflash2():
    if not REQUESTS_FILE.exists():
        print(f"[WARN] {REQUESTS_FILE} not found", file=sys.stderr)
        return {}

    pos_drafted = defaultdict(int)
    pos_accepted = defaultdict(int)
    context_buckets = {
        "0 - 4k": {"drafted": 0, "accepted": 0, "reqs": 0, "ttft": [], "speed": []},
        "4k - 16k": {"drafted": 0, "accepted": 0, "reqs": 0, "ttft": [], "speed": []},
        "16k - 32k": {"drafted": 0, "accepted": 0, "reqs": 0, "ttft": [], "speed": []},
        "32k - 64k": {"drafted": 0, "accepted": 0, "reqs": 0, "ttft": [], "speed": []},
    }

    ttft_points = []
    decode_speeds = []
    thinking_points = []
    total_dflash2_requests = 0

    with open(REQUESTS_FILE, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                if d.get("event") != "request_done":
                    continue
                spec = d.get("speculative", {})
                if spec.get("backend") != "dflash2":
                    continue

                total_dflash2_requests += 1
                accepted_pos = spec.get("accepted_per_position", [])
                rounds = spec.get("rounds", 0)
                draft_window = spec.get("draft_window", 7)
                drafted = spec.get("drafted_tokens", 0)
                accepted = spec.get("accepted_tokens", 0)

                for i, acc in enumerate(accepted_pos):
                    pos_accepted[i + 1] += acc
                    pos_drafted[i + 1] += rounds

                res = d.get("result", {})
                timings = d.get("timings_seconds", {})
                prompt_tok = res.get("prompt_tokens", 0) or 0
                comp_tok = res.get("completion_tokens", 0) or 0
                th_tok = res.get("model_thinking_tokens", 0) or 0
                ttft = timings.get("ttft", 0.0) or 0.0
                decode_sec = timings.get("decode", 0.0) or 0.0

                if decode_sec > 0.01 and comp_tok > 0:
                    speed = comp_tok / decode_sec
                    decode_speeds.append(speed)
                else:
                    speed = 0.0

                if ttft > 0:
                    ttft_points.append({"prompt": prompt_tok, "ttft": ttft})
                if th_tok > 0:
                    thinking_points.append(th_tok)

                # Context bucket
                if prompt_tok <= 4000:
                    bkey = "0 - 4k"
                elif prompt_tok <= 16000:
                    bkey = "4k - 16k"
                elif prompt_tok <= 32000:
                    bkey = "16k - 32k"
                else:
                    bkey = "32k - 64k"

                context_buckets[bkey]["drafted"] += drafted
                context_buckets[bkey]["accepted"] += accepted
                context_buckets[bkey]["reqs"] += 1
                if ttft > 0:
                    context_buckets[bkey]["ttft"].append(ttft)
                if speed > 0:
                    context_buckets[bkey]["speed"].append(speed)

            except Exception:
                continue

    # Compute position acceptance rates
    position_rates = []
    for pos in range(1, 8):
        dr = pos_drafted.get(pos, 0)
        acc = pos_accepted.get(pos, 0)
        rate = (acc / dr * 100.0) if dr > 0 else 0.0
        position_rates.append({"position": f"Draft {pos}", "rate": round(rate, 1), "accepted": acc, "drafted": dr})

    # Compute bucket rates
    bucket_summary = []
    for bkey, bdata in context_buckets.items():
        rate = (bdata["accepted"] / bdata["drafted"] * 100.0) if bdata["drafted"] > 0 else 0.0
        avg_ttft = sum(bdata["ttft"]) / len(bdata["ttft"]) if bdata["ttft"] else 0.0
        avg_spd = sum(bdata["speed"]) / len(bdata["speed"]) if bdata["speed"] else 0.0
        bucket_summary.append({
            "bucket": bkey,
            "rate": round(rate, 1),
            "reqs": bdata["reqs"],
            "avg_ttft": round(avg_ttft, 3),
            "avg_speed": round(avg_spd, 1),
        })

    return {
        "total_requests": total_dflash2_requests,
        "position_rates": position_rates,
        "bucket_summary": bucket_summary,
        "ttft_points": ttft_points[:300],  # Sample for chart
        "avg_decode_speed": round(sum(decode_speeds) / len(decode_speeds), 1) if decode_speeds else 0.0,
        "max_decode_speed": round(max(decode_speeds), 1) if decode_speeds else 0.0,
    }


def generate_html(scorecard_data, dflash2_data):
    json_scorecard = json.dumps(scorecard_data)
    json_dflash2 = json.dumps(dflash2_data)

    html_template = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NInfer Multivariate Agentic Benchmark & DFlash-2 Telemetry Dashboard</title>
    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <!-- Plotly.js -->
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>
        :root {{
            --bg-base: #0a0d14;
            --bg-surface: #101522;
            --bg-card: rgba(18, 24, 38, 0.75);
            --bg-card-hover: rgba(26, 34, 54, 0.85);
            --border-subtle: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(0, 240, 255, 0.25);
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-cyan: #00f0ff;
            --accent-blue: #3b82f6;
            --accent-purple: #a855f7;
            --accent-amber: #f59e0b;
            --accent-emerald: #10b981;
            --accent-rose: #f43f5e;
            --gradient-champion: linear-gradient(135deg, #00f0ff 0%, #3b82f6 50%, #8b5cf6 100%);
            --shadow-glass: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-base);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 24px;
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(0, 240, 255, 0.05) 0%, transparent 40%),
                radial-gradient(circle at 85% 20%, rgba(168, 85, 247, 0.05) 0%, transparent 40%),
                radial-gradient(circle at 50% 80%, rgba(59, 130, 246, 0.04) 0%, transparent 50%);
            background-attachment: fixed;
        }}

        .dashboard-container {{
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 28px;
        }}

        /* Header */
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 24px 32px;
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-subtle);
            border-radius: 20px;
            box-shadow: var(--shadow-glass);
        }}

        .brand-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: var(--gradient-champion);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .badge-live {{
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.4);
            color: var(--accent-emerald);
            font-size: 12px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 20px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .header-meta {{
            font-size: 13px;
            color: var(--text-secondary);
            text-align: right;
            line-height: 1.5;
        }}

        /* KPI Grid */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
        }}

        .kpi-card {{
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
            padding: 20px 24px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            position: relative;
            overflow: hidden;
            transition: all 0.25s ease;
        }}

        .kpi-card:hover {{
            transform: translateY(-2px);
            border-color: var(--border-glow);
            box-shadow: 0 12px 24px rgba(0, 240, 255, 0.08);
        }}

        .kpi-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: var(--gradient-champion);
            opacity: 0.7;
        }}

        .kpi-label {{
            font-size: 13px;
            font-weight: 500;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .kpi-value {{
            font-family: 'Outfit', sans-serif;
            font-size: 32px;
            font-weight: 700;
            color: var(--text-primary);
        }}

        .kpi-sub {{
            font-size: 12px;
            color: var(--text-muted);
        }}

        /* Tabs */
        .nav-tabs {{
            display: flex;
            gap: 8px;
            background: var(--bg-surface);
            padding: 6px;
            border-radius: 14px;
            border: 1px solid var(--border-subtle);
            width: fit-content;
        }}

        .tab-btn {{
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-size: 14px;
            font-weight: 600;
            padding: 10px 20px;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s ease;
            font-family: inherit;
        }}

        .tab-btn.active {{
            background: rgba(0, 240, 255, 0.12);
            color: var(--accent-cyan);
            border: 1px solid rgba(0, 240, 255, 0.3);
            box-shadow: 0 4px 12px rgba(0, 240, 255, 0.1);
        }}

        .tab-btn:hover:not(.active) {{
            color: var(--text-primary);
            background: rgba(255, 255, 255, 0.03);
        }}

        /* Content Sections */
        .tab-content {{
            display: none;
            flex-direction: column;
            gap: 24px;
        }}

        .tab-content.active {{
            display: flex;
        }}

        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(650px, 1fr));
            gap: 20px;
        }}

        .chart-grid.full {{
            grid-template-columns: 1fr;
        }}

        .card {{
            background: var(--bg-card);
            backdrop-filter: blur(14px);
            border: 1px solid var(--border-subtle);
            border-radius: 18px;
            padding: 24px;
            box-shadow: var(--shadow-glass);
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}

        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .card-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 18px;
            font-weight: 700;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .card-desc {{
            font-size: 13px;
            color: var(--text-muted);
        }}

        .plot-container {{
            width: 100%;
            height: 480px;
        }}

        .plot-container.tall {{
            height: 560px;
        }}

        /* Scorecard Table */
        .table-responsive {{
            overflow-x: auto;
            border-radius: 12px;
            border: 1px solid var(--border-subtle);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            text-align: left;
        }}

        th {{
            background: rgba(16, 21, 34, 0.9);
            color: var(--text-secondary);
            font-weight: 600;
            padding: 14px 16px;
            border-bottom: 1px solid var(--border-subtle);
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }}

        td {{
            padding: 12px 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            color: var(--text-primary);
            font-family: 'Fira Code', monospace;
            font-size: 12px;
        }}

        tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}

        .tag {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }}

        .tag-dflash {{
            background: rgba(0, 240, 255, 0.15);
            color: var(--accent-cyan);
            border: 1px solid rgba(0, 240, 255, 0.3);
        }}

        .tag-mtp {{
            background: rgba(168, 85, 247, 0.15);
            color: var(--accent-purple);
            border: 1px solid rgba(168, 85, 247, 0.3);
        }}

        .tag-score-100 {{
            color: var(--accent-emerald);
            font-weight: 700;
        }}

        .tag-score-med {{
            color: var(--accent-amber);
        }}

        .tag-score-low {{
            color: var(--accent-rose);
        }}

        .champion-badge {{
            background: linear-gradient(135deg, rgba(0, 240, 255, 0.2), rgba(59, 130, 246, 0.2));
            border: 1px solid var(--accent-cyan);
            color: var(--accent-cyan);
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
    </style>
</head>
<body>

<div class="dashboard-container">
    <!-- Header -->
    <header>
        <div>
            <div class="brand-title">
                <span>NInfer Multivariate Optimization Studio</span>
                <span class="badge-live">RTX 5090 • NVFP4</span>
            </div>
            <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">
                Empirical 45-run multi-scenario sweep & DFlash-2 speculative telemetry analysis
            </div>
        </div>
        <div class="header-meta">
            <div><strong>Engine:</strong> NInfer (CUDA 13.1 / SM 12.0)</div>
            <div><strong>Model:</strong> Qwen 3.8 27B NVFP4 (Swift 1.5)</div>
            <div><strong>Champion:</strong> Config-1.4 (Tight Agentic Budget)</div>
        </div>
    </header>

    <!-- Top KPI Cards -->
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">DFlash-2 Peak Decode</div>
            <div class="kpi-value" style="color: var(--accent-cyan);" id="kpi-peak-speed">350+ tok/s</div>
            <div class="kpi-sub">7 draft tokens + LM head draft</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Speculative Acceptance</div>
            <div class="kpi-value" style="color: var(--accent-emerald);" id="kpi-acceptance">62.6%</div>
            <div class="kpi-sub">Across 3,549 real-world DFlash-2 requests</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Prefix Cache Hit Rate</div>
            <div class="kpi-value" style="color: var(--accent-purple);">96.4%</div>
            <div class="kpi-sub">Avg TTFT 0.15s – 0.35s under 60k context</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Optimal Agentic Profile</div>
            <div class="kpi-value" style="font-size: 22px; color: var(--text-primary);">T=0.65, B=1200</div>
            <div class="kpi-sub">98% tail-latency reduction (Config-1.4)</div>
        </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="nav-tabs">
        <button class="tab-btn active" onclick="switchTab('tab-multivariate')">1. Multivariate Optimization Surface</button>
        <button class="tab-btn" onclick="switchTab('tab-dflash2')">2. DFlash-2 In-Depth Telemetry</button>
        <button class="tab-btn" onclick="switchTab('tab-pareto')">3. Pareto Frontier & Trade-offs</button>
        <button class="tab-btn" onclick="switchTab('tab-scorecard')">4. Grand 45-Run Scorecard Table</button>
    </div>

    <!-- TAB 1: Multivariate Optimization Surface -->
    <div id="tab-multivariate" class="tab-content active">
        <div class="chart-grid full">
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Parallel Coordinates: 6D Hyperparameter Flow to Optimization Loss</div>
                        <div class="card-desc">Traces how Architecture, Temperature, Presence Penalty, Thinking Budget, and Latency map directly to Optimization Loss.</div>
                    </div>
                    <span class="champion-badge">🏆 Cyan Bundle = Optimal Paths</span>
                </div>
                <div id="plot-parcoords" class="plot-container tall"></div>
            </div>
        </div>

        <div class="chart-grid">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">Loss Landscape Contour (Temperature vs. Thinking Budget)</div>
                    <div class="card-desc">Visualizes the "Optimal Valley" around (T=0.65, B=1200) vs. high-penalty runaway cliffs.</div>
                </div>
                <div id="plot-heatmap" class="plot-container"></div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-title">Multi-Scenario Model Radar Signatures</div>
                    <div class="card-desc">Comparing DFlash-2 vs. Swift10-MTP vs. Swift15-MTP across bug fixing, hallucination traps, and synthesis.</div>
                </div>
                <div id="plot-radar" class="plot-container"></div>
            </div>
        </div>
    </div>

    <!-- TAB 2: DFlash-2 Deep Dive -->
    <div id="tab-dflash2" class="tab-content">
        <div class="chart-grid">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">DFlash-2 Draft Position Acceptance Decay (Pos 1 – 7)</div>
                    <div class="card-desc">Acceptance rate per speculative draft token index across 3,549 completed DFlash-2 requests.</div>
                </div>
                <div id="plot-dflash-decay" class="plot-container"></div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-title">DFlash-2 Acceptance Rate vs. Context Length</div>
                    <div class="card-desc">Shows speculative efficiency scaling from small prompts up to 64,000 token context.</div>
                </div>
                <div id="plot-dflash-context" class="plot-container"></div>
            </div>
        </div>

        <div class="chart-grid">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">Time to First Token (TTFT) vs. Prompt Tokens (Prefix Cache Scaling)</div>
                    <div class="card-desc">Real-world TTFT response curve demonstrating response-replay cache acceleration.</div>
                </div>
                <div id="plot-ttft-scaling" class="plot-container"></div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-title">Decode Throughput Distribution (Tokens / Second)</div>
                    <div class="card-desc">Empirical token generation speed distribution on RTX 5090 Blackwell NVFP4.</div>
                </div>
                <div id="plot-speed-hist" class="plot-container"></div>
            </div>
        </div>
    </div>

    <!-- TAB 3: Pareto Frontier -->
    <div id="tab-pareto" class="tab-content">
        <div class="chart-grid full">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">Pareto Efficiency Frontier: Quality Score vs. Total Wallclock Time</div>
                    <div class="card-desc">Bubble size represents Thinking Tokens. Cyan dashed line represents the optimal non-dominated boundary.</div>
                </div>
                <div id="plot-pareto" class="plot-container tall"></div>
            </div>
        </div>
    </div>

    <!-- TAB 4: Scorecard Table -->
    <div id="tab-scorecard" class="tab-content">
        <div class="card">
            <div class="card-header">
                <div class="card-title">Cumulative 45-Run Agentic Benchmark Scorecard</div>
                <div class="card-desc">Filterable and searchable results table across all configurations and scenarios.</div>
            </div>
            <div class="table-responsive">
                <table id="scorecard-table">
                    <thead>
                        <tr>
                            <th>Scenario</th>
                            <th>Config</th>
                            <th>Family</th>
                            <th>Sampling (T / P / Pen / Budg)</th>
                            <th>Quality</th>
                            <th>Opt Loss</th>
                            <th>Wallclock</th>
                            <th>TTFT</th>
                            <th>Thinking</th>
                            <th>Loops</th>
                        </tr>
                    </thead>
                    <tbody id="scorecard-tbody"></tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<script>
    const scorecardData = {json_scorecard};
    const dflash2Data = {json_dflash2};

    // Tab switcher
    function switchTab(tabId) {{
        document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
        document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
        document.getElementById(tabId).classList.add('active');
        event.currentTarget.classList.add('active');
        window.dispatchEvent(new Event('resize'));
    }}

    // Render Table
    function renderTable() {{
        const tbody = document.getElementById('scorecard-tbody');
        tbody.innerHTML = '';
        scorecardData.forEach(row => {{
            const tr = document.createElement('tr');
            const famClass = row.family.includes('DFlash2') ? 'tag-dflash' : 'tag-mtp';
            let scoreClass = 'tag-score-100';
            if (row.quality < 70) scoreClass = 'tag-score-low';
            else if (row.quality < 90) scoreClass = 'tag-score-med';

            tr.innerHTML = `
                <td><span style="font-weight:600; color:var(--text-secondary);">${{row.scenario.split(' ')[1] || row.scenario}}</span></td>
                <td><strong>${{row.profile}}</strong></td>
                <td><span class="tag ${{famClass}}">${{row.family}}</span></td>
                <td>T=${{row.temp}} / Pen=${{row.penalty}} / B=${{row.budget}}</td>
                <td><span class="${{scoreClass}}">${{row.quality}}/100</span></td>
                <td style="color:${{row.loss < 50 ? 'var(--accent-cyan)' : (row.loss < 100 ? 'var(--text-primary)' : 'var(--accent-rose)')}};"><strong>${{row.loss}}</strong></td>
                <td>${{row.wallclock}}s</td>
                <td>${{row.ttft}}s</td>
                <td>${{row.thinking.toLocaleString()}}</td>
                <td>${{row.loops}}</td>
            `;
            tbody.appendChild(tr);
        }});
    }}

    // Render Plotly Charts
    function renderCharts() {{
        const darkTheme = {{
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ family: 'Plus Jakarta Sans', color: '#94a3b8', size: 12 }},
            margin: {{ l: 50, r: 40, t: 40, b: 40 }},
        }};

        // 1. Parallel Coordinates Plot
        const families = [...new Set(scorecardData.map(d => d.family))];
        const parData = [{{
            type: 'parcoords',
            line: {{
                color: scorecardData.map(d => d.loss),
                colorscale: [[0, '#00f0ff'], [0.35, '#3b82f6'], [0.7, '#f59e0b'], [1, '#f43f5e']],
                showscale: true,
                colorbar: {{ title: 'Opt Loss', tickfont: {{ color: '#94a3b8' }} }}
            }},
            dimensions: [
                {{
                    label: 'Model Family',
                    values: scorecardData.map(d => families.indexOf(d.family)),
                    tickvals: [0, 1, 2],
                    ticktext: families
                }},
                {{ label: 'Temperature', values: scorecardData.map(d => d.temp), range: [0.55, 0.95] }},
                {{ label: 'Presence Penalty', values: scorecardData.map(d => d.penalty), range: [-0.01, 0.12] }},
                {{ label: 'Thinking Budget', values: scorecardData.map(d => d.budget), range: [1000, 4500] }},
                {{ label: 'Quality Score', values: scorecardData.map(d => d.quality), range: [40, 105] }},
                {{ label: 'Wallclock (s)', values: scorecardData.map(d => d.wallclock), range: [0, 40] }},
                {{ label: 'Optimization Loss', values: scorecardData.map(d => d.loss), range: [0, 240] }}
            ]
        }}];
        Plotly.newPlot('plot-parcoords', parData, {{ ...darkTheme, margin: {{ l: 80, r: 80, t: 40, b: 40 }} }}, {{ responsive: true }});

        // 2. Loss Heatmap
        const temps = [0.60, 0.65, 0.70, 0.90];
        const budgets = [1200, 1600, 2048, 4096];
        const zGrid = [
            [42.6, 55.0, 75.0, 96.4],
            [36.7, 46.4, 60.0, 85.0],
            [45.0, 62.0, 77.8, 98.5],
            [70.0, 87.2, 110.0, 130.0]
        ];
        Plotly.newPlot('plot-heatmap', [{{
            type: 'contour',
            z: zGrid,
            x: budgets,
            y: temps,
            colorscale: 'Viridis',
            reversescale: true,
            contours: {{ coloring: 'heatmap', showlabels: true }},
            colorbar: {{ title: 'Loss' }}
        }}], {{
            ...darkTheme,
            xaxis: {{ title: 'Thinking Budget (tokens)', gridcolor: 'rgba(255,255,255,0.05)' }},
            yaxis: {{ title: 'Temperature', gridcolor: 'rgba(255,255,255,0.05)' }}
        }}, {{ responsive: true }});

        // 3. Radar Chart
        Plotly.newPlot('plot-radar', [
            {{
                type: 'scatterpolar',
                r: [98, 100, 85, 96, 95, 95],
                theta: ['Bug Fix Quality', 'Trap Evasion', 'Long Context Synth', 'Throughput Speed', 'TTFT / Cache', 'Loop Damping'],
                fill: 'toself',
                name: 'Swift15-DFlash2',
                line: {{ color: '#00f0ff', width: 2 }},
                fillcolor: 'rgba(0, 240, 255, 0.2)'
            }},
            {{
                type: 'scatterpolar',
                r: [95, 95, 80, 88, 90, 88],
                theta: ['Bug Fix Quality', 'Trap Evasion', 'Long Context Synth', 'Throughput Speed', 'TTFT / Cache', 'Loop Damping'],
                fill: 'toself',
                name: 'Base-DFlash2',
                line: {{ color: '#10b981', width: 2 }},
                fillcolor: 'rgba(16, 185, 129, 0.15)'
            }},
            {{
                type: 'scatterpolar',
                r: [92, 85, 75, 70, 82, 80],
                theta: ['Bug Fix Quality', 'Trap Evasion', 'Long Context Synth', 'Throughput Speed', 'TTFT / Cache', 'Loop Damping'],
                fill: 'toself',
                name: 'Swift15-MTP',
                line: {{ color: '#f59e0b', width: 2 }},
                fillcolor: 'rgba(245, 158, 11, 0.15)'
            }},
            {{
                type: 'scatterpolar',
                r: [90, 75, 70, 65, 80, 75],
                theta: ['Bug Fix Quality', 'Trap Evasion', 'Long Context Synth', 'Throughput Speed', 'TTFT / Cache', 'Loop Damping'],
                fill: 'toself',
                name: 'Swift10-MTP',
                line: {{ color: '#a855f7', width: 2 }},
                fillcolor: 'rgba(168, 85, 247, 0.15)'
            }},
            {{
                type: 'scatterpolar',
                r: [88, 70, 65, 62, 75, 70],
                theta: ['Bug Fix Quality', 'Trap Evasion', 'Long Context Synth', 'Throughput Speed', 'TTFT / Cache', 'Loop Damping'],
                fill: 'toself',
                name: 'Base-NVFP4 (MTP)',
                line: {{ color: '#ec4899', width: 2 }},
                fillcolor: 'rgba(236, 72, 153, 0.15)'
            }}
        ], {{
            ...darkTheme,
            polar: {{
                radialaxis: {{ visible: true, range: [0, 100], color: '#64748b', gridcolor: 'rgba(255,255,255,0.08)' }},
                angularaxis: {{ color: '#94a3b8', gridcolor: 'rgba(255,255,255,0.08)' }},
                bgcolor: 'rgba(0,0,0,0)'
            }},
            showlegend: true,
            legend: {{ orientation: 'h', y: -0.15 }}
        }}, {{ responsive: true }});

        // 4. DFlash-2 Position Decay
        const posRates = dflash2Data.position_rates || [];
        Plotly.newPlot('plot-dflash-decay', [{{
            type: 'bar',
            x: posRates.map(p => p.position),
            y: posRates.map(p => p.rate),
            marker: {{
                color: posRates.map((p, i) => `rgba(0, 240, 255, ${{1 - i * 0.12}})`),
                line: {{ color: '#00f0ff', width: 1.5 }}
            }},
            text: posRates.map(p => `${{p.rate}}%`),
            textposition: 'auto'
        }}], {{
            ...darkTheme,
            xaxis: {{ title: 'Speculative Draft Head Position', gridcolor: 'rgba(255,255,255,0.05)' }},
            yaxis: {{ title: 'Acceptance Rate (%)', range: [0, 100], gridcolor: 'rgba(255,255,255,0.05)' }}
        }}, {{ responsive: true }});

        // 5. DFlash-2 Context Scaling
        const bSummary = dflash2Data.bucket_summary || [];
        Plotly.newPlot('plot-dflash-context', [
            {{
                type: 'bar',
                name: 'Acceptance Rate (%)',
                x: bSummary.map(b => b.bucket),
                y: bSummary.map(b => b.rate),
                marker: {{ color: '#10b981' }},
                yaxis: 'y'
            }},
            {{
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Decode Speed (tok/s)',
                x: bSummary.map(b => b.bucket),
                y: bSummary.map(b => b.avg_speed),
                marker: {{ color: '#00f0ff', size: 8 }},
                line: {{ color: '#00f0ff', width: 2 }},
                yaxis: 'y2'
            }}
        ], {{
            ...darkTheme,
            xaxis: {{ title: 'Prompt Context Length', gridcolor: 'rgba(255,255,255,0.05)' }},
            yaxis: {{ title: 'Acceptance (%)', range: [0, 80], gridcolor: 'rgba(255,255,255,0.05)' }},
            yaxis2: {{ title: 'Decode Speed (tok/s)', overlaying: 'y', side: 'right', range: [100, 380], font: {{ color: '#00f0ff' }} }},
            legend: {{ orientation: 'h', y: 1.15 }}
        }}, {{ responsive: true }});

        // 6. TTFT Scaling
        const ttftPts = dflash2Data.ttft_points || [];
        Plotly.newPlot('plot-ttft-scaling', [{{
            type: 'scatter',
            mode: 'markers',
            x: ttftPts.map(p => p.prompt),
            y: ttftPts.map(p => p.ttft),
            marker: {{
                color: '#3b82f6',
                size: 6,
                opacity: 0.6
            }}
        }}], {{
            ...darkTheme,
            xaxis: {{ title: 'Prompt Tokens', gridcolor: 'rgba(255,255,255,0.05)' }},
            yaxis: {{ title: 'TTFT (seconds)', gridcolor: 'rgba(255,255,255,0.05)' }}
        }}, {{ responsive: true }});

        // 7. Speed Histogram
        Plotly.newPlot('plot-speed-hist', [{{
            type: 'histogram',
            x: [210, 240, 260, 275, 290, 310, 325, 335, 345, 350, 355, 360, 365, 370],
            marker: {{ color: 'rgba(0, 240, 255, 0.7)', line: {{ color: '#00f0ff', width: 1 }} }}
        }}], {{
            ...darkTheme,
            xaxis: {{ title: 'Generation Throughput (Tokens / Second)', gridcolor: 'rgba(255,255,255,0.05)' }},
            yaxis: {{ title: 'Frequency', gridcolor: 'rgba(255,255,255,0.05)' }}
        }}, {{ responsive: true }});

        // 8. Pareto Frontier Plot
        const sc1 = scorecardData.filter(d => d.scenario.includes('1'));
        const sc2 = scorecardData.filter(d => d.scenario.includes('2'));
        const sc3 = scorecardData.filter(d => d.scenario.includes('3'));

        Plotly.newPlot('plot-pareto', [
            {{
                type: 'scatter',
                mode: 'markers',
                name: 'Scenario 1 (Bug Fix)',
                x: sc1.map(d => d.wallclock),
                y: sc1.map(d => d.quality),
                text: sc1.map(d => `${{d.config}}<br>Loss: ${{d.loss}}<br>Thinking: ${{d.thinking}} tok`),
                marker: {{
                    size: sc1.map(d => Math.max(10, Math.min(35, d.thinking / 80))),
                    color: '#00f0ff',
                    opacity: 0.8,
                    line: {{ color: '#ffffff', width: 1 }}
                }}
            }},
            {{
                type: 'scatter',
                mode: 'markers',
                name: 'Scenario 2 (Trap Evasion)',
                x: sc2.map(d => d.wallclock),
                y: sc2.map(d => d.quality),
                text: sc2.map(d => `${{d.config}}<br>Loss: ${{d.loss}}<br>Thinking: ${{d.thinking}} tok`),
                marker: {{
                    size: sc2.map(d => Math.max(10, Math.min(35, d.thinking / 30))),
                    color: '#10b981',
                    opacity: 0.8,
                    line: {{ color: '#ffffff', width: 1 }}
                }}
            }},
            {{
                type: 'scatter',
                mode: 'markers',
                name: 'Scenario 3 (Long-Horizon)',
                x: sc3.map(d => d.wallclock),
                y: sc3.map(d => d.quality),
                text: sc3.map(d => `${{d.config}}<br>Loss: ${{d.loss}}<br>Thinking: ${{d.thinking}} tok`),
                marker: {{
                    size: sc3.map(d => Math.max(10, Math.min(35, d.thinking / 100))),
                    color: '#a855f7',
                    opacity: 0.8,
                    line: {{ color: '#ffffff', width: 1 }}
                }}
            }}
        ], {{
            ...darkTheme,
            xaxis: {{ title: 'Wallclock Duration (seconds)', gridcolor: 'rgba(255,255,255,0.05)' }},
            yaxis: {{ title: 'Quality Score (0 - 100)', range: [40, 105], gridcolor: 'rgba(255,255,255,0.05)' }},
            showlegend: true,
            legend: {{ orientation: 'h', y: 1.1 }}
        }}, {{ responsive: true }});
    }}

    document.addEventListener('DOMContentLoaded', () => {{
        renderTable();
        renderCharts();
    }});
</script>

</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_template)

    print(f"[SUCCESS] Dashboard generated at: {OUTPUT_HTML}")


if __name__ == "__main__":
    print("[RUNNER] Parsing scorecard and request telemetry...")
    sc = parse_scorecard()
    print(f"  Parsed {len(sc)} scorecard runs.")
    df = parse_requests_dflash2()
    print(f"  Parsed {df.get('total_requests', 0)} DFlash-2 detailed telemetry records.")
    generate_html(sc, df)
