# ColorOS 17 coral hardware adapter

Maintainer: **Hecker** · Target: **Google Pixel 4 XL (coral)** · Stage: source audit.

This repository contains ColorOS-specific compatibility checks and future modifications; the complete floral Android 17 hardware tree is currently fetched separately from the pinned HeckerOS source. Do not replace the known-good source with donor OnePlus or OPPO device files.

Run `python3 tools/audit_device.py /path/to/heckeros-floral-devicetree` to verify the base. `source.json` records the reviewed source revision; port-specific patches will be added only after inspecting the actual ColorOS donor archive and boot logs.

**No bootable ROM or installer has been produced.**
