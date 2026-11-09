# Reproducible passive vision benchmarking

The benchmark command processes a bounded sample of an existing authorized video, synthetic sequence, or physical camera. It measures **aggregate image-processing throughput**, not target pursuit quality or pointing precision.

~~~bash
# Synthetic software sanity check:
edgewatch benchmark --frames 300

# Authorized recorded clip:
export EDGEWATCH_SOURCE=video
export EDGEWATCH_VIDEO=/absolute/path/to/clip.mp4
edgewatch benchmark --frames 1000 > benchmark.json

# Hailo model (on verified Raspberry Pi):
export EDGEWATCH_DETECTOR=hailo
export EDGEWATCH_MODEL=/absolute/path/to/model.hef
export EDGEWATCH_LABELS=/absolute/path/to/labels.txt
edgewatch benchmark --frames 1000 > pi_hailo_benchmark.json
~~~

## Report contract

schema=edgewatch.benchmark.v1; includes source, detector, image dimensions, optional SHA256 digests of the model/labels/video, host architecture, frames processed/requested, elapsed wall time, throughput, pipeline p50/p95, inference p50/p95 and per-allowlisted-class observation counts.

No individual object coordinates or movement paths are retained by the benchmark.

## Quality control

Compare runs only when source, OS, camera settings, HEF checksum, class labels, frame sampling, temperature and power conditions are recorded. Synthetic benchmark numbers cannot be compared with camera or accelerator throughput.

This reports host-side capture and inference timing, **not exposure-to-display latency**. Accurate end-to-end latency needs additional camera timestamp validation.
