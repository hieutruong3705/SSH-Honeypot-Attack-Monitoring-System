"""
SSH honeypot server.

Accepts all password logins, records the attempt, then drops the attacker
into a FakeShell â€” an emulated Bash session that executes nothing real.
"""
from __future__ import annotations

import queue
import socket
import threading
from datetime import datetime

import paramiko

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.database import save_attack
from honeypot.fake_shell import FakeShell
from honeypot.logger import ShellSession
from honeypot.telegram_service import send_login_alert
from honeypot.threat_engine import calculate_login_threat
from honeypot.websocket_events import EventBus


def _handle_client(sock: socket.socket, ip: str,
                   host_key: paramiko.RSAKey, bus: EventBus) -> None:

    class _Server(paramiko.ServerInterface):
        def __init__(self) -> None:
            self.session: ShellSession | None = None
            self._shell_ready = threading.Event()

        # â”€â”€ Auth â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        def check_auth_password(self, username: str, password: str) -> int:
            remote_ver = transport.remote_version or "Unknown"
            cipher = getattr(transport, 'remote_cipher', 'N/A')
            mac = getattr(transport, 'remote_mac', 'N/A')
            kex = getattr(transport, 'kex_engine', None)
            kex_name = kex.name if kex else 'N/A'
            comp = getattr(transport, 'remote_compression', 'N/A')

            fingerprint = f"{remote_ver} | {kex_name} | {cipher} | {mac} | {comp}"

            now   = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            score, level, tool = calculate_login_threat(ip, username, password, fingerprint)
            save_attack(ip, username, password, now, score, level, fingerprint, tool)

            self.session = ShellSession.new(ip, username, password, score, level)
            self.session.fingerprint = fingerprint
            self.session.client_tool = tool

            attack = {
                'ip': ip, 'username': username, 'password': password,
                'timestamp': now, 'threat_score': score, 'threat_level': level,
                'fingerprint': fingerprint, 'client_tool': tool
            }
            bus.emit_attack(attack)

            threading.Thread(target=send_login_alert, args=(attack,), daemon=True).start()
            print(f'[{now}] LOGIN  {level:8s} | {ip:15s} | {username}/{password} | {tool}')
            return paramiko.AUTH_SUCCESSFUL

        def check_auth_publickey(self, username, key):
            return paramiko.AUTH_FAILED   # reject key auth silently

        def get_allowed_auths(self, username: str) -> str:
            return 'password'

        # â”€â”€ Channel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        def check_channel_request(self, kind: str, chanid: int) -> int:
            if kind == 'session':
                return paramiko.OPEN_SUCCEEDED
            return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

        def check_channel_pty_request(self, channel, term, width, height,
                                      pixelwidth, pixelheight, modes) -> bool:
            return True

        def check_channel_shell_request(self, channel) -> bool:
            self._shell_ready.set()
            return True

        def check_channel_exec_request(self, channel, command) -> bool:
            return False

    transport = paramiko.Transport(sock)
    transport.add_server_key(host_key)
    srv = _Server()

    try:
        transport.start_server(server=srv)

        chan = transport.accept(timeout=30)
        if chan is None:
            return

        # Wait until the client sends a "shell" request
        if not srv._shell_ready.wait(timeout=10):
            chan.close()
            return

        if srv.session is None:
            chan.close()
            return

        FakeShell(chan, srv.session, bus).run()

    except Exception:
        pass
    finally:
        try:
            transport.close()
        except Exception:
            pass


def start_honeypot(host: str = '0.0.0.0', port: int = 2222,
                   attack_queue: queue.Queue | None = None) -> None:
    bus = EventBus(attack_queue if attack_queue is not None else queue.Queue())

    srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv_sock.bind((host, port))
    srv_sock.listen(100)

    host_key = paramiko.RSAKey.generate(2048)
    print(f'[*] SSH Honeypot (fake-shell mode) on {host}:{port}')

    while True:
        try:
            client_sock, addr = srv_sock.accept()
            threading.Thread(
                target=_handle_client,
                args=(client_sock, addr[0], host_key, bus),
                daemon=True,
            ).start()
        except Exception as e:
            print(f'[!] Accept error: {e}')
