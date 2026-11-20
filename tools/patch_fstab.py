#!/usr/bin/env python3
"""Generate a narrowly scoped coral first-stage fstab compatibility patch.

Reads the existing Pixel fstab and produces a *candidate* patched copy.
NEVER writes the input; NEVER touches AVB, userdata encryption or vendor.
A caller must verify the donor image filesystem after sparse conversion.
"""
import argparse
import difflib
import json
import sys
from pathlib import Path

DYNAMIC = {"system", "system_ext", "product"}
SUPPORTED = {"ext4", "erofs"}


def patch(source, mapping):
    """Return (patched_fstab, audit). Refuse any potentially unsafe layout."""
    if not mapping or set(mapping) - DYNAMIC:
        raise ValueError("Only system, system_ext, product filesystem changes are supported")
    if any(fs not in SUPPORTED for fs in mapping.values()):
        raise ValueError("Filesystem must be independently confirmed as ext4 or erofs")
    lines = source.splitlines(keepends=True)
    found = {}
    patched = []
    for line in lines:
        cols = line.split()
        if not cols or line.lstrip().startswith("#"):
            patched.append(line)
            continue
        name = cols[0]
        if name not in mapping:
            patched.append(line)
            continue
        if len(cols) < 5:
            raise ValueError("Malformed fstab entry for " + name)
        if name in found:
            raise ValueError("Duplicate fstab entry for " + name)
        if cols[1] != "/" + name or "first_stage_mount" not in cols[4].split(","):
            raise ValueError("Not a coral first-stage mount: " + name)
        if "logical" not in cols[4].split(",") or "slotselect" not in cols[4].split(","):
            raise ValueError("Missing dynamic A/B flags on " + name)
        if not any(flag.startswith("avb") for flag in cols[4].split(",")):
            raise ValueError("Missing AVB flag on " + name)
        old_fs, new_fs = cols[2], mapping[name]
        if old_fs not in SUPPORTED:
            raise ValueError("Unexpected original filesystem on " + name)
        cols[2] = new_fs
        if new_fs == "erofs":
            options = [s for s in cols[3].split(",") if s not in ("barrier=1", "discard")]
            if "ro" not in options:
                options.insert(0, "ro")
            cols[3] = ",".join(options)
        # Preserve the unmodified mountpoint and fs_mgr flags byte for byte.
        found[name] = {"from": old_fs, "to": new_fs,
                       "mount": cols[1], "fs_mgr_flags": cols[4]}
        newline = "\n" if line.endswith("\n") else ""
        patched.append(" ".join(cols[:5]) + newline)
    if set(mapping) != set(found):
        raise ValueError("Requested mount(s) absent from coral fstab: " +
                         ", ".join(sorted(set(mapping) - set(found))))
    result = "".join(patched)
    # Invariant: data encryption metadata/flags must be identical.
    old_data = next((s for s in lines if s.startswith("/dev/block/bootdevice/by-name/userdata ")), None)
    new_data = next((s for s in result.splitlines(keepends=True)
                     if s.startswith("/dev/block/bootdevice/by-name/userdata ")), None)
    if old_data != new_data:
        raise AssertionError("Refusing any userdata/encryption mutation")
    return result, found


def main():
    p = argparse.ArgumentParser(description="Coral fstab patch generator, no flash")
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--system-fs", choices=sorted(SUPPORTED), required=True,
                   help="Donor filesystem verified using unsparsed image header")
    p.add_argument("--system-ext-fs", choices=sorted(SUPPORTED))
    p.add_argument("--product-fs", choices=sorted(SUPPORTED))
    a = p.parse_args()
    inputs = {"system": a.system_fs}
    if a.system_ext_fs:
        inputs["system_ext"] = a.system_ext_fs
    if a.product_fs:
        inputs["product"] = a.product_fs
    before = a.original.read_text()
    after, audit = patch(before, inputs)
    if a.output.resolve() == a.original.resolve():
        p.error("--output must differ from --original")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(after)
    print("".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                       fromfile=str(a.original), tofile=str(a.output))))
    print(json.dumps({"changes": audit, "note": "Candidate fstab only; boot ramdisk/AVB "
                      "must be separately validated; userdata preserved"}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        raise SystemExit(2)
