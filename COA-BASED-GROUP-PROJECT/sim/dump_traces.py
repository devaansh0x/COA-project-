"""
dump_traces.py - Save human-readable execution traces as a deliverable.

Writes results/traces.txt containing:
  - the original program on the baseline (direct-mapped) cache
  - the conflict workload on BOTH caches, side by side in effect, so the
    direct-mapped thrashing vs 2-way resident behavior is visible per-access.
These are the "execution traces" referenced by the report.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from config import BASELINE, ENHANCED
from runner import run_program, run_address_trace
from workloads.original_trace import load_program
from workloads import patterns

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_OUT = os.path.join(_REPO_ROOT, "results", "traces.txt")


def section(title):
    return f"\n{'=' * 72}\n{title}\n{'=' * 72}\n"


def main():
    os.makedirs(os.path.dirname(_OUT), exist_ok=True)
    lines = []

    # 1. Original program on the baseline cache
    stats, cpu, mem, tracer = run_program(load_program(), BASELINE,
                                          "baseline/original", trace=True)
    lines.append(section("ORIGINAL PROGRAM on BASELINE (direct-mapped)"))
    lines.append(stats.summary())
    lines.append("\nPer-access cache trace:")
    lines.append(tracer.access_table())

    # 2. Conflict workload on baseline
    b_stats, _, _, b_tr = run_address_trace(patterns.conflict(8), BASELINE,
                                            "baseline/conflict", trace=True)
    lines.append(section("CONFLICT WORKLOAD on BASELINE (direct-mapped)"))
    lines.append(b_stats.summary())
    lines.append("\nPer-access cache trace (every access conflicts -> MISS):")
    lines.append(b_tr.access_table())

    # 3. Conflict workload on enhanced
    e_stats, _, _, e_tr = run_address_trace(patterns.conflict(8), ENHANCED,
                                            "enhanced/conflict", trace=True)
    lines.append(section("CONFLICT WORKLOAD on ENHANCED (2-way + LRU)"))
    lines.append(e_stats.summary())
    lines.append("\nPer-access cache trace (two cold misses, then HITs):")
    lines.append(e_tr.access_table())

    with open(_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", os.path.relpath(_OUT, _REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
