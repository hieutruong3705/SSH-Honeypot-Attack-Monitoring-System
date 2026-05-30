"""
Fake interactive SSH shell.

Reads bytes from a Paramiko channel and emulates a Bash-like session.
NEVER executes any OS command — all responses are emulated strings.
"""
from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING

import paramiko

from honeypot.command_handler import CommandRegistry
from honeypot.logger import ShellSession
from honeypot.threat_engine import score_command, level_from_score
from honeypot.virtual_fs import VirtualFS
from honeypot.websocket_events import EventBus
from honeypot.telegram_service import send_shell_alert

if TYPE_CHECKING:
    pass

# ── Login banner ──────────────────────────────────────────────────────────────

_BANNER = (
    '\r\n'
    'Welcome to Ubuntu 20.04.6 LTS (GNU/Linux 5.15.0-91-generic x86_64)\r\n'
    '\r\n'
    ' * Documentation:  https://help.ubuntu.com\r\n'
    ' * Management:     https://landscape.canonical.com\r\n'
    ' * Support:        https://ubuntu.com/advantage\r\n'
    '\r\n'
    '  System information as of Thu May 29 17:30:00 UTC 2026\r\n'
    '\r\n'
    '  System load:  0.12               Processes:              98\r\n'
    '  Usage of /:   74.8% of 19.76GB   Users logged in:         1\r\n'
    '  Memory usage: 52%                IPv4 address for eth0: 192.168.1.10\r\n'
    '\r\n'
    'Last login: Thu May 29 16:00:00 2026 from 192.168.1.50\r\n'
    '\r\n'
)


class FakeShell:
    """Handles one attacker session. Runs blocking in its own thread."""

    def __init__(self, channel: paramiko.Channel, session: ShellSession, bus: EventBus) -> None:
        self._chan     = channel
        self._session  = session
        self._bus      = bus
        self._fs       = VirtualFS()
        self._registry = CommandRegistry(self._fs)
        self._buf      = ''          # current line buffer

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self) -> None:
        start = time.time()
        self._send(_BANNER)
        self._send(self._prompt())
        self._bus.emit_session_start(self._session)

        while not self._session.should_exit:
            try:
                data = self._chan.recv(256)
            except Exception:
                break
            if not data:
                break

            for byte in data:
                ch = chr(byte)

                if ch in ('\r', '\n'):
                    self._send('\r\n')
                    self._execute(self._buf.strip())
                    self._buf = ''
                    if not self._session.should_exit:
                        self._send(self._prompt())

                elif byte in (127, 8):            # DEL / Backspace
                    if self._buf:
                        self._buf = self._buf[:-1]
                        self._send('\b \b')

                elif ch == '\x03':                # Ctrl-C
                    self._buf = ''
                    self._send('^C\r\n' + self._prompt())

                elif ch == '\x04':                # Ctrl-D  (EOF)
                    self._session.should_exit = True
                    break

                elif ch == '\x1b':                # ESC / arrow keys — discard
                    pass

                elif byte >= 32:                  # printable character
                    self._buf += ch
                    self._send(ch)                # echo back

        duration = int(time.time() - start)
        self._bus.emit_session_end(self._session, duration)
        try:
            self._chan.close()
        except Exception:
            pass

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _prompt(self) -> str:
        cwd = self._session.cwd
        home = '/root' if self._session.username == 'root' else f'/home/{self._session.username}'
        display = '~' if cwd == home else cwd
        char    = '#' if self._session.username == 'root' else '$'
        return f'{self._session.username}@ubuntu-server:{display}{char} '

    def _send(self, text: str) -> None:
        # Normalise line endings for terminal compatibility
        text = text.replace('\r\n', '\n').replace('\n', '\r\n')
        try:
            self._chan.send(text)
        except Exception:
            pass

    def _execute(self, cmd: str) -> None:
        if not cmd:
            return

        # Score and record
        delta = score_command(cmd)
        self._session.threat_score += delta
        self._session.threat_level  = level_from_score(self._session.threat_score)
        self._session.add_command(cmd, delta)

        # Broadcast and alert
        self._bus.emit_command(self._session, cmd, delta)

        if delta > 0:
            threading.Thread(
                target=send_shell_alert,
                args=(self._session.session_id, self._session.ip,
                      self._session.username, cmd,
                      self._session.threat_score, self._session.threat_level),
                daemon=True,
            ).start()

        # Get fake response
        response = self._registry.handle(cmd, self._session)

        if not response:
            return

        # ANSI clear — send raw without extra newline
        if response.startswith('\x1b[2J'):
            self._send(response)
        else:
            self._send(response + '\r\n')
