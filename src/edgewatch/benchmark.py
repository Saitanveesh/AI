"""Reproducible, offline passive-inference benchmarking without video output.

No object trajectories, target selection, physical pointing or location data.
"""
from __future__ import annotations

import hashlib
import platform
import statistics
import time
from collections import Counter
from pathlib import Path

from .config import Settings
from .inference import make_detector
from .privacy import apply_masks, overlaps_privacy
from .sources import make_source


def _digest(path: str) -> str | None:
    if not path:
        return None
    sha = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _percentile(samples: list[float], fraction: float) -> float:
    if not samples:
        return 0.0
    data = sorted(samples)
    index = min(len(data) - 1, max(0, int((len(data) - 1) * fraction)))
    return round(data[index], 3)


def benchmark(settings: Settings, max_frames: int = 300,
              source_factory=make_source, detector_factory=make_detector) -> dict:
    """Process a bounded session; report reproducible aggregate stats only."""
    if not (1 <= max_frames <= 10000):
        raise ValueError("Invalid frame limit")
    settings.validate_inputs()
    source = source_factory(settings)
    detector = detector_factory(settings)
    counts: Counter[str] = Counter()
    latencies: list[float] = []
    inference_latencies: list[float] = []
    frames = 0
    started = time.perf_counter()
    source_ready = False
    detector_ready = False
    try:
        source.open()
        source_ready = True
        detector.open()
        detector_ready = True
        while frames < max_frames:
            t0 = time.perf_counter()
            raw = source.read()
            if raw is None:
                break
            if raw.ndim != 3 or raw.shape[2] != 3:
                raise ValueError("Source returned invalid frame")
            frame = apply_masks(raw, settings.privacy_masks)
            t1 = time.perf_counter()
            observations = detector.detect(frame)
            t2 = time.perf_counter()
            for det in observations:
                if not overlaps_privacy(det, settings.privacy_masks,
                                        frame.shape[1], frame.shape[0]):
                    counts[det.label] += 1
            latencies.append((t2 - t0) * 1000)
            inference_latencies.append((t2 - t1) * 1000)
            frames += 1
    finally:
        if detector_ready:
            detector.close()
        if source_ready:
            source.close()
    elapsed = time.perf_counter() - started
    return {
        "schema": "edgewatch.benchmark.v1",
        "synthetic": settings.source == "synthetic",
        "source": settings.source,
        "inference": settings.detector,
        "model_sha256": _digest(settings.model_path),
        "labels_sha256": _digest(settings.labels_path),
        "video_sha256": _digest(settings.video_path),
        "host": platform.machine(),
        "image_width": settings.width,
        "image_height": settings.height,
        "frames_processed": frames,
        "frames_requested": max_frames,
        "elapsed_seconds": round(elapsed, 3),
        "throughput_fps": round(frames / elapsed, 3) if elapsed > 0 else 0.0,
        "frame_pipeline_ms_p50": _percentile(latencies, 0.5),
        "frame_pipeline_ms_p95": _percentile(latencies, 0.95),
        "inference_ms_p50": _percentile(inference_latencies, 0.5),
        "inference_ms_p95": _percentile(inference_latencies, 0.95),
        "class_observation_counts": dict(sorted(counts.items())),
        "interpretation": (
            "Synthetic benchmark is not evidence of camera or NPU performance."
            if settings.source == "synthetic" else
            "Read/inference processing times only; not sensor-to-display latency."
        ),
    }
