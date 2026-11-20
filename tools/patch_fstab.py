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
EMBEDDABLE = {"system_ext", "product"}
SUPPORTED = {"ext4", "erofs"}


def patch(source, mapping=None, embedded=()):
    """Return (candidate_fstab, audit), keeping vendor and userdata untouched.

    If a verified system-as-root GSI embeds /product and /system_ext inside its
    single system.img, omitting separate first-stage mounts is an optional
    compatibility candidate; still requires boot-chain and AVB verification.
    """
    mapping = mapping or {}
    embedded = set(embedded)
    if not mapping and not embedded:
        raise ValueError("Specify a verified filesystem change or embedded partition")
    if set(mapping) - DYNAMIC or embedded - EMBEDDABLE:
        raise ValueError("Only coral system, product and system_ext adaptations supported")
    if set(mapping) & embedded:
        raise ValueError("Cannot both mount and omit a logical partition")
    if any(fs not in SUPPORTED for fs in mapping.values()):
        raise ValueError("Filesystem must be confirmed as ext4 or erofs")
    lines = source.splitlines(keepends=True)
    found = {}
    patched = []
    for line in lines:
        cols = line.split()
        if not cols or line.lstrip().startswith("#"):
            patched.append(line)
            continue
        name = cols[0]
        if name not in mapping and name not in embedded:
            patched.append(line)
            continue
        if len(cols) < 5 or name in found:
            raise ValueError("Malformed/duplicate fstab entry for " + name)
        if cols[1] != "/" + name or "first_stage_mount" not in cols[4].split(","):
            raise ValueError("Not a coral first-stage mount: " + name)
        if "logical" not in cols[4].split(",") or "slotselect" not in cols[4].split(","):
            raise ValueError("Missing dynamic A/B flags on " + name)
        if not any(flag.startswith("avb") for flag in cols[4].split(",")):
            raise ValueError("Missing AVB descriptor on " + name)
        old_fs = cols[2]
        if old_fs not in SUPPORTED:
            raise ValueError("Unexpected filesystem on " + name)
        if name in embedded:
            found[name] = {"action": "omit_first_stage_mount",
                           "reason": "bundled at /" + name + " inside donor system.img",
                           "original": line.strip()}
            patched.append("# ColorOS17 embedded: " + line)
            continue
        new_fs = mapping[name]
        cols[2] = new_fs
        if new_fs == "erofs":
            options = [s for s in cols[3].split(",") if s not in ("barrier=1", "discard")]
            if "ro" not in options:
                options.insert(0, "ro")
            cols[3] = ",".join(options)
        found[name] = {"action": "filesystem_type", "from": old_fs, "to": new_fs,
                       "mount": cols[1], "fs_mgr_flags": cols[4]}
        newline = "\n" if line.endswith("\n") else ""
        patched.append(" ".join(cols[:5]) + newline)
    requested = set(mapping) | embedded
    if requested != set(found):
        raise ValueError("Requested mount(s) absent from fstab: " +
                         ", ".join(sorted(requested - set(found))))
    result = "".join(patched)
    old_data = [s for s in lines if "/data " in s and "fileencryption=" in s]
    new_data = [s for s in result.splitlines(keepends=True)
                if "/data " in s and "fileencryption=" in s]
    if old_data != new_data:
        raise AssertionError("Refusing any userdata/encryption mutation")
    old_vendor = [s for s in lines if s.startswith("vendor ")]
    new_vendor = [s for s in result.splitlines(keepends=True)
                  if s.startswith("vendor ")]
    if old_vendor != new_vendor:
        raise AssertionError("Pixel vendor fstab must remain unchanged")
    return result, found

def main():
    p = argparse.ArgumentParser(description="Coral fstab patch generator, no flash")
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--system-fs", choices=sorted(SUPPORTED),
                   help="Donor filesystem verified using unsparsed image header")
    p.add_argument("--system-ext-fs", choices=sorted(SUPPORTED))
    p.add_argument("--product-fs", choices=sorted(SUPPORTED))
    p.add_argument("--embed-product", action="store_true", help="Omit separately mounted product (GSI embeds it)")
    p.add_argument("--embed-system-ext", action="store_true", help="Omit separately mounted system_ext (GSI embeds it)")
    a = p.parse_args()
    inputs = {"system": a.system_fs} if a.system_fs else {}
    if a.system_ext_fs:
        inputs["system_ext"] = a.system_ext_fs
    if a.product_fs:
        inputs["product"] = a.product_fs
    before = a.original.read_text()
    embedded = {name for name, enabled in (("product", a.embed_product),
                                        ("system_ext", a.embed_system_ext)) if enabled}
    after, audit = patch(before, inputs, embedded)
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
