"""
cache.py - L1 data cache model.

One class handles BOTH designs, chosen by CacheConfig.associativity:
  - associativity == 1  -> direct-mapped (baseline, reproduces the Verilog)
  - associativity == 2  -> two-way set-associative with LRU (our enhancement)

Write policy (identical for both, pinned from cache_controller.v):
  WRITE-THROUGH + WRITE-AROUND (no-write-allocate):
    * every store writes main memory (and stalls MISS_PENALTY_CYCLES);
    * a store that HITS also updates the cached word in place;
    * a store that MISSES does NOT bring the block into the cache.

Read policy:
    * a load that HITS returns the cached word (no stall);
    * a load that MISSES refills the whole block from main memory
      (stalls MISS_PENALTY_CYCLES), then returns the word.

Timing: the cache adds MISS_PENALTY_CYCLES to stats.stall_cycles for every
main-memory transaction (one refill per read miss, one write-through per store).
A read hit adds nothing. This matches the data_memory counter which charges a
single 4-cycle penalty per transaction (no double counting).

LRU (2-way): one "most-recently-used way" marker per set is enough to identify
the LRU way in a two-way set. Every access to a way makes it MRU; the other way
becomes the LRU candidate for the next eviction.
"""

from config import CacheConfig, MISS_PENALTY_CYCLES, WORDS_PER_BLOCK
from memory import MainMemory
from stats import Stats


class _Way:
    """One cache way (line): valid bit, tag, and WORDS_PER_BLOCK data words."""
    __slots__ = ("valid", "tag", "data")

    def __init__(self):
        self.valid = False
        self.tag = 0
        self.data = [0] * WORDS_PER_BLOCK


class Cache:
    def __init__(self, config: CacheConfig, memory: MainMemory, stats: Stats,
                 tracer=None):
        self.cfg = config
        self.mem = memory
        self.stats = stats
        self.tracer = tracer

        # sets[set_index] -> list of ways (length == associativity)
        self.sets = [[_Way() for _ in range(config.associativity)]
                     for _ in range(config.num_sets)]
        # LRU bookkeeping: for each set, the index of the MOST recently used way.
        # The LRU victim is the "other" way (works exactly for 2-way).
        self.mru_way = [0] * config.num_sets

    # ---- internal helpers ----
    def _find_way(self, set_index: int, tag: int):
        """Return the way index that holds (valid, tag) in this set, or None."""
        for w, way in enumerate(self.sets[set_index]):
            if way.valid and way.tag == tag:
                return w
        return None

    def _choose_victim(self, set_index: int) -> int:
        """Pick a way to install into: first invalid way, else the LRU way."""
        ways = self.sets[set_index]
        for w, way in enumerate(ways):
            if not way.valid:
                return w
        # all ways valid -> evict LRU. For 2-way, LRU is the way that is NOT mru.
        if self.cfg.associativity == 1:
            return 0
        return 1 - self.mru_way[set_index]

    def _touch(self, set_index: int, way_index: int) -> None:
        """Mark a way as most-recently-used."""
        self.mru_way[set_index] = way_index

    # ---- public access API ----
    def load(self, word_addr: int) -> int:
        s = self.cfg.set_index(word_addr)
        t = self.cfg.tag(word_addr)
        off = self.cfg.block_offset(word_addr)

        self.stats.reads += 1
        w = self._find_way(s, t)

        if w is not None:                       # READ HIT
            self.stats.hits += 1
            self.stats.read_hits += 1
            self._touch(s, w)
            value = self.sets[s][w].data[off]
            self._trace("LW", word_addr, s, t, off, "HIT", 0, value)
            return value

        # READ MISS -> refill whole block from main memory
        self.stats.misses += 1
        self.stats.read_misses += 1
        victim = self._choose_victim(s)
        if self.sets[s][victim].valid:
            self.stats.evictions += 1
        block = self.mem.read_block(word_addr)
        way = self.sets[s][victim]
        way.valid = True
        way.tag = t
        way.data = list(block)
        self._touch(s, victim)
        self.stats.stall_cycles += MISS_PENALTY_CYCLES
        value = way.data[off]
        self._trace("LW", word_addr, s, t, off, "MISS", MISS_PENALTY_CYCLES, value)
        return value

    def store(self, word_addr: int, value: int) -> None:
        s = self.cfg.set_index(word_addr)
        t = self.cfg.tag(word_addr)
        off = self.cfg.block_offset(word_addr)

        self.stats.writes += 1
        value &= 0xFFFFFFFF

        # write-through: main memory is always updated, always stalls
        self.mem.write_word(word_addr, value)
        self.stats.stall_cycles += MISS_PENALTY_CYCLES

        w = self._find_way(s, t)
        if w is not None:                       # WRITE HIT -> update cached word
            self.stats.hits += 1
            self.stats.write_hits += 1
            self.sets[s][w].data[off] = value
            self._touch(s, w)
            self._trace("SW", word_addr, s, t, off, "HIT", MISS_PENALTY_CYCLES, value)
        else:                                   # WRITE MISS -> write-around (no allocate)
            self.stats.misses += 1
            self.stats.write_misses += 1
            self._trace("SW", word_addr, s, t, off, "MISS", MISS_PENALTY_CYCLES, value)

    def _trace(self, op, addr, s, t, off, result, stall, value):
        if self.tracer is not None:
            self.tracer.log_access(op, addr, s, t, off, result, stall, value)
