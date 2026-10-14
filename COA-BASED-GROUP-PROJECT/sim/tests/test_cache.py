"""
test_cache.py - Unit and regression tests (Phase 5, Tests A-G).

Run with:  python -m unittest discover -s sim/tests  (from repo root)
       or:  python test_cache.py                      (from sim/tests)

Each test maps to a lettered scenario from the project brief and verifies the
cache behaves correctly AND that the direct-mapped vs 2-way difference is real.
"""

import os
import sys
import unittest

_SIM = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _SIM)

from config import BASELINE, ENHANCED
from memory import MainMemory
from cache import Cache
from stats import Stats
from runner import run_address_trace, run_program
from workloads.original_trace import load_program, EXPECTED_MEM
from workloads import patterns


def fresh(config):
    mem = MainMemory()
    stats = Stats(label=config.name)
    return Cache(config, mem, stats), mem, stats


class TestAddressDecomposition(unittest.TestCase):
    """Sanity: field widths derived from geometry are correct."""

    def test_baseline_fields(self):
        self.assertEqual((BASELINE.tag_bits, BASELINE.index_bits,
                          BASELINE.offset_bits), (3, 5, 2))
        self.assertEqual(BASELINE.num_sets, 32)

    def test_enhanced_fields(self):
        self.assertEqual((ENHANCED.tag_bits, ENHANCED.index_bits,
                          ENHANCED.offset_bits), (4, 4, 2))
        self.assertEqual(ENHANCED.num_sets, 16)

    def test_known_mapping(self):
        # word 50 -> set 12, offset 2 in the baseline (checked in validation)
        self.assertEqual(BASELINE.set_index(50), 12)
        self.assertEqual(BASELINE.block_offset(50), 2)


class TestA_ColdMiss(unittest.TestCase):
    """Test A: a previously unused address produces a compulsory miss."""

    def test_cold_miss_both(self):
        for cfg in (BASELINE, ENHANCED):
            cache, mem, stats = fresh(cfg)
            mem.write_word(20, 0xDEAD)
            cache.load(20)
            self.assertEqual(stats.misses, 1, cfg.name)
            self.assertEqual(stats.read_misses, 1, cfg.name)
            self.assertEqual(stats.hits, 0, cfg.name)


class TestB_RepeatedAccess(unittest.TestCase):
    """Test B: first access misses, subsequent accesses hit (block resident)."""

    def test_repeat_hits(self):
        for cfg in (BASELINE, ENHANCED):
            cache, mem, stats = fresh(cfg)
            mem.write_word(20, 0x1234)
            for _ in range(5):
                cache.load(20)
            self.assertEqual(stats.misses, 1, cfg.name)
            self.assertEqual(stats.hits, 4, cfg.name)


class TestC_TwoBlocksOneSet(unittest.TestCase):
    """Test C: two blocks mapping to the same set coexist in the 2-way cache."""

    def test_coexist_enhanced(self):
        cache, mem, stats = fresh(ENHANCED)
        # words 0 and 128 both map to set 0 in the enhanced cache
        self.assertEqual(ENHANCED.set_index(0), ENHANCED.set_index(128))
        cache.load(0)      # miss, way 0
        cache.load(128)    # miss, way 1
        cache.load(0)      # should HIT - still resident in 2-way
        cache.load(128)    # should HIT
        self.assertEqual(stats.misses, 2)
        self.assertEqual(stats.hits, 2)
        self.assertEqual(stats.evictions, 0)

    def test_thrash_baseline(self):
        cache, mem, stats = fresh(BASELINE)
        # same two addresses THRASH the direct-mapped cache (1 way)
        cache.load(0)      # miss
        cache.load(128)    # miss, evicts block 0
        cache.load(0)      # miss again (evicted), evicts block 128
        cache.load(128)    # miss again
        self.assertEqual(stats.misses, 4)
        self.assertEqual(stats.hits, 0)
        self.assertEqual(stats.evictions, 3)


class TestD_LRUReplacement(unittest.TestCase):
    """Test D: fill both ways, re-touch one, then a third block evicts the LRU."""

    def test_lru_victim(self):
        cache, mem, stats = fresh(ENHANCED)
        # three blocks all mapping to set 0: words 0, 128, 256
        for a in (0, 128, 256):
            self.assertEqual(ENHANCED.set_index(a), 0)
        cache.load(0)      # way for block0 (A)
        cache.load(128)    # way for block1 (B); set now {A,B}, MRU=B
        cache.load(0)      # touch A -> MRU=A, so B is now LRU
        cache.load(256)    # miss -> must evict LRU = B (block128), keep A
        # verify: block 0 (A) still resident -> hit; block 128 (B) evicted -> miss
        hits_before = stats.hits
        cache.load(0)      # expect HIT (A kept)
        self.assertEqual(stats.hits, hits_before + 1, "LRU kept the wrong block")
        miss_before = stats.misses
        cache.load(128)    # expect MISS (B was evicted)
        self.assertEqual(stats.misses, miss_before + 1, "LRU evicted the wrong block")


class TestE_ConflictComparison(unittest.TestCase):
    """Test E: conflict workload - compare direct-mapped vs 2-way, analytically."""

    def test_conflict_counts(self):
        trace = patterns.conflict(iterations=16)  # 32 accesses: L0,L128 x16
        b_stats, *_ = run_address_trace(trace, BASELINE, "base-conflict")
        e_stats, *_ = run_address_trace(trace, ENHANCED, "enh-conflict")

        # Analytical expectation:
        #   baseline: every access conflicts -> 32 misses, 0 hits
        self.assertEqual(b_stats.misses, 32)
        self.assertEqual(b_stats.hits, 0)
        #   enhanced: 2 cold misses, then 30 hits
        self.assertEqual(e_stats.misses, 2)
        self.assertEqual(e_stats.hits, 30)
        # enhanced must strictly reduce misses here
        self.assertLess(e_stats.misses, b_stats.misses)

    def test_conflict3_is_honest(self):
        # 3 hot blocks, 2 ways: 2-way helps vs baseline but still thrashes.
        trace = patterns.conflict3(iterations=16)  # 48 accesses
        b_stats, *_ = run_address_trace(trace, BASELINE, "base-conflict3")
        e_stats, *_ = run_address_trace(trace, ENHANCED, "enh-conflict3")
        self.assertEqual(b_stats.misses, 48)       # baseline: all miss
        # enhanced: LRU with 3 blocks in 2 ways still misses every steady access
        # (classic LRU thrash); confirm it is NOT magically better than baseline
        self.assertGreaterEqual(e_stats.misses, 40)


class TestF_MemoryCorrectness(unittest.TestCase):
    """Test F: enhanced cache returns correct data and preserves semantics."""

    def test_write_through_read_back(self):
        for cfg in (BASELINE, ENHANCED):
            cache, mem, stats = fresh(cfg)
            cache.store(10, 0xABCD1234)      # write-through: main mem updated
            self.assertEqual(mem.read_word(10), 0xABCD1234, cfg.name)
            # write-around: a missing store does NOT allocate
            self.assertIsNone(cache._find_way(cfg.set_index(10), cfg.tag(10)),
                              f"{cfg.name}: store should not allocate (write-around)")
            # a subsequent load fetches the correct value from memory
            self.assertEqual(cache.load(10), 0xABCD1234, cfg.name)

    def test_write_hit_updates_line(self):
        cfg = ENHANCED
        cache, mem, stats = fresh(cfg)
        cache.load(10)                       # allocate the block (read miss)
        cache.store(10, 0x55)                # write hit -> update cached word + mem
        self.assertEqual(mem.read_word(10), 0x55)
        self.assertEqual(cache.load(10), 0x55)  # served from cache, correct value


class TestG_RegressionOriginalProgram(unittest.TestCase):
    """Test G: run the original program on the enhanced cache; behavior correct."""

    def test_enhanced_matches_architecture(self):
        program = load_program()
        stats, cpu, mem, _ = run_program(program, ENHANCED, "enh-original")
        for a, exp in EXPECTED_MEM.items():
            self.assertEqual(mem.read_word(a), exp,
                             f"enhanced cache produced wrong memory[{a}]")
        # testbench criterion must still hold under the enhanced cache
        self.assertEqual(mem.read_word(50), 0xfffff8ae)

    def test_baseline_matches_architecture(self):
        program = load_program()
        stats, cpu, mem, _ = run_program(program, BASELINE, "base-original")
        for a, exp in EXPECTED_MEM.items():
            self.assertEqual(mem.read_word(a), exp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
