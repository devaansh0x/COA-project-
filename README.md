```markdown
# RISC-V Processor with Data Cache — Direct-Mapped vs. 2-Way Set-Associative (LRU)

A single-cycle 32-bit RISC-V (RV32I) processor with an integrated L1 data cache, plus a
Python model that reproduces the original **direct-mapped** cache faithfully and upgrades
it to a **2-way set-associative cache with LRU** — then compares the two with measured
experiments.

> **TL;DR:** On conflict-heavy access patterns, the 2-way + LRU cache raises the hit rate
> from **0% to 93.75%** and runs **4× faster** (160 → 40 cycles) at identical capacity,
> block size, write policy, and latency.

---

## What's inside

This repo has two halves:

1. **The original hardware (upstream, unchanged).** A single-cycle RV32I processor in
   Verilog with a direct-mapped L1 data cache, a SystemVerilog testbench, and a
   machine-code test program. Lives under `RTL/`, `TESTBENCH.sv`, and `riscvtest.txt`.
   Original author: [`mo2men3la2`](https://github.com/mo2men3la2/RISC-V-Processor-with-Data-Cache-Memory-System).

2. **Our contribution (new, under `sim/`).** A faithful Python model of that same cache,
   extended with a 2-way set-associative + LRU design, a fair-comparison harness, unit
   tests, measured results, and graphs.

---

## The cache, briefly

| Property | Value |
|---|---|
| Capacity | 512 bytes |
| Block size | 16 bytes (4 words) |
| Blocks | 32 |
| Main memory | 1024 words, **4 cycles** per access |
| Write policy | Write-through + write-around (no-write-allocate) |
| Load stall | On miss only |
| Store stall | Always (write-through) |

**Baseline (original):** direct-mapped — each block has exactly one slot it can live in
(tag 3 b, index 5 b, offset 2 b → 32 sets). Two hot blocks that map to the same slot keep
evicting each other: a **conflict miss**.

**Enhanced (ours):** 2-way set-associative with LRU — each set has two slots, so colliding
blocks can coexist (tag 4 b, index 4 b, offset 2 b → 16 sets). On a fill with both ways
occupied, the **least-recently-used** way is evicted. Capacity, block size, write policy,
and latency are held constant for a fair comparison.

---

## Results

Measured (not asserted), from `results/comparison.csv`:

| Workload | Direct-mapped | 2-way + LRU | Notes |
|---|---|---|---|
| **conflict** (two blocks → same set) | 0% hit, 32 misses, 160 cycles | 93.75% hit, 2 misses, 40 cycles | **4× speedup** |
| original / sequential / repeated | identical for both | identical for both | no set contention to fix |
| **conflict3** (three blocks → one set) | 0% hit | 0% hit | 2 ways can't hold 3 hot blocks (reported honestly) |

![hit rate](plots/hit_rate.png)
![total cycles](plots/total_cycles.png)

---

## Requirements

- Python 3 (tested on 3.14)
- `matplotlib` (graphs only):
  ```
  python -m pip install matplotlib
  ```
Everything else uses the standard library.

## Run it (from the repository root)

| Step | Command | What it does |
|---|---|---|
| 1. Validate baseline | `python sim/validate_baseline.py` | Runs the original program on the direct-mapped model; checks registers + memory + the testbench criterion; prints baseline stats and the per-access trace |
| 2. Run tests | `python -m unittest discover -s sim/tests` | Tests A–G (14 tests) |
| 3. Experiments | `python sim/experiments.py` | Runs all workloads on both caches; writes `results/results.json`, `results/results.csv`, `results/comparison.csv` |
| 4. Graphs | `python sim/plots.py` | Generates `plots/*.png` from the measured results |

Run them in order — step 4 reads the output of step 3.

---

## Project layout

```
RTL/                     upstream Verilog (unchanged)
  RISC-V/                processor submodules + top (RISCV_TOP.v)
  Cache Memory System/   data_mem_sys.v, cache_controller.v, cache_memory.v, data_memory.v
TESTBENCH.sv             upstream testbench (unchanged)
riscvtest.txt            upstream machine-code program (unchanged)
README.md                upstream README (preserved)

sim/
  config.py              geometry/policy/latency — single source of truth
  memory.py              main memory model (1024 words, 4-cycle access)
  cache.py               Cache: direct-mapped AND 2-way + LRU (selected by config)
  stats.py               performance counters + cycle accounting
  trace.py               execution/access trace logging
  cpu.py                 minimal single-cycle RV32I CPU (upstream subset)
  runner.py              shared harness (same code path for both configs)
  experiments.py         fair comparison -> results/*
  plots.py               graphs from measured results -> plots/*
  validate_baseline.py   correctness gate
  workloads/             original program + sequential/repeated/conflict traces
  tests/test_cache.py    Tests A–G

results/                 measured CSV/JSON (generated)
plots/                   graphs (generated)
docs/
  OVERVIEW.md            short how-it-works guide
  ASSESSMENT.md          findings
  REPORT.md              full COA report
  CONTRIBUTION.md        attribution + original-vs-ours changelog
```

---

## How the model stays faithful

The Python model is a **behavioral reproduction** of the Verilog, not the synthesized RTL.
We validate it against the original author's own known-good program: all registers and
memory match, and the testbench's `memory[50] == 0xfffff8ae` criterion passes. Only after
that gate do we introduce the 2-way change — so the comparison is apples-to-apples.

---

## Attribution & license

The processor and direct-mapped cache RTL, the testbench, and the test program are the
work of the original author ([`mo2men3la2`](https://github.com/mo2men3la2/RISC-V-Processor-with-Data-Cache-Memory-System))
and are included **unmodified**, with their file headers intact. The upstream repository
states no explicit license; under default copyright, all rights remain with the original
author. This project is an **academic citation and derivative study** — we do not relicense
or claim ownership of the upstream Verilog. If redistributing, obtain permission from the
original author first.

Everything under `sim/`, `results/`, `plots/`, and `docs/` is our own contribution. See
`docs/CONTRIBUTION.md` for the full original-vs-ours changelog.
```
