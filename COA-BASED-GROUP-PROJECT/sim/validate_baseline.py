"""
validate_baseline.py - Phase 2 gate.

Runs the original riscvtest.txt program through the Python baseline
(direct-mapped) cache model and checks:
  1. Functional correctness: register file and main memory match the known-good
     values from the README (including the testbench criterion memory[50]).
  2. Prints cache statistics and the per-access trace for hand verification.

The baseline numbers are only trusted AFTER this validation passes.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import BASELINE
from memory import MainMemory
from cache import Cache
from stats import Stats
from trace import Tracer
from cpu import CPU
from workloads.original_trace import load_program, EXPECTED_REGS, EXPECTED_MEM


def main() -> int:
    program = load_program()
    print(f"Loaded {len(program)} instructions (README known-good program)\n")
    print(BASELINE.describe(), "\n")

    mem = MainMemory()
    stats = Stats(label="baseline/original-trace")
    tracer = Tracer(enabled=True)
    cache = Cache(BASELINE, mem, stats, tracer)
    cpu = CPU(program, cache, stats, tracer)
    cpu.run()

    # ---- functional checks ----
    ok = True
    print("Register check:")
    for r, exp in EXPECTED_REGS.items():
        got = cpu.regs[r]
        mark = "OK " if got == exp else "XX "
        if got != exp:
            ok = False
        print(f"  {mark} x{r:<2} = 0x{got:08x}  (expected 0x{exp:08x})")

    print("\nMemory check:")
    for a, exp in EXPECTED_MEM.items():
        got = mem.read_word(a)
        mark = "OK " if got == exp else "XX "
        if got != exp:
            ok = False
        print(f"  {mark} mem[{a:<2}] = 0x{got:08x}  (expected 0x{exp:08x})")

    print("\nTestbench criterion (memory[50] == 0xfffff8ae): ",
          "PASS" if mem.read_word(50) == 0xfffff8ae else "FAIL")

    print("\nCache statistics:")
    print("  " + stats.summary())

    print("\nPer-access trace:")
    print(tracer.access_table())

    print("\nInstruction trace:")
    for e in tracer.instr_log:
        print(f"  {e['index']:3d} pc=0x{e['pc']:04x}  {e['mnemonic']}")

    print("\nRESULT:", "BASELINE VALIDATED" if ok else "VALIDATION FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
