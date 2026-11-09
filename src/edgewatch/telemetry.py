"""Bounded telemetry, capped event files, and structured audit events."""
from __future__ import annotations

import json
import threading
import time
from collections import deque
from pathlib import Path

from .models import utc_timestamp


class Telemetry:
    def __init__(
        self, events_path: str, history_size: int = 200,
        max_file_bytes: int = 5_000_000, backups: int = 3,
    ):
        if history_size < 1 or max_file_bytes < 128 or not (0 <= backups <= 20):
            raise ValueError("Invalid telemetry retention configuration")
        self._lock = threading.Lock()
        self._recent = deque(maxlen=history_size)
        self._samples = deque(maxlen=history_size)
        self._events_path = Path(events_path)
        self._events_path.parent.mkdir(parents=True, exist_ok=True)
        self._max_file_bytes = max_file_bytes
        self._backups = backups
        self._total = 0
        self._errors = 0

    def _rotate_if_needed(self, upcoming_size: int) -> None:
        path = self._events_path
        if not path.exists() or path.stat().st_size + upcoming_size <= self._max_file_bytes:
            return
        if self._backups:
            oldest = path.with_name(path.name + f".{self._backups}")
            oldest.unlink(missing_ok=True)
            for index in range(self._backups - 1, 0, -1):
                prev = path.with_name(path.name + f".{index}")
                if prev.exists():
                    prev.replace(path.with_name(path.name + f".{index + 1}"))
            path.replace(path.with_name(path.name + ".1"))
        else:
            # A zero-backup policy explicitly discards earlier records.
            path.unlink()

    def emit(self, kind: str, message: str, **detail: object) -> None:
        record = {
            "at": utc_timestamp(), "kind": kind,
            "message": message, "detail": detail,
        }
        payload = (json.dumps(record, default=str, ensure_ascii=False) + "\n").encode("utf-8")
        with self._lock:
            self._recent.append(record)
            try:
                self._rotate_if_needed(len(payload))
                with self._events_path.open("ab") as fh:
                    fh.write(payload)
            except OSError:
                self._errors += 1

    def frame(self, latency_ms: float, count: int) -> None:
        with self._lock:
            self._total += 1
            self._samples.append((time.monotonic(), latency_ms, count))

    def recent_events(self) -> list[dict]:
        with self._lock:
            return list(self._recent)

    def summary(self) -> dict:
        with self._lock:
            samples = list(self._samples)
            now = time.monotonic()
            in_window = [s for s in samples if now - s[0] <= 10]
            if len(in_window) >= 2:
                duration = max(0.001, in_window[-1][0] - in_window[0][0])
                fps = (len(in_window) - 1) / duration
            else:
                fps = 0.0
            timings = sorted(s[1] for s in samples)
            p95 = timings[min(len(timings) - 1, int(0.95 * len(timings)))] if timings else 0.0
            return {
                "frames_processed": self._total,
                "processing_fps_10s": round(fps, 2),
                "pipeline_latency_p95_ms": round(p95, 1),
                "detections_last_frame": samples[-1][2] if samples else 0,
                "event_write_errors": self._errors,
                "samples": len(samples),
            }
