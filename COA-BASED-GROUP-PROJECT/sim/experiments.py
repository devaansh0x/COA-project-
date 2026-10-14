"""
experiments.py - Phase 6/7 fair comparison harness.

Runs every workload through BOTH cache configs on the same code path and writes
machine-readable results (JSON + CSV). Held constant across the two configs:
capacity, block size, CPU, instruction/access sequence, memory contents, main-
memory latency, hit latency, write policy. Only associativity differs.

Outputs (written under results/):
  - results.json : full per-run stats for both configs and all workloads
  - results.csv  : flat table, one row per (workload, config)
  - comparison.csv : one row per workload with baseline vs enhanced + deltas
"""

import os
import sys
import json
import csv

sys.path.insert(0, os.path.dirname(__file__))

from config import BASELINE, ENHANCED
from runner import run_address_trace, run_program
from workloads import patterns
from workloads.original_trace import load_program

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_RESULTS = os.path.join(_REPO_ROOT, "results")


def _pct(numer, denom):
    """Safe percentage; returns 0.0 when denominator is zero."""
    return (numer / denom * 100.0) if denom else 0.0


def build_workloads():
    """Return an ordered dict of workload_name -> ('program'|'trace', payload)."""
    return {
        "original":   ("program", load_program()),
        "sequential": ("trace", patterns.sequential(64)),
        "repeated":   ("trace", patterns.repeated(repeats=8)),
        "conflict":   ("trace", patterns.conflict(iterations=16)),
        "conflict3":  ("trace", patterns.conflict3(iterations=16)),
    }


def run_one(kind, payload, config, label):
    if kind == "program":
        stats, *_ = run_program(payload, config, label)
    else:
        stats, *_ = run_address_trace(payload, config, label)
    return stats


def main():
    os.makedirs(_RESULTS, exist_ok=True)
    workloads = build_workloads()

    all_rows = []          # flat rows for results.csv
    comparison_rows = []   # per-workload baseline vs enhanced
    full = {"configs": {"baseline": BASELINE.describe(),
                        "enhanced": ENHANCED.describe()},
            "runs": {}}

    print(f"{'workload':12} {'config':14} {'acc':>4} {'hit':>4} {'miss':>5} "
          f"{'hit%':>6} {'evict':>5} {'stall':>6} {'cycles':>7} {'CPI':>6}")
    print("-" * 86)

    for wl, (kind, payload) in workloads.items():
        b = run_one(kind, payload, BASELINE, f"baseline/{wl}")
        e = run_one(kind, payload, ENHANCED, f"enhanced/{wl}")
        full["runs"][wl] = {"baseline": b.to_dict(), "enhanced": e.to_dict()}

        for cfgname, s in (("baseline", b), ("enhanced", e)):
            row = {"workload": wl, "config": cfgname}
            row.update(s.to_dict())
            all_rows.append(row)
            print(f"{wl:12} {cfgname:14} {s.total_accesses:4d} {s.hits:4d} "
                  f"{s.misses:5d} {s.hit_rate*100:6.2f} {s.evictions:5d} "
                  f"{s.stall_cycles:6d} {s.total_cycles:7d} {s.cpi:6.3f}")

        # per-workload comparison with safe formulas
        comparison_rows.append({
            "workload": wl,
            "accesses": b.total_accesses,
            "base_hits": b.hits, "enh_hits": e.hits,
            "base_misses": b.misses, "enh_misses": e.misses,
            "base_hit_rate": round(b.hit_rate, 4),
            "enh_hit_rate": round(e.hit_rate, 4),
            "base_evictions": b.evictions, "enh_evictions": e.evictions,
            "base_stalls": b.stall_cycles, "enh_stalls": e.stall_cycles,
            "base_cycles": b.total_cycles, "enh_cycles": e.total_cycles,
            # improvement metrics (brief's formulas, zero-safe)
            # hit-rate improvement as a RATIO is undefined when baseline==0;
            # report the absolute percentage-point gain too so the result is
            # not silently lost (conflict workload has baseline hit rate 0).
            "hit_rate_improve_pct": round(
                _pct(e.hit_rate - b.hit_rate, b.hit_rate), 2),
            "hit_rate_gain_points": round((e.hit_rate - b.hit_rate) * 100, 2),
            "miss_reduction_pct": round(
                _pct(b.misses - e.misses, b.misses), 2),
            "speedup": round(b.total_cycles / e.total_cycles, 4)
                       if e.total_cycles else 0.0,
        })

    # ---- write JSON ----
    with open(os.path.join(_RESULTS, "results.json"), "w") as f:
        json.dump(full, f, indent=2)

    # ---- write flat CSV ----
    flat_fields = ["workload", "config", "label", "reads", "writes",
                   "hits", "misses", "read_hits", "read_misses",
                   "write_hits", "write_misses", "evictions", "instructions",
                   "stall_cycles", "total_accesses", "total_cycles",
                   "hit_rate", "miss_rate", "cpi"]
    with open(os.path.join(_RESULTS, "results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=flat_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)

    # ---- write comparison CSV ----
    with open(os.path.join(_RESULTS, "comparison.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(comparison_rows[0].keys()))
        w.writeheader()
        w.writerows(comparison_rows)

    print("\nWrote results/results.json, results/results.csv, "
          "results/comparison.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
