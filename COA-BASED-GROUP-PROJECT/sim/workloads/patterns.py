"""
patterns.py - The three experimental workloads, defined as access traces.

Each workload is a list of (op, word_addr[, value]) tuples driven through the
SAME cache harness for both the baseline and enhanced configs. Addresses are
chosen from the ACTUAL address-mapping logic (config.py) and each choice is
justified in the docstring so the mapping can be defended in a viva.

Word-address space is 0..1023 (10-bit). A block is 4 words. The baseline has
32 sets (index = bits[6:2]); the enhanced has 16 sets (index = bits[5:2]).

Two block base addresses B1, B2 collide in the SAME set when they differ by a
multiple of (num_sets * words_per_block). For the baseline that span is
32*4 = 128 words; for the enhanced it is 16*4 = 64 words. Addresses that are a
multiple of 128 apart therefore collide in BOTH caches - the difference is that
the 2-way cache can keep two colliding blocks resident at once.
"""

# ---- Workload 1: Sequential access (spatial locality) ----
# Traverse a contiguous region of 64 words (16 blocks) once, as a load stream.
# Purpose: ordinary spatial locality. Within each 4-word block the first word
# misses (cold) and the next three hit. Associativity should NOT matter here
# because there is no set contention - we expect baseline == enhanced.
def sequential(n_words: int = 64):
    return [("L", a) for a in range(n_words)]


# ---- Workload 2: Repeated access (temporal locality) ----
# A small working set of 8 words (spanning 2 blocks) accessed repeatedly.
# These 8 words live in blocks {0..3} (set 0..0) and {4..7} (set 1) in BOTH
# caches, so they fit comfortably with no contention. After the first pass
# everything hits. Purpose: temporal locality; again we expect baseline and
# enhanced to behave essentially the same (both capture the reuse).
def repeated(working_set=(0, 1, 2, 3, 4, 5, 6, 7), repeats: int = 8):
    trace = []
    for _ in range(repeats):
        for a in working_set:
            trace.append(("L", a))
    return trace


# ---- Workload 3: Conflict-heavy access ----
# Alternate between TWO block base addresses that map to the SAME set in the
# direct-mapped cache: word 0 and word 128.
#   baseline: set_index(0)=0, set_index(128)=0  -> same set, 1 way
#             -> each alternation evicts the other -> conflict miss every time
#   enhanced: set_index(0)=0, set_index(128)=0  -> same set, 2 ways
#             -> both blocks stay resident -> hits after the two cold misses
# This is the scenario the enhancement is designed to fix.
def conflict(iterations: int = 16):
    trace = []
    for _ in range(iterations):
        trace.append(("L", 0))     # block at words 0..3,   set 0
        trace.append(("L", 128))   # block at words 128..131, set 0
    return trace


# A tougher conflict variant: THREE blocks competing for one set. A 2-way cache
# still thrashes here (only 2 ways for 3 hot blocks), which is an honest result
# we report rather than hide - it shows 2-way helps but is not a cure-all.
def conflict3(iterations: int = 16):
    trace = []
    for _ in range(iterations):
        for a in (0, 128, 256):    # all map to set 0 in both caches
            trace.append(("L", a))
    return trace


ALL_WORKLOADS = {
    "sequential": sequential,
    "repeated": repeated,
    "conflict": conflict,
    "conflict3": conflict3,
}
