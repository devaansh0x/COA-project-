"""
memory.py - Behavioral model of the main data memory.

Mirrors RTL/Cache Memory System/data_memory.v:
  - 1024 words of storage (word-addressable).
  - A read returns the whole 4-word block containing the address (used to
    refill a cache line on a miss).
  - A write updates a single word (write-through).
  - Each access to main memory costs MISS_PENALTY_CYCLES cycles; that timing
    is accounted by the cache, not here, so this class stays a pure store.
"""

from config import MAIN_MEM_WORDS, WORDS_PER_BLOCK


class MainMemory:
    def __init__(self):
        self.words = [0] * MAIN_MEM_WORDS

    def read_word(self, word_addr: int) -> int:
        return self.words[word_addr] & 0xFFFFFFFF

    def write_word(self, word_addr: int, value: int) -> None:
        self.words[word_addr] = value & 0xFFFFFFFF

    def read_block(self, word_addr: int) -> list[int]:
        """Return the WORDS_PER_BLOCK words of the block containing word_addr."""
        base = word_addr & ~(WORDS_PER_BLOCK - 1)
        return [self.read_word(base + i) for i in range(WORDS_PER_BLOCK)]
