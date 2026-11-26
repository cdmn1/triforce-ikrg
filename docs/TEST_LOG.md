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
\n\n## 2026-11-26 — Hello World DOL v01 CI build\n\n- Stage: GameCube DOL build and structural validation\n- Status: PASS\n- Workflow run: [45882393884](https://github.com/cdmn1/triforce-ikrg/actions/runs/45882393884) (run #6)\n- Commit: `aba0cbe01cb60837d80a12c3e69cef2143b8801f`\n- Container: `devkitpro/devkitppc:20261102`\n- Artifact: `triforce-hello-v01` (contains `triforce-hello-v01.dol`, build info and SHA256SUMS)\n- Artifact ID: `15148286371`; archive SHA-256: `74ee0a3fedb8211f857e96836fa0d2ad6a88c742203ac16ebc461d027d9acd60`\n- Passed steps: toolchain check, build, DOL validation, artifact packaging and upload.\n- Emulator: Not tested.\n- Real Triforce: Not tested.\n- Notes: This validates compilation and DOL structure only. It does not establish Triforce NetDIMM packaging or boot compatibility.\n