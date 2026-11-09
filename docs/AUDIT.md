# Offline image-space observation audit

The audit command connects the existing frame-source and detector adapters to a deterministic JSONL export. Its purpose is reproducible data quality review without storing raw camera images or enabling any physical control interface.

~~~bash
edgewatch audit --frames 60 --output runtime/audit_001.jsonl

# For a consented recorded video:
export EDGEWATCH_SOURCE=video
export EDGEWATCH_VIDEO=/path/to/consented_video.mp4
edgewatch audit --frames 300 --output runtime/audit_002.jsonl
~~~

If EDGEWATCH_DETECTOR is none, all prediction arrays are empty. This is correct: synthetic preview frames are not evidence of neural-network inference.

## Data contract

Each line contains a deterministic image_id, an array of class-filtered predicted normalized boxes, and a privacy-aware scalar image-quality summary. This export contains **no ground truth** and therefore cannot directly provide valid precision, recall or AP figures. A separate annotation process must supply truth before invoking the evaluator.

The output is written to a temporary file and published only after successful processing; previous audit outputs are never silently overwritten. The report includes a SHA256 digest of the JSONL file.

Masking happens before inference. Boxes intersecting masked rectangles are excluded. By default, no camera frames or raw images are written to disk.

## Limitations

This module is a passive frame-by-frame audit, not an object-identity tracker. It provides no trajectories, gimbal commands, autonomous targeting, geolocation, or aircraft control. Image quality flags are heuristics and require validation against field conditions.
