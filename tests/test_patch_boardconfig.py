import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "patch_boardconfig", ROOT / "tools/patch_boardconfig.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

BOARD = """AB_OTA_PARTITIONS += \
    boot \
    dtbo \
    product \
    system \
    system_ext \
    vbmeta \
    vbmeta_system \
    vendor
BOARD_GOOGLE_DYNAMIC_PARTITIONS_PARTITION_LIST := \
    product \
    system \
    system_ext \
    vendor
BOARD_AVB_VBMETA_SYSTEM := system system_ext product
BOARD_AVB_VBMETA_SYSTEM_ALGORITHM := SHA256_RSA2048
BOARD_SUPER_PARTITION_SIZE := 16106127360
TARGET_KERNEL_SOURCE := kernel/google/msm-4.14
"""


class BoardPatchTests(unittest.TestCase):
    def test_keeps_critical_partition_and_signing_config(self):
        out, report = mod.patch(BOARD)
        self.assertEqual(report["BOARD_AVB_VBMETA_SYSTEM"]["retained"], ["system"])
        for line in ("BOARD_SUPER_PARTITION_SIZE := 16106127360",
                     "TARGET_KERNEL_SOURCE := kernel/google/msm-4.14",
                     "BOARD_AVB_VBMETA_SYSTEM_ALGORITHM := SHA256_RSA2048"):
            self.assertIn(line, out)
        self.assertEqual(mod.vars_in_lines(out, "AB_OTA_PARTITIONS")[3],
                         ["boot", "dtbo", "system", "vbmeta", "vbmeta_system", "vendor"])
        self.assertEqual(mod.vars_in_lines(
            out, "BOARD_GOOGLE_DYNAMIC_PARTITIONS_PARTITION_LIST")[3], ["system", "vendor"])

    def test_missing_vendor_is_fatal(self):
        with self.assertRaises(ValueError):
            mod.patch(BOARD.replace("    vendor\n", "", 1))

    def test_unreviewed_config_is_fatal(self):
        with self.assertRaises(ValueError):
            mod.patch(BOARD.replace("system system_ext product",
                                    "system system_ext"))

if __name__ == "__main__":
    unittest.main()
