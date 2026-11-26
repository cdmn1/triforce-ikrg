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
