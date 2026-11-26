#!/usr/bin/env python3
"""Basic structural checks for a GameCube DOL; not a Triforce boot test."""
import struct
import sys
from pathlib import Path

HEADER_SIZE = 0x100
BSS_OFFSET = 0xD8
ENTRY_OFFSET = 0xE0


def fail(message):
    print("DOL VALIDATION: FAIL: " + message)
    raise SystemExit(1)


def main():
    if len(sys.argv) != 2:
        fail("usage: validate_dol.py path/to/file.dol")
    path = Path(sys.argv[1])
    if not path.is_file():
        fail("file not found: " + str(path))
    data = path.read_bytes()
    if len(data) < HEADER_SIZE:
        fail("file smaller than DOL header")

    offsets = struct.unpack_from(">18I", data, 0x00)
    addresses = struct.unpack_from(">18I", data, 0x48)
    sizes = struct.unpack_from(">18I", data, 0x90)
    bss_addr, bss_size, entry = struct.unpack_from(">III", data, BSS_OFFSET)

    count = 0
    for i, (offset, address, size) in enumerate(zip(offsets, addresses, sizes)):
        if not size:
            continue
        count += 1
        if offset < HEADER_SIZE:
            fail("section %d overlaps header" % i)
        if offset + size > len(data):
            fail("section %d extends beyond file" % i)
        if not address:
            fail("section %d has zero load address" % i)

    if not count:
        fail("no non-empty sections")
    if not entry:
        fail("zero entry point")

    print("DOL VALIDATION: PASS")
    print("File: %s" % path.name)
    print("Size: %d bytes" % len(data))
    print("Loaded sections: %d" % count)
    print("Entry point: 0x%08X" % entry)
    print("BSS: 0x%08X + 0x%X" % (bss_addr, bss_size))


if __name__ == "__main__":
    main()
