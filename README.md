# Triforce Netboot

Research and development project to establish a reproducible workflow for building, packaging, validating and booting custom software on Sega/Namco/Nintendo Triforce arcade hardware.

**Current milestone:** the Hello World candidate boots in Dolphin 2609b with Triforce Baseboard enabled. An experimental raw `.bin` NetDIMM payload packager is now implemented; its output-size guard and custom homebrew header still need validation against the user's image and real Segaboot.

## Status

| Stage | Status |
|---|---|
| devkitPPC in GitHub Actions | Passed (run #6) |
| Minimal framebuffer Hello World | Compiled into DOL |
| DOL structural validation | Passed (run #6) |
| GameCube source-image inspection | Passed for Ikaruga USA (run [45897021932](https://github.com/cdmn1/triforce-ikrg/actions/runs/45897021932)) |
| System-area component extraction | Passed (run [45897618626](https://github.com/cdmn1/triforce-ikrg/actions/runs/45897618626)); BI2 field decoding added, CI rerun pending |
| GameCube disc-image packaging | Candidate GCM boots in Dolphin 2609b; packaged BIN retest pending |
| NetDIMM transfer protocol | Legacy Triforce uploader inspected; hardware not tested |
| Triforce NetDIMM BIN format | Raw image transfer is supported by legacy tool evidence; custom homebrew header/SegaBoot acceptance not verified |
| Emulator boot | Passed in Dolphin 2609b with Triforce Baseboard enabled (user-confirmed 2026-11-26) |
| Real Triforce boot | Not tested |
| JVS input | Not implemented |

See docs/ for research, build instructions, packaging investigation and test logs.

## Build

GitHub Actions uses the official devkitPro devkitPPC container. No local toolchain installation is required. The first versioned artifact is triforce-hello-v01.dol.

## Principles

- Keep Hello World self-contained: no DVD reads, filesystem, network, Joybus input or external assets.
- Keep the GCM candidate and experimental raw NetDIMM payload stages distinct; never describe emulator success as hardware confirmation.
- Never include copyrighted IPL, SegaBoot, apploader or game data in this repository.
- Record toolchain versions, build results, image hashes and test observations.
- Distinguish emulator observations from real hardware confirmation.

## Important caveat

A DOL is an executable, not a complete disc image. The current Hello World packager takes the tested candidate GCM, validates its FST and file extents, then builds a compact image containing the boot header, BI2, apploader and DOL with an empty root-only FST (the program has no disc/file reads). It aligns the result to 32 bytes, enforces a 512 MiB DIMM limit, and writes a six-character homebrew ID/title into the 0x40-byte disc header. This is an experimental raw payload, not yet proven to pass real SegaBoot. Do not rename a DOL to BIN and assume it is bootable.

## References

- https://github.com/devkitPro/libogc
- https://github.com/OpenGP-dev/OpenGP/blob/main/docs/triforce.md
- https://dolphin-emu.org/blog/2026/02/16/rise-of-the-triforce/
- https://github.com/JoshuaMKW/pyisotools
