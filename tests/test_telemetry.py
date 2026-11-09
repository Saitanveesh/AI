import json

from edgewatch.telemetry import Telemetry


def test_bounded_event_memory_and_jsonl(tmp_path):
    path = tmp_path / "events.jsonl"
    telemetry = Telemetry(str(path), history_size=4)
    for idx in range(9):
        telemetry.emit("test", "event", index=idx)
    assert len(telemetry.recent_events()) == 4
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(records) == 9
    telemetry.frame(12.5, 2)
    summary = telemetry.summary()
    assert summary["frames_processed"] == 1
    assert summary["detections_last_frame"] == 2
