import numpy as np

from edgewatch.benchmark import _percentile, benchmark
from edgewatch.config import Settings


class SampleSource:
    def __init__(self, settings):
        self.n = 0
    def open(self):
        pass
    def read(self):
        self.n += 1
        return np.zeros((240, 320, 3), dtype=np.uint8) if self.n <= 3 else None
    def close(self):
        pass


class EmptyDetector:
    def open(self):
        pass
    def detect(self, frame):
        return []
    def close(self):
        pass


def test_offline_benchmark_is_bounded_and_has_provenance():
    settings = Settings(width=320, height=240)
    result = benchmark(
        settings, max_frames=6,
        source_factory=SampleSource,
        detector_factory=lambda _: EmptyDetector(),
    )
    assert result["schema"] == "edgewatch.benchmark.v1"
    assert result["frames_processed"] == 3
    assert result["frames_requested"] == 6
    assert result["synthetic"]
    assert result["model_sha256"] is None
    assert result["class_observation_counts"] == {}


def test_percentiles_are_defined_on_empty_and_sorted_data():
    assert _percentile([], 0.95) == 0
    assert _percentile([100.0, 1.0, 4.0], 0.5) == 4.0
