# Python Cache Simulator — Setup, Run, and Viva Guide

This is our contribution on top of the upstream Verilog project
(`github.com/mo2men3la2/RISC-V-Processor-with-Data-Cache-Memory-System`). It faithfully
reproduces the upstream **direct-mapped** L1 data cache behavior in Python and adds a
**2-way set-associative cache with LRU**, then compares the two with measured experiments.

The upstream Verilog under `RTL/`, `TESTBENCH.sv`, `riscvtest.txt`, and `README.md` is
**unmodified**. Everything we added lives in `sim/`, `results/`, `plots/`, and `docs/`.

## Requirements
- Python 3 (tested on 3.14)
- matplotlib (for graphs only; already present in this environment)
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

Run them in order (3 must precede 4).

## Project layout
```
RTL/                     upstream Verilog (unchanged)
TESTBENCH.sv             upstream testbench (unchanged)
riscvtest.txt            upstream program (unchanged; note: truncated vs README)
README.md                upstream README (unchanged)

sim/
  config.py              geometry/policy/latency — one source of truth
  memory.py              main memory model (1024 words, 4-cycle access)
  cache.py               Cache: direct-mapped AND 2-way+LRU (selected by config)
  stats.py               performance counters + cycle accounting
  trace.py               execution/access trace logging
  cpu.py                 minimal single-cycle RV32I CPU (upstream subset)
  runner.py              shared harness (same code path for both configs)
  experiments.py         fair comparison -> results/*
  plots.py               graphs from measured results -> plots/*
  validate_baseline.py   Phase-2 correctness gate
  workloads/             original program + sequential/repeated/conflict traces
  tests/test_cache.py    Tests A–G

results/                 measured CSV/JSON (generated)
plots/                   graphs (generated)
docs/
  ASSESSMENT.md          Phase 1+2 findings
  REPORT.md              full COA report (32 sections)
  CONTRIBUTION.md        attribution + original-vs-ours changelog
```

## Key configuration (one place)
`sim/config.py` holds the geometry. `BASELINE` = direct-mapped (1-way, 32 sets);
`ENHANCED` = 2-way + LRU (16 sets). Capacity (512 B) and block size (16 B) are identical;
the index/tag field widths are **derived** from associativity, not hard-coded.

## Viva walkthrough — how to defend this

**What is the project?** We took a real RV32I + direct-mapped L1 cache, reproduced it
faithfully in Python, found its conflict-miss weakness with measured data, and fixed it
with a 2-way set-associative cache using LRU — then compared both fairly.

**Why Python, not the Verilog?** The rubric permits Python; no Verilog simulator is
installed here. We kept the Verilog as the cited reference and validated our model against
the author's own known-good program (all registers/memory match; the testbench's
`memory[50]==0xfffff8ae` criterion passes).

**Where is the address decomposition?** `config.py`. Baseline: tag `[9:7]`, index `[6:2]`
(32 sets), offset `[1:0]`. Enhanced: tag `[9:6]`, index `[5:2]` (16 sets), offset `[1:0]`.
Both derived from geometry.

**How does LRU work (2-way)?** One MRU bit per set; the victim is the other way. Every
hit/fill marks its way MRU. Verified by Test D.

**What is the headline result?** On the conflict workload (alternating words 0 and 128,
both set 0): baseline 0% hit rate, 160 cycles; enhanced 93.75% hit rate, 40 cycles → 4×
speedup. See `results/comparison.csv` and `plots/`.

**Why no change on other workloads?** Associativity only helps set contention. Sequential
(spatial) and repeated (temporal) locality are already captured by both caches, so they are
identical — we report that honestly.

**What is the honest limitation?** The `conflict3` workload (three blocks, one set) still
thrashes with 2 ways. 2-way reduces conflicts between two hot blocks, not three.

**What did we actually build vs. reuse?** See `docs/CONTRIBUTION.md`. We changed no upstream
file; our architectural change (direct-mapped → 2-way+LRU) and all tests/experiments/graphs
are ours.
```
