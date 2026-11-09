"""Atomic, reproducible export of passive image-space model observations.

Exports per-frame box observations and scalar image QA, never raw images,
target identity, trajectories, world locations, or movement commands.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np

from .config import Settings
from .inference import make_detector
from .privacy import apply_masks, overlaps_privacy
from .quality import assess_image_quality
from .sources import make_source


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_observations(
    settings: Settings,
    output_path: str,
    max_frames: int = 300,
    source_factory=make_source,
    detector_factory=make_detector,
) -> dict:
    """Export bounded observations; atomically publish only complete output."""
    if not 1 <= max_frames <= 10000:
        raise ValueError("Frame limit must be between 1 and 10000")
    settings.validate_inputs()
    destination = Path(output_path).expanduser().resolve()
    if settings.source == "video" and Path(settings.video_path).resolve() == destination:
        raise ValueError("Output cannot overwrite input video")
    if settings.detector == "hailo" and destination in (
        Path(settings.model_path).resolve(), Path(settings.labels_path).resolve()
    ):
        raise ValueError("Output cannot overwrite model or label files")
    if destination.exists():
        raise FileExistsError("Refusing to overwrite an existing audit")
    destination.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(prefix=".edgewatch-audit-", suffix=".tmp",
                                     dir=destination.parent)
    os.close(fd)
    temporary = Path(temp_name)
    source = source_factory(settings)
    detector = detector_factory(settings)
    source_open = detector_open = False
    frames = observed = quality_warnings = 0
    try:
        source.open()
        source_open = True
        detector.open()
        detector_open = True
        with temporary.open("w", encoding="utf-8", newline="\n") as output:
            while frames < max_frames:
                raw = source.read()
                if raw is None:
                    break
                if not isinstance(raw, np.ndarray) or raw.ndim != 3 \
                   or raw.shape[2] != 3 or raw.dtype != np.uint8:
                    raise ValueError("Source returned an invalid BGR frame")
                frame = apply_masks(raw, settings.privacy_masks)
                detections = detector.detect(frame)
                allowed = set(settings.allowed_labels)
                selected = [d for d in detections
                            if d.label in allowed and d.score >= settings.min_score
                            and not overlaps_privacy(
                                d, settings.privacy_masks, frame.shape[1], frame.shape[0])]
                quality = assess_image_quality(frame, settings.privacy_masks)
                quality_warnings += int(bool(quality["warnings"]))
                record = {
                    "image_id": f"frame-{frames + 1:06d}",
                    "predictions": [
                        {
                            "label": d.label,
                            "score": d.score,
                            "bbox": [
                                round(d.x0 / frame.shape[1], 6),
                                round(d.y0 / frame.shape[0], 6),
                                round(d.x1 / frame.shape[1], 6),
                                round(d.y1 / frame.shape[0], 6),
                            ],
                        } for d in selected
                    ],
                    "quality": quality,
                }
                output.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
                observed += len(selected)
                frames += 1
        if frames == 0:
            raise ValueError("Source had no frames; audit output was not published")
        # Prevent replacing a destination that appeared while the audit was running.
        # On POSIX, link() fails with EEXIST instead of silently overwriting.
        os.link(temporary, destination)
        temporary.unlink(missing_ok=True)
        return {
            "schema": "edgewatch.audit.v1",
            "source": settings.source,
            "detector": settings.detector,
            "output": str(destination),
            "output_sha256": _sha256(destination),
            "frames": frames,
            "observations": observed,
            "frames_with_quality_warnings": quality_warnings,
            "annotated_ground_truth": False,
            "note": "Boxes and image-quality metrics only; independent truth is required for evaluation.",
        }
    finally:
        if detector_open:
            detector.close()
        if source_open:
            source.close()
        temporary.unlink(missing_ok=True)
