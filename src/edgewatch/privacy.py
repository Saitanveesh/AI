"""Privacy masking happens before inference, overlays, streaming and storage."""
from __future__ import annotations

import cv2
import numpy as np


def apply_masks(
    frame: np.ndarray,
    regions: tuple[tuple[float, float, float, float], ...],
) -> np.ndarray:
    if not regions:
        return frame
    masked = frame.copy()
    height, width = frame.shape[:2]
    for x0, y0, x1, y1 in regions:
        cv2.rectangle(masked, (round(x0 * width), round(y0 * height)),
                      (round(x1 * width), round(y1 * height)), (0, 0, 0), -1)
    return masked


def overlaps_privacy(
    det: object, regions: tuple[tuple[float, float, float, float], ...],
    width: int, height: int,
) -> bool:
    for x0, y0, x1, y1 in regions:
        if det.x0 < x1 * width and det.x1 > x0 * width and \
           det.y0 < y1 * height and det.y1 > y0 * height:
            return True
    return False
