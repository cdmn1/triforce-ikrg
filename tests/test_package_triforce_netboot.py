import importlib.util
import tempfile
import unittest
from pathlib import Path
import struct

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "package_triforce_netboot.py"
spec = importlib.util.spec_from_file_location("package_triforce_netboot", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def make_test_gcm(path):
    image = bytearray(0x4000)
    image[0:6] = b"GIKE70"
    struct.pack_into(">I", image, 0x1C, module.MAGIC)
    struct.pack_into(">IIII", image, 0x420, 0x3000, 0x3400, 0x20, 0x20)
    # Empty apploader, with a valid 0x20-byte header.
    # One loaded DOL section at file offset 0x100.
    struct.pack_into(">I", image, 0x3000, 0x100)
    struct.pack_into(">I", image, 0x3000 + 0x48, 0x80003100)
    struct.pack_into(">I", image, 0x3000 + 0x90, 0x20)
    struct.pack_into(">I", image, 0x3000 + 0xE0, 0x80003100)
    # FST: root directory + one file named "file.bin".
    struct.pack_into(">III", image, 0x3400, 0x01000000, 0, 2)
    struct.pack_into(">III", image, 0x340C, 0x00000000, 0x3800, 0x100)
    image[0x3418:0x3420] = b"file.bin"
    image[0x3800:0x3900] = b"X" * 0x100
    path.write_bytes(image)


class PackageTest(unittest.TestCase):
    def test_packages_and_trims_to_last_file_extent(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.iso"
            output = Path(td) / "hello.bin"
            make_test_gcm(source)
            info = module.package_image(source, output)
            self.assertEqual(info["payload_size"], 0x3900)
            self.assertEqual(output.stat().st_size, 0x3900)
            data = output.read_bytes()
            self.assertEqual(data[:6], b"THWJ01")
            self.assertEqual(data[0x20:0x40], module.DEFAULT_TITLE.encode().ljust(32, b"\\0"))
            self.assertEqual(struct.unpack_from(">I", data, 0x1C)[0], module.MAGIC)
            self.assertEqual(data[0x3800:0x3900], b"X" * 0x100)

    def test_refuses_payload_over_limit_without_output(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.iso"
            output = Path(td) / "hello.bin"
            make_test_gcm(source)
            with self.assertRaises(ValueError):
                module.package_image(source, output, max_size=0x3800)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
