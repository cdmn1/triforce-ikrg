#!/usr/bin/env python3
"""Create an experimental raw Triforce NetDIMM payload from a GameCube GCM.

This does not upload the file and does not prove SegaBoot accepts a custom
homebrew game ID. It preserves all referenced disc data and only trims the
unreferenced tail of the image.
"""
import argparse
import hashlib
import os
import shutil
import struct
from pathlib import Path

MAGIC = 0xC2339F3D
BOOT_SIZE = 0x440
BI2_OFFSET = 0x440
BI2_SIZE = 0x2000
APP_OFFSET = 0x2440
APP_HEADER_SIZE = 0x20
DI_READ_ALIGNMENT = 0x20
DEFAULT_MAX_SIZE = 512 * 1024 * 1024
DEFAULT_GAME_ID = "THWJ01"
DEFAULT_TITLE = "TRIFORCE NETBOOT HELLO WORLD"


def read_at(f, offset, length, image_size, label):
    if offset < 0 or length < 0 or offset + length > image_size:
        raise ValueError(f"{label} range 0x{offset:X}+0x{length:X} is outside the source image")
    f.seek(offset)
    data = f.read(length)
    if len(data) != length:
        raise ValueError(f"short read while reading {label}")
    return data


def inspect_gcm(path):
    image_size = path.stat().st_size
    with path.open("rb") as f:
        boot = read_at(f, 0, BOOT_SIZE, image_size, "boot header")
        magic = struct.unpack_from(">I", boot, 0x1C)[0]
        if magic != MAGIC:
            raise ValueError(f"wrong GameCube boot magic 0x{magic:08X}")
        dol_offset, fst_offset, fst_size, fst_max = struct.unpack_from(">IIII", boot, 0x420)
        if not dol_offset or not fst_offset or not fst_size or fst_max < fst_size:
            raise ValueError("invalid DOL/FST offsets or sizes")
        if dol_offset < APP_OFFSET + APP_HEADER_SIZE:
            raise ValueError("DOL overlaps the disc system area")
        if fst_offset <= dol_offset:
            raise ValueError("FST does not follow the DOL")
        if fst_offset + fst_size > image_size:
            raise ValueError("FST extends beyond the source image")

        bi2 = read_at(f, BI2_OFFSET, BI2_SIZE, image_size, "BI2")
        app_header = read_at(f, APP_OFFSET, APP_HEADER_SIZE, image_size, "apploader header")
        app_code_size, app_trailer_size = struct.unpack_from(">II", app_header, 0x14)
        app_size = APP_HEADER_SIZE + app_code_size + app_trailer_size
        app_end = APP_OFFSET + app_size
        if app_end > dol_offset:
            raise ValueError("apploader overlaps the DOL slot")
        read_at(f, APP_OFFSET, app_size, image_size, "apploader")

        dol_header = read_at(f, dol_offset, 0x100, image_size, "DOL header")
        offsets = struct.unpack_from(">18I", dol_header, 0x00)
        sizes = struct.unpack_from(">18I", dol_header, 0x90)
        dol_extents = []
        for index, (offset, size) in enumerate(zip(offsets, sizes)):
            if size:
                if offset < 0x100:
                    raise ValueError(f"DOL section {index} overlaps its header")
                end = dol_offset + offset + size
                if end > image_size:
                    raise ValueError(f"DOL section {index} extends beyond the source image")
                dol_extents.append(end)
        if not dol_extents:
            raise ValueError("DOL has no file-backed sections")
        dol_end = max(dol_offset + 0x100, max(dol_extents))

        fst = read_at(f, fst_offset, fst_size, image_size, "FST")
        if len(fst) < 12:
            raise ValueError("FST is too small")
        entry_count = struct.unpack_from(">I", fst, 8)[0]
        entries_bytes = entry_count * 12
        if entry_count < 1 or entries_bytes > len(fst):
            raise ValueError("FST entry count is invalid")
        root_type_name, root_parent, root_end = struct.unpack_from(">III", fst, 0)
        if not (root_type_name >> 24) or root_end != entry_count:
            raise ValueError("FST root directory entry is invalid")
        string_table_offset = entries_bytes
        max_file_end = 0
        file_count = 0
        for index in range(entry_count):
            type_name, first, second = struct.unpack_from(">III", fst, index * 12)
            name_offset = type_name & 0xFFFFFF
            name_pos = string_table_offset + name_offset
            if name_pos >= len(fst) or fst.find(b"\0", name_pos) < 0:
                raise ValueError(f"FST entry {index} has an invalid name")
            is_dir = bool(type_name >> 24)
            if is_dir:
                if second <= index or second > entry_count:
                    raise ValueError(f"FST directory entry {index} has an invalid end index")
            else:
                file_offset, file_size = first, second
                file_end = file_offset + file_size
                if file_end > image_size:
                    raise ValueError(f"FST file entry {index} extends beyond the source image")
                max_file_end = max(max_file_end, file_end)
                file_count += 1

        required_end = max(
            BOOT_SIZE,
            BI2_OFFSET + BI2_SIZE,
            app_end,
            dol_end,
            fst_offset + fst_size,
            max_file_end,
        )
        payload_size = (required_end + DI_READ_ALIGNMENT - 1) & ~(DI_READ_ALIGNMENT - 1)
        return {
            "source_size": image_size,
            "game_id": boot[0:6].decode("ascii", "replace"),
            "dol_offset": dol_offset,
            "fst_offset": fst_offset,
            "fst_size": fst_size,
            "app_end": app_end,
            "dol_end": dol_end,
            "file_count": file_count,
            "max_file_end": max_file_end,
            "required_end": required_end,
            "payload_size": payload_size,
        }


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_image(source, output, game_id=DEFAULT_GAME_ID, title=DEFAULT_TITLE,
                  max_size=DEFAULT_MAX_SIZE):
    source = Path(source)
    output = Path(output)
    if not source.is_file():
        raise ValueError("source GCM does not exist")
    if source.resolve() == output.resolve():
        raise ValueError("output must not overwrite the source GCM")
    if output.suffix.lower() != ".bin":
        raise ValueError("output filename must use the .bin extension")
    try:
        game_id_bytes = game_id.encode("ascii")
        title_bytes = title.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("game ID and title must contain ASCII characters only") from exc
    if len(game_id_bytes) != 6 or any(c < 0x20 or c > 0x7E for c in game_id_bytes):
        raise ValueError("game ID must be exactly six printable ASCII characters")
    if not title_bytes or len(title_bytes) > 32:
        raise ValueError("title must be 1 to 32 ASCII bytes")

    info = inspect_gcm(source)
    payload_size = info["payload_size"]
    if payload_size > max_size:
        raise ValueError(
            f"referenced disc data requires {payload_size:,} bytes, exceeding "
            f"the {max_size:,}-byte DIMM limit; no output was written"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    source_size = info["source_size"]
    with source.open("rb") as src, output.open("w+b") as dst:
        remaining = min(payload_size, source_size)
        while remaining:
            block = src.read(min(1024 * 1024, remaining))
            if not block:
                raise ValueError("unexpected end of source while copying payload")
            dst.write(block)
            remaining -= len(block)
        if payload_size > source_size:
            dst.write(b"\0" * (payload_size - source_size))
        dst.seek(0)
        header = bytearray(dst.read(0x40))
        if len(header) != 0x40:
            raise ValueError("could not read complete output boot header")
        header[0:6] = game_id_bytes
        header[0x20:0x40] = title_bytes.ljust(32, b"\0")
        dst.seek(0)
        dst.write(header)
        dst.flush()
        os.fsync(dst.fileno())

    if output.stat().st_size != payload_size:
        raise ValueError("output size verification failed")
    with output.open("rb") as f:
        check = f.read(0x40)
    if check[0:6] != game_id_bytes or check[0x20:0x40] != title_bytes.ljust(32, b"\0"):
        raise ValueError("output header verification failed")
    if struct.unpack_from(">I", check, 0x1C)[0] != MAGIC:
        raise ValueError("output GameCube magic changed unexpectedly")
    return info


def main():
    parser = argparse.ArgumentParser(
        description="Trim a candidate GameCube GCM to referenced data and write an experimental Triforce .bin payload."
    )
    parser.add_argument("source_gcm", type=Path)
    parser.add_argument("output_bin", type=Path)
    parser.add_argument("--game-id", default=DEFAULT_GAME_ID,
                        help="six-character homebrew ID (default: THWJ01)")
    parser.add_argument("--title", default=DEFAULT_TITLE,
                        help="disc title, maximum 32 ASCII bytes")
    parser.add_argument("--max-size-mib", type=int, default=512,
                        help="DIMM size limit in MiB (default: 512)")
    args = parser.parse_args()
    if args.max_size_mib <= 0:
        parser.error("--max-size-mib must be positive")
    try:
        info = package_image(
            args.source_gcm, args.output_bin, args.game_id, args.title,
            args.max_size_mib * 1024 * 1024
        )
    except (OSError, ValueError) as exc:
        raise SystemExit("Triforce NetDIMM packaging: FAIL: " + str(exc))

    print("TRIFORCE NETDIMM EXPERIMENTAL PACKAGE: PASS")
    print(f"Source GCM: {args.source_gcm}")
    print(f"Source size: {info['source_size']:,} bytes")
    print(f"Original game ID: {info['game_id']}")
    print(f"Output BIN: {args.output_bin}")
    print(f"Output size: {info['payload_size']:,} bytes")
    print(f"New game ID: {args.game_id}")
    print(f"Disc title: {args.title}")
    print(f"FST files checked: {info['file_count']}")
    print(f"Last referenced file byte: 0x{info['max_file_end']:X}")
    print(f"SHA-256: {sha256_file(args.output_bin)}")
    print("Payload: raw disc bytes, trimmed only after the last referenced extent, 0x20-byte aligned.")
    print("NOTE: transport-compatible raw upload is inferred from legacy Triforce DIMM tools.")
    print("NOTE: custom homebrew ID/SegaBoot acceptance and real Triforce boot are NOT verified.")


if __name__ == "__main__":
    main()
