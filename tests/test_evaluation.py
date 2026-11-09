import json
import math

import pytest

from edgewatch.evaluation import _average_precision, _iou, evaluate_file


def _write(tmp_path, rows):
    path = tmp_path / "dataset.jsonl"
    path.write_text("\n".join(json.dumps(x) for x in rows) + "\n", encoding="utf-8")
    return str(path)


def test_iou_is_symmetric_bounded():
    a = (0, 0, .5, .5)
    b = (.25, .25, .75, .75)
    assert _iou(a, a) == 1
    assert math.isclose(_iou(a, b), _iou(b, a))
    assert _iou(a, (.5, .5, 1, 1)) == 0


def test_duplicate_predictions_are_false_positives(tmp_path):
    rows = [
        {"image_id": "a", "truth": [{"label": "bicycle", "bbox": [0, 0, .5, .5]}],
         "predictions": [{"label": "bicycle", "bbox": [0, 0, .5, .5], "score": .95},
                         {"label": "bicycle", "bbox": [0, 0, .5, .5], "score": .8}]},
        {"image_id": "b", "truth": [{"label": "bicycle", "bbox": [.5, .5, 1, 1]}],
         "predictions": [{"label": "bicycle", "bbox": [.5, .5, 1, 1], "score": .7}]},
    ]
    result = evaluate_file(_write(tmp_path, rows))
    stats = result["per_class"]["bicycle"]
    assert result["images"] == 2
    assert (stats["true_positive"], stats["false_positive"], stats["false_negative"]) == (2, 1, 0)
    assert stats["precision"] == 0.66667
    assert stats["recall"] == 1.0
    assert 0.8 < stats["ap_101"] < 0.85
    assert result["map_101"] == stats["ap_101"]


def test_incorrect_class_cannot_match_truth(tmp_path):
    result = evaluate_file(_write(tmp_path, [{
        "image_id": "a", "truth": [{"label": "ball", "bbox": [0, 0, 1, 1]}],
        "predictions": [{"label": "bicycle", "bbox": [0, 0, 1, 1], "score": .99}],
    }]))
    assert result["micro"]["true_positive"] == 0
    assert result["micro"]["false_positive"] == 1
    assert result["micro"]["false_negative"] == 1
    assert result["per_class"]["bicycle"]["ap_101"] is None
    assert result["per_class"]["ball"]["ap_101"] == 0


def test_confidence_threshold_does_not_change_ap(tmp_path):
    path = _write(tmp_path, [{
        "image_id": "a", "truth": [{"label": "ball", "bbox": [0, 0, .5, .5]}],
        "predictions": [{"label": "ball", "bbox": [0, 0, .5, .5], "score": .4}],
    }])
    high = evaluate_file(path, confidence_threshold=.5)
    low = evaluate_file(path, confidence_threshold=.3)
    assert high["micro"]["true_positive"] == 0
    assert low["micro"]["true_positive"] == 1
    assert high["map_101"] == low["map_101"] == 1.0


def test_invalid_datasets_rejected(tmp_path):
    with pytest.raises(ValueError, match="duplicate image_id"):
        evaluate_file(_write(tmp_path, [
            {"image_id": "a", "truth": [], "predictions": []},
            {"image_id": "a", "truth": [], "predictions": []},
        ]))
    with pytest.raises(ValueError, match="invalid normalized"):
        evaluate_file(_write(tmp_path, [{
            "image_id": "a", "truth": [{"label": "ball", "bbox": [-.1, 0, .5, 1]}],
            "predictions": [],
        }]))
    with pytest.raises(ValueError, match="score must be finite"):
        evaluate_file(_write(tmp_path, [{
            "image_id": "a", "truth": [],
            "predictions": [{"label": "ball", "bbox": [0, 0, 1, 1],
                             "score": float("nan")}],
        }]))
    with pytest.raises(ValueError, match="frame-count limit"):
        evaluate_file(_write(tmp_path, [
            {"image_id": "a", "truth": [], "predictions": []},
            {"image_id": "b", "truth": [], "predictions": []},
        ]), max_frames=1)


def test_empty_ground_truth_and_ap_boundaries(tmp_path):
    result = evaluate_file(_write(tmp_path, [
        {"image_id": "a", "truth": [], "predictions": []},
    ]))
    assert result["map_101"] is None
    assert result["micro"]["precision"] is None
    assert result["per_class"] == {}
    assert _average_precision([1, 1], 2) == 1
    assert _average_precision([], 1) == 0
    assert _average_precision([1], 0) is None
