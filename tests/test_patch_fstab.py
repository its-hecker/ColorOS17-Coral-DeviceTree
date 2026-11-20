import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "patch_fstab", Path(__file__).resolve().parents[1] / "tools/patch_fstab.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

FSTAB = (
    "system /system ext4 ro,barrier=1 wait,slotselect,avb=vbmeta_system,logical,first_stage_mount\n"
    "system_ext /system_ext ext4 ro,barrier=1 wait,slotselect,avb=vbmeta_system,logical,first_stage_mount\n"
    "product /product ext4 ro,barrier=1 wait,slotselect,avb,logical,first_stage_mount\n"
    "vendor /vendor ext4 ro,barrier=1 wait,slotselect,avb=vbmeta,logical,first_stage_mount\n"
    "/dev/block/bootdevice/by-name/userdata /data f2fs nosuid,nodev latemount,wait,"
    "fileencryption=ice,keydirectory=/metadata/vold/metadata_encryption\n"
)


class FstabTests(unittest.TestCase):
    def test_only_system_erofs(self):
        patched, report = p.patch(FSTAB, {"system": "erofs"})
        self.assertIn("system /system erofs ro wait,slotselect,avb=vbmeta_system,"
                      "logical,first_stage_mount", patched)
        self.assertIn(FSTAB.splitlines()[3], patched)  # Pixel vendor kept intact
        self.assertIn(FSTAB.splitlines()[4], patched)  # Encryption kept intact
        self.assertEqual(report["system"]["from"], "ext4")

    def test_more_dynamic_partitions(self):
        out, report = p.patch(FSTAB, {"system": "erofs", "product": "erofs"})
        self.assertIn("product /product erofs ro ", out)
        self.assertEqual(set(report), {"system", "product"})

    def test_unchecked_vendor_disallowed(self):
        with self.assertRaises(ValueError):
            p.patch(FSTAB, {"vendor": "erofs"})

    def test_missing_mount_rejected(self):
        with self.assertRaises(ValueError):
            p.patch(FSTAB, {"odm": "ext4"})

    def test_missing_avb_rejected(self):
        with self.assertRaises(ValueError):
            p.patch(FSTAB.replace("avb=vbmeta_system,", "", 1), {"system": "erofs"})

    def test_boot_flags_preserved(self):
        out, _ = p.patch(FSTAB, {"system": "erofs"})
        self.assertIn("wait,slotselect,avb=vbmeta_system,logical,first_stage_mount", out)


if __name__ == "__main__":
    unittest.main()
