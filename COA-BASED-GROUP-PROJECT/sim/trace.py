"""
trace.py - Execution / cache-access trace logging.

Produces the human-readable execution traces required as a deliverable
(per-access cache behavior and, optionally, per-instruction CPU state).
"""


class Tracer:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.access_log: list[dict] = []
        self.instr_log: list[dict] = []

    def log_access(self, op, addr, set_index, tag, offset, result, stall, value):
        if not self.enabled:
            return
        self.access_log.append(dict(
            op=op, word_addr=addr, set_index=set_index, tag=tag,
            offset=offset, result=result, stall=stall, value=value,
        ))

    def log_instruction(self, index, pc, mnemonic, note=""):
        if not self.enabled:
            return
        self.instr_log.append(dict(
            index=index, pc=pc, mnemonic=mnemonic, note=note,
        ))

    def access_table(self) -> str:
        lines = [
            "idx | op | word_addr | set | tag | off | result | stall | value",
            "----+----+-----------+-----+-----+-----+--------+-------+---------",
        ]
        for i, a in enumerate(self.access_log):
            lines.append(
                f"{i:3d} | {a['op']:2s} | {a['word_addr']:9d} | {a['set_index']:3d} | "
                f"{a['tag']:3d} | {a['offset']:3d} | {a['result']:6s} | "
                f"{a['stall']:5d} | 0x{a['value']:08x}"
            )
        return "\n".join(lines)
