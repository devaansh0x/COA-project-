"""
original_trace.py - The upstream program used to validate the baseline.

IMPORTANT UPSTREAM INCONSISTENCY (discovered during Phase-2 validation):
The shipped riscvtest.txt contains only 17 instruction words and ends with
`sw x8, 0(x0)` (0x00802023). The repository's README documents a 19-instruction
program whose last three instructions are:
    0x00902023  sw  x9, 0(x0)      # [0] = 0xfffff8ae
    0x00002603  lw  x12, 0(x0)     # x12 = [0]
    0x02c02923  sw  x12, 50(x0)    # [50] = 0xfffff8ae  <-- testbench success value
The Verilog testbench (TESTBENCH.sv) checks `memory[50] == 0xfffff8ae`, which the
shipped file can NEVER satisfy because it never writes [50]. So the shipped file
is a truncated/edited variant that does not match either the README or the TB.

We therefore validate the baseline against the README's documented,
testbench-passing program (the known-good reference). We also expose the shipped
file's contents separately so the discrepancy is visible and documented, and we
NEVER modify the upstream riscvtest.txt.
"""

import os
import re

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_RISCVTEST = os.path.join(_REPO_ROOT, "riscvtest.txt")

# The README's full, testbench-passing program (machine code from the README
# table). This is the known-good reference for baseline validation.
README_PROGRAM = [
    0x00000013,  # addi x0, x0, 0
    0x00100093,  # addi x1, x0, 1
    0x00200113,  # addi x2, x0, 2
    0x00300193,  # addi x3, x0, 3
    0x45700213,  # addi x4, x0, 0x457
    0x8ae00293,  # addi x5, x0, 0xfffff8ae
    0xd0500313,  # addi x6, x0, 0xfffffd05
    0x15c00393,  # addi x7, x0, 0x15c
    0x00402023,  # sw x4, 0(x0)
    0x0050a023,  # sw x5, 0(x1)
    0x00612023,  # sw x6, 0(x2)
    0x0071a023,  # sw x7, 0(x3)
    0x00002403,  # lw x8, 0(x0)
    0x0000a483,  # lw x9, 0(x1)
    0x00012503,  # lw x10, 0(x2)
    0x0001a583,  # lw x11, 0(x3)
    0x00902023,  # sw x9, 0(x0)      -> [0] = 0xfffff8ae
    0x00002603,  # lw x12, 0(x0)     -> x12 = 0xfffff8ae
    0x02c02923,  # sw x12, 50(x0)    -> [50] = 0xfffff8ae (TB success)
]


def load_shipped_program() -> list[int]:
    """Parse the shipped riscvtest.txt into 32-bit words (as-is, truncated)."""
    words = []
    with open(_RISCVTEST, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            if re.fullmatch(r"[0-9A-Fa-f]{8}", line):
                words.append(int(line, 16))
    return words


def load_program() -> list[int]:
    """Known-good reference program used for baseline validation."""
    return list(README_PROGRAM)


# Expected architectural results (from the README comments), used for validation.
EXPECTED_REGS = {
    1: 0x00000001, 2: 0x00000002, 3: 0x00000003,
    4: 0x00000457, 5: 0xfffff8ae, 6: 0xfffffd05, 7: 0x0000015c,
    8: 0x00000457, 9: 0xfffff8ae, 10: 0xfffffd05, 11: 0x0000015c,
    12: 0xfffff8ae,  # lw x12, 0(x0) after [0] overwritten by sw x9
}
EXPECTED_MEM = {
    0: 0xfffff8ae,   # [0] overwritten by sw x9
    1: 0xfffff8ae,
    2: 0xfffffd05,
    3: 0x0000015c,
    50: 0xfffff8ae,  # testbench success criterion
}
