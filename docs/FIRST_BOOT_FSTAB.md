# PLK110-specific coral first-stage mount candidate

The verified September 18, 2026 PLK110 ColorOS 17 Axis GSI contains **one raw ext4 system.img**. Inspection of that image (Actions run 44828896866) found populated top-level `/system`, `/product`, `/system_ext`, `/my_product`, `/my_stock`, and other ColorOS `my_*` directories inside **that same filesystem**.

Coral's stock `init/fstab.hardware` instead tries to mount **separate** A/B logical `product` and `system_ext` images. Mounting these from PixelOS would shadow the ColorOS directories in the GSI. A candidate first-boot fstab must therefore omit the separate `product` and `system_ext` mount rows while keeping `system` and `vendor` intact.

### Generate (does not flash or edit the original)

```bash
python3 tools/patch_fstab.py \
  --original /path/to/floral-device-tree/init/fstab.hardware \
  --embed-product --embed-system-ext \
  --output /tmp/coral-coloros17-fstab.candidate
```

The tool comments the selected rows instead of deleting evidence; preserves Pixel vendor, metadata, encrypted userdata, mount flags and existing AVB references. **Do not use `--system-fs erofs` for the verified PLK110 donor; it is ext4.**

This is a **reviewable candidate**, not a bootable ramdisk patch. The installer and boot chain still need to verify the GSI's system-as-root mount context, `/product` and `/system_ext` overlay behavior, linker namespaces, SELinux contexts and exact vbmeta descriptors. Boot-time logging and reversible test packaging are necessary before a flash recommendation.
