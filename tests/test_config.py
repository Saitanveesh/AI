import pytest

from edgewatch.config import Settings


def test_defaults_are_non_hardware_and_passive():
    s = Settings()
    assert s.source == "synthetic"
    assert s.detector == "none"
    assert s.save_snapshots is False


def test_hailo_requires_explicit_model_and_labels():
    with pytest.raises(ValueError):
        Settings(detector="hailo")


def test_video_requires_input():
    with pytest.raises(ValueError):
        Settings(source="video")


def test_privacy_masks_are_validated():
    s = Settings(mask_regions="0.1,0.2,0.3,0.6;0.8,0.8,1,1")
    assert len(s.privacy_masks) == 2
    with pytest.raises(ValueError):
        Settings(mask_regions="0.3,0.1,0.2,0.5")
    with pytest.raises(ValueError):
        Settings(mask_regions="a,b,c,d")
    with pytest.raises(ValueError):
        Settings(mask_regions="0.1,0.2,0.3")


def test_invalid_dimensions_and_score():
    with pytest.raises(ValueError):
        Settings(width=10)
    with pytest.raises(ValueError):
        Settings(min_score=2.0)
