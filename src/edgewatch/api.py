"""Local-only, read-only HTTP API and MJPEG operator dashboard."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from importlib.resources import files

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse

from .config import Settings
from .engine import ObservationEngine


def create_app(settings: Settings | None = None, engine: ObservationEngine | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    runtime = engine or ObservationEngine(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime.start()
        yield
        runtime.stop()

    app = FastAPI(
        title="EdgeWatch Observer",
        description="Passive, read-only image-space observation service",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.runtime = runtime

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def homepage():
        return files("edgewatch").joinpath("static/index.html").read_text(encoding="utf-8")

    @app.get("/api/v1/health/live")
    async def liveness():
        return {"alive": True}

    @app.get("/api/v1/health/ready")
    async def readiness():
        state = runtime.status()
        if state["state"] != "observing" or not state["frame_fresh"]:
            raise HTTPException(status_code=503, detail={
                "state": state["state"], "frame_fresh": state["frame_fresh"]})
        return {"ready": True}

    @app.get("/api/v1/status")
    async def status():
        return runtime.status()

    @app.get("/api/v1/events")
    async def events():
        return {"events": runtime.telemetry.recent_events()[-100:]}

    @app.get("/api/v1/frame.jpg")
    async def frame():
        _, jpeg = runtime.latest_jpeg()
        if jpeg is None or not runtime.status()["frame_fresh"]:
            raise HTTPException(status_code=503, detail="No image available")
        return Response(jpeg, media_type="image/jpeg",
                        headers={"Cache-Control": "no-store"})

    @app.get("/api/v1/stream.mjpeg")
    async def stream(request: Request):
        async def frames():
            last = -1
            while not await request.is_disconnected():
                seq, jpeg = runtime.latest_jpeg()
                if jpeg is not None and seq != last and runtime.status()["frame_fresh"]:
                    last = seq
                    yield (b"--frame\r\nContent-Type: image/jpeg\r\n" +
                           b"Content-Length: " + str(len(jpeg)).encode() +
                           b"\r\n\r\n" + jpeg + b"\r\n")
                await asyncio.sleep(0.04)
        return StreamingResponse(
            frames(),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={"Cache-Control": "no-cache, no-store",
                     "X-Content-Type-Options": "nosniff"},
        )

    return app
