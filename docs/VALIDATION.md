# Engineering validation protocol

## Gate 0: non-hardware checks

- CI compiles the package and executes deterministic tests.
- Synthetic mode starts with no camera/NPU attached.
- API endpoints return schemas that are human-auditable and read-only.
- Local events are preserved in JSONL.
- Verify privacy masking before both inference and streaming.

## Gate 1: Raspberry Pi compatibility

Record exact Pi model, OS release, Python version, picamera2 version, hailortcli version, camera ID, Hailo device architecture, HEF checksum and label-file checksum. Run the official camera and Hailo demos before enabling EdgeWatch hardware mode.

Acceptance: full 30-minute session without unexpected source failures. Do not extrapolate from synthetic FPS.

## Gate 2: passive outdoor observations

Use prearranged, consenting, non-threatening scenes. Suggested objects include a toy ball, bicycle, kite or birds where lawful and appropriate; choose only labels supported by the selected model. Do not collect biometric identity data.

Record 300+ independently annotated frames across different lighting and motion conditions. Report precision and recall per class and split. Do not claim percent accuracy from a few cherry-picked frames.

## Gate 3: performance and reliability

Capture sample counts, p50/p95 per-loop latency, 10-second processing FPS, CPU/thermal telemetry from external Pi diagnostics, memory, log-write errors, and source restarts. Run at least one 30-minute continuous recording. Mark all metrics with model/version, resolution and environmental conditions.

Provisional (not yet demonstrated) targets:
- No unhandled application error in a 30-minute run.
- 20 fps or better on the chosen compatible HEF model if hardware can support it.
- 90% or better precision and 85% or better recall on the selected authorized object class in a defined daylight dataset.
- Stable and explicit error states on forced missing camera/model tests.
- Privacy-masked pixels never appear in saved previews.

## Limitations

No gimbal stabilization accuracy, physical boresight control, airborne test, autonomous reacquisition, or pursuit metrics can be inferred from Sprint 1. Those claims are intentionally excluded from this codebase.
