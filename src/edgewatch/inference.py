"""Passive object detection adapter for officially supported Hailo Picamera2 APIs.

This module emits image-space boxes only. No target acquisition, pursuit,
future-location estimate, steering command, or hardware control is exposed.
"""
from __future__ import annotations

from typing import Protocol

import cv2
import numpy as np

from .config import Settings
from .models import Detection


class Detector(Protocol):
    def open(self) -> None: ...
    def detect(self, frame: np.ndarray) -> list[Detection]: ...
    def close(self) -> None: ...


class DisabledDetector:
    def open(self) -> None:
        pass

    def detect(self, frame: np.ndarray) -> list[Detection]:
        return []

    def close(self) -> None:
        pass


def parse_hailo(
    output: object,
    labels: list[str],
    frame_width: int,
    frame_height: int,
    min_score: float,
    allowed: frozenset[str],
    limit: int,
) -> list[Detection]:
    """Parse the official Hailo postprocessed [class][N, 5] layout.

    Detection coordinates are normalized in y0,x0,y1,x1 order.
    Bad rows are ignored, never extrapolated.
    """
    result: list[Detection] = []
    for class_id, rows in enumerate(output):
        if class_id >= len(labels):
            continue
        label = labels[class_id].strip().lower()
        if label not in allowed:
            continue
        for row in rows:
            if len(row) < 5:
                continue
            y0, x0, y1, x1, score = (float(v) for v in row[:5])
            if not all(np.isfinite(v) for v in (x0, y0, x1, y1, score)):
                continue
            if score < min_score:
                continue
            a, b, c, d = (
                round(max(0, min(1, x0)) * frame_width),
                round(max(0, min(1, y0)) * frame_height),
                round(max(0, min(1, x1)) * frame_width),
                round(max(0, min(1, y1)) * frame_height),
            )
            if c <= a or d <= b:
                continue
            result.append(Detection(label, round(score, 4), a, b, c, d))
    result.sort(key=lambda det: det.score, reverse=True)
    return result[:limit]


class HailoDetector:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.device = None
        self.model_size = None
        self.labels: list[str] = []

    def open(self) -> None:
        try:
            from picamera2.devices import Hailo
        except ImportError as exc:
            raise RuntimeError(
                "Hailo Picamera2 bindings missing; install and validate official Pi packages"
            ) from exc
        self.labels = [line.strip() for line in open(
            self.settings.labels_path, encoding="utf-8").read().splitlines()]
        if not any(self.labels):
            raise ValueError("Empty labels file")
        device = Hailo(self.settings.model_path)
        try:
            height, width, channels = device.get_input_shape()
            if channels != 3:
                raise ValueError("Expected a three-channel Hailo model")
            self.model_size = (int(width), int(height))
        except Exception:
            device.close()
            raise
        self.device = device

    def detect(self, frame: np.ndarray) -> list[Detection]:
        if self.device is None or self.model_size is None:
            raise RuntimeError("Detector is not open")
        rgb = cv2.cvtColor(cv2.resize(frame, self.model_size),
                           cv2.COLOR_BGR2RGB)
        output = self.device.run(np.ascontiguousarray(rgb))
        return parse_hailo(
            output, self.labels, frame.shape[1], frame.shape[0],
            self.settings.min_score, frozenset(self.settings.allowed_labels),
            self.settings.max_detections,
        )

    def close(self) -> None:
        if self.device is not None:
            self.device.close()
            self.device = None


def make_detector(settings: Settings) -> Detector:
    return HailoDetector(settings) if settings.detector == "hailo" else DisabledDetector()
