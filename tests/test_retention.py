import pytest

from edgewatch.config import Settings
from edgewatch.engine import ObservationEngine


def test_snapshot_retention_limits_file_count(tmp_path):
    directory = tmp_path / "snapshots"
    settings = Settings(
        width=320, height=240, save_snapshots=True,
        snapshot_every_s=1, snapshot_max_files=2,
        session_dir=str(directory),
        events_path=str(tmp_path / "e.jsonl"),
    )
    engine = ObservationEngine(settings)
    for step in range(6):
        engine._snapshot(b"synthetic-jpeg-payload", now=20 + 2 * step)
    files = list(directory.glob("snapshot_*.jpg"))
    assert len(files) == 2
    assert all(path.read_bytes() == b"synthetic-jpeg-payload" for path in files)


def test_snapshot_quota_rejects_invalid_configuration():
    with pytest.raises(ValueError, match="snapshot_max_files"):
        Settings(snapshot_max_files=0)
    with pytest.raises(ValueError, match="snapshot_max_files"):
        Settings(snapshot_max_files=10001)


def test_snapshots_remain_off_by_default(tmp_path):
    settings = Settings(session_dir=str(tmp_path / "snapshots"),
                        events_path=str(tmp_path / "e.jsonl"))
    engine = ObservationEngine(settings)
    engine._snapshot(b"data", now=10)
    assert not (tmp_path / "snapshots").exists()
