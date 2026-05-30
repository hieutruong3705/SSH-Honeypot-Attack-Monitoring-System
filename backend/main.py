import asyncio
import queue
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend.database import (
    init_db, get_recent_attacks, get_stats,
    get_recent_sessions, get_session_commands,
    save_session, save_commands,
)

attack_queue: queue.Queue = queue.Queue()


# ── WebSocket connection manager ──────────────────────────────────────────────

class ConnectionManager:
    def __init__(self) -> None:
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict) -> None:
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


# ── Queue processor — drains honeypot events into WebSocket ──────────────────

async def _process_queue() -> None:
    while True:
        try:
            event = attack_queue.get_nowait()
            event_type = event.get('type')

            # Always broadcast to dashboard
            await manager.broadcast(event)

            # Persist completed sessions to DB
            if event_type == 'session_end':
                data = event['data']
                save_session(data)
                if data.get('commands'):
                    save_commands(data['session_id'], data['commands'])

        except queue.Empty:
            pass
        await asyncio.sleep(0.1)


# ── App lifecycle ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(_process_queue())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@app.websocket('/ws')
async def ws_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.get('/api/attacks')
def api_attacks():
    return get_recent_attacks(50)


@app.get('/api/stats')
def api_stats():
    return get_stats()


@app.get('/api/sessions')
def api_sessions():
    return get_recent_sessions(20)


@app.get('/api/sessions/{session_id}/commands')
def api_session_commands(session_id: str):
    return get_session_commands(session_id)


# ── Serve built frontend (production) ────────────────────────────────────────

_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
if os.path.isdir(_dist):
    app.mount('/', StaticFiles(directory=_dist, html=True), name='static')
