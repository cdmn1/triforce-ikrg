#!/usr/bin/env python3
"""Replace a GameCube GCM's main DOL in-place for a local/ephemeral test."""
import argparse
import hashlib
import os
import shutil
import struct
from pathlib import Path

MAGIC = 0xC2339F3D
BOOT_SIZE = 0x440
BI2_OFFSET, BI2_SIZE = 0x440, 0x2000
APP_OFFSET, APP_HEADER_SIZE = 0x2440, 0x20


def fail(message):
    raise SystemExit("GCM DOL replacement: FAIL: " + message)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def validate_dol(data):
    if len(data) < 0x100:
        fail("replacement DOL is smaller than its 0x100-byte header")
    offsets = struct.unpack_from(">18I", data, 0x00)
    addresses = struct.unpack_from(">18I", data, 0x48)
    sizes = struct.unpack_from(">18I", data, 0x90)
    entry = struct.unpack_from(">I", data, 0xE0)[0]
    sections = []
    for index, (off, addr, size) in enumerate(zip(offsets, addresses, sizes)):
        if not size:
            continue
        if off < 0x100 or off + size > len(data) or addr == 0:
            fail(f"DOL section {index} has invalid file/load bounds")
        sections.append((off, off + size, addr, addr + size, index))
    if not sections or entry == 0:
        fail("replacement DOL has no loadable sections or entry point")
    if not any(start <= entry < end for _, _, start, end, _ in sections):
        fail("DOL entry point is not inside a loaded section")
    return entry, sections


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_iso", type=Path)
    parser.add_argument("replacement_dol", type=Path)
    parser.add_argument("output_iso", type=Path)
    args = parser.parse_args()
    if not args.source_iso.is_file() or not args.replacement_dol.is_file():
        fail("source ISO or replacement DOL does not exist")

    source_size = args.source_iso.stat().st_size
    dol = args.replacement_dol.read_bytes()
    entry, sections = validate_dol(dol)
    with open(args.source_iso, "rb") as src:
        boot = src.read(BOOT_SIZE)
        if len(boot) != BOOT_SIZE:
            fail("source image is too small for a GameCube boot header")
        magic = struct.unpack_from(">I", boot, 0x1C)[0]
        if magic != MAGIC:
            fail(f"unexpected boot magic 0x{magic:08X}")
        dol_offset, fst_offset, fst_size, fst_max = struct.unpack_from(">IIII", boot, 0x420)
        if not dol_offset or not fst_offset or not fst_size or fst_offset <= dol_offset:
            fail("source boot header has invalid DOL/FST offsets")
        if dol_offset < APP_OFFSET + APP_HEADER_SIZE:
            fail("DOL slot overlaps the system area")
        if fst_offset + fst_size > source_size or fst_max < fst_size:
            fail("source FST range or maximum size is invalid")
        capacity = fst_offset - dol_offset
        if len(dol) > capacity:
            fail(f"replacement DOL ({len(dol)} bytes) exceeds DOL slot ({capacity} bytes)")
        src.seek(APP_OFFSET)
        app_header = src.read(APP_HEADER_SIZE)
        if len(app_header) != APP_HEADER_SIZE:
            fail("source apploader header is truncated")
        app_code, app_trailer = struct.unpack_from(">II", app_header, 0x14)
        app_size = APP_HEADER_SIZE + app_code + app_trailer
        if APP_OFFSET + app_size > dol_offset:
            fail("source apploader overlaps the DOL slot")

    args.output_iso.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.source_iso, args.output_iso)
    with open(args.output_iso, "r+b") as dst:
        dst.seek(dol_offset)
        dst.write(b"\\0" * capacity)
        dst.seek(dol_offset)
        dst.write(dol)
        dst.flush()
        os.fsync(dst.fileno())

    with open(args.source_iso, "rb") as src, open(args.output_iso, "rb") as out:
        if src.read(BOOT_SIZE) != out.read(BOOT_SIZE):
            fail("boot header changed unexpectedly")
        src.seek(BI2_OFFSET); out.seek(BI2_OFFSET)
        if src.read(BI2_SIZE) != out.read(BI2_SIZE):
            fail("BI2 changed unexpectedly")
        src.seek(APP_OFFSET); out.seek(APP_OFFSET)
        if src.read(app_size) != out.read(app_size):
            fail("apploader changed unexpectedly")
        src.seek(dol_offset); out.seek(dol_offset)
        if out.read(len(dol)) != dol:
            fail("replacement DOL does not match at the declared DOL offset")
        src.seek(fst_offset); out.seek(fst_offset)
        if src.read(fst_size) != out.read(fst_size):
            fail("FST changed unexpectedly")
        if os.path.getsize(args.output_iso) != source_size:
            fail("candidate image size changed")

    print("GCM DOL REPLACEMENT: PASS")
    print(f"Image size: {source_size} bytes (unchanged)")
    print(f"GameCube magic: 0x{MAGIC:08X}")
    print(f"DOL offset: 0x{dol_offset:X}; slot capacity: {capacity} bytes")
    print(f"FST offset: 0x{fst_offset:X}; size: 0x{fst_size:X}")
    print(f"Replacement DOL: {len(dol)} bytes; sections: {len(sections)}; entry: 0x{entry:08X}")
    print(f"Replacement DOL SHA-256: {hashlib.sha256(dol).hexdigest()}")
    print(f"Candidate GCM SHA-256: {sha256_file(args.output_iso)}")
    print("Preserved and verified: boot header, BI2, apploader, FST and image length")
    print("NOTE: structural candidate only; apploader execution and Triforce boot are untested")


if __name__ == "__main__":
    main()
