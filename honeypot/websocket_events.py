"""
Bridge between synchronous honeypot threads and the async FastAPI broadcaster.
Puts typed event dicts into a thread-safe queue; backend/main.py drains it.
"""
from __future__ import annotations

import queue
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from honeypot.logger import ShellSession


class EventBus:
    def __init__(self, q: queue.Queue) -> None:
        self._q = q

    # ── Attack / login events ─────────────────────────────────────────────────

    def emit_attack(self, data: dict) -> None:
        self._q.put({'type': 'attack', 'data': data})

    # ── Session lifecycle events ──────────────────────────────────────────────

    def emit_session_start(self, session: 'ShellSession') -> None:
        self._q.put({'type': 'session_start', 'data': session.to_dict()})

    def emit_session_end(self, session: 'ShellSession', duration_seconds: int) -> None:
        data = session.to_dict()
        data['duration_seconds'] = duration_seconds
        data['commands'] = session.commands_as_dicts()
        self._q.put({'type': 'session_end', 'data': data})

    # ── Per-command events ────────────────────────────────────────────────────

    def emit_command(self, session: 'ShellSession', cmd: str, score_delta: int) -> None:
        last = session.commands[-1] if session.commands else None
        self._q.put({
            'type': 'session_command',
            'data': {
                'session_id':  session.session_id,
                'ip':          session.ip,
                'username':    session.username,
                'cmd':         cmd,
                'score_delta': score_delta,
                'threat_score':session.threat_score,
                'threat_level':session.threat_level,
                'timestamp':   last.timestamp if last else '',
            },
        })
