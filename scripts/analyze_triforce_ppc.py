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
    0x811F, 0x8120, 0xCC00, 0xFF00, 0x2440, 0x0910, 0x4000, 0x6000, 0x7000,
    0x400000, 0x600000, 0x700000, 0x70, 0x20, 0x1000, 0x0800, 0x80, 0x40, 0xA8, 0xAA, 0xAB,
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
    di_register_pairs = []
    si_register_pairs = []
    all_instructions = []
    for index, (file_offset, address, length) in enumerate(sections):
        with args.image.open("rb") as f:
            f.seek(dol_offset + file_offset)
            code = f.read(length)
        decoded = []
        for word_offset in range(0, len(code) - 3, 4):
            one = next(md.disasm(code[word_offset:word_offset + 4], address + word_offset), None)
            if one is not None:
                decoded.append(one)
        all_instructions.extend(decoded)
        for pos, insn in enumerate(decoded):
            if insn.mnemonic not in ("lis", "addis"):
                continue
            ops = insn.operands
            if len(ops) < 2 or ops[-1].type != PPC_OP_IMM:
                continue
            high = ops[-1].imm & 0xFFFF
            dest = ops[0].reg
            for nxt in decoded[pos + 1:pos + 5]:
                nops = nxt.operands
                if len(nops) < 3 or nops[-1].type != PPC_OP_IMM:
                    continue
                same_reg = nops[0].reg == dest and nops[1].reg == dest
                low = nops[-1].imm & 0xFFFF
                if not same_reg:
                    continue
                if ((high == 0x811F and nxt.mnemonic in ("ori", "addi") and low == 0xFF00) or
                    (high == 0x8120 and nxt.mnemonic in ("addi", "subi") and low in (0xFF00, 0x0100))):
                    reset_address_pairs.append((insn.address, nxt.address))
                    break
                if high == 0xCC00 and nxt.mnemonic in ("ori", "addi") and low in (0x6000, 0x6004, 0x6008, 0x600C, 0x6010):
                    di_register_pairs.append((insn.address, nxt.address, 0xCC000000 | low))
                if high == 0xCC00 and nxt.mnemonic in ("ori", "addi") and low in (0x6400, 0x6404, 0x6408, 0x640C, 0x6410, 0x6414, 0x6418, 0x641C, 0x6420):
                    si_register_pairs.append((insn.address, nxt.address, 0xCC000000 | low))
    lines.append("")
    lines.append(f"TOTAL DECODED INSTRUCTIONS: {decoded_total:,}")
    lines.append(f"BRANCH-AND-LINK CALLS: {len(calls):,}")
    lines.append("CALL TARGET SAMPLE: " + (
        "; ".join(f"0x{addr:08X} {op}" for addr, op in calls[:80]) or "(none)"
    ))
    lines.append("")
    # Detect the common PPC form for 0x811FFF00: lis rN, 0x8120
    # followed by an address calculation or D-form load/store at -0x100(rN).
    reset_direct_accesses = []
    for pos, insn in enumerate(all_instructions):
        if insn.mnemonic not in ("lis", "addis") or len(insn.operands) < 2:
            continue
        if insn.operands[-1].type != PPC_OP_IMM or (insn.operands[-1].imm & 0xFFFF) != 0x8120:
            continue
        base_reg = insn.operands[0].reg
        for nxt in all_instructions[pos + 1:pos + 17]:
            ops = nxt.operands
            if nxt.mnemonic in ("addi", "addis") and len(ops) >= 3 and ops[1].reg == base_reg and ops[-1].type == PPC_OP_IMM and ops[-1].imm == -0x100:
                reset_direct_accesses.append((insn.address, nxt.address, "address calculation"))
            for op in ops:
                if op.type == 3 and op.mem.base == base_reg and op.mem.disp == -0x100:
                    reset_direct_accesses.append((insn.address, nxt.address, nxt.mnemonic))
    lines.append(f"RESET FLAG 0x811FFF00 HIGH/LOW PAIRS: {len(reset_address_pairs)}")
    lines.append(f"RESET FLAG 0x811FFF00 DIRECT 0x81200000/-0x100 ACCESS CANDIDATES: {len(reset_direct_accesses)}")
    for high_addr, access_addr, kind in reset_direct_accesses[:80]:
        lines.append(f"0x{high_addr:08X} -> 0x{access_addr:08X} [{kind}]")
    instruction_by_address = {insn.address: insn for insn in all_instructions}
    for high_addr, low_addr in reset_address_pairs[:40]:
        lines.append(f"0x{high_addr:08X} + 0x{low_addr:08X} -> 0x811FFF00 candidate")
    if reset_address_pairs:
        lines.append("")
        lines.append("RESET FLAG ADDRESS CODE CONTEXT (±8 instructions):")
        emitted = set()
        for high_addr, low_addr in reset_address_pairs[:20]:
            for center in (high_addr, low_addr):
                ordered = sorted(instruction_by_address)
                try:
                    at = ordered.index(center)
                except ValueError:
                    continue
                for address in ordered[max(0, at - 8):at + 9]:
                    if address in emitted:
                        continue
                    emitted.add(address)
                    insn = instruction_by_address[address]
                    lines.append(f"0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
    lines.append("")
    lines.append(f"DI MMIO REGISTER ADDRESS PAIRS: {len(di_register_pairs)}")
    for high_addr, low_addr, effective in di_register_pairs[:100]:
        lines.append(f"0x{high_addr:08X} + 0x{low_addr:08X} -> 0x{effective:08X}")
    si_direct_accesses = []
    for pos, insn in enumerate(all_instructions):
        if insn.mnemonic not in ("lis", "addis") or len(insn.operands) < 2:
            continue
        if insn.operands[-1].type != PPC_OP_IMM or (insn.operands[-1].imm & 0xFFFF) != 0xCC00:
            continue
        base_reg = insn.operands[0].reg
        for nxt in all_instructions[pos + 1:pos + 25]:
            for op in nxt.operands:
                if op.type == 3 and op.mem.base == base_reg and 0x6400 <= op.mem.disp <= 0x6420:
                    si_direct_accesses.append((insn.address, nxt.address, op.mem.disp, nxt.mnemonic, nxt.op_str))
    if si_direct_accesses:
        lines.append("")
        lines.append(f"SI MMIO DIRECT ACCESS CANDIDATES: {len(si_direct_accesses)}")
        for high_addr, access_addr, disp, mnemonic, operands in si_direct_accesses[:160]:
            lines.append(f"0x{high_addr:08X} -> 0x{access_addr:08X}: {mnemonic} {operands} [0xCC00{disp:04X}]")
        lines.append("SI MMIO DIRECT ACCESS CONTEXT (±10 instructions):")
        emitted = set()
        ordered = sorted(instruction_by_address)
        for high_addr, access_addr, disp, mnemonic, operands in si_direct_accesses[:50]:
            try:
                at = ordered.index(access_addr)
            except ValueError:
                continue
            for address in ordered[max(0, at - 10):at + 11]:
                if address not in emitted:
                    emitted.add(address)
                    insn = instruction_by_address[address]
                    lines.append(f"0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
    if si_register_pairs:
        lines.append("")
        lines.append(f"SI MMIO REGISTER ADDRESS PAIRS: {len(si_register_pairs)}")
        for high_addr, low_addr, effective in si_register_pairs[:100]:
            lines.append(f"0x{high_addr:08X} + 0x{low_addr:08X} -> 0x{effective:08X}")
        lines.append("SI MMIO ACCESS CODE CONTEXT (±12 instructions):")
        emitted = set()
        ordered = sorted(instruction_by_address)
        for high_addr, low_addr, effective in si_register_pairs[:40]:
            for center in (high_addr, low_addr):
                try:
                    at = ordered.index(center)
                except ValueError:
                    continue
                for address in ordered[max(0, at - 12):at + 13]:
                    if address not in emitted:
                        emitted.add(address)
                        insn = instruction_by_address[address]
                        lines.append(f"0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
    if si_register_pairs:
        lines.append("")
        lines.append("SI MMIO ENCLOSING ROUTINES AND CALLERS:")
        ordered = sorted(instruction_by_address)
        emitted_starts = set()
        for high_addr, access_addr, effective in si_register_pairs:
            try:
                at = ordered.index(access_addr)
            except ValueError:
                continue
            starts = [a for a in ordered[max(0, at - 180):at + 1]
                      if instruction_by_address[a].mnemonic == "stwu"
                      and instruction_by_address[a].op_str.startswith("r1, -")]
            if not starts:
                lines.append(f"-- access 0x{access_addr:08X}: no nearby stack-frame prologue found --")
                continue
            start = starts[-1]
            if start in emitted_starts:
                continue
            emitted_starts.add(start)
            end_candidates = [a for a in ordered[ordered.index(start) + 1:
                                                    min(len(ordered), ordered.index(start) + 500)]
                              if instruction_by_address[a].mnemonic == "blr"]
            end = end_candidates[0] if end_candidates else ordered[min(len(ordered) - 1,
                                                                          ordered.index(start) + 120)]
            lines.append(f"-- routine 0x{start:08X}..0x{end:08X} (SI access near 0x{access_addr:08X}) --")
            for address in ordered[ordered.index(start):ordered.index(end) + 1]:
                insn = instruction_by_address[address]
                lines.append(f"0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
            xrefs = [(a, op) for a, op in calls
                     if op.strip().lower() in (hex(start), f"0x{start:08x}")]
            lines.append("DIRECT CALLERS: " + (", ".join(f"0x{a:08X}" for a, _ in xrefs) or "(none found)"))
            for caller, _ in xrefs[:12]:
                try:
                    caller_at = ordered.index(caller)
                except ValueError:
                    continue
                lines.append(f"CALLER CONTEXT around 0x{caller:08X}:")
                for address in ordered[max(0, caller_at - 10):caller_at + 8]:
                    insn = instruction_by_address[address]
                    lines.append(f"0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
    # SI functions are often installed as callbacks or stored in SDK
    # dispatch tables. Search both code address construction and aligned
    # DOL words for references, not only direct branch-and-link callers.
    si_function_targets = (0x8020F33C, 0x8020F62C, 0x8020FE80,
                           0x8020FEF4, 0x8020FF08, 0x8020FF18, 0x8020FF8C)
    lines.append("")
    lines.append("SI FUNCTION POINTER / ADDRESS REFERENCES:")
    for target in si_function_targets:
        direct = [a for a, op in calls if op.strip().lower() in
                  (hex(target), f"0x{target:08x}")]
        constructed = []
        for pos, insn in enumerate(all_instructions):
            if insn.mnemonic not in ("lis", "addis") or len(insn.operands) < 2:
                continue
            if insn.operands[-1].type != PPC_OP_IMM:
                continue
            high = insn.operands[-1].imm & 0xFFFF
            base_reg = insn.operands[0].reg
            for nxt in all_instructions[pos + 1:pos + 5]:
                ops = nxt.operands
                if len(ops) < 3 or ops[1].reg != base_reg or ops[-1].type != PPC_OP_IMM:
                    continue
                low = ops[-1].imm
                if nxt.mnemonic == "addi":
                    value = (((high << 16) + low) & 0xFFFFFFFF)
                elif nxt.mnemonic == "ori":
                    value = ((high << 16) | (low & 0xFFFF))
                else:
                    continue
                if value == target:
                    constructed.append((insn.address, nxt.address))
                    break
        data_refs = []
        with args.image.open("rb") as f:
            for file_offset, address, length in sections:
                f.seek(dol_offset + file_offset)
                section_data = f.read(length)
                for pos in range(0, len(section_data) - 3, 4):
                    if struct.unpack_from(">I", section_data, pos)[0] == target:
                        data_refs.append(address + pos)
        lines.append(f"TARGET 0x{target:08X}: direct BL callers=" +
                     (", ".join(f"0x{x:08X}" for x in direct) or "(none)") +
                     "; constructed addresses=" +
                     (", ".join(f"0x{a:08X}/0x{b:08X}" for a, b in constructed[:20]) or "(none)") +
                     "; aligned data pointers=" +
                     (", ".join(f"0x{x:08X}" for x in data_refs[:40]) or "(none)"))
        for ref_addr in [x for pair in constructed[:8] for x in pair]:
            try:
                at = ordered.index(ref_addr)
            except ValueError:
                continue
            lines.append(f"ADDRESS-REFERENCE CONTEXT at 0x{ref_addr:08X}:")
            for address in ordered[max(0, at - 5):at + 8]:
                insn = instruction_by_address[address]
                lines.append(f"0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
        for caller in direct[:20]:
            try:
                at = ordered.index(caller)
            except ValueError:
                continue
            starts = [a for a in ordered[max(0, at - 180):at + 1]
                      if instruction_by_address[a].mnemonic == "stwu"
                      and instruction_by_address[a].op_str.startswith("r1, -")]
            start = starts[-1] if starts else ordered[max(0, at - 12)]
            ends = [a for a in ordered[at:min(len(ordered), at + 500)]
                    if instruction_by_address[a].mnemonic == "blr"]
            end = ends[0] if ends else ordered[min(len(ordered) - 1, at + 80)]
            lines.append(f"CALLER ROUTINE 0x{start:08X}..0x{end:08X} for target 0x{target:08X}:")
            for address in ordered[ordered.index(start):ordered.index(end) + 1]:
                insn = instruction_by_address[address]
                lines.append(f"0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
    lines.append("")
    if di_register_pairs:
        lines.append("")
        lines.append("DI MMIO ACCESS CODE CONTEXT (±10 instructions):")
        emitted = set()
        ordered = sorted(instruction_by_address)
        for high_addr, low_addr, effective in di_register_pairs[:30]:
            for center in (high_addr, low_addr):
                try:
                    at = ordered.index(center)
                except ValueError:
                    continue
                for address in ordered[max(0, at - 10):at + 11]:
                    if address in emitted:
                        continue
                    emitted.add(address)
                    insn = instruction_by_address[address]
                    lines.append(f"0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
    lines.append("")
    lines.append("RESET-FLAG CANDIDATE FUNCTION TRACE:")
    ordered = sorted(instruction_by_address)
    for candidate in (0x801C661C, 0x801C662C):
        if candidate not in instruction_by_address:
            lines.append(f"0x{candidate:08X}: address not decoded")
            continue
        at = ordered.index(candidate)
        # Find a nearby conventional PPC function prologue, then its return.
        starts = [a for a in ordered[max(0, at - 160):at + 1]
                  if instruction_by_address[a].mnemonic == "stwu"
                  and instruction_by_address[a].op_str.startswith("r1, -")]
        start = starts[-1] if starts else ordered[max(0, at - 40)]
        end_candidates = [a for a in ordered[at:min(len(ordered), at + 240)]
                          if instruction_by_address[a].mnemonic == "blr"]
        end = end_candidates[0] if end_candidates else ordered[min(len(ordered)-1, at + 80)]
        lines.append(f"-- candidate 0x{candidate:08X}; probable function 0x{start:08X}..0x{end:08X} --")
        for address in ordered[max(0, ordered.index(start)):ordered.index(end) + 1]:
            insn = instruction_by_address[address]
            lines.append(f"0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
        # Static direct-call xrefs to the probable function start and candidate.
        xrefs = [(a, op) for a, op in calls
                 if op.strip() in (hex(start), hex(candidate), f"0x{start:08x}", f"0x{candidate:08x}")]
        lines.append("CALL XREFS: " + (", ".join(f"0x{a:08X}" for a, _ in xrefs) or "(none found)"))
    lines.append("")
    lines.append("TARGETED CODE WINDOWS:")
    for center in (0x800546EC, 0x8005C310, 0x8000FEB8, 0x801DC760, 0x80039C00, 0x80039D00, 0x801C6A20, 0x801C6B30, 0x801C7408, 0x801C744C, 0x801C897C, 0x8020FF18, 0x80210A70, 0x801CEA2C, 0x801CEAEC, 0x801CECBC, 0x801CF12C, 0x801CF130, 0x80039D40, 0x80039F00, 0x80039FBC, 0x8003A02C, 0x80039E94, 0x8005B86C, 0x801C6A24, 0x801C709C, 0x801C7138, 0x801C6FE8, 0x801C726C, 0x801C7450, 0x801C7928, 0x801CB7E4, 0x801CB864, 0x8022DDE0, 0x80226CD0):
        if center not in instruction_by_address:
            continue
        at = ordered.index(center)
        lines.append(f"-- around 0x{center:08X} --")
        for address in ordered[max(0, at - 12):at + 101]:
            insn = instruction_by_address[address]
            lines.append(f"0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
    target_hits = [hit for hit in all_hits if any(value in (0x910, 0x2440, 0xFF00, 0x811FFF00) for value in hit[3])]
    lines.append("")
    lines.append(f"TARGETED RESET/DI IMMEDIATE HITS: {len(target_hits)}")
    for addr, mnemonic, operands, matched in target_hits[:200]:
        values = ",".join(f"0x{x:X}" for x in matched)
        lines.append(f"0x{addr:08X}: {mnemonic} {operands} [imm {values}]")
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
    # Locate likely GC-AM/JVS transaction setup sequences. The known probe
    # sends command 0x70 with subcommand 0x40, then JVS SwitchInput 0x20.
    # This is a heuristic only: candidates require both constants and a call
    # in a short instruction window; they are not assigned semantic meaning.
    jvs_command_candidates = []
    for pos, insn in enumerate(all_instructions):
        if insn.mnemonic != "li" or len(insn.operands) < 2:
            continue
        if insn.operands[-1].type != PPC_OP_IMM or (insn.operands[-1].imm & 0xFFFF) != 0x70:
            continue
        window = all_instructions[pos:min(len(all_instructions), pos + 24)]
        has_40 = any(x.mnemonic == "li" and len(x.operands) >= 2
                     and x.operands[-1].type == PPC_OP_IMM
                     and (x.operands[-1].imm & 0xFFFF) == 0x40 for x in window)
        has_call = any(x.mnemonic in ("bl", "bla") for x in window)
        if has_40 and has_call:
            jvs_command_candidates.append(insn.address)
    lines.append("")
    lines.append(f"GC-AM/JVS 0x70 + 0x40 CALL-SEQUENCE CANDIDATES: {len(jvs_command_candidates)}")
    emitted = set()
    ordered = sorted(instruction_by_address)
    for center in jvs_command_candidates[:80]:
        at = ordered.index(center)
        lines.append(f"-- candidate around 0x{center:08X} --")
        for address in ordered[max(0, at - 8):at + 25]:
            if address not in emitted:
                emitted.add(address)
                insn = instruction_by_address[address]
                lines.append(f"0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
    lines.append("")
    lines.append("TEST-MENU / JVS INPUT INVESTIGATION")
    lines.append("Immediate-mask candidates (inspect surrounding function before assigning meaning):")
    mask_hits = []
    for insn in all_instructions:
        immediates = [op.imm & 0xFFFFFFFF for op in insn.operands if op.type == PPC_OP_IMM]
        if any(value in (0x1000, 0x0800, 0x80, 0x40) for value in immediates):
            mask_hits.append(insn)
    lines.append(f"BUTTON-MASK IMMEDIATE HITS: {len(mask_hits)}")
    for insn in mask_hits[:300]:
        lines.append(f"0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")

    # The test-menu text is in the DOL's read-only data section. Resolve its
    # virtual addresses from the section map and report direct PPC references.
    menu_strings = (
        (0x26A3F8, "VIRTUA STRIKER 2002 TEST MENU"),
        (0x26A418, "INPUT TEST"),
        (0x26A424, "OUTPUT TEST"),
        (0x26A464, "SELECT WITH SERVICE BUTTON"),
        (0x26A480, "AND PRESS TEST BUTTON"),
        (0x26AB68, "PRESS TEST BUTTON TO CONTINUE"),
        (0x26B014, "PRESS TEST BUTTON TO EXIT"),
        (0x26B744, "PRESS TEST AND SERVICE BUTTON TO EXIT"),
    )
    lines.append("")
    lines.append("TEST-MENU STRING REFERENCES:")
    string_refs = set()
    for dol_file_offset, label in menu_strings:
        for section_file, section_addr, section_len in sections:
            if section_file <= dol_file_offset < section_file + section_len:
                string_addr = section_addr + (dol_file_offset - section_file)
                break
        else:
            continue
        hits = []
        # PPC small-data relocations commonly use either:
        #   lis rN, high16(addr); ori/addi rN, rN, low16(addr)
        # or the adjusted-high/signed-low form:
        #   lis rN, (addr + 0x8000) >> 16; addi rM, rN, sign16(addr)
        # Account for both forms; the previous scan missed strings whose low
        # half had bit 15 set (e.g. 0x8026D3F8 -> lis 0x8027, addi -0x2C08).
        high_unsigned = (string_addr >> 16) & 0xFFFF
        low_unsigned = string_addr & 0xFFFF
        high_adjusted = ((string_addr + 0x8000) >> 16) & 0xFFFF
        low_signed = low_unsigned if low_unsigned < 0x8000 else low_unsigned - 0x10000
        for pos, insn in enumerate(all_instructions):
            if insn.mnemonic not in ("lis", "addis"):
                continue
            ops = insn.operands
            if len(ops) < 2 or ops[-1].type != PPC_OP_IMM:
                continue
            high = ops[-1].imm & 0xFFFF
            if high not in (high_unsigned, high_adjusted):
                continue
            dest = ops[0].reg
            for nxt in all_instructions[max(0, pos+1):pos+5]:
                nops = nxt.operands
                if len(nops) < 3 or nops[-1].type != PPC_OP_IMM or nops[1].reg != dest:
                    continue
                low = nops[-1].imm
                matches_unsigned = (nxt.mnemonic in ("ori", "addi") and (low & 0xFFFF) == low_unsigned)
                matches_adjusted = (nxt.mnemonic == "addi" and low == low_signed)
                if matches_unsigned or matches_adjusted:
                    hits.append((insn.address, nxt.address))
                    string_refs.add(insn.address)
                    string_refs.add(nxt.address)
                    break
        lines.append(f"{label} @ 0x{string_addr:08X}: " +
                     (", ".join(f"0x{a:08X}/0x{b:08X}" for a,b in hits[:12]) or "(no direct lis+addi reference found)"))
    # Report context around logical mask-building instructions. In PPC, ORIS
    # shifts the 16-bit immediate into the upper half, so 0x0800/0x1000
    # may appear as ORIS immediates rather than low-half AND masks.
    logical_mask_candidates = [
        insn for insn in all_instructions
        if insn.mnemonic in ("ori", "oris", "andi.", "andis.")
        and any((op.imm & 0xFFFF) in (0x0800, 0x1000) for op in insn.operands
                if op.type == PPC_OP_IMM)
    ]
    lines.append("")
    lines.append(f"LOGICAL TEST/SERVICE MASK CANDIDATES: {len(logical_mask_candidates)}")
    if logical_mask_candidates:
        ordered_addresses = sorted(instruction_by_address)
        emitted = set()
        for center_insn in logical_mask_candidates[:80]:
            at = ordered_addresses.index(center_insn.address)
            for address in ordered_addresses[max(0, at-20):at+21]:
                if address not in emitted:
                    emitted.add(address)
                    insn = instruction_by_address[address]
                    lines.append(f"0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")

    if string_refs:
        ordered_addresses = sorted(instruction_by_address)
        lines.append("")
        lines.append("CODE AROUND TEST-MENU STRING REFERENCES (±12 instructions):")
        emitted = set()
        for center in sorted(string_refs):
            at = ordered_addresses.index(center)
            for address in ordered_addresses[max(0, at-12):at+13]:
                if address not in emitted:
                    emitted.add(address)
                    insn = instruction_by_address[address]
                    lines.append(f"0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")

    lines.append(f"SELECTED DOL STRINGS: {len(strings)}")
    for offset, value in strings[:100]:
        lines.append(f"file+0x{offset:X}: {value}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
