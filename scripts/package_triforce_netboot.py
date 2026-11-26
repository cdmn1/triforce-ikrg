#!/usr/bin/env python3
"""Build a compact experimental raw Triforce NetDIMM payload from a GCM.

This is specific to the self-contained Hello World program: it retains the
GameCube boot/system area, apploader and DOL, and replaces the source FST with
an empty root directory because the program performs no disc/file reads.
"""
import argparse
import hashlib
import os
import struct
from pathlib import Path

MAGIC = 0xC2339F3D
BOOT_SIZE = 0x440
BI2_OFFSET = 0x440
BI2_SIZE = 0x2000
APP_OFFSET = 0x2440
APP_HEADER_SIZE = 0x20
ALIGNMENT = 0x20
EMPTY_FST = struct.pack(">III", 0x01000000, 0, 1) + b"\0"
DEFAULT_MAX_SIZE = 512 * 1024 * 1024
DEFAULT_GAME_ID = "THWJ01"
DEFAULT_TITLE = "TRIFORCE NETBOOT HELLO WORLD"


def align_up(value, alignment=ALIGNMENT):
    return (value + alignment - 1) & ~(alignment - 1)


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
        if dol_offset < APP_OFFSET + APP_HEADER_SIZE or fst_offset <= dol_offset:
            raise ValueError("invalid DOL/FST placement")
        if fst_offset + fst_size > image_size:
            raise ValueError("source FST extends beyond the image")

        bi2 = read_at(f, BI2_OFFSET, BI2_SIZE, image_size, "BI2")
        app_header = read_at(f, APP_OFFSET, APP_HEADER_SIZE, image_size, "apploader header")
        app_code_size, app_trailer_size = struct.unpack_from(">II", app_header, 0x14)
        app_size = APP_HEADER_SIZE + app_code_size + app_trailer_size
        app_end = APP_OFFSET + app_size
        if app_end > dol_offset:
            raise ValueError("apploader overlaps the DOL slot")
        app = read_at(f, APP_OFFSET, app_size, image_size, "apploader")

        dol_header = read_at(f, dol_offset, 0x100, image_size, "DOL header")
        offsets = struct.unpack_from(">18I", dol_header, 0x00)
        addresses = struct.unpack_from(">18I", dol_header, 0x48)
        sizes = struct.unpack_from(">18I", dol_header, 0x90)
        sections = []
        for index, (offset, address, size) in enumerate(zip(offsets, addresses, sizes)):
            if not size:
                continue
            if offset < 0x100 or address == 0:
                raise ValueError(f"DOL section {index} has invalid offset or load address")
            end = dol_offset + offset + size
            if end > image_size:
                raise ValueError(f"DOL section {index} extends beyond the source image")
            sections.append((offset, address, size))
        entry = struct.unpack_from(">I", dol_header, 0xE0)[0]
        if not sections or not any(address <= entry < address + size for _, address, size in sections):
            raise ValueError("DOL has no valid sections or its entry point is not loaded")
        dol_size = max([0x100] + [offset + size for offset, _, size in sections])
        if dol_offset + dol_size > fst_offset:
            raise ValueError("DOL data overlaps the source FST")

        # Validate the source FST and all of its file extents, even though the
        # self-contained Hello World package intentionally drops those files.
        fst = read_at(f, fst_offset, fst_size, image_size, "FST")
        if len(fst) < 12:
            raise ValueError("FST is too small")
        entry_count = struct.unpack_from(">I", fst, 8)[0]
        entries_bytes = entry_count * 12
        if entry_count < 1 or entries_bytes > len(fst):
            raise ValueError("FST entry count is invalid")
        root_type_name, _, root_end = struct.unpack_from(">III", fst, 0)
        if not (root_type_name >> 24) or root_end != entry_count:
            raise ValueError("FST root directory entry is invalid")
        string_table_offset = entries_bytes
        file_count = 0
        for index in range(entry_count):
            type_name, first, second = struct.unpack_from(">III", fst, index * 12)
            name_pos = string_table_offset + (type_name & 0xFFFFFF)
            if name_pos >= len(fst) or fst.find(b"\0", name_pos) < 0:
                raise ValueError(f"FST entry {index} has an invalid name")
            if type_name >> 24:
                if second <= index or second > entry_count:
                    raise ValueError(f"FST directory entry {index} has an invalid end index")
            else:
                if first + second > image_size:
                    raise ValueError(f"FST file entry {index} extends beyond the source image")
                file_count += 1

        new_fst_offset = align_up(dol_offset + dol_size)
        new_fst_size = len(EMPTY_FST)
        output_size = align_up(new_fst_offset + new_fst_size)
        return {
            "source_size": image_size,
            "original_game_id": boot[0:6].decode("ascii", "replace"),
            "dol_offset": dol_offset,
            "dol_size": dol_size,
            "dol_entry": entry,
            "fst_offset": new_fst_offset,
            "fst_size": new_fst_size,
            "source_fst_files": file_count,
            "app_size": app_size,
            "output_size": output_size,
            "boot": boot,
            "bi2": bi2,
            "apploader": app,
            "dol": read_at(f, dol_offset, dol_size, image_size, "DOL data"),
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
        raise ValueError("source candidate GCM does not exist")
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
    output_size = info["output_size"]
    if output_size > max_size:
        raise ValueError(
            f"compact payload requires {output_size:,} bytes, exceeding "
            f"the {max_size:,}-byte DIMM limit; no output was written"
        )

    image = bytearray(output_size)
    image[0:BOOT_SIZE] = info["boot"]
    image[BI2_OFFSET:BI2_OFFSET + BI2_SIZE] = info["bi2"]
    image[APP_OFFSET:APP_OFFSET + info["app_size"]] = info["apploader"]
    dol_offset = info["dol_offset"]
    image[dol_offset:dol_offset + info["dol_size"]] = info["dol"]
    fst_offset = info["fst_offset"]
    image[fst_offset:fst_offset + len(EMPTY_FST)] = EMPTY_FST

    image[0:6] = game_id_bytes
    image[0x20:0x40] = title_bytes.ljust(32, b"\0")
    struct.pack_into(">IIII", image, 0x420, dol_offset, fst_offset,
                     len(EMPTY_FST), len(EMPTY_FST))

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as dst:
        dst.write(image)
        dst.flush()
        os.fsync(dst.fileno())

    if output.stat().st_size != output_size:
        raise ValueError("output size verification failed")
    with output.open("rb") as f:
        check = f.read(BOOT_SIZE)
        f.seek(fst_offset)
        fst_check = f.read(len(EMPTY_FST))
    if check[0:6] != game_id_bytes or check[0x20:0x40] != title_bytes.ljust(32, b"\0"):
        raise ValueError("output disc header verification failed")
    if struct.unpack_from(">I", check, 0x1C)[0] != MAGIC:
        raise ValueError("output GameCube magic changed unexpectedly")
    if struct.unpack_from(">IIII", check, 0x420) != (
        dol_offset, fst_offset, len(EMPTY_FST), len(EMPTY_FST)
    ):
        raise ValueError("output DOL/FST pointers did not verify")
    if fst_check != EMPTY_FST:
        raise ValueError("output empty FST did not verify")
    return info


def main():
    parser = argparse.ArgumentParser(
        description="Build a compact raw Triforce .bin from the self-contained Hello World candidate GCM."
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
    print(f"Original game ID: {info['original_game_id']}")
    print(f"Output BIN: {args.output_bin}")
    print(f"Output size: {info['output_size']:,} bytes")
    print(f"New game ID: {args.game_id}")
    print(f"Disc title: {args.title}")
    print(f"DOL: offset 0x{info['dol_offset']:X}, size {info['dol_size']:,} bytes, entry 0x{info['dol_entry']:08X}")
    print(f"Apploader: {info['app_size']:,} bytes")
    print(f"Original FST files removed: {info['source_fst_files']}")
    print(f"New FST: offset 0x{info['fst_offset']:X}, empty root only ({info['fst_size']} bytes)")
    print(f"SHA-256: {sha256_file(args.output_bin)}")
    print("Payload: compact raw GameCube/Triforce-style image; no wrapper, encryption or upload.")
    print("NOTE: this Hello World performs no disc/file reads; original FST files are intentionally omitted.")
    print("NOTE: custom homebrew ID/SegaBoot acceptance and real Triforce boot are NOT verified.")


if __name__ == "__main__":
    main()
