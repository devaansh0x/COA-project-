# Phase 1 + 2 Repository Assessment

This document records what the upstream repository actually contains (verified by
reading every source file), how to run it, the reproducible baseline we
established, the limitation we found, and our proposed change. It is the factual
foundation for the rest of the project; nothing here is assumed from the README
prose alone.

## 1. Languages, tools, dependencies

| Aspect | Finding |
|---|---|
| Implementation language (upstream) | Verilog (`.v`) RTL + one SystemVerilog testbench (`TESTBENCH.sv`) |
| Upstream dependency | A Verilog simulator (e.g. ModelSim/Questa, Icarus Verilog, Verilator) |
| Python in upstream | **None** |
| Simulator present on the build machine | **None** (no iverilog/verilator/modelsim); only Python 3.14 |
| Our enhancement language | Python 3 (standard library) + matplotlib for plots (both present) |

Because the rubric explicitly permits Python as a simulation tool and no Verilog
simulator is installed, our contribution is a faithful **behavioral Python model**
of the upstream cache memory system. The Verilog is kept untouched as the cited
upstream artifact and as the correctness reference.

## 2. Source files and responsibilities

### Processor (`RTL/RISC-V/`) — single-cycle RV32I
| File | Responsibility |
|---|---|
| `RISCV_TOP.v` | Datapath top; wires all components; sends `ALUResult[9:0]` to the cache as the data word address |
| `PCunit.v` | Program counter; `stall` input freezes the PC during cache stalls |
| `Instruction_Memory.v` | Loads `riscvtest.txt` via `$readmemh`; word-indexed `MEM[A>>2]` |
| `register_file.v` | 32×32-bit registers; async read, sync write |
| `Control_Unit.v` → `Main_Decoder.v`, `ALU_Decoder.v` | Opcode/funct decode for lw, sw, R-type, addi, beq, jal |
| `ALUunit.v` | add, sub, and, or, slt (ALUControl 000/001/010/011/101) |
| `Sign_Extend.v`, `Adder.v`, `mux_2x1.v`, `mux_3x1.v` | Immediate generation, PC math, result/operand muxing |

### Cache memory system (`RTL/Cache Memory System/`)
| File | Responsibility |
|---|---|
| `data_mem_sys.v` | Glue; performs the address field split `tag=[9:7]`, `index=[6:2]`, offset=`[1:0]` |
| `cache_controller.v` | FSM (idle/reading/writing); hit detection; 32 valid bits + 32 tags; drives stall/refill/update |
| `cache_memory.v` | 128×32-bit data array (32 blocks × 4 words); whole-block refill on miss |
| `data_memory.v` | 1024×32-bit main memory; 4-cycle access latency via a counter |

## 3. Pinned architectural facts (from the RTL, not the README prose)

- **Word-addressable** data memory; address bus is `WordAddress[9:0]` (10 bits), 1024 words.
- Direct-mapped split: **tag = 3 bits, index = 5 bits (32 sets), word offset = 2 bits (4 words/block)**.
- Block = 16 bytes; cache = 32 blocks = **512 bytes**; associativity = **1 (direct-mapped)**.
- Write policy: **write-through + write-around (no-write-allocate)**. Every store writes main memory and stalls; a store that hits also updates the cached word; a store that misses does **not** allocate.
- Read miss refills the whole 4-word block and stalls; read hit does not stall.
- **Miss penalty = 4 cycles**, counted once per main-memory transaction.
- CPU is single-cycle: one base cycle per instruction plus memory stalls.

### README inconsistency (resolved)
The README's prose ("byte addressable using 12 bits", "offset: 2 bits") is loose.
In **word** terms the RTL is self-consistent: offset=2, index=5, tag=3, matching the
geometry (512 B, 16 B blocks, 32 blocks, direct-mapped). We use the word-addressable
model because that is what the RTL implements.

## 4. `riscvtest.txt` discrepancy (important, documented)

The shipped `riscvtest.txt` contains **17** instruction words and ends with
`sw x8, 0(x0)` (`0x00802023`). The README documents a **19**-instruction program whose
last three instructions are `sw x9,0(x0)`, `lw x12,0(x0)`, `sw x12,50(x0)`. The Verilog
testbench (`TESTBENCH.sv`) checks `memory[50] == 0xfffff8ae`, which the shipped file can
never satisfy (it never writes `[50]`). The shipped file is therefore a truncated/edited
variant that matches neither the README nor the testbench.

**Resolution:** we validate the baseline against the README's documented,
testbench-passing 19-instruction program (the known-good reference), keep the shipped
`riscvtest.txt` **unmodified**, and record this discrepancy here and in the report's
limitations. Our loader exposes both (`load_program()` = README program;
`load_shipped_program()` = the file as-is).

## 5. How to run

### Upstream (Verilog) — requires a simulator (not installed here)
Compile the modules in `RTL/RISC-V/` and `RTL/Cache Memory System/` with `TESTBENCH.sv`,
load `riscvtest.txt` into instruction memory, and run. Success prints "Simulation succeeded".

### Our Python model — no toolchain beyond Python 3 + matplotlib
```
python sim/validate_baseline.py      # Phase-2 gate: correctness + baseline stats
python -m unittest discover -s sim/tests   # Tests A–G
python sim/experiments.py            # fair comparison -> results/*.csv, results/*.json
python sim/plots.py                  # graphs -> plots/*.png
```

## 6. Reproducible baseline (direct-mapped, README program) — MEASURED

Validated: all registers x1–x12 and memory `[0..3]`, `[50]` match the README; the
testbench criterion `memory[50]==0xfffff8ae` passes. Hand-verified against the
per-access trace.

| Metric | Value |
|---|---|
| Memory accesses | 11 (5 loads, 6 stores) |
| Hits / Misses | 5 / 6 |
| Hit rate | 45.45% |
| Evictions | 0 |
| Stall cycles | 28 |
| Instructions | 19 |
| Total cycles | 47 |
| CPI | 2.474 |

## 7. Limitation discovered

The direct-mapped cache maps each block to exactly one line (`index = addr[6:2]`).
Blocks whose addresses differ by a multiple of 128 words (= 32 sets × 4 words) collide
on the same line even when other lines are empty. Alternating accesses to two such
blocks evict each other every time → a conflict miss on every access. This is the
classic direct-mapped weakness our enhancement targets.

## 8. Proposed modification

Replace the direct-mapped L1 data cache with a **2-way set-associative** cache using
**LRU** replacement, keeping capacity (512 B), block size (16 B), write policy, and all
latencies identical so the comparison is fair. Expected: unchanged behavior where there
is no set contention; large reduction in conflict misses when two hot blocks share a set.

## 9. Risks and plan

- Risk: unfair comparison. Mitigation: one shared code path; only associativity changes.
- Risk: double-counting miss penalty. Mitigation: penalty charged once per transaction; verified by hand against the trace.
- Risk: overclaiming. Mitigation: three workloads including a case (`conflict3`) where 2-way does **not** help, reported honestly.
