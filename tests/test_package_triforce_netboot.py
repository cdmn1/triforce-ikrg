import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "package_triforce_netboot.py"
spec = importlib.util.spec_from_file_location("package_triforce_netboot", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def make_test_gcm(path):
    image = bytearray(0x4000)
    image[0:6] = b"GIKE70"
    struct.pack_into(">I", image, 0x1C, module.MAGIC)
    struct.pack_into(">IIII", image, 0x420, 0x3000, 0x3400, 0x22, 0x22)
    # Empty apploader, with a valid 0x20-byte header.
    # One loaded DOL section at file offset 0x100.
    struct.pack_into(">I", image, 0x3000, 0x100)
    struct.pack_into(">I", image, 0x3000 + 0x48, 0x80003100)
    struct.pack_into(">I", image, 0x3000 + 0x90, 0x20)
    struct.pack_into(">I", image, 0x3000 + 0xE0, 0x80003100)
    image[0x3100:0x3120] = b"D" * 0x20
    # FST: root directory + one file named "file.bin".
    struct.pack_into(">III", image, 0x3400, 0x01000000, 0, 2)
    struct.pack_into(">III", image, 0x340C, 0x00000001, 0x3800, 0x100)
    image[0x3418:0x3422] = b"\0file.bin\0"
    image[0x3800:0x3900] = b"X" * 0x100
    path.write_bytes(image)


class PackageTest(unittest.TestCase):
    def test_builds_compact_payload_with_triforce_boot_id(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.iso"
            output = Path(td) / "hello.bin"
            make_test_gcm(source)
            info = module.package_image(source, output)
            data = output.read_bytes()
            self.assertEqual(data[:6], b"THWJ01")
            _, fst_offset, fst_size, fst_max = struct.unpack_from(">IIII", data, 0x420)
            self.assertEqual(fst_size, 33)
            self.assertEqual(fst_max, fst_size)
            fst = data[fst_offset:fst_offset + fst_size]
            self.assertEqual(struct.unpack_from(">III", fst, 0), (0x01000000, 0, 2))
            name_type, file_offset, file_size = struct.unpack_from(">III", fst, 12)
            self.assertEqual(name_type, 1)
            self.assertEqual(file_offset, info["boot_id_offset"])
            self.assertEqual(file_size, 480)
            self.assertEqual(fst[24:], b"\0boot.id\0")
            boot_id = data[file_offset:file_offset + file_size]
            self.assertEqual(boot_id[:4], b"BTID")
            self.assertEqual(boot_id[0x20:0x24], b"GCAM")
            self.assertEqual(struct.unpack_from(">I", boot_id, 0x38)[0], 0x0E)
            self.assertEqual(boot_id[0x80:0xA0].rstrip(b"\0"), module.DEFAULT_TITLE.encode())
            self.assertEqual(data[0x3100:0x3120], b"D" * 0x20)
            self.assertNotIn(b"file.bin", data)

    def test_refuses_payload_over_limit_without_output(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.iso"
            output = Path(td) / "hello.bin"
            make_test_gcm(source)
            with self.assertRaises(ValueError):
                module.package_image(source, output, max_size=0x3000)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
