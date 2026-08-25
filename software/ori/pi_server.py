"""Ori Raspberry Pi 3 API and control coordinator.

Run with: uvicorn software.ori.pi_server:app --host 0.0.0.0 --port 8000

Control sources are concurrent inputs, not mutually-exclusive modes. Auto-pilot
can remain active while browser or voice temporarily supplies a higher-priority
intent. Pico controllers remain responsible for real-time actuation/watchdogs.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from software.ori.core.control_sources import ControlArbiter
from software.ori.core.voice import parse_voice

app = FastAPI(title="Ori Pi API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

arbiter = ControlArbiter()
clients: set[WebSocket] = set()
state: dict[str, Any] = {
    "battery_percent": None,
    "feet": [False, False, False, False],
    "imu": {"status": "not_connected"},
    "joints": [{"id": i + 1, "position_deg": 0.0} for i in range(16)],
    "auto_pilot": {"enabled": False, "running": False},
    "camera": {"status": "not_configured", "transport": "webrtc"},
}


class Command(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: float | None = None


class SourceHeartbeat(BaseModel):
    source: str
    ttl_s: float = Field(default=1.5, ge=0.1, le=10.0)


class VoiceRequest(BaseModel):
    text: str


def snapshot() -> dict[str, Any]:
    selected = arbiter.select()
    return {
        "api_version": "1.0",
        "timestamp": time.time(),
        "safe": selected is not None and selected.source == "safety",
        "selected_source": selected.source if selected else None,
        **state,
    }


async def broadcast() -> None:
    message = snapshot()
    dead = []
    for ws in clients:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)


@app.get("/api/v1/status")
async def status() -> dict[str, Any]:
    return snapshot()


@app.post("/api/v1/command")
async def command(command: Command) -> dict[str, Any]:
    source = str(command.payload.pop("source", "browser")).lower()
    if source not in {"browser", "voice", "auto"}:
        raise HTTPException(400, "source must be browser, voice, or auto")

    if command.type == "safe":
        arbiter.safe()
    elif command.type == "auto_start":
        state["auto_pilot"].update(enabled=True, running=True)
        arbiter.submit("auto", "auto_hold", {}, ttl_s=3600)
    elif command.type == "auto_stop":
        state["auto_pilot"].update(enabled=False, running=False)
        arbiter.clear("auto")
    elif command.type in {"drive", "stand", "sit", "arm", "head", "tool", "look"}:
        selected = arbiter.select()
        if selected and selected.source == "safety":
            raise HTTPException(409, "Ori is safe; explicitly release safety first")
        ttl = 0.35 if command.type == "drive" else 2.0
        arbiter.submit(source, command.type, command.payload, ttl_s=ttl)
    else:
        raise HTTPException(400, f"unknown command: {command.type}")

    await broadcast()
    selected = arbiter.select()
    return {"accepted": True, "selected_source": selected.source if selected else None}


@app.post("/api/v1/voice")
async def voice(request: VoiceRequest) -> dict[str, Any]:
    parsed = parse_voice(request.text)
    if parsed is None:
        return {"accepted": False, "reason": "unrecognized", "text": request.text}
    command_type, payload = parsed
    payload["source"] = "voice"
    result = await command(Command(type=command_type, payload=payload))
    return {**result, "text": request.text, "intent": command_type}


@app.post("/api/v1/safe")
async def safe() -> dict[str, Any]:
    arbiter.safe()
    await broadcast()
    return {"accepted": True, "safe": True}


@app.post("/api/v1/safety/release")
async def release_safety() -> dict[str, Any]:
    arbiter.release_safe()
    await broadcast()
    return {"accepted": True, "safe": False}


@app.post("/api/v1/source/heartbeat")
async def source_heartbeat(heartbeat: SourceHeartbeat) -> dict[str, Any]:
    source = heartbeat.source.lower()
    if source not in {"browser", "voice", "auto"}:
        raise HTTPException(400, "invalid source")
    arbiter.submit(source, "heartbeat", {}, ttl_s=heartbeat.ttl_s)
    return {"accepted": True, "source": source}


@app.websocket("/api/v1/telemetry")
async def telemetry(websocket: WebSocket) -> None:
    await websocket.accept()
    clients.add(websocket)
    try:
        await websocket.send_json(snapshot())
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, Exception):
        clients.discard(websocket)


@app.get("/api/v1/camera/offer")
async def camera_offer() -> dict[str, Any]:
    raise HTTPException(503, "Camera transport is not configured yet")


@app.post("/api/v1/camera/answer")
async def camera_answer(_: dict[str, Any]) -> dict[str, Any]:
    raise HTTPException(503, "Camera transport is not configured yet")


async def telemetry_loop() -> None:
    while True:
        await broadcast()
        await asyncio.sleep(0.2)


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(telemetry_loop())
