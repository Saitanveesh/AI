"""Replaceable image sources with deterministic resource cleanup."""
from __future__ import annotations

import math
from typing import Protocol

import cv2
import numpy as np

from .config import Settings


class FrameSource(Protocol):
    def open(self) -> None: ...
    def read(self) -> np.ndarray | None: ...
    def close(self) -> None: ...


class SyntheticSource:
    """Clearly synthetic test imagery. No fabricated AI detections are produced."""

    def __init__(self, settings: Settings):
        self.width = settings.width
        self.height = settings.height
        self.index = 0
        self.started = False

    def open(self) -> None:
        self.index = 0
        self.started = True

    def read(self) -> np.ndarray:
        if not self.started:
            raise RuntimeError("Source has not been opened")
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        frame[:] = (25, 33, 45)
        x = round(self.width * (0.5 + 0.34 * math.sin(self.index / 19)))
        y = round(self.height * (0.5 + 0.25 * math.cos(self.index / 29)))
        cv2.circle(frame, (x, y), 18, (95, 196, 126), -1)
        cv2.putText(frame, "SYNTHETIC TEST FEED - NO AI INFERENCE",
                    (14, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (216, 231, 240), 1)
        self.index += 1
        return frame

    def close(self) -> None:
        self.started = False


class VideoSource:
    def __init__(self, settings: Settings):
        self.path = settings.video_path
        self.width = settings.width
        self.height = settings.height
        self.capture = None

    def open(self) -> None:
        self.capture = cv2.VideoCapture(self.path)
        if not self.capture.isOpened():
            raise RuntimeError("Could not open video input")

    def read(self) -> np.ndarray | None:
        if self.capture is None:
            raise RuntimeError("Source has not been opened")
        ok, frame = self.capture.read()
        if not ok:
            return None  # End of recording is a clean terminal event.
        return cv2.resize(frame, (self.width, self.height))

    def close(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None


class PiCameraSource:
    def __init__(self, settings: Settings):
        self.width = settings.width
        self.height = settings.height
        self.fps = settings.fps
        self.camera = None

    def open(self) -> None:
        try:
            from picamera2 import Picamera2
        except ImportError as exc:
            raise RuntimeError("Picamera2 missing: install python3-picamera2 via apt") from exc
        camera = Picamera2()
        try:
            config = camera.create_video_configuration(
                main={"size": (self.width, self.height), "format": "RGB888"},
                controls={"FrameRate": self.fps},
            )
            camera.configure(config)
            camera.start()
        except Exception:
            camera.close()
            raise
        self.camera = camera

    def read(self) -> np.ndarray:
        if self.camera is None:
            raise RuntimeError("Camera is not open")
        rgb = self.camera.capture_array("main")
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    def close(self) -> None:
        if self.camera is not None:
            self.camera.stop()
            self.camera.close()
            self.camera = None


def make_source(settings: Settings) -> FrameSource:
    if settings.source == "synthetic":
        return SyntheticSource(settings)
    if settings.source == "video":
        return VideoSource(settings)
    return PiCameraSource(settings)
