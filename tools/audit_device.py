#!/usr/bin/env python3
"""Read-only coral device tree prerequisite checks for ColorOS 17."""
import argparse
import json
from pathlib import Path

REQUIRED = (
    "BoardConfig-common.mk", "device-common.mk", "coral/device.mk",
    "manifest.xml", "sepolicy", "configs", "init",
)


def audit(root):
    checks = {p: (root / p).exists() for p in REQUIRED}
    mk = root / "coral/device.mk"
    text = mk.read_text(errors="replace") if mk.is_file() else ""
    features = {"coral_hardware_identity": "PRODUCT_HARDWARE := coral" in text,
                "chre_reference": "chre" in text.lower(),
                "base_manifest_present": checks["manifest.xml"]}
    return {"source": str(root.resolve()), "required": checks,
            "evidence": features,
            "pass": all(checks.values()) and all(features.values())}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("device_tree", type=Path)
    a = p.parse_args()
    result = audit(a.device_tree)
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
