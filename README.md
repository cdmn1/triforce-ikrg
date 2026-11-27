# Triforce Netboot

Research and development project to establish a reproducible workflow for building, packaging, validating and booting custom software on Sega/Namco/Nintendo Triforce arcade hardware.

**Current milestone:** the Hello World candidate DOL boots in Dolphin 2609b with Triforce Baseboard enabled. A known-good Virtua Striker 2002 raw image has now been structurally analyzed in GitHub Actions. That comparison corrected the experimental `boot.id` metadata used by the compact NetDIMM packager. The corrected v04 package still needs a fresh Dolphin test; real Triforce hardware has not been tested.

## Status

| Stage | Status |
|---|---|
| devkitPPC in GitHub Actions | Passed |
| Minimal framebuffer Hello World | Compiled into DOL |
| DOL structural validation | Passed (latest build workflow) |
| Ikaruga USA source-image inspection | Passed in earlier CI run |
| Candidate GCM | User-confirmed boot in Dolphin 2609b, Triforce Baseboard enabled |
| Known-good Virtua Striker 2002 reference | Passed structural checks in [reference analysis run #9](https://github.com/cdmn1/triforce-ikrg/actions/runs/46031201499) |
| Reference PowerPC static analysis | Completed; report contains section map, immediate hits and selected strings only |
| Compact raw BIN packager | Unit tests passed; defaults now mirror reference Triforce boot metadata |
| Dolphin recognition with corrected metadata | Expected title ID is `GEYP6E`; v06 retest pending |
| NetDIMM transfer protocol | Legacy Triforce uploader inspected; hardware transfer not tested |
| Real Triforce boot | Not tested |
| JVS input / game test menu | Not implemented in Hello World |

The reference analysis workflow downloads the supplied Virtua Striker 2002 archive to temporary GitHub runner storage, extracts it there, and uploads only small text reports. The game image and extracted game data are not committed or uploaded as workflow artifacts.

## Reference-matched boot metadata

The supplied known-good image confirms these separate identifiers:

- Disc header ID: `GVSJ8P`
- `boot.id` game ID field: `SBEY`
- Media-board type: `GCAM`
- Region flags: `0x0C` (Export / PAL)
- Manufacturer: `SEGA CORPORATION`

Dolphin constructs its six-character Triforce title ID from the `boot.id` fields, not from the six-character disc header. For the reference metadata, the expected constructed ID is `GEYP6E`:

- `SBEY` contributes `EY`
- region flag `0x0C` contributes `P`
- `SEGA CORPORATION` contributes maker code `6E`

The corrected packager uses these reference values by default. The disc header remains `GVSJ8P`; do not replace it with `GEYP6E`.

## Build

GitHub Actions uses the official devkitPro devkitPPC container. No local toolchain installation is required. The latest artifact is `triforce-hello-v04`, containing the DOL, updated packaging script, build information and checksums.

To package the already-tested candidate GCM locally, use the v06 packaging script and give it a new output name, for example:

```text
python package_triforce_netboot.py candidate-homebrew.iso triforce-hello-v06.bin
```

The script's default metadata now matches the reference values above. It still enforces the 512 MiB DIMM size limit.

## Test/Service input caveat

The Virtua Striker 2002 DOL contains its own test-menu implementation and strings such as `VIRTUA STRIKER 2002 TEST MENU`, `SELECT WITH SERVICE BUTTON`, and `PRESS TEST BUTTON TO EXIT`. It also contains explicit JVS I/O-board error messages.

The Hello World DOL does not poll JVS inputs or implement a game test menu. Therefore, pressing Test or Service while Hello World is running is not a valid test of whether the Triforce boot environment or SegaBoot was recognized. The known-good game's menu is game code, not a generic menu that every DOL automatically inherits.

## Principles

- Keep Hello World self-contained: no DVD reads, filesystem, network, Joybus input or external assets.
- Keep the GCM candidate and experimental raw NetDIMM payload stages distinct; never describe emulator success as hardware confirmation.
- Never include copyrighted IPL, SegaBoot, apploader or game data in this repository.
- Record toolchain versions, build results, image hashes and test observations.
- Distinguish emulator observations from real hardware confirmation.

## Important caveat

A DOL is an executable, not a complete disc image. The current Hello World packager takes the tested candidate GCM, validates its FST and file extents, then builds a compact image containing the boot header, BI2, apploader and DOL with an empty root-only FST (the program has no disc/file reads). It aligns the result to 32 bytes, writes a `boot.id` entry and enforces a 512 MiB DIMM limit. This remains an experimental raw payload: passing Dolphin tests does not prove real SegaBoot or real Triforce acceptance.

See `docs/` for research, build instructions, packaging investigation and test logs.

## References

- https://github.com/devkitPro/libogc
- https://github.com/OpenGP-dev/OpenGP/blob/main/docs/triforce.md
- https://dolphin-emu.org/blog/2026/02/16/rise-of-the-triforce/
- https://github.com/JoshuaMKW/pyisotools
