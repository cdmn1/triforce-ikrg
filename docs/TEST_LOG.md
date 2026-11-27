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
- BI2 raw-word sample: +0x18, +0x1C and +0x20 are 1; these decode as USA country code, single-disc count and long-filename support. The simulated-memory-size field at +0x04 is zero.
- Cleanup: PASS. RVZ, ISO, extracted component files and converter working tree removed from the ephemeral runner.
- Artifacts: None uploaded.
- Emulator: Not tested.
- Real Triforce: Not tested.
- Interpretation: source system-area extraction works. Rebuilt GCM and Triforce NetDIMM payload compatibility remain unverified.


## 2026-11-26 — BI2 field mapping and inspection update

- Research result: BI2 +0x18 is country code; +0x1C is total disc count; +0x20 is long-filename support.
- Ikaruga USA values decode as country=1 (USA), disc count=1, long-filename support=1.
- BI2 +0x04 is the simulated-memory-size field and is zero in this image. The three earlier 1 values are not RAM-size settings.
- Debug flag at +0x0C is zero (normal boot); MetroTRK/track location and size at +0x10/+0x14 are zero.
- Updated workflow commit: f1151efdd557573b319df97c5ada4cdc5d948429.
- CI validation of the newly labeled output: pending.
- Emulator: Not tested.
- Real Triforce: Not tested.


## 2026-11-26 — candidate GCM replacement utility added

- Added `scripts/replace_gcm_dol.py` to replace a source GCM's main DOL in-place.
- The utility preserves and rechecks boot header, BI2, apploader, FST and total image length; checks the replacement DOL's section bounds and entry point; and verifies it fits before the FST.
- Updated the manual RVZ inspection workflow to build the project's Hello World DOL in a devkitPPC job, pass only that DOL to the image-inspection job, construct a candidate GCM temporarily, report hashes and delete the candidate.
- Candidate GCM and copyrighted source image are not uploaded as artifacts.
- Workflow run: pending manual dispatch.
- Emulator/apploader execution: not tested.
- Real Triforce: not tested.
- NetDIMM BIN compatibility: not tested.


## 2026-11-26 — experimental raw Triforce NetDIMM packager added

- Added scripts/package_triforce_netboot.py.
- It validates the GameCube boot header, BI2, apploader, DOL sections and source FST; checks all source FST file extents; then creates a compact image with the boot/system area, apploader, replacement DOL and a new 13-byte root-only FST. This is safe for the current Hello World because it performs no disc/file reads.
- It aligns output to 0x20 bytes, writes a custom homebrew game ID (THWJ01) and title into the first 0x40 bytes, preserves GameCube magic, updates FST pointers, and enforces the default 512 MiB DIMM limit.
- The output is a compact raw .bin payload; the script does not upload it, encrypt it or wrap it in a new container.
- Added unit tests for successful trimming/header patching and rejection when the payload exceeds the DIMM limit. The normal build workflow now runs these tests.
- Updated the RVZ inspection workflow to package the candidate temporarily, report its size and SHA-256, and delete it. No game-derived ISO/BIN artifact is uploaded.
- Evidence: legacy Triforce DIMM uploader transmits file bytes directly; Triforce Header Patcher uses a 0x40-byte GameCube-style header; published Triforce notes report 512 MiB DIMM.
- CI status: pending a new workflow run.
- Emulator: original candidate boot confirmed by user in Dolphin 2609b; compact root-only-FST/custom-ID BIN not yet re-tested.
- Real Triforce / NetDIMM: not tested. In particular, acceptance of a custom homebrew ID by SegaBoot remains unknown.


## 2026-11-27 — Triforce SI/JVS input probe v07

- Stage: Triforce baseboard SI/JVS communication and input validation in Dolphin.
- Artifact: `triforce-hello-v07`; DOL explicitly supplied to the compact packager with `--dol triforce-hello-v07.dol`.
- User-confirmed display: `TRIFORCE NETBOOT JVS INPUT PROBE v07`.
- JVS SetAddress transfer: sent.
- JVS SwitchInput response: PASS; response framing and checksum accepted.
- Test input: PASS; pressing mapped Test set system-input bit 7 (`0x80`).
- Service input: PASS; pressing mapped Service set player 1 switch byte 0 bit 6 (`0x40`).
- Source interpretation: Dolphin's `Common_IOAdapter::Update` sets Test bit 7 only when `AMMediaboard::GetTestMenu()` is true; `AMMediaboard::Init` sets that flag only after successfully loading `segaboot.gcm`. The observed Test bit therefore confirms SegaBoot firmware is available and loaded by Dolphin for this session. Service alone would not prove this.
- Conclusion: the emulated baseboard SI/JVS path and both Test/Service mappings are validated. Basic JVS transport testing is complete.
- Next investigation: determine the exact Triforce reset/firmware-map hand-off sequence. Dolphin's current AMMediaboard source checks reset flag `0x811FFF00 == 1` during an AM-Mediaboard DI command whose decoded offset is `0x2440`; it enables firmware mapping unless the SegaBoot signature at `0x8006BF70` is present. This is a source-level clue, not yet a proven complete reset procedure.
- Safety: v07 did not write firmware, set the reset flag, or reset the emulated machine.
- Real Triforce hardware: not tested.
