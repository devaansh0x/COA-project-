# Original Project and Our Contributions

## Original project (upstream)
- **Repository:** RISC-V-Processor-with-Data-Cache-Memory-System
- **URL:** https://github.com/mo2men3la2/RISC-V-Processor-with-Data-Cache-Memory-System
- **Author / maintainer:** Mo'men Alaa Aldeen Abd Alkader (GitHub user `mo2men3la2`;
  the name also appears in every RTL file header, e.g. `RISCV_TOP.v`, `TESTBENCH.sv`).
- **What it is:** a single-cycle 32-bit RISC-V (RV32I) processor in Verilog with an
  integrated direct-mapped L1 data cache (geometry 512 B, 16 B blocks, 1-way), a
  SystemVerilog testbench, and a machine-code test program (`riscvtest.txt`).

## License
As of inspection, the upstream repository contains **no LICENSE file** and states no
explicit open-source license. Under default copyright, all rights are reserved by the
original author. We therefore treat this strictly as an **academic citation and
derivative study**: we keep the original author's name and file headers intact, we do
**not** relicense or claim ownership of the upstream Verilog, and we clearly separate our
additions from the original work. If this project were to be published or redistributed,
explicit permission from the original author should be obtained first. *(Content about the
upstream was rephrased for compliance with licensing restrictions.)*

## Files that originated upstream (unmodified by us)
Everything under `RTL/` and the top-level upstream artifacts are the original author's work
and are **left byte-for-byte unchanged**:
- `RTL/RISC-V/*.v` — processor submodules and top (`RISCV_TOP.v`)
- `RTL/Cache Memory System/*.v` — `data_mem_sys.v`, `cache_controller.v`, `cache_memory.v`, `data_memory.v`
- `TESTBENCH.sv` — the SystemVerilog testbench
- `riscvtest.txt` — the shipped machine-code program (**unmodified**, including its known truncation)
- `README.md` — the original documentation

## What we added (our independent contribution)
All of our work lives in **new** directories and files; we did not edit any upstream file.
- `sim/` — a faithful **behavioral Python model** of the upstream cache memory system:
  - `config.py` (geometry/policy/latency, single source of truth; fields derived)
  - `memory.py`, `cache.py` (direct-mapped **and** our 2-way+LRU), `stats.py`, `trace.py`, `cpu.py`
  - `runner.py`, `experiments.py`, `plots.py`, `validate_baseline.py`
  - `workloads/` (the original program loader + sequential/repeated/conflict traces)
  - `tests/test_cache.py` (Tests A–G, 14 tests)
- `results/` — machine-readable measured results (`results.json`, `results.csv`, `comparison.csv`)
- `plots/` — graphs generated from the measured results
- `docs/` — `ASSESSMENT.md`, `REPORT.md`, this file
- `README_SIM.md` — setup and run instructions for our model

## What we changed and why
We did not change the upstream RTL. Our *architectural* change is implemented in our Python
model: the L1 data cache placement policy goes from **direct-mapped** to **2-way
set-associative with LRU**, at identical capacity (512 B), block size (16 B), write policy
(write-through, write-around), and latencies. Reason: to reduce conflict misses, which the
direct-mapped design suffers when two active blocks map to the same line.

## Features and tests we added
- A configurable cache supporting both associativities from one code path.
- A 2-way LRU replacement policy with an independent unit test (Test D).
- Three experimental workloads with addresses justified from the real mapping.
- A fair-comparison harness and measured CSV/JSON outputs.
- Four result graphs generated strictly from measured data.
- 14 unit/regression tests (Tests A–G), all passing.

## Experimental evidence supporting our conclusions
From `results/comparison.csv` (measured, not asserted):
- **conflict** workload: hit rate 0% → 93.75%; misses 32 → 2; cycles 160 → 40 (**4× speedup**).
- **original / sequential / repeated**: identical for both designs (no set contention).
- **conflict3** workload: both designs 0% hit rate — 2-way does not fix a 3-block conflict
  (reported honestly, not hidden).

## Change log (original vs. ours)
| Area | Upstream (original) | Ours (added) |
|---|---|---|
| Processor RTL | Verilog single-cycle RV32I | Unchanged; mirrored behaviorally in `sim/cpu.py` |
| Cache placement | Direct-mapped (1-way) Verilog | 2-way set-associative + LRU in `sim/cache.py` |
| Replacement policy | None (direct-mapped) | LRU (2-way) |
| Tests | One SystemVerilog testbench | 14 Python unit/regression tests (A–G) |
| Benchmarks | One test program | + sequential, repeated, conflict, conflict3 |
| Results | Waveform/screenshots in README | Machine-readable CSV/JSON + generated graphs |
| Docs | README | Assessment, full COA report, contribution/changelog |

## Honesty notes
- Our model is a **behavioral reproduction** of the Verilog, validated against the README's
  known-good program; it is not the synthesized RTL.
- The shipped `riscvtest.txt` is truncated relative to the README/testbench; we validate
  against the README program and leave the file unmodified (details in `docs/ASSESSMENT.md`).
