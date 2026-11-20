# Coral first-stage mount compatibility candidate

Pixel's existing `init/fstab.hardware` mounts `system`, `system_ext`, `vendor`, `product` as `ext4`, using A/B slot selection and AVB descriptors. A donor EROFS image cannot be mounted as `ext4`. This script **generates an explicit fstab candidate** only when the donor's real filesystem format has been independently established.

```bash
python3 tools/patch_fstab.py \
  --original /path/to/coral/init/fstab.hardware \
  --system-fs erofs \
  --output /tmp/coral-fstab.coloros17.candidate
```

The generator removes ext4-only mount options on changed filesystems, but leaves the Pixel vendor mount, metadata, userdata encryption flags, AVB entries and partition names intact. Never set `--system-fs erofs` just because a zip is named ColorOS; inspect the unsparsed image. If only `system.img` is supplied, the GSI's nested `system_ext` and `product` content needs separate consideration; do not blindly overwrite Pixel logical partitions.

**Unresolved:** actual ColorOS donor filesystem, ramdisk fstab instance, ColorOS init mounting behavior, and matching AVB descriptors/verification are not yet validated. This is not a boot image or flashable patch.
