import time

from edgewatch.config import Settings
from edgewatch.engine import ObservationEngine


def test_synthetic_observation_end_to_end(tmp_path):
    settings = Settings(width=320, height=240, fps=30,
                        events_path=str(tmp_path / "events.jsonl"))
    engine = ObservationEngine(settings)
    engine.start()
    time.sleep(0.45)
    engine.stop()
    state = engine.status()
    sequence, jpeg = engine.latest_jpeg()
    assert sequence >= 2
    assert jpeg is not None and jpeg.startswith(b"\xff\xd8")
    assert state["frames_processed"] >= 2
    assert state["state"] == "stopped"
    assert state["remote_actuation"] is False
    assert state["aircraft_control"] is False
    assert (tmp_path / "events.jsonl").exists()


def test_start_is_idempotent_and_stop_is_safe(tmp_path):
    settings = Settings(width=320, height=240, events_path=str(tmp_path / "e.jsonl"))
    engine = ObservationEngine(settings)
    engine.start()
    engine.start()
    time.sleep(0.2)
    engine.stop()
    engine.stop()
    assert engine.status()["state"] == "stopped"
