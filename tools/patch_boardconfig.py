#!/usr/bin/env python3
"""Generate review-only coral BoardConfig partition-list candidate.

This tool NEVER modifies the pinned hardware tree, vbmeta image or signing keys.
It only removes separately generated product/system_ext partitions from three
specific make variables because PLK110 already embeds those roots in system.img.
Exact system/vendor/boot/OTA and AVB verification remain separate gates.
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

CHANGES = {
    "BOARD_AVB_VBMETA_SYSTEM": {"product", "system_ext"},
    "BOARD_GOOGLE_DYNAMIC_PARTITIONS_PARTITION_LIST": {"product", "system_ext"},
    "AB_OTA_PARTITIONS": {"product", "system_ext"}
}
KEEP = {
    "BOARD_AVB_VBMETA_SYSTEM": {"system"},
    "BOARD_GOOGLE_DYNAMIC_PARTITIONS_PARTITION_LIST": {"system", "vendor"},
    "AB_OTA_PARTITIONS": {"boot", "vbmeta", "vbmeta_system", "system", "vendor"}
}


def vars_in_lines(src, variable):
    lines = src.splitlines(keepends=True)
    hits = []
    rx = re.compile(r"^\s*" + re.escape(variable) + r"\s*(?P<op>\+=|:=|=)\s*(?P<rest>.*)$")
    for i, line in enumerate(lines):
        m = rx.match(line)
        if not m:
            continue
        j = i
        value = m.group("rest")
        while value.rstrip().endswith("\\"):
            j += 1
            if j >= len(lines):
                raise ValueError("Incomplete make continuation for " + variable)
            value = value.rstrip()[:-1] + " " + lines[j].strip()
        tokens = value.split("#", 1)[0].replace("\\", "").split()
        hits.append((i, j, m.group("op"), tokens))
    if len(hits) != 1:
        raise ValueError(f"Expected exactly one {variable}; found {len(hits)}")
    return hits[0]


def patch(text):
    lines = text.splitlines(keepends=True)
    locations = {}
    changes = {}
    for name, omitted in CHANGES.items():
        start, end, op, tokens = vars_in_lines(text, name)
        if not omitted.issubset(tokens):
            raise ValueError("Expected embedded partitions absent from " + name)
        remain = [t for t in tokens if t not in omitted]
        if not KEEP[name].issubset(remain):
            raise ValueError("Critical boot/vendor/AVB entries missing in " + name)
        if not remain:
            raise ValueError("Cannot clear " + name)
        if name == "BOARD_AVB_VBMETA_SYSTEM":
            replacement = f"{name} {op} {' '.join(remain)}\n"
        else:
            replacement = f"{name} {op} \\\n" + "".join(
                f"    {item}" + (" \\\n" if index < len(remain)-1 else "\n")
                for index, item in enumerate(remain))
        locations[(start, end)] = replacement
        changes[name] = {"removed": sorted(omitted), "retained": remain}
    result = "".join(lines)
    for (start, end), replacement in sorted(locations.items(), reverse=True):
        parts = result.splitlines(keepends=True)
        parts[start:end+1] = [replacement]
        result = "".join(parts)
    for name in CHANGES:
        _, _, _, tokens = vars_in_lines(result, name)
        if CHANGES[name].intersection(tokens):
            raise AssertionError("Embedded partitions not removed from " + name)
    if result == text:
        raise ValueError("Unexpected no-op: source already patched or invalid")
    return result, changes


def main():
    p = argparse.ArgumentParser(description="ColorOS17 coral BoardConfig candidate generator")
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.original.resolve() == args.output.resolve():
        p.error("Never modify the original BoardConfig in place")
    before = args.original.read_text()
    result, diff = patch(before)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result)
    print("".join(difflib.unified_diff(
        before.splitlines(True), result.splitlines(True),
        fromfile=str(args.original), tofile=str(args.output))))
    print(json.dumps({"changes": diff, "status": "CANDIDATE_ONLY",
                      "warning": "AVB signing, vbmeta descriptors and super metadata "
                                 "must be rebuilt and verified before any flash"}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, AssertionError) as error:
        print("ERROR:", error, file=sys.stderr)
        raise SystemExit(2)
