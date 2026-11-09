import json

import numpy as np
import pytest

from edgewatch.audit import export_observations
from edgewatch.config import Settings
from edgewatch.models import Detection


class Frames:
    def __init__(self, _):
        self.n = 0
    def open(self):
        pass
    def read(self):
        self.n += 1
        return np.full((240, 320, 3), 128, dtype=np.uint8) if self.n <= 3 else None
    def close(self):
        pass


class Stub:
    def open(self):
        pass
    def detect(self, _):
        return [Detection("bicycle", .9, 12, 10, 62, 80),
                Detection("person", .99, 90, 40, 130, 170)]
    def close(self):
        pass


class Faulty(Frames):
    def read(self):
        raise RuntimeError("Simulated frame read failure")


def test_audit_export_is_atomic_and_cannot_invent_ground_truth(tmp_path):
    settings = Settings(width=320, height=240)
    output = tmp_path / "audit.jsonl"
    result = export_observations(settings, str(output), max_frames=8,
                                 source_factory=Frames, detector_factory=lambda _: Stub())
    assert result["frames"] == 3
    assert result["observations"] == 3
    assert result["annotated_ground_truth"] is False
    data = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(data) == 3
    assert all(len(d["predictions"]) == 1 for d in data)
    assert all(d["predictions"][0]["label"] == "bicycle" for d in data)
    assert all("truth" not in d for d in data)
    assert all("quality" in d for d in data)
    assert len(result["output_sha256"]) == 64
    with pytest.raises(FileExistsError):
        export_observations(settings, str(output), source_factory=Frames,
                            detector_factory=lambda _: Stub())


def test_failed_audit_never_publishes_partial_output(tmp_path):
    dest = tmp_path / "failed.jsonl"
    with pytest.raises(RuntimeError, match="Simulated"):
        export_observations(Settings(width=320, height=240), str(dest),
                            source_factory=Faulty, detector_factory=lambda _: Stub())
    assert not dest.exists()
    assert list(tmp_path.glob(".edgewatch-audit-*")) == []


def test_audit_enforces_privacy_masks(tmp_path):
    dest = tmp_path / "privacy.jsonl"
    settings = Settings(width=320, height=240, mask_regions="0,0,0.5,0.5")
    result = export_observations(settings, str(dest), source_factory=Frames,
                                 detector_factory=lambda _: Stub())
    assert result["frames"] == 3
    assert result["observations"] == 0
