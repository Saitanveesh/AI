"""Validated, immutable settings. The default configuration needs no camera or NPU."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool(value: str) -> bool:
    if value.strip().lower() in ("1", "true", "yes", "on"):
        return True
    if value.strip().lower() in ("0", "false", "no", "off"):
        return False
    raise ValueError("Expected a boolean environment variable")


@dataclass(frozen=True, slots=True)
class Settings:
    source: str = "synthetic"  # synthetic | video | picamera2
    video_path: str = ""
    detector: str = "none"     # none | hailo
    model_path: str = ""
    labels_path: str = ""
    width: int = 640
    height: int = 480
    fps: int = 15
    min_score: float = 0.55
    max_detections: int = 24
    allowed_labels: tuple[str, ...] = ("bird", "kite", "sports ball", "bicycle")
    mask_regions: str = ""    # semicolon-delimited normalized x0,y0,x1,y1
    events_path: str = "runtime/events.jsonl"
    jpeg_quality: int = 78
    session_dir: str = "runtime/sessions"
    save_snapshots: bool = False
    snapshot_every_s: int = 30
    snapshot_max_files: int = 200

    def __post_init__(self) -> None:
        if self.source not in ("synthetic", "video", "picamera2"):
            raise ValueError("Invalid source")
        if self.detector not in ("none", "hailo"):
            raise ValueError("Invalid detector")
        if self.source == "video" and not self.video_path:
            raise ValueError("video_path is required for video source")
        if self.detector == "hailo" and (not self.model_path or not self.labels_path):
            raise ValueError("Hailo requires both model_path and labels_path")
        if not (160 <= self.width <= 3840 and 120 <= self.height <= 2160):
            raise ValueError("Unsupported image dimensions")
        if not (1 <= self.fps <= 60):
            raise ValueError("fps must be 1..60")
        if not (0.0 <= self.min_score <= 1.0):
            raise ValueError("min_score must be 0..1")
        if not (1 <= self.max_detections <= 100):
            raise ValueError("max_detections must be 1..100")
        if not (40 <= self.jpeg_quality <= 95):
            raise ValueError("jpeg_quality must be 40..95")
        if self.snapshot_every_s < 1:
            raise ValueError("snapshot_every_s must be positive")
        if not (1 <= self.snapshot_max_files <= 10000):
            raise ValueError("snapshot_max_files must be 1..10000")
        for region in self.privacy_masks:
            if not (0 <= region[0] < region[2] <= 1 and
                    0 <= region[1] < region[3] <= 1):
                raise ValueError("Invalid normalized privacy mask")

    @property
    def privacy_masks(self) -> tuple[tuple[float, float, float, float], ...]:
        if not self.mask_regions.strip():
            return ()
        try:
            regions = tuple(tuple(float(v) for v in entry.split(","))
                            for entry in self.mask_regions.split(";") if entry.strip())
        except (ValueError, TypeError) as exc:
            raise ValueError("Malformed privacy mask") from exc
        if any(len(region) != 4 for region in regions):
            raise ValueError("Each privacy mask needs four coordinates")
        return regions

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ
        return cls(
            source=env.get("EDGEWATCH_SOURCE", "synthetic").strip(),
            video_path=env.get("EDGEWATCH_VIDEO", ""),
            detector=env.get("EDGEWATCH_DETECTOR", "none").strip(),
            model_path=env.get("EDGEWATCH_MODEL", ""),
            labels_path=env.get("EDGEWATCH_LABELS", ""),
            width=int(env.get("EDGEWATCH_WIDTH", "640")),
            height=int(env.get("EDGEWATCH_HEIGHT", "480")),
            fps=int(env.get("EDGEWATCH_FPS", "15")),
            min_score=float(env.get("EDGEWATCH_MIN_SCORE", "0.55")),
            max_detections=int(env.get("EDGEWATCH_MAX_DETECTIONS", "24")),
            allowed_labels=tuple(x.strip().lower() for x in
                env.get("EDGEWATCH_ALLOWED_LABELS",
                        "bird,kite,sports ball,bicycle").split(",") if x.strip()),
            mask_regions=env.get("EDGEWATCH_PRIVACY_MASKS", ""),
            events_path=env.get("EDGEWATCH_EVENTS", "runtime/events.jsonl"),
            jpeg_quality=int(env.get("EDGEWATCH_JPEG_QUALITY", "78")),
            session_dir=env.get("EDGEWATCH_SESSION_DIR", "runtime/sessions"),
            save_snapshots=_bool(env.get("EDGEWATCH_SAVE_SNAPSHOTS", "false")),
            snapshot_every_s=int(env.get("EDGEWATCH_SNAPSHOT_INTERVAL", "30")),
            snapshot_max_files=int(env.get("EDGEWATCH_SNAPSHOT_MAX_FILES", "200")),
        )

    def validate_inputs(self) -> None:
        if self.source == "video" and not Path(self.video_path).is_file():
            raise FileNotFoundError("Video input is unavailable")
        if self.detector == "hailo":
            if not Path(self.model_path).is_file():
                raise FileNotFoundError("Hailo HEF model is unavailable")
            if not Path(self.labels_path).is_file():
                raise FileNotFoundError("Hailo labels file is unavailable")
