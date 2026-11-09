# EdgeWatch Observer

**Passive edge-vision observation platform** for Raspberry Pi 5 (8 GB) and a compatible Hailo AI HAT+.

EdgeWatch is a software engineering research platform for supervised observation of permitted, non-threatening outdoor objects. It is not a counter-UAS weapon, target acquisition system, autonomous gimbal controller, or aircraft pursuit controller. It has **no physical actuation, geolocation, navigation, weapon, or flight-control endpoints**.

## Current capabilities

- Camera-source abstraction: deterministic synthetic frames, recorded video, or Raspberry Pi Picamera2.
- Optional Hailo inference through the official Picamera2 Hailo wrapper and a compatible postprocessed HEF model.
- Explicit COCO-class allowlist, confidence threshold, and bounded detections.
- Configurable privacy regions applied before inference, display, and optional snapshots.
- One-producer camera pipeline with thread-safe, latest-frame MJPEG streaming for multiple local viewers.
- Read-only local operator dashboard, health endpoints, frame capture, status, audit events and rolling latency/FPS metrics.
- Fail-visible lifecycle state, bounded event memory, opt-in snapshot recording, and synthetic-first test configuration.
- No model training required for the initial demonstration; no fabricated inference results in synthetic mode.
- Unit/integration tests and GitHub Actions validation.

## Architecture

Camera or video source -> privacy mask -> optional Hailo image-space detection -> annotated video frame -> bounded shared buffer -> read-only localhost API/dashboard.

See [architecture](docs/ARCHITECTURE.md), [validation matrix](docs/VALIDATION.md) and [security](docs/SECURITY.md).

## Desktop / synthetic simulation (no Pi or Hailo needed)

Requires Python 3.11 or newer.

~~~bash
git clone https://github.com/Saitanveesh/AI.git
cd AI
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
edgewatch check
edgewatch serve
~~~

Open http://127.0.0.1:8090 . The feed will identify itself as synthetic, and the detector will be disabled. Windows PowerShell activation: .venv\Scripts\Activate.ps1.

For recorded footage set environment variables before starting:

~~~bash
export EDGEWATCH_SOURCE=video
export EDGEWATCH_VIDEO=/absolute/path/to/consented_test_video.mp4
edgewatch serve
~~~

Recorded files stop cleanly at end-of-file. The service is read-only; restart it to replay.

## Raspberry Pi OS setup

The Pi camera/Hailo Python bindings should be installed using the system package manager. Do not replace working camera/Hailo libraries with arbitrary pip versions.

~~~bash
sudo apt update
sudo apt install python3-picamera2 python3-opencv python3-venv rpicam-apps
# Only when necessary for your compatible AI HAT+:
sudo apt install dkms hailo-all
rpicam-hello --list-cameras
hailortcli fw-control identify
~~~

Consult the current Raspberry Pi documentation before changes to Hailo system packages:
https://www.raspberrypi.com/documentation/computers/ai.html

Python environment (reuse system-provided camera and NumPy/OpenCV bindings):

~~~bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install fastapi uvicorn
pip install --no-deps -e .
export EDGEWATCH_SOURCE=picamera2
edgewatch check
edgewatch serve
~~~

For optional Hailo inference, select a **compatible postprocessed model** and matching class-label file. The application does not download or guess an HEF model.

~~~bash
export EDGEWATCH_DETECTOR=hailo
export EDGEWATCH_MODEL=/absolute/path/to/compatible_model.hef
export EDGEWATCH_LABELS=/absolute/path/to/labels.txt
export EDGEWATCH_ALLOWED_LABELS="bird,kite,sports ball,bicycle"
edgewatch check
edgewatch serve
~~~

The model output must match the documented Hailo postprocessing format: a sequence of class-indexed arrays containing (y0, x0, y1, x1, confidence). Other HEF output layouts are **not supported** without adding and validating a separate adapter.

## Privacy and local access

Default HTTP bind: 127.0.0.1:8090. To access over an authenticated SSH link from a laptop:

~~~bash
ssh -L 8090:127.0.0.1:8090 pi@YOUR_PI_HOST
~~~

Then visit http://127.0.0.1:8090 in the laptop browser. Avoid exposing the API on an untrusted network.

Optional masking of sensitive image regions (normalized coordinates x0,y0,x1,y1):

~~~bash
export EDGEWATCH_PRIVACY_MASKS="0,0,0.20,0.35;0.75,0,1,0.30"
~~~

Snapshots are off by default. To opt in to periodic snapshots (JPEG, not continuous video):

~~~bash
export EDGEWATCH_SAVE_SNAPSHOTS=true
export EDGEWATCH_SNAPSHOT_INTERVAL=30
~~~

Events append to runtime/events.jsonl; stored footage/snapshots should be managed according to local consent and retention policies.

## Validation

~~~bash
python -m compileall -q src
pytest
ruff check src tests --select E4,E7,E9,F
~~~

**Quality claim:** Architecture and tests can be checked in CI, but real throughput, AI quality, and Pi/Hailo compatibility require physical verification. There is no justified claim of military-grade stabilization, unbreakable lock, autonomous pursuit, or 20+ AI FPS until independent testing has occurred.

## Operational scope

Use only for permitted, non-threatening observation. The system does not estimate pursuit paths, identify hostile threats, assign targeting priority, output gimbal commands, or control drones.
