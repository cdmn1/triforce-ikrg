# Disc image and NetDIMM packaging investigation

## Current status: NOT VERIFIED

Do not treat copying main.dol into an arbitrary sys directory and renaming a rebuilt ISO to BIN as a proven Triforce netboot procedure.

A conventional GameCube disc image contains more than a DOL: disc header/boot information, BI2 configuration, apploader, main DOL, and filesystem table/files where applicable.

The GameCube image builder pyisotools documents extraction:

~~~sh
python -m pyisotools input.iso E --dest extracted
~~~

and rebuilding:

~~~sh
python -m pyisotools extracted B --dest output.iso
~~~

The documented tool usage does not establish that its output is suitable for a real Triforce NetDIMM. A normal GameCube ISO does not automatically establish the correct Triforce media-board/NetDIMM format.

## Evidence gathered (2026-11-26)\n\n- OpenGP's Triforce hardware notes identify standard GameCube disc images for its documented Mario Kart Arcade GP (GGPE01) and GP 2 (GGPE02) targets. The notes describe the real boot path as Segaboot initializing the media board, loading the game from DIMM into RAM, and jumping to the DOL entry point. This is strong evidence for those game images, not proof that every Triforce board/game or every NetDIMM upload path accepts an arbitrary rebuilt ISO.\n- Dolphin's Triforce hardware article explains that Triforce storage varied: most games used GD-ROM with DIMM RAM, while Namco GP titles used NAND cartridges. Both deliver a disc image to the internal GameCube, but the storage and board protocol differ.\n- Dolphin's Triforce boot implementation runs the disc apploader, initializes the DIMM from the disc image and seeds media-board command keys from the first 12 bytes of low memory. This confirms that Triforce execution is not simply a retail GameCube DOL launch.\n- DragonMinded's `netboot` utility advertises NetDIMM transfers for Naomi, Triforce and Chihiro, but its README explicitly says it has been tested on Naomi and not verified on Triforce/Chihiro. It is a candidate for understanding the transport layer, not proof of Triforce compatibility.\n\nReferences:\n- https://github.com/OpenGP-dev/OpenGP/blob/main/docs/triforce.md\n- https://dolphin-emu.org/blog/2026/02/16/rise-of-the-triforce/\n- https://github.com/dolphin-emu/dolphin/blob/master/Source/Core/Core/Boot/Boot_BS2Emu.cpp\n- https://github.com/DragonMinded/netboot\n\n## NetDIMM transport versus payload format

The legacy Triforce-specific `triforcetools.py` source provides concrete evidence about the upload transport:

- It opens a TCP connection to the NetDIMM service (the Piforce wrapper uses port 10703).
- `DIMM_UploadFile` reads the selected file in 0x8000-byte chunks and sends each chunk to DIMM memory.
- It computes a CRC over the transferred bytes, writes a final marker, then sends the CRC and total length with `DIMM_SetInformation`.
- The Piforce project lists Triforce as a target and stores game entries as binary files (commonly named `.bin`).

This suggests the uploader does not wrap a DOL into a disc image. It transfers the selected file byte-for-byte into DIMM memory and records transfer metadata. The file's contents must already be in a format the Triforce boot software understands.

Important limitations:

- The inspected Piforce implementation is old Python 2 code and should be treated as protocol research, not as the uploader we will ship.
- The newer DragonMinded/netboot project also lists Triforce, but explicitly says its non-Naomi operation has not been verified.
- We have not yet established whether SegaBoot expects a raw DOL, a complete GameCube disc image, a Triforce-specific game image, or a particular header/container.
- A successful upload/CRC does not prove that SegaBoot can boot the payload.

References:
- https://github.com/travistyoj/piforcetools/blob/master/triforcetools.py
- https://github.com/travistyoj/piforcetools
- https://github.com/DragonMinded/netboot
- https://www.arcade-projects.com/threads/updating-a-triforce-type-3-to-use-cf-cards-tutorial.18576/

## Building a conventional GameCube GCM for a controlled test

A native GameCube GCM is not the same thing as an ISO9660/El Torito homebrew disc. For a conventional GameCube image, the boot/system area includes at least:

- `boot.bin` (disc header)
- `bi2.bin` (boot configuration, including memory-size information)
- `apploader.img`
- `main.dol`
- `fst.bin` and filesystem content when used

Tools such as pyisotools can rebuild an extracted GameCube image, but they do not supply Nintendo system files. GCubeSDK's disc-image documentation likewise requires the four system files to be extracted from a disc the operator owns.

One additional complication: a normal devkitPPC DOL may need relocation/compression for execution by a disc apploader. GCubeSDK documents a `dollz3`/relocation step for its real GCM workflow. We must verify the exact tool and output behavior before adding it to CI.

Therefore the first controlled disc-image experiment should use a legally dumped source image, preserve its system files and metadata, replace only the main executable with a suitably apploader-compatible build, rebuild, and then test the resulting GCM in Dolphin's Triforce mode. That will validate the disc-image path in an emulator, not real NetDIMM boot.

References:
- https://github.com/JoshuaMKW/pyisotools
- https://fenixfox-studios.com/manual/gcubesdk/disc.html
- https://fenixfox-studios.com/manual/gcubesdk/config.html
- https://gc-forever.com/wiki/index.php?title=Create_a_bootable_homebrew_disc

## Safe packaging investigation

1. Obtain a legally dumped, known-good GameCube or Triforce disc image from hardware the operator owns.
2. Record source filename, size and SHA-256 locally; do not commit copyrighted system data or game contents.
3. Extract it with a known, versioned GameCube image tool.
4. Inspect boot header, BI2, apploader, DOL and FST placement.
5. Replace only the DOL with this project's Hello World DOL.
6. Rebuild and verify the image can be reopened and extracted by the same tool.
7. Compare the rebuilt image with a known-good Triforce NetDIMM image, if available, at the structural level.
8. Only after the exact NetDIMM format is established, add deterministic conversion and CI validation.

## Important distinction

The file extension BIN is not a format specification. A renamed ISO is still an ISO; the extension alone does not make it a valid NetDIMM upload image.

## Copyright and security

Do not put IPL dumps, SegaBoot, copyrighted apploader/system files, game images, security keys or PIC bypass material in this repository. Document how to use legitimately obtained local system data without distributing it.


## Verified source image inspection (2026-11-26)

The private GitHub Actions inspection workflow successfully downloaded and converted the user's Ikaruga (USA) RVZ dump. The source file was 141,130,444 bytes (SHA-256 `64b3c6b6c11643f08d3e0849ebfcf9550ee70b3c970a26ab5bde385ee05d46d7`); conversion produced a 1,459,978,240-byte GameCube ISO.

Observed disc metadata:
- Game ID: `GIKE`; maker: `70`; disc number/version: 0/0.
- GameCube boot magic: `0xC2339F3D`.
- DOL offset: `0x1E000`; entry point: `0x80003140`; eight file-backed sections.
- FST offset: `0x189900`; size/max size: `0x7AF4`.
- Apploader date: `2002/04/10`; entry: `0x81200268`; code size: 5,588 bytes; trailer size: 107,888 bytes.
- No ordinary FST entries were found under `sys/`; boot header, BI2 and apploader are system-area structures, not ordinary FST files.

The inspection workflow has now been extended to extract these components into ephemeral runner storage and print their sizes and SHA-256 fingerprints:
- `boot.bin` (0x440 bytes)
- `bi2.bin` (0x2000 bytes)
- `apploader.img` (header + declared code + trailer)
- `main.dol` (header + all file-backed sections)
- `fst.bin`

It also prints the first 16 BI2 big-endian words for analysis. The extracted copyrighted components are not uploaded as artifacts, committed to this repository, or retained after the job; the cleanup step removes the temporary image and extracted files.

This establishes a reproducible way to inspect the owned source dump. It does not establish that a rebuilt ISO is accepted by SegaBoot/Triforce NetDIMM, nor does it establish that replacing the DOL alone is sufficient for an executable homebrew disc.


## Verified system-area component extraction (2026-11-26)

Workflow run [45897618626](https://github.com/cdmn1/triforce-ikrg/actions/runs/45897618626) completed successfully, including the component extraction and cleanup steps.

The workflow extracted these byte ranges from the user's Ikaruga (USA) image into temporary runner storage:

| Component | Size | SHA-256 |
|---|---:|---|
| `boot.bin` | 1,088 bytes (0x440) | `01a145fd1fe763015321b75e56652478a9bb718dd7fc37d092beea9e17c6c69c` |
| `bi2.bin` | 8,192 bytes (0x2000) | `7294bc146d7ad38f7fd8b02038e563dc9380ff272b66e9bd215631def4fd6cec` |
| `apploader.img` | 113,508 bytes | `1a864e15684124c72e55abb3dc283acccc97ce3fa5dd0f60dee17317b17819ec` |
| `main.dol` | 1,489,152 bytes | `2c149f4bca8e05c051feb9d4dec066326e4243c6f49aff51712dcde87261ed0a` |
| `fst.bin` | 31,476 bytes (0x7AF4) | `b54e6ac5091c058aef25ff4dd565b2816e404b60057cb209d27e0c22b611ee3b` |

Range consistency checks:
- Boot header: `0x0000–0x0440`
- BI2: `0x0440–0x2440`
- Apploader: `0x2440–0x1DFA4` (header + declared code + trailer)
- Main DOL: `0x1E000–0x189900` (header and file-backed section extents)
- FST: `0x189900–0x1913F4`

The DOL range ends exactly at the FST start. The BI2 inspection printed the first 16 big-endian words; the values at offsets +0x18, +0x1C and +0x20 were 1, while the other displayed words were 0. These raw values are recorded without assigning meanings until the field layout is independently verified.

The workflow deleted the source RVZ, converted ISO, extracted components and converter working tree during cleanup. No binary component or game image was uploaded or committed. This is a successful extraction/fingerprinting test, not a boot test.


## BI2 field interpretation (2026-11-26)

The previously recorded values at BI2 offsets +0x18, +0x1C and +0x20 are now mapped:

| BI2 offset | Field | Ikaruga USA value | Interpretation |
|---|---|---:|---|
| +0x00 | Debug monitor size | 0 | No debug monitor size declared |
| +0x04 | Simulated memory size | 0 | No nonzero simulated-memory override declared |
| +0x08 | Argument offset | 0 | No argument block offset declared |
| +0x0C | Debug flag | 0 | Normal boot |
| +0x10 | MetroTRK/track location | 0 | No track/debug monitor location |
| +0x14 | MetroTRK/track size | 0 | No track/debug monitor size |
| +0x18 | Country code | 1 | USA |
| +0x1C | Total disc count | 1 | Single-disc title |
| +0x20 | Long filename support | 1 | Long filenames enabled |
| +0x24 | PAD spec | 0 | Default/zero PAD specification |
| +0x28 | DOL limit | 0 | No nonzero limit declared |

The field layout is documented by the GameCube GCM format reference; Nintendont independently reads BI2 +0x18 as the region code. The values now explain the three earlier 1 words: USA region, one disc, and long-filename support. They are not RAM-size values.

The memory-related BI2 field is +0x04 (SimulatedMemorySize), and this Ikaruga image stores zero there. Do not infer a Triforce RAM requirement from the three 1 values. Game-specific Triforce memory configuration still needs its own evidence.

The inspection workflow now prints these named BI2 fields as well as the raw first 16 words. This is an interpretation/reporting enhancement only; the updated workflow must run before it is considered CI-verified.

References:
- https://wiki.re.virtualworld.fr/index.php/GCM_(File_format)
- https://github.com/FIX94/Nintendont/blob/master/loader/source/main.c


## Controlled Hello World DOL replacement experiment

A new utility, `scripts/replace_gcm_dol.py`, builds a candidate GameCube image from an operator-owned ISO and this project's Hello World DOL. It replaces only the replacement DOL's byte range at the boot header's declared DOL offset, leaving the remaining original DOL-area bytes intact. It leaves the boot header, BI2, apploader, FST, image length and all bytes outside the replacement DOL range untouched.

The utility checks the GameCube magic, source DOL/FST ranges, apploader extent, replacement DOL section bounds and entry point, available DOL slot capacity, and byte-for-byte preservation of the boot header, BI2, apploader and FST after writing.

The updated `Inspect Triforce source RVZ` workflow builds the Hello World DOL in a separate devkitPPC job, transfers only that project-owned DOL as a temporary workflow artifact, downloads the operator-provided RVZ, converts it to ISO, constructs the candidate image, prints its hashes and structural checks, then deletes the source, candidate and extracted components. The candidate image is deliberately not uploaded as an artifact because it contains copyrighted game data.

This is a controlled packaging experiment, not proof that Ikaruga's retail apploader will execute the replacement, not a Dolphin boot result, and not a Triforce NetDIMM payload. The next validation is to run the updated workflow and inspect its structural report; actual apploader execution still requires an emulator test.


## Experimental raw NetDIMM payload packaging (2026-11-26)

New evidence narrows the payload format:

- The legacy Triforce DIMM_UploadFile implementation sends the selected file's bytes directly to DIMM memory in 0x8000-byte chunks, then sends a final marker and the CRC/length. It does not add a file container around the payload. This is transport evidence from an old tool, not a real-hardware test of our image.
- The Triforce Header Patcher operates on raw image files. It recognises known Triforce image sizes, validates the SHA-1 of the image body (starting at byte 0x40), and writes a 0x40-byte GameCube-style disc header for known titles. Its headers place the six-byte game ID at 0x00, GameCube magic 0xC2339F3D at 0x1C, and title text at 0x20. The tool only assigns known IDs after matching known game hashes; it does not prove arbitrary custom IDs are accepted by SegaBoot.
- Published Triforce hardware notes report a 512 MiB DIMM size. Known Triforce image sizes in the header patcher are below that limit (for example F-Zero AX 0x19FCC500, Mario Kart Arcade GP 0x15000000 and GP 2 0x1E000000).
- The Triforce Type 3 netboot tutorial uses transfergame.exe <IP> FZ.bin, consistent with a raw binary payload being sent to the DIMM.

Based on that evidence, scripts/package_triforce_netboot.py now creates an **experimental compact raw .bin payload** from the working candidate GCM. Because this Hello World does not read files from disc, the packager deliberately removes the original game's FST entries and game files instead of carrying them into the NetDIMM image:

1. Validates the GameCube boot magic, BI2, apploader and DOL section extents.
2. Parses the source FST and checks every file extent before discarding the source FST contents.
3. Retains the boot header, BI2, apploader and replacement DOL at the declared DOL offset.
4. Creates a valid 13-byte root-only FST and updates the boot header's FST offset/size fields.
5. Aligns the final payload to 0x20 bytes, matching the 32-byte DI read granularity described in the Triforce hardware notes.
6. Enforces a default 512 MiB limit and refuses to write an output if the compact image exceeds it.
7. Writes the custom six-byte homebrew ID THWJ01 and title TRIFORCE NETBOOT HELLO WORLD into the 0x40-byte disc header, preserving the GameCube magic and other header fields.
8. Writes the compact raw bytes as .bin; it does not encrypt, wrap, or upload them.

### What remains unverified

- The compact payload size must be checked by running the packager on the user's Ikaruga-derived candidate. The original ISO is 1.36 GiB, but the compact output contains only the boot/system area, apploader, replacement DOL and empty FST, so it should be much smaller. The script still validates the original FST and all file extents before discarding those files.
- The custom homebrew ID/title may not be accepted by the cabinet's SegaBoot. Known-image header patching is hash-gated for a reason; we must not claim that a made-up ID is accepted.
- Dolphin boot was confirmed for the candidate before this compact-image/header operation. The resulting .bin must be reopened in Dolphin 2609b with Triforce Baseboard enabled and tested again.
- A successful Dolphin boot or successful NetDIMM transfer/CRC is not a real Triforce boot. Hardware confirmation remains outstanding.

References:
- https://github.com/travistyoj/piforcetools/blob/master/triforcetools.py
- https://github.com/FIX94/triforce-header-patcher
- https://github.com/OpenGP-dev/OpenGP/blob/main/docs/triforce.md
- https://www.arcade-projects.com/threads/updating-a-triforce-type-3-to-use-cf-cards-tutorial.18576/


## Compact Triforce-recognition experiment (v02)

The compact Hello World package includes a synthetic boot.id file in its GameCube FST. Dolphin's VolumeGC checks the FST for boot.id, validates the four-byte BTID magic, and then treats the volume as Triforce. The 480-byte structure contains GCAM at offset 0x20, an eight-byte homebrew identifier, USA region flags (0x0E), and homebrew manufacturer/title strings.

This metadata is constructed for Dolphin's source-level recognition path. It is not copied from a retail Triforce title and is not evidence that SegaBoot accepts arbitrary homebrew metadata. The Type-3 compatibility byte is left unset. The six-byte GameCube boot header ID remains THWJ01.

Expected test:
- Dolphin should classify the volume as Triforce based on boot.id.
- Its AM-Mediaboard code may still report an unknown game ID and use default controls.
- A successful Dolphin classification/boot does not establish real Triforce NetDIMM compatibility.

The packager retains only the boot.id metadata file; original game FST entries and assets remain omitted.
