#!/usr/bin/env python3
"""
NInfer Request & Reasoning Log Analyzer
Parses requests.jsonl to provide stats on reasoning tokens, looping behavior,
MTP speculative decoding efficiency, latency, and prompt cache hit rates.
"""

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path


def load_events(log_path, tail=0):
    if not os.path.exists(log_path):
        print(f"[ERROR] Log file not found: {log_path}", file=sys.stderr)
        return []

    events = []
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        if tail > 0:
            lines = lines[-tail:]
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def analyze(log_path, tail=0, show_spikes=False, show_slowest=False, inspect_id=None):
    events = load_events(log_path, tail=tail)
    if not events:
        print(f"[INFO] No events found in {log_path}")
        return

    # Specific request inspection
    if inspect_id is not None:
        matched = [e for e in events if e.get("request", {}).get("request_id") == inspect_id]
        if not matched:
            print(f"[INFO] No request found with ID {inspect_id}")
            return
        for ev in matched:
            print(json.dumps(ev, indent=2))
        return

    done_events = [e for e in events if e.get("event") == "request_done"]
    if not done_events:
        print(f"[INFO] No completed requests found yet in {log_path}")
        return

    total_requests = len(done_events)
    thinking_tokens = []
    completion_tokens = []
    prompt_tokens = []
    cache_hits = []
    total_durations = []
    ttfts = []
    decode_speeds = []
    drafted_total = 0
    accepted_total = 0
    finish_reasons = Counter()
    budget_caps_hit = 0
    output_limits_hit = 0

    for ev in done_events:
        res = ev.get("result", {})
        req = ev.get("request", {})
        spec = ev.get("speculative", {})
        timings = ev.get("timings_seconds", {})

        th = res.get("model_thinking_tokens", 0) or 0
        thinking_tokens.append(th)

        comp = res.get("completion_tokens", 0) or 0
        completion_tokens.append(comp)

        pr = res.get("prompt_tokens", 0) or 0
        prompt_tokens.append(pr)

        ch = res.get("prefix_cache_hit_tokens", 0) or 0
        cache_hits.append(ch)

        budget = res.get("thinking_budget", 4096) or 4096
        if th >= (budget - 50):
            budget_caps_hit += 1

        reason = res.get("finish_reason", "unknown")
        finish_reasons[reason] += 1
        if reason in ("output_limit", "length"):
            output_limits_hit += 1

        tot = timings.get("total", 0.0) or 0.0
        ttft = timings.get("ttft", 0.0) or 0.0
        dec = timings.get("decode", 0.0) or 0.0
        total_durations.append(tot)
        ttfts.append(ttft)

        if dec > 0 and comp > 0:
            decode_speeds.append(comp / dec)

        drafted_total += spec.get("drafted_tokens", 0) or 0
        accepted_total += spec.get("accepted_tokens", 0) or 0

    avg_thinking = sum(thinking_tokens) / total_requests
    med_thinking = sorted(thinking_tokens)[total_requests // 2]
    max_thinking = max(thinking_tokens)
    min_thinking = min(thinking_tokens)

    tot_prompt = sum(prompt_tokens)
    tot_cache = sum(cache_hits)
    cache_rate = (tot_cache / tot_prompt * 100) if tot_prompt > 0 else 0.0
    spec_rate = (accepted_total / drafted_total * 100) if drafted_total > 0 else 0.0
    avg_speed = sum(decode_speeds) / len(decode_speeds) if decode_speeds else 0.0
    avg_ttft = sum(ttfts) / total_requests
    avg_duration = sum(total_durations) / total_requests

    # Header
    print("=" * 60)
    print(" NInfer Request & Reasoning Log Analysis")
    print(f" Source: {os.path.basename(log_path)} | Total Requests Analyzed: {total_requests}")
    print("=" * 60)

    # Thinking metrics
    print("\n--- Thinking & Reasoning Performance ---")
    print(f"  Average Thinking Tokens: {avg_thinking:.1f} (Median: {med_thinking}, Range: {min_thinking} - {max_thinking})")
    status_cap = "None (Healthy)" if budget_caps_hit == 0 else f"{budget_caps_hit} request(s)"
    status_loop = "0 (Loops prevented!)" if output_limits_hit == 0 else f"{output_limits_hit} WARNING: runaway output hit!"
    print(f"  Hit Thinking Budget Cap: {status_cap}")
    print(f"  Output Limit Exceeded:   {status_loop}")

    # Acceleration & Efficiency
    print("\n--- Engine & Acceleration ---")
    print(f"  Average Decode Speed:    {avg_speed:.1f} tok/s")
    print(f"  Prompt Cache Hit Rate:   {cache_rate:.1f}%")
    print(f"  Spec Acceptance Rate:    {spec_rate:.1f}% ({accepted_total:,} / {drafted_total:,} tokens)")
    print(f"  Average TTFT:            {avg_ttft * 1000:.1f} ms")
    print(f"  Average Request Time:    {avg_duration:.2f} s")

    # Finish Reasons
    print("\n--- Finish Reasons ---")
    for r, count in finish_reasons.most_common():
        pct = (count / total_requests) * 100
        print(f"  {r:<20} {count:>4} ({pct:.1f}%)")

    # Spikes
    if show_spikes:
        print("\n--- Top 5 Longest Reasoning Requests ---")
        spikes = sorted(done_events, key=lambda x: x.get("result", {}).get("model_thinking_tokens", 0) or 0, reverse=True)[:5]
        for s in spikes:
            req_id = s.get("request", {}).get("request_id")
            res = s.get("result", {})
            t = s.get("timings_seconds", {})
            print(f"  Req #{req_id:<3} | Thinking: {res.get('model_thinking_tokens', 0):>4} tok | Output: {res.get('completion_tokens', 0):>4} tok | Duration: {t.get('total', 0.0):.2f}s | Prompt: {res.get('prompt_tokens', 0):>6} tok")

    # Slowest
    if show_slowest:
        print("\n--- Top 5 Slowest Requests (Total Latency) ---")
        slowest = sorted(done_events, key=lambda x: x.get("timings_seconds", {}).get("total", 0.0) or 0.0, reverse=True)[:5]
        for s in slowest:
            req_id = s.get("request", {}).get("request_id")
            res = s.get("result", {})
            t = s.get("timings_seconds", {})
            print(f"  Req #{req_id:<3} | Total: {t.get('total', 0.0):.2f}s (TTFT: {t.get('ttft', 0.0):.2f}s) | Thinking: {res.get('model_thinking_tokens', 0):>4} tok | Finish: {res.get('finish_reason')}")

    print("\n" + "=" * 60)


def watch(log_path, interval=2.0):
    print(f"[WATCH] Tailing {log_path} for new completed requests... (Ctrl+C to stop)\n")
    seen_ids = set()
    events = load_events(log_path)
    for e in events:
        if e.get("event") == "request_done":
            seen_ids.add(e.get("request", {}).get("request_id"))

    print(f"{'Time':<10} | {'Req #':<5} | {'Thinking':<10} | {'Output':<8} | {'Speed':<10} | {'Duration':<9} | {'Finish Reason'}")
    print("-" * 80)

    try:
        while True:
            new_events = load_events(log_path)
            for e in new_events:
                if e.get("event") == "request_done":
                    rid = e.get("request", {}).get("request_id")
                    if rid not in seen_ids:
                        seen_ids.add(rid)
                        res = e.get("result", {})
                        t = e.get("timings_seconds", {})
                        dec = t.get("decode", 0.0) or 0.0
                        comp = res.get("completion_tokens", 0) or 0
                        speed = f"{comp / dec:.1f} tok/s" if dec > 0 else "-"
                        now_str = time.strftime("%H:%M:%S")
                        print(f"{now_str:<10} | #{rid:<4} | {res.get('model_thinking_tokens', 0):>6} tok | {comp:>6} tok | {speed:>10} | {t.get('total', 0.0):>7.2f}s | {res.get('finish_reason')}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[WATCH] Stopped.")


def main():
    parser = argparse.ArgumentParser(description="Analyze NInfer requests.jsonl logs")
    parser.add_argument("--file", "-f", default="requests.jsonl", help="Path to requests.jsonl (default: requests.jsonl)")
    parser.add_argument("--tail", "-n", type=int, default=0, help="Analyze only the last N requests")
    parser.add_argument("--spikes", action="store_true", help="Show top thinking spikes")
    parser.add_argument("--slowest", action="store_true", help="Show slowest requests")
    parser.add_argument("--inspect", type=int, default=None, help="Inspect a specific request_id (outputs full JSON)")
    parser.add_argument("--watch", action="store_true", help="Live tail completed requests")

    args = parser.parse_args()
    log_file = args.file
    if not os.path.isabs(log_file):
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), log_file)

    if args.watch:
        watch(log_file)
    else:
        analyze(log_file, tail=args.tail, show_spikes=args.spikes, show_slowest=args.slowest, inspect_id=args.inspect)


if __name__ == "__main__":
    main()
