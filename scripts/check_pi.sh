#!/usr/bin/env bash
set -u
printf '%s\n' '=== EdgeWatch hardware inventory (read-only) ==='
uname -a
cat /etc/os-release || true
python3 --version
printf '%s\n' '=== Camera enumeration ==='
if command -v rpicam-hello >/dev/null 2>&1; then
  rpicam-hello --list-cameras || true
else
  printf '%s\n' 'rpicam-hello is not installed'
fi
printf '%s\n' '=== Hailo device identity ==='
if command -v hailortcli >/dev/null 2>&1; then
  hailortcli fw-control identify || true
else
  printf '%s\n' 'hailortcli is not installed'
fi
printf '%s\n' '=== Relevant Python packages ==='
python3 - <<'PY'
import importlib.util
for name in ("picamera2", "cv2", "numpy", "hailo_platform"):
    print(f"{name}: {'available' if importlib.util.find_spec(name) else 'missing'}")
PY
