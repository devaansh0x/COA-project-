"""
stats.py - Performance counters for the cache memory system.

Metric definitions (kept identical for baseline and enhanced):
    hit rate  = hits  / total cache accesses
    miss rate = misses / total cache accesses
    total cache accesses = reads + writes

Cycle accounting mirrors the RTL:
    - Each instruction costs 1 base cycle (single-cycle CPU).
    - A memory transaction that goes to main memory adds MISS_PENALTY_CYCLES
      stall cycles (block refill on a read miss, or the store write-through).
    - A read hit adds no stall.
These stall cycles are summed in `stall_cycles` and added on top of the base
instruction cycles to get `total_cycles`.
"""

from dataclasses import dataclass, field, asdict


@dataclass
class Stats:
    label: str = ""

    # memory-access breakdown
    reads: int = 0
    writes: int = 0

    hits: int = 0
    misses: int = 0

    read_hits: int = 0
    read_misses: int = 0
    write_hits: int = 0
    write_misses: int = 0

    evictions: int = 0        # LRU/replacement evictions (0 for a fresh direct-mapped line reuse that is a conflict replacement is still counted)

    # cycle accounting
    instructions: int = 0     # instructions retired (base cycles)
    stall_cycles: int = 0     # extra cycles from main-memory transactions

    @property
    def total_accesses(self) -> int:
        return self.reads + self.writes

    @property
    def total_cycles(self) -> int:
        # single-cycle CPU: one base cycle per instruction + memory stalls
        return self.instructions + self.stall_cycles

    @property
    def hit_rate(self) -> float:
        return self.hits / self.total_accesses if self.total_accesses else 0.0

    @property
    def miss_rate(self) -> float:
        return self.misses / self.total_accesses if self.total_accesses else 0.0

    @property
    def cpi(self) -> float:
        return self.total_cycles / self.instructions if self.instructions else 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(
            total_accesses=self.total_accesses,
            total_cycles=self.total_cycles,
            hit_rate=round(self.hit_rate, 6),
            miss_rate=round(self.miss_rate, 6),
            cpi=round(self.cpi, 6),
        )
        return d

    def summary(self) -> str:
        return (
            f"[{self.label}] accesses={self.total_accesses} "
            f"(R={self.reads} W={self.writes}) "
            f"hits={self.hits} misses={self.misses} "
            f"evictions={self.evictions} "
            f"hit_rate={self.hit_rate:.3f} miss_rate={self.miss_rate:.3f} "
            f"stalls={self.stall_cycles} cycles={self.total_cycles} "
            f"CPI={self.cpi:.3f}"
        )
