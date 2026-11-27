#!/usr/bin/env python3
"""Read-only structural inspection of a reference Triforce/GameCube image.

Only metadata, offsets, hashes, and boot.id fields are emitted. No game data
is copied into the report or uploaded as an artifact.
"""
import argparse
import hashlib
import struct
from pathlib import Path

GC_MAGIC = 0xC2339F3D
BOOT_ID_MAGIC = b"BTID"


def sha256_range(path, offset=0, length=None):
    h = hashlib.sha256()
    with path.open("rb") as f:
        f.seek(offset)
        remaining = length
        while remaining is None or remaining > 0:
            block = f.read(1024 * 1024 if remaining is None else min(1024 * 1024, remaining))
            if not block:
                break
            h.update(block)
            if remaining is not None:
                remaining -= len(block)
    return h.hexdigest()


def ascii_field(data):
    return data.split(b"\0", 1)[0].decode("ascii", "replace").strip()


def inspect(path):
    size = path.stat().st_size
    lines = [
        f"FILE: {path.name}",
        f"SIZE: {size:,} bytes",
        f"SHA256: {sha256_range(path)}",
    ]
    if size < 0x440:
        return lines + ["FORMAT: too small for a GameCube boot header"]

    with path.open("rb") as f:
        boot = f.read(0x440)
        magic = struct.unpack_from(">I", boot, 0x1C)[0]
        lines.append(f"HEADER ID: {boot[:6].decode('ascii', 'replace')}")
        lines.append(f"DISC TITLE: {ascii_field(boot[0x20:0x40])}")
        lines.append(f"GAMECUBE MAGIC: 0x{magic:08X} ({'valid' if magic == GC_MAGIC else 'not standard GC magic'})")
        if magic != GC_MAGIC:
            return lines + ["FORMAT: not recognized as a standard GameCube/Triforce disc image"]

        dol, fst, fst_size, fst_max = struct.unpack_from(">IIII", boot, 0x420)
        lines.append(f"DOL OFFSET: 0x{dol:X}")
        lines.append(f"FST OFFSET/SIZE/MAX: 0x{fst:X} / {fst_size:,} / {fst_max:,}")
        lines.append(f"HEADER POINTER CHECK: {'PASS' if dol and fst and fst_size and fst + fst_size <= size else 'FAIL'}")

        # Apploader header and executable extent.
        if 0x2460 <= size:
            f.seek(0x2440)
            apph = f.read(0x20)
            app_date = apph[:16].split(b"\0", 1)[0].decode("ascii", "replace")
            app_entry, app_size, app_trailer = struct.unpack_from(">III", apph, 0x10)
            app_total = 0x20 + app_size + app_trailer
            lines.append(f"APPLOADER DATE: {app_date}")
            lines.append(f"APPLOADER ENTRY: 0x{app_entry:08X}")
            lines.append(f"APPLOADER CODE/TRAILER/TOTAL: {app_size:,} / {app_trailer:,} / {app_total:,} bytes")
            lines.append(f"APPLOADER RANGE CHECK: {'PASS' if 0x2440 + app_total <= size else 'FAIL'}")
        else:
            lines.append("APPLOADER: missing")

        # DOL section map.
        if dol + 0x100 <= size:
            f.seek(dol)
            dh = f.read(0x100)
            offsets = struct.unpack_from(">18I", dh, 0)
            addresses = struct.unpack_from(">18I", dh, 0x48)
            lengths = struct.unpack_from(">18I", dh, 0x90)
            entry = struct.unpack_from(">I", dh, 0xE0)[0]
            sections = [(o, a, n) for o, a, n in zip(offsets, addresses, lengths) if n]
            dol_end = max([0x100] + [o + n for o, _, n in sections])
            valid = bool(sections) and all(o >= 0x100 and dol + o + n <= size for o, _, n in sections)
            loaded = any(a <= entry < a + n for _, a, n in sections)
            lines.append(f"DOL ENTRY: 0x{entry:08X}")
            lines.append(f"DOL SECTIONS: {len(sections)}")
            lines.append(f"DOL RANGE/ENTRY CHECK: {'PASS' if valid and loaded else 'FAIL'}")
            lines.append(f"DOL EXTENT: {dol_end:,} bytes")
            if valid:
                lines.append(f"DOL SHA256: {sha256_range(path, dol, dol_end)}")
        else:
            lines.append("DOL: invalid offset")

        # FST directory and file entries.
        boot_id = None
        file_names = []
        if fst and fst_size >= 12 and fst + fst_size <= size:
            f.seek(fst)
            table = f.read(fst_size)
            count = struct.unpack_from(">I", table, 8)[0]
            table_bytes = count * 12
            fst_valid = count > 0 and table_bytes <= len(table)
            if fst_valid:
                _, _, root_end = struct.unpack_from(">III", table, 0)
                fst_valid = root_end == count
            file_count = dir_count = 0
            if fst_valid:
                for i in range(count):
                    typ_name, first, second = struct.unpack_from(">III", table, i * 12)
                    name_pos = table_bytes + (typ_name & 0xFFFFFF)
                    name_end = table.find(b"\0", name_pos) if name_pos < len(table) else -1
                    if name_end < 0:
                        fst_valid = False
                        break
                    name = table[name_pos:name_end].decode("ascii", "replace")
                    if typ_name >> 24:
                        dir_count += 1
                        if second <= i or second > count:
                            fst_valid = False
                            break
                    else:
                        file_count += 1
                        if first + second > size:
                            fst_valid = False
                            break
                        file_names.append(name)
                        if name.lower() == "boot.id":
                            boot_id = (first, second)
            lines.append(f"FST ENTRIES: {count if fst_valid else 'invalid'}")
            lines.append(f"FST DIRECTORIES/FILES: {dir_count} / {file_count}")
            lines.append(f"FST EXTENT CHECK: {'PASS' if fst_valid else 'FAIL'}")
        else:
            lines.append("FST: invalid or out-of-range")

        if boot_id:
            off, length = boot_id
            f.seek(off)
            data = f.read(min(length, 480))
            lines.append(f"BOOT.ID: FOUND at 0x{off:X}, FST length {length:,}")
            lines.append(f"BOOT.ID MAGIC: {data[:4]!r} ({'PASS' if data[:4] == BOOT_ID_MAGIC else 'FAIL'})")
            lines.append(f"MEDIABOARD TYPE: {data[0x20:0x24]!r}")
            lines.append(f"BOOT ID: {data[0x30:0x34].decode('ascii', 'replace')}")
            lines.append(f"REGION/FLAGS: 0x{struct.unpack_from('<I', data, 0x38)[0]:08X}" if len(data) >= 0x3C else "REGION/FLAGS: truncated")
            lines.append(f"MANUFACTURER: {ascii_field(data[0x60:0x80])}")
            lines.append(f"BOOT TITLE: {ascii_field(data[0x80:0xA0])}")
        else:
            lines.append("BOOT.ID: NOT FOUND IN FST")

        lines.append("FST FILE NAME SAMPLE: " + (", ".join(file_names[:24]) if file_names else "(none)"))
    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candidates = sorted(p for p in args.directory.rglob("*")
                        if p.is_file() and p.suffix.lower() in {".bin", ".iso", ".gcm"})
    report = [
        "TRIFORCE REFERENCE IMAGE STRUCTURAL ANALYSIS",
        "Read-only metadata report. No game payload bytes are included.",
        f"SCAN ROOT: {args.directory}",
        f"CANDIDATE IMAGE COUNT: {len(candidates)}",
        "",
    ]
    for path in candidates:
        report.extend(inspect(path))
        report.append("")
    if not candidates:
        report.append("No .bin/.iso/.gcm images found in extracted archive.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
