import numpy as np

from edgewatch.quality import assess_image_quality


def test_low_light_is_identified_without_imaging_hardware():
    frame = np.zeros((160, 320, 3), dtype=np.uint8)
    result = assess_image_quality(frame)
    assert result["available"]
    assert "low_light" in result["warnings"]
    assert "low_spatial_detail" in result["warnings"]


def test_overexposure_is_reported():
    frame = np.full((240, 320, 3), 255, dtype=np.uint8)
    result = assess_image_quality(frame)
    assert "high_exposure" in result["warnings"]


def test_masked_pixels_not_counted_as_darkness():
    frame = np.full((100, 200, 3), 160, dtype=np.uint8)
    frame[:, :100] = 0
    result = assess_image_quality(frame, ((0, 0, 0.5, 1),))
    assert result["brightness_mean_0_255"] > 150
    assert "low_light" not in result["warnings"]


def test_fully_masked_frame_is_unavailable():
    frame = np.full((64, 64, 3), 128, dtype=np.uint8)
    result = assess_image_quality(frame, ((0, 0, 1, 1),))
    assert not result["available"]
    assert result["warnings"] == ["insufficient_unmasked_area"]


def test_quality_never_modifies_caller_array():
    frame = np.random.default_rng(123).integers(0, 255, (120, 180, 3), dtype=np.uint8)
    original = frame.copy()
    assess_image_quality(frame, ((0.1, 0.2, 0.5, 0.7),))
    assert np.array_equal(frame, original)
