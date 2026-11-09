import numpy as np

from edgewatch.inference import DisabledDetector, parse_hailo


def test_normalized_hailo_layout_and_allowlist():
    output = [
        np.asarray([[0.1, 0.2, 0.5, 0.6, 0.9]], dtype=np.float32),
        np.asarray([[0.2, 0.2, 0.3, 0.3, 0.99]], dtype=np.float32),
    ]
    boxes = parse_hailo(output, ["bird", "person"], 640, 480, 0.5,
                        frozenset(["bird"]), 4)
    assert len(boxes) == 1
    b = boxes[0]
    assert b.label == "bird"
    assert (b.x0, b.y0, b.x1, b.y1) == (128, 48, 384, 240)


def test_nonfinite_low_score_and_bad_shape_filtered():
    output = [np.asarray([[0.0, 0.0, 0.1, 0.1, float("nan")],
                          [0.0, 0.0, 0.0, 0.1, 0.9],
                          [0.0, 0.0, 0.5, 0.5, 0.1],
                          [0.0, 0.0, 0.5, 0.5, 0.8]])]
    result = parse_hailo(output, ["kite"], 320, 240, 0.5, frozenset(["kite"]), 4)
    assert len(result) == 1
    assert result[0].score == 0.8


def test_disabled_detector_emits_no_fake_detections():
    detector = DisabledDetector()
    detector.open()
    assert detector.detect(np.zeros((240, 320, 3), dtype=np.uint8)) == []
    detector.close()
