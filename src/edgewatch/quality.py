"""Low-cost, explainable frame-quality indicators for passive camera QA.

The outputs are heuristics, not image-quality ground truth. Masked areas do not
contribute to brightness or spatial-detail measurements.
"""
from __future__ import annotations

import cv2
import numpy as np


def assess_image_quality(
    frame: np.ndarray,
    excluded_regions: tuple[tuple[float, float, float, float], ...] = (),
    max_width: int = 256,
) -> dict:
    """Return bounded, non-identifying scalar measurements from a BGR image.

    The input is read-only to the caller. Privacy rectangles are excluded
    and their boundaries are excluded from the Laplacian measurement.
    """
    if frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8:
        raise ValueError("Expected a uint8, three-channel BGR image")
    if not (32 <= max_width <= 1024):
        raise ValueError("Invalid quality sampling resolution")

    height, width = frame.shape[:2]
    scale = min(1.0, max_width / max(1, width))
    if scale < 1.0:
        resized = cv2.resize(frame, (max(1, round(width * scale)),
                                     max(1, round(height * scale))),
                             interpolation=cv2.INTER_AREA)
    else:
        resized = frame
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    valid = np.ones((h, w), dtype=np.uint8)
    for x0, y0, x1, y1 in excluded_regions:
        left, right = round(x0 * w), round(x1 * w)
        top, bottom = round(y0 * h), round(y1 * h)
        valid[top:bottom, left:right] = 0

    available_count = int(np.count_nonzero(valid))
    if available_count < max(16, int(0.01 * h * w)):
        return {
            "available": False, "warnings": ["insufficient_unmasked_area"],
            "unmasked_fraction": round(available_count / (h * w), 4),
        }

    intensities = gray[valid.astype(bool)]
    brightness = float(np.mean(intensities))
    dark_fraction = float(np.mean(intensities <= 20))
    clipped_fraction = float(np.mean(intensities >= 245))

    # Eroding the mask prevents artificial edges at privacy-region boundaries
    # from inflating the apparent detail metric.
    safe_valid = cv2.erode(valid, np.ones((3, 3), np.uint8), iterations=1)
    detail_samples = cv2.Laplacian(gray, cv2.CV_32F)[safe_valid.astype(bool)]
    detail = float(np.var(detail_samples)) if detail_samples.size else 0.0

    warnings = []
    if brightness < 45.0 or dark_fraction > 0.45:
        warnings.append("low_light")
    if brightness > 210.0 or clipped_fraction > 0.35:
        warnings.append("high_exposure")
    if detail < 45.0:
        warnings.append("low_spatial_detail")

    return {
        "available": True,
        "brightness_mean_0_255": round(brightness, 2),
        "dark_fraction": round(dark_fraction, 4),
        "clipped_fraction": round(clipped_fraction, 4),
        "laplacian_variance": round(detail, 2),
        "unmasked_fraction": round(available_count / (h * w), 4),
        "warnings": warnings,
    }
