"""Bounded in-memory telemetry and append-only JSONL event recording."""
from __future__ import annotations

import json
import statistics
import threading
import time
from collections import deque
from pathlib import Path

from .models import utc_timestamp


class Telemetry:
    def __init__(self, events_path: str, history_size: int = 200):
        self._lock = threading.Lock()
        self._recent = deque(maxlen=history_size)
        self._samples = deque(maxlen=history_size)
        self._events_path = Path(events_path)
        self._events_path.parent.mkdir(parents=True, exist_ok=True)
        self._total = 0
        self._errors = 0

    def emit(self, kind: str, message: str, **detail: object) -> None:
        record = {"at": utc_timestamp(), "kind": kind,
                  "message": message, "detail": detail}
        with self._lock:
            self._recent.append(record)
            try:
                with self._events_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, default=str) + "\n")
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
            fps = len(in_window) / min(10.0, max(0.001,
                (now - in_window[0][0]) if in_window else 10.0))
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
