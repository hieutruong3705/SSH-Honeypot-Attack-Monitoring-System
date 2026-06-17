import asyncio
import os
import queue
import sys
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend.database import (
    get_map_data,
    get_malware_captures,
    get_recent_attacks,
    get_recent_sessions,
    get_session_commands,
    get_or_fetch_ip_location,
    get_stats,
    init_db,
    save_commands,
    save_session,
)

attack_queue: queue.Queue = queue.Queue()


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


async def _resolve_ip_location_and_broadcast(ip: str) -> None:
    location = await asyncio.to_thread(get_or_fetch_ip_location, ip)
    if not location:
        return

    await manager.broadcast({
        'type': 'ip_location_update',
        'data': {
            'ip': ip,
            'country': location.get('country'),
            'city': location.get('city'),
            'lat': location.get('lat'),
            'lon': location.get('lon'),
            'proxy_type': location.get('proxy_type'),
        },
    })


async def _process_queue() -> None:
    while True:
        try:
            event = attack_queue.get_nowait()
            event_type = event.get('type')

            await manager.broadcast(event)

            if event_type in ('attack', 'session_start'):
                ip = event['data'].get('ip')
                if ip:
                    asyncio.create_task(_resolve_ip_location_and_broadcast(ip))

            if event_type == 'session_end':
                data = event['data']
                save_session(data)
                if data.get('commands'):
                    save_commands(data['session_id'], data['commands'])

        except queue.Empty:
            pass
        await asyncio.sleep(0.1)


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


@app.websocket('/ws')
async def ws_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


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


@app.get('/api/map')
def api_map():
    return get_map_data()


@app.get('/api/malware')
def api_malware():
    return get_malware_captures(20)


_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
if os.path.isdir(_dist):
    app.mount('/', StaticFiles(directory=_dist, html=True), name='static')
