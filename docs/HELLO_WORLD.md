# Hello World

## Goal

Build a minimal GameCube-native program that initializes video, displays text and remains running without cabinet input, DVD access or external files.

## Source behavior

source/main.c initializes video with VIDEO_Init, selects the preferred mode, allocates a framebuffer, initializes libogc's text console, configures video output and waits for vertical sync forever.

It deliberately does not call DVDInit, DVDRead, PAD_ScanPads or any JVS/EXI/SI routines.

## Build

GitHub Actions uses the official devkitPro devkitPPC container and standard GameCube make rules. The toolchain creates an ELF and converts it to a DOL with elf2dol.

## Artifact

The first build artifact is `triforce-hello-v01.dol`. The version suffix ties test results to an exact binary.\n\nSuccessful CI run: [#6](https://github.com/cdmn1/triforce-ikrg/actions/runs/45882393884), commit `aba0cbe01cb60837d80a12c3e69cef2143b8801f`. The workflow completed toolchain detection, compilation, ELF-to-DOL conversion, structural validation and artifact upload. Artifact name: `triforce-hello-v01`.

## What a passing build proves

- Source compiles with the selected devkitPPC toolchain.
- Linker produces a GameCube-targeted ELF.
- Toolchain produces a DOL.
- DOL passes basic structural checks.

## What it does not prove

- DOL boots in Dolphin.
- DOL boots through a real Triforce IPL/SegaBoot.
- Standard GCM/ISO can be loaded by the real NetDIMM.
- Triforce video output matches the preferred retail GameCube mode.

Those require separate tests and must be recorded in TEST_LOG.md.
