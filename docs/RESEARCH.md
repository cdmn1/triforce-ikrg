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
