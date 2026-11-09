import time

from fastapi.testclient import TestClient

from edgewatch.api import create_app
from edgewatch.config import Settings


def test_local_read_only_api(tmp_path):
    settings = Settings(width=320, height=240, fps=20,
                        events_path=str(tmp_path / "events.jsonl"))
    app = create_app(settings)
    with TestClient(app) as client:
        assert client.get("/api/v1/health/live").json()["alive"] is True
        assert client.get("/").status_code == 200
        status = client.get("/api/v1/status")
        assert status.status_code == 200
        assert "weapon_interface" in status.json()
        assert client.get("/api/v1/events").status_code == 200
        assert client.post("/api/v1/command").status_code == 404
        deadline = time.monotonic() + 3
        response = client.get("/api/v1/frame.jpg")
        while response.status_code != 200 and time.monotonic() < deadline:
            time.sleep(0.05)
            response = client.get("/api/v1/frame.jpg")
        assert response.status_code == 200
        assert response.content[:2] == b"\xff\xd8"
