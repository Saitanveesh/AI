"""Deterministic offline evaluation for passive image-space detections.

Class-aware, image-local box matching only. No trajectories, motion prediction,
geospatial outputs, target priority, or actuator interfaces.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path


def _box(raw: object, context: str) -> tuple[float, float, float, float]:
    if not isinstance(raw, list) or len(raw) != 4:
        raise ValueError(f"{context}: expected four normalized bbox coordinates")
    if any(isinstance(v, bool) or not isinstance(v, (int, float))
           or not math.isfinite(v) for v in raw):
        raise ValueError(f"{context}: bbox coordinates must be finite numbers")
    x0, y0, x1, y1 = (float(v) for v in raw)
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise ValueError(f"{context}: invalid normalized bounding box")
    return x0, y0, x1, y1


def _item(raw: object, context: str, prediction: bool) -> dict:
    if not isinstance(raw, dict):
        raise ValueError(f"{context}: object expected")
    label = raw.get("label")
    if not isinstance(label, str) or not (1 <= len(label) <= 64) or not label.strip():
        raise ValueError(f"{context}: label must be a short nonempty string")
    result = {"label": label.strip().lower(), "bbox": _box(raw.get("bbox"), context)}
    if prediction:
        score = raw.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) \
           or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError(f"{context}: score must be finite and in [0,1]")
        result["score"] = float(score)
    return result


def _iou(a: tuple[float, float, float, float],
         b: tuple[float, float, float, float]) -> float:
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    intersection = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    a_area = (a[2] - a[0]) * (a[3] - a[1])
    b_area = (b[2] - b[0]) * (b[3] - b[1])
    union = a_area + b_area - intersection
    return intersection / union if union else 0.0


def _ratio(a: int, b: int) -> float | None:
    return round(a / b, 5) if b else None


def _f1(p: float | None, r: float | None) -> float | None:
    if p is None or r is None:
        return None
    return round(2 * p * r / (p + r), 5) if p + r else 0.0


def _average_precision(decisions: list[int], total_truth: int) -> float | None:
    """101-point interpolated AP at a fixed IoU threshold."""
    if not total_truth:
        return None
    tp = 0
    points = []
    for n, correct in enumerate(decisions, start=1):
        tp += correct
        points.append((tp / total_truth, tp / n))
    return round(sum(
        max((precision for recall, precision in points if recall >= i / 100.0),
            default=0.0) for i in range(101)) / 101, 5)


def _scores(rows: list[dict], iou_threshold: float,
            confidence_threshold: float) -> dict:
    truth = defaultdict(dict)
    pred = defaultdict(list)
    for row in rows:
        image_id = row["image_id"]
        grouped = defaultdict(list)
        for item in row["truth"]:
            grouped[item["label"]].append(item["bbox"])
        for label, boxes in grouped.items():
            truth[label][image_id] = boxes
        for index, item in enumerate(row["predictions"]):
            pred[item["label"]].append((item["score"], image_id, index, item["bbox"]))

    classes = {}
    tp_all = fp_all = fn_all = 0
    aps = []
    for label in sorted(set(truth) | set(pred)):
        candidates = sorted(pred.get(label, []), key=lambda item: (-item[0], item[1], item[2]))
        taken = set()
        decisions = []
        tp = fp = 0
        total_truth = sum(len(boxes) for boxes in truth.get(label, {}).values())
        for score, image_id, _, predicted_box in candidates:
            best_overlap, best_index = 0.0, None
            for index, actual_box in enumerate(truth.get(label, {}).get(image_id, [])):
                if (image_id, index) in taken:
                    continue
                overlap = _iou(predicted_box, actual_box)
                if overlap > best_overlap:
                    best_overlap, best_index = overlap, index
            hit = int(best_index is not None and best_overlap >= iou_threshold)
            if hit:
                taken.add((image_id, best_index))
            decisions.append(hit)
            if score >= confidence_threshold:
                tp += hit
                fp += 1 - hit
        fn = total_truth - tp
        precision = _ratio(tp, tp + fp)
        recall = _ratio(tp, total_truth)
        ap = _average_precision(decisions, total_truth)
        if ap is not None:
            aps.append(ap)
        classes[label] = {
            "ground_truth": total_truth, "predictions": len(candidates),
            "true_positive": tp, "false_positive": fp, "false_negative": fn,
            "precision": precision, "recall": recall, "f1": _f1(precision, recall),
            "ap_101": ap,
        }
        tp_all += tp
        fp_all += fp
        fn_all += fn

    p = _ratio(tp_all, tp_all + fp_all)
    r = _ratio(tp_all, tp_all + fn_all)
    return {
        "per_class": classes,
        "micro": {
            "true_positive": tp_all, "false_positive": fp_all,
            "false_negative": fn_all, "precision": p,
            "recall": r, "f1": _f1(p, r),
        },
        "map_101": round(sum(aps) / len(aps), 5) if aps else None,
        "ap_included_classes": len(aps),
    }


def evaluate_file(
    path: str, iou_threshold: float = 0.5, confidence_threshold: float = 0.5,
    max_frames: int = 10000, max_file_bytes: int = 50_000_000,
) -> dict:
    """Strictly validate bounded JSONL, then score independent annotations."""
    if not (0 < iou_threshold <= 1):
        raise ValueError("IoU threshold must be in (0,1]")
    if not (0 <= confidence_threshold <= 1):
        raise ValueError("Confidence threshold must be in [0,1]")
    if not (1 <= max_frames <= 50000 and max_file_bytes >= 100):
        raise ValueError("Invalid evaluation resource limits")
    source = Path(path)
    if source.stat().st_size > max_file_bytes:
        raise ValueError("Evaluation exceeds file-size limit")

    digest = hashlib.sha256()
    rows = []
    seen = set()
    with source.open("rb") as handle:
        for lineno, raw in enumerate(handle, start=1):
            digest.update(raw)
            if not raw.strip():
                continue
            if len(raw) > 100_000:
                raise ValueError(f"line {lineno}: record too large")
            if len(rows) >= max_frames:
                raise ValueError("Evaluation exceeds frame-count limit")
            try:
                record = json.loads(raw)
            except (ValueError, UnicodeDecodeError) as exc:
                raise ValueError(f"line {lineno}: invalid JSON") from exc
            if not isinstance(record, dict):
                raise ValueError(f"line {lineno}: object expected")
            image_id = record.get("image_id")
            if not isinstance(image_id, str) or not 1 <= len(image_id) <= 128:
                raise ValueError(f"line {lineno}: invalid image_id")
            if image_id in seen:
                raise ValueError(f"line {lineno}: duplicate image_id")
            seen.add(image_id)
            gt, predicted = record.get("truth"), record.get("predictions")
            if not isinstance(gt, list) or not isinstance(predicted, list):
                raise ValueError(f"line {lineno}: truth and predictions must be lists")
            if len(gt) > 200 or len(predicted) > 200:
                raise ValueError(f"line {lineno}: too many boxes")
            rows.append({
                "image_id": image_id,
                "truth": [_item(x, f"line {lineno} truth[{i}]", False)
                          for i, x in enumerate(gt)],
                "predictions": [_item(x, f"line {lineno} predictions[{i}]", True)
                                for i, x in enumerate(predicted)],
            })
    if not rows:
        raise ValueError("Annotation dataset contains no frames")
    return {
        "schema": "edgewatch.evaluation.v1",
        "dataset_sha256": digest.hexdigest(),
        "images": len(rows),
        "iou_threshold": float(iou_threshold),
        "confidence_threshold": float(confidence_threshold),
        "ap_definition": "101-point interpolation at fixed IoU over all confidences",
        **_scores(rows, iou_threshold, confidence_threshold),
        "caveats": [
            "Results describe only the supplied annotations.",
            "Precision/recall apply to predictions at or above confidence threshold.",
            "AP considers all scores and excludes classes without ground truth.",
            "Tracking, sensor latency and Pi/Hailo performance are not evaluated.",
        ],
    }
