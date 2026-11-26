# Triforce Netboot

Research and development project to establish a reproducible workflow for building, packaging, validating and booting custom software on Sega/Namco/Nintendo Triforce arcade hardware.

**Current milestone:** minimal GameCube Hello World DOL built and structurally validated; an owned Ikaruga RVZ has now been downloaded, converted and structurally inspected in GitHub Actions. This is not yet a verified Triforce NetDIMM image or hardware boot.

## Status

| Stage | Status |
|---|---|
| devkitPPC in GitHub Actions | Passed (run #6) |
| Minimal framebuffer Hello World | Compiled into DOL |
| DOL structural validation | Passed (run #6) |
| GameCube source-image inspection | Passed for Ikaruga USA (run [45897021932](https://github.com/cdmn1/triforce-ikrg/actions/runs/45897021932)) |
| System-area component extraction | Passed (run [45897618626](https://github.com/cdmn1/triforce-ikrg/actions/runs/45897618626)); BI2 field decoding added, CI rerun pending |
| GameCube disc-image packaging | Candidate DOL replacement utility and ephemeral CI test added; run pending |
| NetDIMM transfer protocol | Legacy Triforce uploader inspected; hardware not tested |
| Triforce NetDIMM BIN format | Not verified |
| Emulator boot | Not tested |
| Real Triforce boot | Not tested |
| JVS input | Not implemented |

See docs/ for research, build instructions, packaging investigation and test logs.

## Build

GitHub Actions uses the official devkitPro devkitPPC container. No local toolchain installation is required. The first versioned artifact is triforce-hello-v01.dol.

## Principles

- Keep Hello World self-contained: no DVD reads, filesystem, network, Joybus input or external assets.
- Keep ordinary GameCube disc packaging separate from Triforce NetDIMM packaging until the latter is established.
- Never include copyrighted IPL, SegaBoot, apploader or game data in this repository.
- Record toolchain versions, build results, image hashes and test observations.
- Distinguish emulator observations from real hardware confirmation.

## Important caveat

A DOL is an executable, not a complete disc image. A conventional GameCube ISO/GCM contains additional system structures. Whether a standard GameCube image can be loaded and executed by the Triforce NetDIMM/SegaBoot path, and what exact image layout the real NetDIMM expects, remains a research question. Do not rename a DOL to BIN and assume it is bootable.

## References

- https://github.com/devkitPro/libogc
- https://github.com/OpenGP-dev/OpenGP/blob/main/docs/triforce.md
- https://dolphin-emu.org/blog/2026/02/16/rise-of-the-triforce/
- https://github.com/JoshuaMKW/pyisotools
