import numpy as np

from edgewatch.models import Detection
from edgewatch.privacy import apply_masks, overlaps_privacy


def test_masks_do_not_mutate_input():
    image = np.full((100, 100, 3), 255, dtype=np.uint8)
    masked = apply_masks(image, ((0, 0, 0.5, 0.5),))
    assert masked[10, 10].tolist() == [0, 0, 0]
    assert image[10, 10].tolist() == [255, 255, 255]
    assert masked[90, 90].tolist() == [255, 255, 255]


def test_overlap_rejects_observations_in_sensitive_region():
    det = Detection("bird", 0.95, 8, 8, 30, 30)
    assert overlaps_privacy(det, ((0, 0, 0.2, 0.2),), 100, 100)
    assert not overlaps_privacy(det, ((0.7, 0.7, 1, 1),), 100, 100)
