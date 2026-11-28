# Triforce Netboot

Research and development project to establish a reproducible workflow for building, packaging, validating and booting custom software on Sega/Namco/Nintendo Triforce arcade hardware.

**Current milestone:** JVS SwitchInput and Test/Service input mappings are confirmed in Dolphin 2609b; v08 also confirmed Dolphin's SegaBoot firmware-read mapping. The next milestone is the actual game-side TEST-to-System-Menu transition. OpenGP documents one Triforce title's flow (save-region wake flag, then reboot into its test menu), but that is not yet verified for Virtua Striker 2002. The known-good Virtua Striker DOL has its own test-menu strings; its handler still needs to be identified. No real Triforce hardware test has been performed.

## Status

| Stage | Status |
|---|---|
| devkitPPC in GitHub Actions | Passed |
| Versioned diagnostics | v07 JVS input probe; v08 firmware-map read probe passed in Dolphin |
| DOL structural validation | Passed (latest build workflow) |
| Ikaruga USA source-image inspection | Passed in earlier CI run |
| Candidate GCM | User-confirmed boot in Dolphin 2609b, Triforce Baseboard enabled |
| Known-good Virtua Striker 2002 reference | Passed structural checks in [reference analysis run #9](https://github.com/cdmn1/triforce-ikrg/actions/runs/46031201499) |
| Reference PowerPC static analysis | Completed; report contains section map, immediate hits and selected strings only |
| Compact raw BIN packager | Unit tests passed; defaults now mirror reference Triforce boot metadata |
| Dolphin Triforce metadata recognition | Expected title ID `GEYP6E`; v07 JVS probe running under Triforce baseboard |
| NetDIMM transfer protocol | Legacy Triforce uploader inspected; hardware transfer not tested |
| Real Triforce boot | Not tested |
| JVS SI input transport | PASS in Dolphin v07; valid SwitchInput response and checksum |
| Test / Service controls | PASS in Dolphin v07; Test `0x80`, Service `0x40` |
| SegaBoot availability in Dolphin | Confirmed indirectly by Test bit being exposed only when `GetTestMenu()` is true |
| Firmware-read source switch | PASS in Dolphin v08; offset 0x0000 returned valid SegaBoot image header |
| TEST to Triforce System Menu | Not yet verified; game-side handler investigation in progress |

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

GitHub Actions uses the official devkitPro devkitPPC container. No local toolchain installation is required. The latest build artifact contains the versioned DOL, packaging script, build information and checksums.

To package a versioned DOL, explicitly pass that DOL to the packaging script. The source GCM supplies the boot header, BI2 and apploader; the `--dol` argument supplies the executable placed in the output BIN. Without `--dol`, the script falls back to the DOL embedded in the source GCM.

For the v08 firmware-map probe, use the artifact from [build run #127](https://github.com/cdmn1/triforce-ikrg/actions/runs/46084065276), which includes the corrected MEM1 key-address reads. Put `candidate-homebrew.iso`, `triforce-hello-v08.dol` and `package_triforce_netboot.py` in the same folder, then run:

```text
python package_triforce_netboot.py candidate-homebrew.iso triforce-hello-v08.bin --dol triforce-hello-v08.dol
```

The packager validates the replacement DOL's sections and entry point, recalculates the FST position, and enforces the 512 MiB DIMM size limit.

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


## v07: Triforce SI/JVS input probe

The v07 DOL replaces the passive Hello World wait loop with a diagnostic that talks to
the Triforce baseboard on SI channel 0. It sends a JVS broadcast SetAddress request,
then repeatedly requests one player's switch inputs through the GC-AM JVS-IO command.

The display reports:
- JVS SwitchInput response validity
- JVS system-input byte, including the Test bit (0x80)
- Player 1 switch byte 0, including the Service bit (0x40)
- Player 1 switch byte 1

This follows Dolphin's current Triforce implementation: its AM-baseboard SI device forwards
GC-AM command 0x40 to JVS-IO, and JVS command 0x20 returns the system-input byte followed
by player switch bytes. Dolphin's Triforce I/O adapter maps Test to system-input bit 7 when
SegaBoot is loaded, and Service to bit 6 of player 1 switch byte 0.

The probe does not call OSResetSystem, change the DIMM, or write firmware. A successful
input read will establish that the emulated SI/JVS input path is working; it will not by
itself launch SegaBoot or prove real Triforce hardware compatibility.

Build artifact: `triforce-hello-v07`. Use the explicit `--dol triforce-hello-v07.dol` argument when packaging; otherwise the older DOL embedded in the candidate GCM will be reused.


## v08: SegaBoot firmware-read mapping confirmed

The user-tested v08 probe completed both encrypted Triforce DI reads in Dolphin 2609b with Triforce Baseboard enabled:

- Decoder keys read through the PowerPC MEM1 alias: A `4756534A`, B `38500000`, C `01000000`.
- SegaBoot signature address before mapping: `10801080` (not the SegaBoot signature).
- Reset flag: `0x00000001`.
- DI read at byte offset `0x2440`: COMPLETE, status `0x00000010`.
- DI read at byte offset `0x0000`: COMPLETE, status `0x00000010`.
- Returned ID: `RELSAB`; title: `SegaBoot`; GameCube magic: `0xC2339F3D` (valid).

**Conclusion:** Dolphin's AM-Mediaboard firmware-read source switch is directly confirmed. The first read at `0x2440`, with the reset flag set and SegaBoot signature absent, causes subsequent reads to return the SegaBoot GCM buffer rather than the game DIMM image. This is a stronger result than merely confirming firmware availability or JVS Test input.

The v08 probe did not reset the CPU or execute the SegaBoot apploader. The firmware-map flag remains set until Dolphin is restarted. The next technical milestone is to establish the actual apploader/reset hand-off path; this is still emulator-only research. Real Triforce boot remains untested.


## v09: Dolphin-only SegaBoot reset / hand-off experiment

After v08 directly confirmed that the DI read at `0x2440` maps subsequent reads to SegaBoot, v09 moves to the next question: whether a normal PPC cold reset causes Dolphin's boot path to perform that hand-off without the probe manually issuing DI reads.

The v09 DOL displays a warning and waits for the GameCube controller START button. On START it:
1. Sets `0x811FFF00=1` and flushes the flag to RAM.
2. Calls libogc `SYS_ResetSystem(SYS_RESTART, 0, TRUE)` to request a cold PPC reset.
3. Does not issue a DI Write or Execute command and does not write firmware.

**Dolphin 2609b / Triforce Baseboard only. Do not run v09 on real Triforce hardware.** Ensure `segaboot.gcm` and `IPL_TRI.bin` are configured in Dolphin. A successful result should leave the probe screen and enter the SegaBoot boot/menu path. If it returns to the probe or errors, capture the Dolphin log and screen. The reset/handoff result is pending.

Build artifact [triforce-hello-v09](https://github.com/cdmn1/triforce-ikrg/actions/runs/46084690570) is built and CI-validated (artifact ID `15237679896`). Package the DOL explicitly with:

```text
python package_triforce_netboot.py candidate-homebrew.iso triforce-hello-v09.bin --dol triforce-hello-v09.dol
```
