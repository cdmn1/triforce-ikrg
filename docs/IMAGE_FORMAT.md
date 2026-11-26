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
