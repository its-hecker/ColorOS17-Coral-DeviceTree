# Coral hardware integration / ColorOS binary port

## Invariants

- Pixel 4 XL `coral` remains the target. The OnePlus 7 Pro port is a **reference only**; no OnePlus boot, modem, camera, power or VINTF files will be flashed on coral.
- Keep tested Pixel Android 17 hardware manifests, init services, camera provider, CHRE/Soli firmware links and Citadel keymaster chain intact until a specific failure is reproduced.
- Use ColorOS system-side framework/SystemUI with the original Pixel hardware drivers. Resolve AIDL/HIDL differences one interface at a time; avoid fake-success security implementations.
- Preserve file-based encryption and secure biometric authentication, rather than disabling either to make the device appear to boot.

## Feature stages

1. First-boot audit: first-stage mount, partition metadata, init, property contexts, VINTF and graphics composer compatibility.
2. Core hardware: display/touch, radio, Wi-Fi, audio, camera, sensors and charging.
3. **GCam:** preserve the Pixel camera provider and app signature; adapt the existing plugin's APK/privapp packaging after extracting the ColorOS system.
4. **3D Face Unlock:** keep Google IR/Citadel HAL and calibration; investigate the ColorOS framework biometric integration separately. Do not replace hardware authentication with software-only shortcuts.
5. **Motion Sense:** keep CHRE/Oslo firmware and bridge; adapt ColorOS SystemUI's plugin support (the AOSP SystemUI plugin interface cannot be assumed).

## Not yet resolved

Actual donor partition topology, ColorOS framework ABI, SELinux policy merge, encryption behavior and full compatibility with the three plugins are unverified. This is not a flashable tree.
