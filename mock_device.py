#!/usr/bin/env python3
"""CyboPal ONE FastAPI hardware simulator + live visual dashboard.

    python3 mock_device.py
    open http://127.0.0.1:5000/
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from cybopal.cameras import render_base, render_bezel
from cybopal.device import CyboPalSim, LIMITS, PRESETS

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

sim = CyboPalSim()


@asynccontextmanager
async def lifespan(app: FastAPI):
    sim.set_mode("tracking")
    sim.display_markdown = (
        "# CyboPal ONE simulator\n\n"
        "Firmware **FOLLOW** is on. The arm is tracking the simulated user.\n\n"
        "Attach Hermes with `python3 agent_core.py` or drive it from this panel."
    )
    sim.pauli_text = "FOLLOW"
    yield


app = FastAPI(title="CyboPal ONE Hardware Simulator", version="0.2.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")

_clients: set[WebSocket] = set()


class ControlPayload(BaseModel):
    """Recipe-compatible payload plus the extra 6-DOF fields."""

    tilt: float | None = None
    pan: float | None = None
    height_mm: float | None = None
    reach_mm: float | None = None
    roll: float | None = None
    elbow: float | None = None
    display_markdown: str | None = None
    pauli_text: str | None = None
    mode: str | None = None


class ModePayload(BaseModel):
    mode: str = Field(..., examples=["tracking", "sit", "stand", "recline", "wave", "estop", "idle"])


@app.get("/", response_class=HTMLResponse)
def dashboard() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/v1/health")
def health() -> dict[str, Any]:
    return {"ok": True, "device": "cybopal-one-sim", "mode": sim.mode}


@app.get("/api/v1/limits")
def limits() -> dict[str, Any]:
    return {"limits": LIMITS, "presets": {k: v.as_dict() for k, v in PRESETS.items()}}


@app.get("/api/v1/telemetry")
def get_telemetry() -> dict[str, Any]:
    snap = sim.snapshot()
    return {"status": snap["status"], "hardware_state": snap}


@app.post("/api/v1/control")
async def control_hardware(payload: ControlPayload) -> dict[str, Any]:
    snap = sim.apply_control(
        pan=payload.pan,
        tilt=payload.tilt,
        height_mm=payload.height_mm,
        reach_mm=payload.reach_mm,
        roll=payload.roll,
        elbow=payload.elbow,
        display_markdown=payload.display_markdown,
        pauli_text=payload.pauli_text,
        mode=payload.mode,
        source="agent" if payload.mode is None else "api",
    )
    await _broadcast(snap)
    return {"status": "SUCCESS", "current_state": snap}


@app.post("/api/v1/mode")
async def set_mode(payload: ModePayload) -> dict[str, Any]:
    sim.set_mode(payload.mode)
    snap = sim.snapshot()
    await _broadcast(snap)
    return {"status": "SUCCESS", "current_state": snap}


@app.get("/api/v1/camera/frame")
@app.get("/api/v1/camera/bezel")
def camera_bezel() -> Response:
    return Response(content=render_bezel(sim), media_type="image/jpeg")


@app.get("/api/v1/camera/base")
def camera_base() -> Response:
    return Response(content=render_base(sim), media_type="image/jpeg")


def _mjpeg(renderer):
    async def gen():
        while True:
            frame = renderer(sim)
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            await asyncio.sleep(1 / 18)

    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/api/v1/camera/bezel.mjpeg")
def bezel_mjpeg():
    return _mjpeg(render_bezel)


@app.get("/api/v1/camera/base.mjpeg")
def base_mjpeg():
    return _mjpeg(render_base)


@app.websocket("/ws/telemetry")
async def ws_telemetry(ws: WebSocket) -> None:
    await ws.accept()
    _clients.add(ws)
    try:
        await ws.send_text(json.dumps(sim.snapshot()))
        while True:
            await asyncio.sleep(1 / 20)
            await ws.send_text(json.dumps(sim.snapshot()))
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(ws)


async def _broadcast(snap: dict[str, Any]) -> None:
    dead: list[WebSocket] = []
    payload = json.dumps(snap)
    for ws in list(_clients):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _clients.discard(ws)


if __name__ == "__main__":
    import os
    import uvicorn

    uvicorn.run(
        "mock_device:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        reload=False,
    )
