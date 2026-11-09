# Offline object-detection evaluation

This module objectively compares **image-space object detections** with independent manually annotated frame data. It does not track individual objects through time, compute movement paths, aim a camera, or control an aircraft.

## Annotation format

Supply one JSON object per line, with a unique image_id, a truth array, and a predictions array. Bounding boxes are normalized x0,y0,x1,y1, values from 0 to 1. Prediction confidence is from 0 to 1. An empty array is allowed for frames with no objects or predictions.

~~~json
{"image_id":"scene-a-001","truth":[{"label":"bicycle","bbox":[0.1,0.2,0.5,0.8]}],"predictions":[{"label":"bicycle","bbox":[0.11,0.2,0.5,0.79],"score":0.9}]}
{"image_id":"scene-a-002","truth":[],"predictions":[]}
~~~

All input must be consented and suitable for passive observation. Avoid biometric identity or incidental personal data.

## Execute

~~~bash
edgewatch evaluate --dataset examples/evaluation/sample.jsonl
edgewatch evaluate --dataset /path/to/independent_annotations.jsonl --iou 0.5 --confidence 0.6
~~~

The command is entirely offline and does not load the camera or Hailo accelerator.

## Definitions and interpretation

- TP, FP, FN use one-to-one, class-aware, image-local assignment at the specified intersection-over-union threshold. Duplicate predictions count as false positives.
- Precision, recall and F1 are reported at the selected confidence threshold.
- AP uses the 101-point interpolated precision-recall curve over all prediction confidences at the fixed IoU threshold. mAP averages classes that have ground truth. Classes with zero GT have null AP and are excluded from the mean, though their predictions count toward micro false positives.
- The input SHA256 makes evaluation input traceable across builds.

Inputs are resource-limited: maximum 50 MB per file, 10,000 frames by default, 200 ground-truth and 200 predicted boxes per frame. Invalid, nonfinite or non-normalized coordinates cause a hard failure rather than silent correction.

## Model qualification practice

Create multiple independent, stratified datasets: daylight/shade, motion blur, object size, varied backgrounds, and object-free negative controls. Never evaluate only on training images. This evaluator produces bounding-box quality metrics only; its outputs cannot validate track identity, target lock, gimbal boresight accuracy, hardware FPS, or deployment certification.

The supplied sample fixture is manually constructed to exercise the evaluator. It is **not** evidence of model quality.
