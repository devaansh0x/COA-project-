"""
config.py - Single source of truth for the cache memory system geometry,
            write policy, and timing penalties.

This project is a faithful BEHAVIORAL reproduction of the Verilog cache memory
system found in RTL/Cache Memory System/. All geometry and policy values below
are pinned to what the actual RTL does (not the loose README prose).

Pinned facts from the RTL (verified by reading the source):
  - Memory is WORD-ADDRESSABLE. The data address bus is WordAddress[9:0]
    (see RTL/.../data_mem_sys.v and RISCV_TOP.v: WordAddress(ALUResult_i[9:0])).
  - Main memory is 1024 words (RTL/.../data_memory.v: mem_depth=1024).
  - Direct-mapped baseline split (data_mem_sys.v):
        tag        = WordAddress[9:7]  (3 bits)
        set index  = WordAddress[6:2]  (5 bits -> 32 sets)
        word offset= WordAddress[1:0]  (2 bits -> 4 words per block)
  - Block = 4 words = 16 bytes. Cache = 32 blocks = 512 bytes.
  - Write policy: WRITE-THROUGH + WRITE-AROUND (no-write-allocate)
    (cache_controller.v FSM: a store always writes main memory and stalls;
     a store that HITS also updates the cached line; a store that MISSES
     does NOT allocate a line).
  - Main-memory access latency = 4 cycles (data_memory.v counter 0..3),
    counted ONCE per memory transaction (one block refill, or one store).
  - Load stalls only on a miss. Store always stalls.
  - CPU is single-cycle: 1 cycle/instruction unless the memory system stalls.

The ENHANCED design changes ONLY the associativity (and therefore the
index/tag split, which is DERIVED below, never hard-coded twice). Capacity,
block size, write policy, and latencies are held constant for a fair compare.
"""

from dataclasses import dataclass


# ---- fixed hardware facts (identical for baseline and enhanced) ----
WORD_ADDR_BITS = 10          # WordAddress[9:0]
MAIN_MEM_WORDS = 1 << WORD_ADDR_BITS  # 1024 words
WORDS_PER_BLOCK = 4          # 16-byte block / 4-byte word
BYTES_PER_WORD = 4
CACHE_BLOCKS = 32            # total blocks (512 bytes / 16 bytes)
CACHE_CAPACITY_BYTES = 512
BLOCK_SIZE_BYTES = 16

MISS_PENALTY_CYCLES = 4      # main-memory access latency (data_memory.v)
HIT_LATENCY_CYCLES = 0       # a hit adds no extra stall; access completes in-cycle


@dataclass(frozen=True)
class CacheConfig:
    """
    Cache geometry derived from associativity. The index/tag/offset field
    widths are COMPUTED from the geometry so there is exactly one place that
    defines the address decomposition.
    """
    name: str
    associativity: int        # 1 = direct-mapped (baseline), 2 = two-way (enhanced)

    # --- derived geometry (filled in __post_init__ via object.__setattr__) ---
    num_sets: int = 0
    offset_bits: int = 0
    index_bits: int = 0
    tag_bits: int = 0

    def __post_init__(self):
        if CACHE_BLOCKS % self.associativity != 0:
            raise ValueError("associativity must divide the number of blocks")
        num_sets = CACHE_BLOCKS // self.associativity

        offset_bits = _log2_exact(WORDS_PER_BLOCK)   # 2 (word offset within block)
        index_bits = _log2_exact(num_sets)
        tag_bits = WORD_ADDR_BITS - index_bits - offset_bits

        object.__setattr__(self, "num_sets", num_sets)
        object.__setattr__(self, "offset_bits", offset_bits)
        object.__setattr__(self, "index_bits", index_bits)
        object.__setattr__(self, "tag_bits", tag_bits)

    # --- address decomposition, derived from the computed field widths ---
    def block_offset(self, word_addr: int) -> int:
        return word_addr & (WORDS_PER_BLOCK - 1)

    def set_index(self, word_addr: int) -> int:
        return (word_addr >> self.offset_bits) & (self.num_sets - 1)

    def tag(self, word_addr: int) -> int:
        return word_addr >> (self.offset_bits + self.index_bits)

    def block_base_word(self, word_addr: int) -> int:
        """First word address of the block containing word_addr."""
        return word_addr & ~(WORDS_PER_BLOCK - 1)

    def describe(self) -> str:
        return (
            f"{self.name}: assoc={self.associativity}-way, sets={self.num_sets}, "
            f"blocks={CACHE_BLOCKS}, block={BLOCK_SIZE_BYTES}B, "
            f"capacity={CACHE_CAPACITY_BYTES}B | "
            f"tag={self.tag_bits}b index={self.index_bits}b offset={self.offset_bits}b"
        )


def _log2_exact(n: int) -> int:
    if n <= 0 or (n & (n - 1)) != 0:
        raise ValueError(f"{n} is not a power of two")
    return n.bit_length() - 1


# Canonical configurations used across the project.
BASELINE = CacheConfig(name="direct-mapped", associativity=1)   # tag=3 index=5 offset=2
ENHANCED = CacheConfig(name="2-way-LRU", associativity=2)        # tag=4 index=4 offset=2
