"""
runner.py - Shared harness to run one workload through one cache config.

Keeps the baseline and enhanced runs on EXACTLY the same code path so the
comparison is fair: same CPU, same memory, same policy, same latencies -
only the CacheConfig (associativity) differs.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import CacheConfig
from memory import MainMemory
from cache import Cache
from stats import Stats
from trace import Tracer
from cpu import CPU


def run_program(program: list[int], config: CacheConfig, label: str,
                trace: bool = False):
    """Run a machine-code program; return (stats, cpu, memory, tracer)."""
    mem = MainMemory()
    stats = Stats(label=label)
    tracer = Tracer(enabled=trace)
    cache = Cache(config, mem, stats, tracer)
    cpu = CPU(program, cache, stats, tracer)
    cpu.run()
    return stats, cpu, mem, tracer


def run_address_trace(addresses, config: CacheConfig, label: str,
                      trace: bool = False):
    """
    Drive the cache directly from a list of (op, word_addr[, value]) tuples,
    where op is 'L' (load) or 'S' (store). Used by unit tests and by workloads
    that are defined as pure access traces rather than full programs.

    Each access still counts as one 'instruction' so CPI/cycle accounting stays
    comparable with program-driven runs.
    """
    mem = MainMemory()
    stats = Stats(label=label)
    tracer = Tracer(enabled=trace)
    cache = Cache(config, mem, stats, tracer)
    for item in addresses:
        op = item[0]
        addr = item[1]
        stats.instructions += 1
        if op == "L":
            cache.load(addr)
        elif op == "S":
            value = item[2] if len(item) > 2 else 0
            cache.store(addr, value)
        else:
            raise ValueError(f"unknown op {op!r}")
    return stats, cache, mem, tracer
