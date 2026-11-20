# ColorOS 17 single-system-image partition declaration candidate

Coral's original `BoardConfig-common.mk` still declares `product` and `system_ext` in three independently generated lists:

1. `BOARD_AVB_VBMETA_SYSTEM` — descriptors currently include system, product and system_ext.
2. `BOARD_GOOGLE_DYNAMIC_PARTITIONS_PARTITION_LIST` — group currently allocates all four partitions.
3. `AB_OTA_PARTITIONS` — the stock OTA manifest still names product and system_ext.

PLK110 instead embeds those directories in a single 6.58 GB raw ext4 `system.img`. Our first-stage fstab candidate omits the separate mounts. To keep a **candidate build configuration** consistent, this tool proposes removing `product` and `system_ext` from those three lists. It leaves system, vendor, boot, vbmeta, vbmeta_system, rollback metadata, kernel, recovery, partition geometry and signing configuration unchanged.

```bash
python3 tools/patch_boardconfig.py \
  --original /path/to/floral/BoardConfig-common.mk \
  --output /tmp/BoardConfig-common.coloros17.candidate.mk
```

This is only a diff for review. It does not produce signed vbmeta descriptors. It also does not delete existing logical partitions from an installed phone, change AVB policy, or claim the ColorOS boot chain is compatible. Any real build must verify super metadata layout, product/system_ext directory roots, OTA migration rules and the actual signing chain with `avbtool` and `checkvintf`. It must preserve existing userdata encryption.

**Do not flash generated files at this stage.**
