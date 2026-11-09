import json
import time

from edgewatch.config import Settings
from edgewatch.engine import ObservationEngine
from edgewatch.telemetry import Telemetry


def test_event_log_rotation_caps_disk_usage(tmp_path):
    path = tmp_path / "events.jsonl"
    t = Telemetry(str(path), history_size=3, max_file_bytes=320, backups=2)
    for idx in range(30):
        t.emit("quality", "test event", index=idx, detail="x" * 70)
    assert path.exists()
    assert len(t.recent_events()) == 3
    assert (tmp_path / "events.jsonl.1").exists()
    assert not (tmp_path / "events.jsonl.3").exists()
    assert path.stat().st_size <= 320
    for filename in tmp_path.glob("events.jsonl*"):
        for line in filename.read_text(encoding="utf-8").splitlines():
            assert json.loads(line)["kind"] == "quality"
    assert t.summary()["event_write_errors"] == 0


def test_freshness_is_explicit_and_expires(tmp_path):
    engine = ObservationEngine(Settings(width=320, height=240, fps=10,
                                        events_path=str(tmp_path / "e.jsonl")))
    assert engine.status()["frame_fresh"] is False
    engine.start()
    deadline = time.monotonic() + 3
    while engine.status()["sequence"] < 1 and time.monotonic() < deadline:
        time.sleep(0.02)
    assert engine.status()["sequence"] >= 1
    assert engine.status()["frame_fresh"] is True
    assert engine.status()["image_quality"]["available"] is True
    with engine._lock:
        engine._last_frame_mono -= 10.0
    assert engine.status()["frame_fresh"] is False
    engine.stop()
