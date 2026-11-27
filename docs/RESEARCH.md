# Triforce hardware research notes

## Platform overview

Triforce is a GameCube-derived arcade platform with two arcade-specific boards:

- GameCube main board: PowerPC Gekko CPU, Flipper graphics/audio hardware and GameCube system interfaces.
- AM-Baseboard: cabinet I/O and related interfaces, including JVS.
- AM-Mediaboard: DIMM/media-board functionality and communication with the GameCube through the disc interface.

Record the board revision and DIMM configuration for every hardware test.

## CPU, graphics and memory

**CONFIRMED:** devkitPPC is the established open-source development toolchain for GameCube software.

**CONFIRMED:** Do not assume every Triforce title or board uses 48 MiB. Public Triforce research and Dolphin's implementation show that memory size is associated with the disc BI2 configuration; documented titles request different amounts.

**UNKNOWN:** Which memory configurations are accepted by each real Triforce revision and SegaBoot/NetDIMM configuration for custom software.

## Input and JVS

The cabinet input path is not the retail GameCube controller-pad path.

Dolphin's Triforce hardware notes identify JVS I/O with the AM-Baseboard and GameCube Serial Interface (SI). Therefore, the claim that JVS is simply accessed over EXI should not be treated as established.

Hello World deliberately does not poll input. Future work should inspect the baseboard protocol and relevant implementation before writing a driver.

## Boot chain and media

The Triforce boot process involves a modified GameCube boot ROM, Triforce-specific hardware initialization and SegaBoot. The AM-Mediaboard provides a disc-interface/media-board path; it is not safe to assume that a retail GameCube optical-disc workflow and a Triforce NetDIMM workflow are identical.

A DOL is an executable. A normal GameCube disc image includes boot/system metadata and an apploader in addition to the DOL and filesystem. This project must determine whether a conventional GCM/ISO, a Triforce-specific image, or a particular NetDIMM conversion is required for real hardware.

## Toolchain

Use the official devkitPro devkitPPC container in CI. The toolchain provides GameCube build rules and elf2dol conversion. libogc provides GameCube hardware support, including video and console initialization.

Pin the container tag in CI rather than using floating latest. Record toolchain changes in the test log.

## References

- https://github.com/devkitPro/docker/tree/master/devkitppc
- https://github.com/devkitPro/libogc
- https://github.com/OpenGP-dev/OpenGP/blob/main/docs/triforce.md
- https://dolphin-emu.org/blog/2026/02/16/rise-of-the-triforce/
- https://blog.jchw.dev/triforce-bs1/

## Open questions

1. What exact file format and header does the real Triforce NetDIMM upload utility expect?
2. Is the image a raw disc image, GD-ROM-derived image, Triforce media-board image or tool-specific container?
3. What image size, byte order, padding and alignment are required?
4. Does SegaBoot accept a standard GameCube homebrew GCM/ISO, and under which boot mode?
5. What is the minimal valid BI2/apploader combination for a custom DOL?
6. Can a legally obtained clean GameCube image be used as a packaging base, or are Triforce-specific structures needed?
7. Which JVS commands and SI transfer framing are required for coin, service and player inputs?
8. Which memory configurations are safe for homebrew on each board type?


## Triforce media-board reset and DI command research (2026-11-27)

**Confirmed in Dolphin source:**
- Triforce DI command words 0–2 are XOR-decoded with three evolving keys before the command byte and offset are interpreted.
- The decoded command byte is the low byte of command word 0. The decoded media-board offset is command word 1 multiplied by four.
- When a decoded DI command uses offset `0x2440`, Dolphin checks RAM address `0x811FFF00`. If it contains 1 and the SegaBoot signature at `0x8006BF70` is absent, Dolphin enables its firmware-read path.
- While enabled, subsequent media-board Read commands are served from the 2 MiB `segaboot.gcm` firmware buffer instead of the game DIMM image. An Inquiry command clears the firmware-read flag.
- This is a read-source switch in Dolphin's AM-Mediaboard handler; the flag check itself does not directly branch the PPC CPU into SegaBoot.

**Confirmed in the known-good Virtua Striker 2002 DOL (static analysis):**
- A command encoder at approximately `0x801C744C` generates an odd 16-bit seed, combines it with the command ID, XORs the three command words with the current keys, multiplies the keys by the seed, and writes the encoded words to DI registers `0xCC006008`, `0xCC00600C` and `0xCC006010`.
- Adjacent media-board routines write the DMA address, DMA length and DI control registers. A write command path uses decoded command `0xAA` and control value 7.
- A boot/apploader-loading routine calls a helper with offset `0x2440`, first for a 0x20-byte header and then for the apploader body. This is the standard GameCube apploader offset and is a plausible point where a reset/reboot path encounters the firmware-read switch.
- No direct PPC instruction pair constructing `0x811FFF00` was found in the scanned game DOL. The flag write may belong to a system OS routine or be constructed indirectly; this is not yet resolved.

**Implementation warning:** libogc's ordinary `DVD_LowRead` writes un-obfuscated DVD command words directly to DI registers. That is not equivalent to the Triforce command encoder found in the reference DOL. Do not use the ordinary libogc DVD read API as a presumed Triforce media-board command until its compatibility is proven.

**Next safe experiment:** reproduce one read-only Triforce DI Read using the reference command encoding, set the reset flag in emulated RAM, trigger offset `0x2440`, then read the emulated firmware header at offset zero. This can test whether Dolphin switches the read source without actually resetting or writing firmware. It is an emulator-only diagnostic, not a real-hardware procedure.


## Firmware-map experiment result (2026-11-27)

**USER-TESTED PASS in Dolphin 2609b / Triforce Baseboard mode:**
- DI decoder keys read by PPC through the MEM1 cached alias: A=`0x4756534A`, B=`0x38500000`, C=`0x01000000`. Physical RAM offsets 0/4/8 must be accessed by PPC at `0x80000000`, `0x80000004`, and `0x80000008`; direct dereferences of addresses 0/4/8 caused a DSI.
- The probe observed pre-map SegaBoot signature address value `0x10801080`, so the Dolphin guard against remapping while already in SegaBoot did not block the experiment.
- With reset flag `0x811FFF00=1`, a Triforce DI Read at byte offset `0x2440` completed (status `0x10`).
- A following DI Read at byte offset `0x0000` completed (status `0x10`) and returned ID `RELSAB`, title `SegaBoot`, and valid GameCube magic `0xC2339F3D`.

**Conclusion:** the Dolphin firmware-read source switch is proven end-to-end at the DI data level. The DI read at `0x2440` activates the map, and the next read at zero returns the SegaBoot GCM header. This does not yet prove that the PPC CPU resets, executes the SegaBoot apploader, or launches the SegaBoot menu. The firmware map is a source-selection state in Dolphin's AM-Mediaboard; it is not itself a CPU branch.

**Next stage:** investigate the full reset/apploader hand-off using Dolphin-only experiments. Preserve the current safety boundary: no test on real Triforce hardware until the reset behavior and hardware-safe command sequence are independently understood.
