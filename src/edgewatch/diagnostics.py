"""Read-only environment inventory; never installs or modifies device packages."""
from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def _probe_command(command: list[str], timeout_s: float = 4) -> dict:
    if shutil.which(command[0]) is None:
        return {"available": False, "output": "Executable is not installed"}
    try:
        proc = subprocess.run(command, timeout=timeout_s, capture_output=True,
                              text=True, check=False)
        return {
            "available": True,
            "exit_code": proc.returncode,
            "output": (proc.stdout or proc.stderr)[-4000:],
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": True, "error": type(exc).__name__}


def collect_diagnostics() -> dict:
    packages = {}
    for name in ("picamera2", "cv2", "numpy", "hailo_platform", "fastapi"):
        try:
            packages[name] = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            packages[name] = False
    thermal = Path("/sys/class/thermal/thermal_zone0/temp")
    cpu_celsius = None
    try:
        if thermal.is_file():
            cpu_celsius = round(int(thermal.read_text().strip()) / 1000, 1)
    except (ValueError, OSError):
        pass
    return {
        "schema": "edgewatch.diagnostics.v1",
        "system": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "user_is_root": hasattr(os, "geteuid") and os.geteuid() == 0,
        "python_modules": packages,
        "cpu_temperature_celsius": cpu_celsius,
        "camera_command": _probe_command(["rpicam-hello", "--list-cameras"]),
        "hailo_identity": _probe_command(["hailortcli", "fw-control", "identify"]),
        "hardware_verified": False,
        "note": "Inventory only. Successful process execution does not qualify vision performance.",
    }
