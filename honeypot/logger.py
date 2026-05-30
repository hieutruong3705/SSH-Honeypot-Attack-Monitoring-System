"""Session and command data classes. No I/O — pure data."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class CommandEntry:
    cmd:         str
    timestamp:   str
    score_delta: int


@dataclass
class ShellSession:
    session_id:      str
    ip:              str
    username:        str
    password:        str
    login_time:      str
    cwd:             str
    commands:        list[CommandEntry] = field(default_factory=list)
    command_history: list[str]         = field(default_factory=list)
    threat_score:    int               = 0
    threat_level:    str               = 'LOW'
    should_exit:     bool              = False

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def new(cls, ip: str, username: str, password: str,
            base_score: int, base_level: str) -> 'ShellSession':
        return cls(
            session_id  = uuid.uuid4().hex[:12],
            ip          = ip,
            username    = username,
            password    = password,
            login_time  = datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            cwd         = '/root' if username == 'root' else f'/home/{username}',
            threat_score= base_score,
            threat_level= base_level,
        )

    # ── Mutations ─────────────────────────────────────────────────────────────

    def add_command(self, cmd: str, score_delta: int) -> None:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.commands.append(CommandEntry(cmd=cmd, timestamp=ts, score_delta=score_delta))
        if cmd:
            self.command_history.append(cmd)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            'session_id':    self.session_id,
            'ip':            self.ip,
            'username':      self.username,
            'password':      self.password,
            'login_time':    self.login_time,
            'cwd':           self.cwd,
            'threat_score':  self.threat_score,
            'threat_level':  self.threat_level,
            'command_count': len(self.commands),
        }

    def commands_as_dicts(self) -> list[dict]:
        return [
            {'cmd': c.cmd, 'time': c.timestamp, 'score_delta': c.score_delta}
            for c in self.commands
        ]
