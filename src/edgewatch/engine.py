"""Single-producer bounded-memory vision runtime; no physical control output."""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from .config import Settings
from .inference import make_detector
from .models import Health, utc_timestamp
from .privacy import apply_masks, overlaps_privacy
from .sources import make_source
from .telemetry import Telemetry


class ObservationEngine:
    def __init__(self, settings: Settings, source_factory=make_source,
                 detector_factory=make_detector):
        self.settings = settings
        self._source_factory = source_factory
        self._detector_factory = detector_factory
        self.telemetry = Telemetry(settings.events_path)
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._state = Health.STOPPED
        self._error: str | None = None
        self._jpeg: bytes | None = None
        self._seq = 0
        self._last_frame_utc: str | None = None
        self._last_snapshot = 0.0

    def _transition(self, state: Health, reason: str = "") -> None:
        with self._lock:
            if self._state == state:
                return
            self._state = state
        self.telemetry.emit("state_change", state.value, reason=reason)

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._error = None
            self._state = Health.STARTING
            self._thread = threading.Thread(
                target=self._run, daemon=True, name="edgewatch-observer")
            self._thread.start()
        self.telemetry.emit("lifecycle", "Starting observation engine")

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)
        if thread is not None and thread.is_alive():
            self.telemetry.emit("warning", "Shutdown waiting for blocking camera operation")
            self._transition(Health.DEGRADED, "Camera did not stop within timeout")
        else:
            self._transition(Health.STOPPED, "Operator or server shutdown")

    def status(self) -> dict:
        with self._lock:
            data = {
                "state": self._state.value,
                "error": self._error,
                "source": self.settings.source,
                "inference": self.settings.detector,
                "sequence": self._seq,
                "last_frame_utc": self._last_frame_utc,
                "privacy_masks": len(self.settings.privacy_masks),
                "recording_snapshots": self.settings.save_snapshots,
                "remote_actuation": False,
                "aircraft_control": False,
                "weapon_interface": False,
            }
        data.update(self.telemetry.summary())
        return data

    def latest_jpeg(self) -> tuple[int, bytes | None]:
        with self._lock:
            return self._seq, self._jpeg

    def _snapshot(self, jpeg: bytes, now: float) -> None:
        cfg = self.settings
        if not cfg.save_snapshots or now - self._last_snapshot < cfg.snapshot_every_s:
            return
        self._last_snapshot = now
        folder = Path(cfg.session_dir)
        folder.mkdir(parents=True, exist_ok=True)
        name = datetime.now(timezone.utc).strftime("snapshot_%Y%m%dT%H%M%S_%fZ.jpg")
        (folder / name).write_bytes(jpeg)

    def _run(self) -> None:
        source = None
        detector = None
        try:
            self.settings.validate_inputs()
            source = self._source_factory(self.settings)
            detector = self._detector_factory(self.settings)
            source.open()
            detector.open()
            self._transition(Health.OBSERVING, "Source and inference ready")
            period = 1.0 / self.settings.fps
            while not self._stop.is_set():
                loop_start = time.monotonic()
                raw = source.read()
                if raw is None:
                    self.telemetry.emit("session", "End of video input")
                    break
                if raw.ndim != 3 or raw.shape[2] != 3:
                    raise ValueError("Image source returned unsupported frame")
                frame = apply_masks(raw, self.settings.privacy_masks)
                detections = detector.detect(frame)
                detections = [d for d in detections if not overlaps_privacy(
                    d, self.settings.privacy_masks, frame.shape[1], frame.shape[0])]
                for det in detections:
                    cv2.rectangle(frame, (det.x0, det.y0), (det.x1, det.y1),
                                  (92, 217, 132), 2)
                    cv2.putText(frame, f"{det.label}: {det.score:.2f}",
                                (det.x0, max(18, det.y0 - 6)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (92, 217, 132), 1)
                ok, encoded = cv2.imencode(
                    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY,
                                   self.settings.jpeg_quality])
                if not ok:
                    raise RuntimeError("JPEG encoding failed")
                jpeg = encoded.tobytes()
                now = time.monotonic()
                latency_ms = (now - loop_start) * 1000
                with self._lock:
                    self._jpeg = jpeg
                    self._seq += 1
                    self._last_frame_utc = utc_timestamp()
                self.telemetry.frame(latency_ms, len(detections))
                try:
                    self._snapshot(jpeg, now)
                except OSError as exc:
                    self.telemetry.emit("storage_error", "Snapshot could not be saved",
                                        error=type(exc).__name__)
                self._stop.wait(max(0.0, period - (time.monotonic() - loop_start)))
        except Exception as exc:
            with self._lock:
                self._error = f"{type(exc).__name__}: {exc}"
            self.telemetry.emit("fatal", "Observation loop stopped", error=self._error)
            self._transition(Health.ERROR, "Source, inference or runtime failure")
            return
        finally:
            for device in (detector, source):
                if device is not None:
                    try:
                        device.close()
                    except Exception as exc:
                        self.telemetry.emit("cleanup_warning", str(exc))
        self._transition(Health.STOPPED, "Observation completed")
