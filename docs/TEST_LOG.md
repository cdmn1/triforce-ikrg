# Test log

Record exact artifact version, toolchain/container tag, emulator version or hardware configuration, test method and visible result.

## 2026-11-26 — project initialization

- Stage: Repository scaffold
- Status: Implemented; CI result pending
- Artifact target: triforce-hello-v01.dol
- Build environment: devkitpro/devkitppc:20261102
- Source: source/main.c
- Automated validation: DOL header, section bounds and entry-point checks
- Emulator: Not tested
- Real Triforce: Not tested
- Notes: DOL build milestone only, not a NetDIMM image or boot confirmation.

## 2026-11-26 — CI attempt 1

- Run: 45881270134
- Result: Failed before compilation.
- Failure: devkitPPC compiler was installed in the container but its bin directory was not on PATH during the toolchain-version check.
- Correction: explicitly prepend DEVKITPPC/bin and DEVKITPRO/tools/bin in the workflow before checking tool versions.
- No source compilation or DOL validation occurred in this attempt.
