"""
plots.py - Phase 7 visualisations, generated from MEASURED results.

Reads results/results.json (produced by experiments.py) and renders four
grouped bar charts under plots/:
    1. hit_rate.png     - cache hit rate by workload
    2. miss_count.png   - cache misses by workload
    3. stall_cycles.png - memory stall cycles by workload
    4. total_cycles.png - total execution cycles by workload

Never fabricates values: if results.json is missing, it tells you to run
experiments.py first. Uses the non-interactive 'Agg' backend so it never
blocks on a window.
"""

import os
import sys
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_RESULTS = os.path.join(_REPO_ROOT, "results", "results.json")
_PLOTS = os.path.join(_REPO_ROOT, "plots")


def _load():
    if not os.path.exists(_RESULTS):
        print("results/results.json not found - run `python sim/experiments.py` first.")
        sys.exit(1)
    with open(_RESULTS) as f:
        return json.load(f)


def _grouped_bar(workloads, base_vals, enh_vals, title, ylabel, fname,
                 fmt="{:.0f}", as_percent=False):
    x = range(len(workloads))
    width = 0.38
    fig, ax = plt.subplots(figsize=(9, 5))
    b = ax.bar([i - width / 2 for i in x], base_vals, width,
               label="Baseline (direct-mapped)", color="#4C72B0")
    e = ax.bar([i + width / 2 for i in x], enh_vals, width,
               label="Enhanced (2-way + LRU)", color="#DD8452")

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Workload")
    ax.set_xticks(list(x))
    ax.set_xticklabels(workloads)
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    for bars in (b, e):
        for rect in bars:
            h = rect.get_height()
            label = (fmt.format(h * 100) + "%") if as_percent else fmt.format(h)
            ax.annotate(label, xy=(rect.get_x() + rect.get_width() / 2, h),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    out = os.path.join(_PLOTS, fname)
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print("wrote", os.path.relpath(out, _REPO_ROOT))


def main():
    data = _load()
    runs = data["runs"]
    workloads = list(runs.keys())

    def col(cfg, key):
        return [runs[w][cfg][key] for w in workloads]

    os.makedirs(_PLOTS, exist_ok=True)

    _grouped_bar(workloads, col("baseline", "hit_rate"), col("enhanced", "hit_rate"),
                 "Cache Hit Rate by Workload", "Hit rate", "hit_rate.png",
                 fmt="{:.1f}", as_percent=True)

    _grouped_bar(workloads, col("baseline", "misses"), col("enhanced", "misses"),
                 "Cache Misses by Workload", "Misses (count)", "miss_count.png")

    _grouped_bar(workloads, col("baseline", "stall_cycles"),
                 col("enhanced", "stall_cycles"),
                 "Memory Stall Cycles by Workload", "Stall cycles",
                 "stall_cycles.png")

    _grouped_bar(workloads, col("baseline", "total_cycles"),
                 col("enhanced", "total_cycles"),
                 "Total Execution Cycles by Workload", "Total cycles",
                 "total_cycles.png")

    print("\nAll plots generated from measured results in results/results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
