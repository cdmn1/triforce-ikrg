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

## Evidence gathered (2026-11-26)\n\n- OpenGP's Triforce hardware notes identify standard GameCube disc images for its documented Mario Kart Arcade GP (GGPE01) and GP 2 (GGPE02) targets. The notes describe the real boot path as Segaboot initializing the media board, loading the game from DIMM into RAM, and jumping to the DOL entry point. This is strong evidence for those game images, not proof that every Triforce board/game or every NetDIMM upload path accepts an arbitrary rebuilt ISO.\n- Dolphin's Trifold hardware article explains that Triforce storage varied: most games used GD-ROM with DIMM RAM, while Namco GP titles used NAND cartridges. Both deliver a disc image to the internal GameCube, but the storage and board protocol differ.\n- Dolphin's Triforce boot implementation runs the disc apploader, initializes the DIMM from the disc image and seeds media-board command keys from the first 12 bytes of low memory. This confirms that Triforce execution is not simply a retail GameCube DOL launch.\n- DragonMinded's `netboot` utility advertises NetDIMM transfers for Naomi, Triforce and Chihiro, but its README explicitly says it has been tested on Naomi and not verified on Triforce/Chihiro. It is a candidate for understanding the transport layer, not proof of Triforce compatibility.\n\nReferences:\n- https://github.com/OpenGP-dev/OpenGP/blob/main/docs/triforce.md\n- https://dolphin-emu.org/blog/2026/02/16/rise-of-the-triforce/\n- https://github.com/dolphin-emu/dolphin/blob/master/Source/Core/Core/Boot/Boot_BS2Emu.cpp\n- https://github.com/DragonMinded/netboot\n\n## Safe packaging investigation

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
