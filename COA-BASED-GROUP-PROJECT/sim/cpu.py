"""
cpu.py - Minimal single-cycle RV32I CPU, faithful to the original datapath.

Scope: exactly the instruction subset the original Verilog decoders support
(RTL/RISC-V/Main_Decoder.v + ALU_Decoder.v):
    - I-type ALU:  addi            (opcode 0010011, funct3=000)
    - R-type ALU:  add sub and or slt (opcode 0110011)
    - Load:        lw              (opcode 0000011)
    - Store:       sw              (opcode 0100011)
    - Branch:      beq             (opcode 1100011)
    - Jump:        jal             (opcode 1101111)
This is enough to run the original riscvtest.txt program and our workloads.

Data-memory addressing is reproduced EXACTLY as in RISCV_TOP.v:
    data_mem_sys .WordAddress(ALUResult_i[9:0])
i.e. the ALU result's low 10 bits are used directly as the WORD address into
the cache/memory. The cache then splits that word address into tag/index/offset
(see config.py). This matches the original hardware, where the test program's
"byte" offsets are used directly as word indices.

The CPU is single-cycle: each retired instruction costs one base cycle
(stats.instructions). Memory stalls are added by the cache (stats.stall_cycles).
"""

from cache import Cache
from stats import Stats


def _sext(value: int, bits: int) -> int:
    """Sign-extend `value` from `bits` wide to a Python signed int."""
    mask = 1 << (bits - 1)
    return (value ^ mask) - mask


def _u32(x: int) -> int:
    return x & 0xFFFFFFFF


class CPU:
    def __init__(self, program: list[int], cache: Cache, stats: Stats,
                 tracer=None, max_cycles: int = 1_000_000):
        self.program = [p & 0xFFFFFFFF for p in program]
        self.cache = cache
        self.stats = stats
        self.tracer = tracer
        self.max_cycles = max_cycles

        self.regs = [0] * 32
        self.pc = 0

    def _addr(self, rs1: int, imm: int) -> int:
        # ALU result low 10 bits used as the word address (see module docstring)
        return _u32(self.regs[rs1] + imm) & 0x3FF

    def run(self) -> Stats:
        steps = 0
        n = len(self.program)
        while 0 <= (self.pc >> 2) < n and steps < self.max_cycles:
            steps += 1
            instr = self.program[self.pc >> 2]
            if instr == 0:
                # all-zero word: treat as the end of the loaded program
                # (addi x0,x0,0 is 0x00000013, not 0x0; a true 0 is padding)
                break
            self._execute(instr)
        return self.stats

    def _execute(self, instr: int) -> None:
        opcode = instr & 0x7F
        rd = (instr >> 7) & 0x1F
        funct3 = (instr >> 12) & 0x7
        rs1 = (instr >> 15) & 0x1F
        rs2 = (instr >> 20) & 0x1F
        funct7 = (instr >> 25) & 0x7F

        next_pc = _u32(self.pc + 4)
        mnemonic = f"0x{instr:08x}"

        if opcode == 0b0010011:          # I-type ALU (addi)
            imm = _sext(instr >> 20, 12)
            self._write_reg(rd, _u32(self.regs[rs1] + imm))
            mnemonic = f"addi x{rd}, x{rs1}, {imm}"

        elif opcode == 0b0110011:        # R-type
            a, b = self.regs[rs1], self.regs[rs2]
            if funct3 == 0b000:
                res = _u32(a - b) if funct7 == 0b0100000 else _u32(a + b)
                name = "sub" if funct7 == 0b0100000 else "add"
            elif funct3 == 0b111:
                res, name = a & b, "and"
            elif funct3 == 0b110:
                res, name = a | b, "or"
            elif funct3 == 0b010:
                res, name = (1 if _sext(a, 32) < _sext(b, 32) else 0), "slt"
            else:
                res, name = 0, "r?"
            self._write_reg(rd, _u32(res))
            mnemonic = f"{name} x{rd}, x{rs1}, x{rs2}"

        elif opcode == 0b0000011:        # lw
            imm = _sext(instr >> 20, 12)
            addr = self._addr(rs1, imm)
            value = self.cache.load(addr)
            self._write_reg(rd, value)
            mnemonic = f"lw x{rd}, {imm}(x{rs1})"

        elif opcode == 0b0100011:        # sw
            imm = _sext(((instr >> 25) << 5) | ((instr >> 7) & 0x1F), 12)
            addr = self._addr(rs1, imm)
            self.cache.store(addr, self.regs[rs2])
            mnemonic = f"sw x{rs2}, {imm}(x{rs1})"

        elif opcode == 0b1100011:        # beq
            imm = _sext(
                (((instr >> 31) & 1) << 12) |
                (((instr >> 7) & 1) << 11) |
                (((instr >> 25) & 0x3F) << 5) |
                (((instr >> 8) & 0xF) << 1), 13)
            if self.regs[rs1] == self.regs[rs2]:
                next_pc = _u32(self.pc + imm)
            mnemonic = f"beq x{rs1}, x{rs2}, {imm}"

        elif opcode == 0b1101111:        # jal
            imm = _sext(
                (((instr >> 31) & 1) << 20) |
                (((instr >> 12) & 0xFF) << 12) |
                (((instr >> 20) & 1) << 11) |
                (((instr >> 21) & 0x3FF) << 1), 21)
            self._write_reg(rd, next_pc)
            next_pc = _u32(self.pc + imm)
            mnemonic = f"jal x{rd}, {imm}"

        self.stats.instructions += 1
        if self.tracer is not None:
            self.tracer.log_instruction(self.stats.instructions - 1,
                                         self.pc, mnemonic)
        self.pc = next_pc

    def _write_reg(self, rd: int, value: int) -> None:
        # x0 is hardwired to zero in RV32I. The original relies on the program
        # writing 0 to x0; we enforce the architectural rule for safety.
        if rd != 0:
            self.regs[rd] = _u32(value)
