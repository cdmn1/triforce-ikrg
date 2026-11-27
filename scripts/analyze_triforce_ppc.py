#!/usr/bin/env python3
"""Disassemble selected PowerPC metadata from a Triforce reference image.

The report contains section maps, immediate-constant hits, call destinations,
and selected strings only. It never writes or uploads the executable payload.
"""
import argparse
import re
import struct
from pathlib import Path

from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN
from capstone.ppc import PPC_OP_IMM


INTERESTING = {
    0x811F, 0xCC00, 0xFF00, 0x2440, 0x4000, 0x6000, 0x7000,
    0x400000, 0x600000, 0x700000, 0xA8, 0xAA, 0xAB,
    0xCC006000, 0xCC006004, 0xCC006008, 0xCC00600C,
}
STRING_TERMS = (
    "reset", "firmware", "sega", "dimm", "media", "board",
    "service", "test", "jvs", "boot", "disc", "network",
)


def inspect_image(path):
    size = path.stat().st_size
    with path.open("rb") as f:
        header = f.read(0x440)
        if len(header) != 0x440 or struct.unpack_from(">I", header, 0x1C)[0] != 0xC2339F3D:
            raise ValueError("not a standard GameCube/Triforce image")
        dol_offset = struct.unpack_from(">I", header, 0x420)[0]
        f.seek(dol_offset)
        dh = f.read(0x100)
        offsets = struct.unpack_from(">18I", dh, 0)
        addresses = struct.unpack_from(">18I", dh, 0x48)
        lengths = struct.unpack_from(">18I", dh, 0x90)
        entry = struct.unpack_from(">I", dh, 0xE0)[0]
        sections = [(o, a, n) for o, a, n in zip(offsets, addresses, lengths) if n]
        return size, dol_offset, entry, sections


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    size, dol_offset, entry, sections = inspect_image(args.image)

    md = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
    md.detail = True
    lines = [
        "TRIFORCE REFERENCE POWERPC STATIC ANALYSIS",
        "Metadata-only output; executable bytes are not included.",
        f"IMAGE: {args.image.name}",
        f"IMAGE SIZE: {size:,} bytes",
        f"DOL OFFSET: 0x{dol_offset:X}",
        f"DOL ENTRY: 0x{entry:08X}",
        f"DOL SECTION COUNT: {len(sections)}",
        "",
    ]

    all_hits = []
    calls = []
    decoded_total = 0
    for index, (file_offset, address, length) in enumerate(sections):
        with args.image.open("rb") as f:
            f.seek(dol_offset + file_offset)
            code = f.read(length)
        decoded = []
        for word_offset in range(0, len(code) - 3, 4):
            one = next(md.disasm(code[word_offset:word_offset + 4], address + word_offset), None)
            if one is not None:
                decoded.append(one)
        decoded_total += len(decoded)
        lines.append(
            f"SECTION {index}: file+0x{file_offset:X}, address 0x{address:08X}, "
            f"{length:,} bytes, {len(decoded):,} word-aligned decode candidates"
        )
        for insn in decoded:
            immediates = [op.imm & 0xFFFFFFFF for op in insn.operands if op.type == PPC_OP_IMM]
            matched = [imm for imm in immediates
                       if imm in INTERESTING or (imm & 0xFFFF) in INTERESTING]
            if matched:
                all_hits.append((insn.address, insn.mnemonic, insn.op_str, matched))
            if insn.mnemonic in ("bl", "bla"):
                calls.append((insn.address, insn.op_str))

    # Look for the known reset-flag address assembled from PPC high/low immediates.
    reset_address_pairs = []
    for index, (file_offset, address, length) in enumerate(sections):
        with args.image.open("rb") as f:
            f.seek(dol_offset + file_offset)
            code = f.read(length)
        decoded = []
        for word_offset in range(0, len(code) - 3, 4):
            one = next(md.disasm(code[word_offset:word_offset + 4], address + word_offset), None)
            if one is not None:
                decoded.append(one)
        for pos, insn in enumerate(decoded):
            if insn.mnemonic not in ("lis", "addis"):
                continue
            ops = insn.operands
            if len(ops) < 2 or ops[-1].type != PPC_OP_IMM or (ops[-1].imm & 0xFFFF) != 0x811F:
                continue
            dest = ops[0].reg
            for nxt in decoded[pos + 1:pos + 4]:
                nops = nxt.operands
                if (nxt.mnemonic in ("ori", "addi") and len(nops) >= 3 and
                        nops[0].reg == dest and nops[1].reg == dest and
                        nops[2].type == PPC_OP_IMM and (nops[2].imm & 0xFFFF) == 0xFF00):
                    reset_address_pairs.append((insn.address, nxt.address))
                    break
    lines.append("")
    lines.append(f"TOTAL DECODED INSTRUCTIONS: {decoded_total:,}")
    lines.append(f"BRANCH-AND-LINK CALLS: {len(calls):,}")
    lines.append("CALL TARGET SAMPLE: " + (
        "; ".join(f"0x{addr:08X} {op}" for addr, op in calls[:80]) or "(none)"
    ))
    lines.append("")
    lines.append(f"RESET FLAG 0x811FFF00 HIGH/LOW PAIRS: {len(reset_address_pairs)}")
    for high_addr, low_addr in reset_address_pairs[:40]:
        lines.append(f"0x{high_addr:08X} + 0x{low_addr:08X} -> 0x811FFF00 candidate")
    lines.append("")
    lines.append(f"INTERESTING IMMEDIATE HITS: {len(all_hits)}")
    if all_hits:
        for addr, mnemonic, operands, matched in all_hits[:160]:
            values = ",".join(f"0x{x:X}" for x in matched)
            lines.append(f"0x{addr:08X}: {mnemonic} {operands} [imm {values}]")
    else:
        lines.append("(none)")
    lines.append("")

    with args.image.open("rb") as f:
        f.seek(dol_offset)
        dol_size = max(o + n for o, _, n in sections)
        dol = f.read(dol_size)
    strings = []
    for match in re.finditer(rb"[\x20-\x7e]{6,}", dol):
        value = match.group().decode("ascii", "replace")
        lower = value.lower()
        if any(term in lower for term in STRING_TERMS):
            strings.append((match.start(), value[:100]))
    lines.append(f"SELECTED DOL STRINGS: {len(strings)}")
    for offset, value in strings[:100]:
        lines.append(f"file+0x{offset:X}: {value}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
