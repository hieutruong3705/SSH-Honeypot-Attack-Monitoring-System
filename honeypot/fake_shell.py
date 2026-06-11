"""
Fake interactive SSH shell.

Reads bytes from a Paramiko channel and emulates a Bash-like session.
NEVER executes any OS command; all responses are emulated strings.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime

import paramiko

from honeypot.command_handler import CommandRegistry
from honeypot.logger import ShellSession
from honeypot.telegram_service import send_shell_alert
from honeypot.threat_engine import level_from_score, score_command
from honeypot.virtual_fs import VirtualFS
from honeypot.websocket_events import EventBus


_BANNER = (
    "\r\n"
    "Welcome to Ubuntu 20.04.6 LTS (GNU/Linux 5.15.0-91-generic x86_64)\r\n"
    "\r\n"
    " * Documentation:  https://help.ubuntu.com\r\n"
    " * Management:     https://landscape.canonical.com\r\n"
    " * Support:        https://ubuntu.com/advantage\r\n"
    "\r\n"
    "  System information as of Thu May 29 17:30:00 UTC 2026\r\n"
    "\r\n"
    "  System load:  0.12               Processes:              98\r\n"
    "  Usage of /:   74.8% of 19.76GB   Users logged in:         1\r\n"
    "  Memory usage: 52%                IPv4 address for eth0: 192.168.1.10\r\n"
    "\r\n"
    "Last login: Thu May 29 16:00:00 2026 from 192.168.1.50\r\n"
    "\r\n"
)


class FakeShell:
    """Handles one attacker session. Runs blocking in its own thread."""

    def __init__(self, channel: paramiko.Channel, session: ShellSession, bus: EventBus) -> None:
        self._chan = channel
        self._session = session
        self._bus = bus
        self._fs = VirtualFS()
        self._registry = CommandRegistry(self._fs)
        self._buf = ""
        self._cursor = 0
        self._esc_buf = ""

    def run(self) -> None:
        start = time.time()
        self._send(_BANNER)
        self._send(self._prompt())
        self._bus.emit_session_start(self._session)

        while not self._session.should_exit:
            try:
                data = self._chan.recv(1024)
            except Exception:
                break
            if not data:
                break

            for byte in data:
                self._handle_byte(byte)
                if self._session.should_exit:
                    break

        duration = int(time.time() - start)
        self._bus.emit_session_end(self._session, duration)
        try:
            self._chan.close()
        except Exception:
            pass

    def _prompt(self) -> str:
        cwd = self._session.cwd
        home = "/root" if self._session.username == "root" else f"/home/{self._session.username}"
        display = "~" if cwd == home else cwd
        char = "#" if self._session.username == "root" else "$"
        return f"{self._session.username}@ubuntu-server:{display}{char} "

    def _send(self, text: str) -> None:
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")
        try:
            self._chan.send(text)
        except Exception:
            pass

    def _handle_byte(self, byte: int) -> None:
        ch = chr(byte)

        if self._esc_buf:
            self._consume_escape(ch)
            return

        if ch in ("\r", "\n"):
            line = self._buf.strip()
            self._send("\r\n")
            self._buf = ""
            self._cursor = 0
            self._execute_line(line)
            if not self._session.should_exit:
                self._send(self._prompt())
            return

        if byte in (127, 8):
            self._backspace()
            return

        if ch == "\x01":  # Ctrl-A
            self._move_cursor(-self._cursor)
            self._cursor = 0
            return

        if ch == "\x03":  # Ctrl-C
            self._buf = ""
            self._cursor = 0
            self._send("^C\r\n" + self._prompt())
            return

        if ch == "\x04":  # Ctrl-D
            self._session.should_exit = True
            return

        if ch == "\x05":  # Ctrl-E
            self._move_cursor(len(self._buf) - self._cursor)
            self._cursor = len(self._buf)
            return

        if ch == "\x15":  # Ctrl-U
            self._clear_current_line()
            return

        if ch == "\x1b":
            self._esc_buf = ch
            return

        if byte == 9:  # Tab
            return

        if byte >= 32:
            self._insert_text(ch)

    def _consume_escape(self, ch: str) -> None:
        self._esc_buf += ch
        seq = self._esc_buf

        if seq in ("\x1b[D", "\x1bOD"):
            if self._cursor > 0:
                self._move_cursor(-1)
                self._cursor -= 1
            self._esc_buf = ""
            return

        if seq in ("\x1b[C", "\x1bOC"):
            if self._cursor < len(self._buf):
                self._move_cursor(1)
                self._cursor += 1
            self._esc_buf = ""
            return

        if seq in ("\x1b[H", "\x1bOH"):
            self._move_cursor(-self._cursor)
            self._cursor = 0
            self._esc_buf = ""
            return

        if seq in ("\x1b[F", "\x1bOF"):
            self._move_cursor(len(self._buf) - self._cursor)
            self._cursor = len(self._buf)
            self._esc_buf = ""
            return

        if seq == "\x1b[3~":
            self._delete_forward()
            self._esc_buf = ""
            return

        if len(seq) > 2 and "@" <= ch <= "~":
            self._esc_buf = ""

    def _insert_text(self, text: str) -> None:
        if self._cursor == len(self._buf):
            self._buf += text
            self._cursor += len(text)
            self._send(text)
            return

        self._buf = self._buf[:self._cursor] + text + self._buf[self._cursor:]
        tail = self._buf[self._cursor:]
        self._cursor += len(text)
        self._send(tail)
        self._move_cursor(-(len(tail) - len(text)))

    def _backspace(self) -> None:
        if self._cursor == 0:
            return
        self._buf = self._buf[: self._cursor - 1] + self._buf[self._cursor :]
        self._cursor -= 1
        tail = self._buf[self._cursor :]
        self._send("\b" + tail + " ")
        self._move_cursor(-(len(tail) + 1))

    def _delete_forward(self) -> None:
        if self._cursor >= len(self._buf):
            return
        self._buf = self._buf[: self._cursor] + self._buf[self._cursor + 1 :]
        tail = self._buf[self._cursor :]
        self._send(tail + " ")
        self._move_cursor(-(len(tail) + 1))

    def _clear_current_line(self) -> None:
        total = len(self._buf)
        self._move_cursor(-self._cursor)
        self._send(" " * total)
        self._move_cursor(-total)
        self._buf = ""
        self._cursor = 0

    def _move_cursor(self, offset: int) -> None:
        if offset > 0:
            self._send(f"\x1b[{offset}C")
        elif offset < 0:
            self._send(f"\x1b[{-offset}D")

    def _execute_line(self, line: str) -> None:
        for cmd in self._split_commands(line):
            self._execute(cmd)
            if self._session.should_exit:
                break

    @staticmethod
    def _split_commands(line: str) -> list[str]:
        commands: list[str] = []
        current: list[str] = []
        quote = ""
        escape = False
        i = 0

        while i < len(line):
            ch = line[i]

            if escape:
                current.append(ch)
                escape = False
                i += 1
                continue

            if ch == "\\":
                current.append(ch)
                escape = True
                i += 1
                continue

            if quote:
                current.append(ch)
                if ch == quote:
                    quote = ""
                i += 1
                continue

            if ch in ("'", '"'):
                quote = ch
                current.append(ch)
                i += 1
                continue

            if line.startswith("&&", i) or line.startswith("||", i):
                cmd = "".join(current).strip()
                if cmd:
                    commands.append(cmd)
                current = []
                i += 2
                continue

            if ch in ";|":
                cmd = "".join(current).strip()
                if cmd:
                    commands.append(cmd)
                current = []
                i += 1
                continue

            current.append(ch)
            i += 1

        cmd = "".join(current).strip()
        if cmd:
            commands.append(cmd)
        return commands

    def _execute(self, cmd: str) -> None:
        if not cmd:
            return

        delta = score_command(cmd)
        self._session.threat_score += delta
        self._session.threat_level = level_from_score(self._session.threat_score)
        self._session.add_command(cmd, delta)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"[{now}] CMD    {self._session.threat_level:8s} | "
            f"{self._session.ip:15s} | {self._session.username} | {cmd}",
            flush=True,
        )

        self._bus.emit_command(self._session, cmd, delta)

        if delta > 0:
            threading.Thread(
                target=send_shell_alert,
                args=(
                    self._session.session_id,
                    self._session.ip,
                    self._session.username,
                    cmd,
                    self._session.threat_score,
                    self._session.threat_level,
                ),
                daemon=True,
            ).start()

        response = self._registry.handle(cmd, self._session)
        if not response:
            return

        if response.startswith("\x1b[2J"):
            self._send(response)
        else:
            self._send(response + "\r\n")
