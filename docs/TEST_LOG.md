# Test log

Record exact artifact version, toolchain/container tag, emulator version or hardware configuration, test method and visible result.

## 2026-11-26 — project initialization

- Stage: Repository scaffold
- Status: Implemented; first CI build passed in run #6
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
\n\n## 2026-11-26 — Hello World DOL v01 CI build\n\n- Stage: GameCube DOL build and structural validation\n- Status: PASS\n- Workflow run: [45882393884](https://github.com/cdmn1/triforce-ikrg/actions/runs/45882393884) (run #6)\n- Commit: `aba0cbe01cb60837d80a12c3e69cef2143b8801f`\n- Container: `devkitpro/devkitppc:20261102`\n- Artifact: `triforce-hello-v01` (contains `triforce-hello-v01.dol`, build info and SHA256SUMS)\n- Artifact ID: `15148286371`; archive SHA-256: `74ee0a3fedb8211f857e96836fa0d2ad6a88c742203ac16ebc461d027d9acd60`\n- Passed steps: toolchain check, build, DOL validation, artifact packaging and upload.\n- Emulator: Not tested.\n- Real Triforce: Not tested.\n- Notes: This validates compilation and DOL structure only. It does not establish Triforce NetDIMM packaging or boot compatibility.\n

## 2026-11-26 — Ikaruga USA RVZ structural inspection

- Stage: Source GameCube image download, conversion and structural inspection
- Status: PASS
- Workflow run: [45897021932](https://github.com/cdmn1/triforce-ikrg/actions/runs/45897021932)
- Source: user-provided Dropbox RVZ; 141,130,444 bytes
- Source SHA-256: `64b3c6b6c11643f08d3e0849ebfcf9550ee70b3c970a26ab5bde385ee05d46d7`
- Converted ISO size: 1,459,978,240 bytes (about 1.36 GiB)
- Game ID/maker: `GIKE` / `70`
- Boot magic: `0xC2339F3D`
- DOL: offset `0x1E000`, entry `0x80003140`, 8 file-backed sections all within image bounds
- FST: offset `0x189900`, size/max `0x7AF4`
- Apploader: date `2002/04/10`, entry `0x81200268`, code 5,588 bytes, trailer 107,888 bytes
- Result: boot header, apploader header, DOL and FST passed structural readability checks.
- System-file note: no `sys/` entries were present in the FST; boot header, BI2 and apploader occupy the disc system area.
- Emulator: Not tested.
- Real Triforce: Not tested.
- Privacy: source RVZ and temporary ISO were deleted from the ephemeral runner; no game image artifact was uploaded.

## 2026-11-26 — system component extraction workflow added

- Commit: `04833a7893aa620f83881b0e29d355b1f6528e87`
- Added extraction/fingerprinting for boot header, BI2, apploader, main DOL and FST.
- Prints sizes, SHA-256 hashes, BI2 first 16 words and component ranges.
- Extracted copyrighted data remains only in ephemeral runner storage and is removed by the always-run cleanup step.
- Status: Workflow update committed; new run required to validate this extraction step.


## 2026-11-26 — Ikaruga system-area component extraction

- Stage: Extract and fingerprint GameCube boot/system components
- Status: PASS
- Workflow run: [45897618626](https://github.com/cdmn1/triforce-ikrg/actions/runs/45897618626)
- Source RVZ: 141,130,444 bytes; SHA-256 `64b3c6b6c11643f08d3e0849ebfcf9550ee70b3c970a26ab5bde385ee05d46d7`
- Converted ISO: 1,459,978,240 bytes
- Extracted temporarily: boot.bin 1,088 bytes; bi2.bin 8,192 bytes; apploader.img 113,508 bytes; main.dol 1,489,152 bytes; fst.bin 31,476 bytes.
- All five component reads and SHA-256 calculations passed.
- Layout: boot 0x0000–0x0440; BI2 0x0440–0x2440; apploader 0x2440–0x1DFA4; DOL 0x1E000–0x189900; FST 0x189900–0x1913F4.
- BI2 raw-word sample: +0x18, +0x1C and +0x20 are 1; other displayed words +0x00 through +0x3C are 0. Semantics not yet assigned.
- Cleanup: PASS. RVZ, ISO, extracted component files and converter working tree removed from the ephemeral runner.
- Artifacts: None uploaded.
- Emulator: Not tested.
- Real Triforce: Not tested.
- Interpretation: source system-area extraction works. Rebuilt GCM and Triforce NetDIMM payload compatibility remain unverified.
