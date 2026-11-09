# EdgeWatch technical architecture

## Operational boundary

This is a **passive vision observability** product for supervised, consented bench/outdoor evaluation. Its data plane is camera -> image-space detections -> preview/events. It does not implement target lock, intercept prediction, weapon aiming, host-platform motion compensation, or UAV maneuver commands.

## Interfaces

| Layer | Contract | Concurrency |
| --- | --- | --- |
| FrameSource | open / read BGR ndarray / close | Single producer thread |
| Detector | open / detect(frame) -> Detection[] / close | Single producer thread |
| Privacy | normalize rects and black out pixels | Producer, before inference |
| Engine | state, latest JPEG buffer, lifecycle | One daemon producer, RLock |
| Telemetry | rolling bounded samples and JSONL events | Thread-safe, bounded memory |
| API | read-only status, events, MJPEG and JPEG | Async web requests |
| UI | polling telemetry and read-only stream | Browser only |

Captured images are held in a single latest-frame buffer. The server does **not** queue a separate unlimited frame history for each client; slow clients skip old frames instead of growing memory indefinitely. Memory use therefore scales primarily with camera buffers, runtime state, and bounded telemetry.

## Lifecycle and failure semantics

STOPPED -> STARTING -> OBSERVING -> STOPPED is normal. Any frame acquisition, inference, or encoding exception transitions to ERROR and emits a structured event. API readiness returns HTTP 503 outside OBSERVING. No misleading successful state is emitted when the camera or model fails.

No automatic hardware reconfiguration, unverified failover, or auto-resume after an unexpected error is performed.

## Inference contract

A model is only usable when its .hef input is RGB and its postprocessed output is a class-indexed list of boxes encoded as normalized (y0,x0,y1,x1,confidence). All other models must have a separately tested adapter. Class labels are supplied by the operator; the allowlist defaults to bird, kite, sports ball, bicycle. Output is clipped, filtered for finite scores, and capped.

The coordinate data is for image annotation, not physical movement control.

## Time semantics

Metrics use monotonic time. Events contain UTC timestamps. The reported pipeline time measures each iteration's source-read through JPEG encode; **it is not camera exposure-to-display latency**. That requires additional hardware timestamp instrumentation.

## Data governance

Privacy masks are applied before detector inference and preview. Objects overlapping masked regions are excluded from the emitted set. The browser never accesses direct camera handles. Snapshot saving requires an explicit opt-in. Files and logs remain local.

## Intended extension points

Additional camera sources, isolated analytics backends, offline validation and calibration utilities, retention controls, and better observability can be added through the defined interfaces. Motion-controller, aircraft and weapon integrations are intentionally outside scope.
