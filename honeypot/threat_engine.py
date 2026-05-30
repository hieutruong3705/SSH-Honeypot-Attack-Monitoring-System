"""
Threat scoring for both login attempts and shell commands.
No real command execution — purely heuristic scoring.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from datetime import datetime

# ── Login-time scoring ────────────────────────────────────────────────────────

_attempt_times: dict[str, list[float]] = defaultdict(list)
_lock = threading.Lock()

SENSITIVE_USERNAMES = {'root', 'admin', 'administrator', 'ubuntu', 'pi', 'vagrant', 'user', 'test'}
COMMON_PASSWORDS    = {'123456', 'password', 'admin', 'root', '12345', '12345678', 'qwerty', ''}


def _count_recent(ip: str, seconds: int = 60) -> int:
    cutoff = datetime.now().timestamp() - seconds
    with _lock:
        times = _attempt_times[ip]
        times[:] = [t for t in times if t > cutoff]
        return len(times)


def _record(ip: str) -> None:
    with _lock:
        _attempt_times[ip].append(datetime.now().timestamp())


def calculate_login_threat(ip: str, username: str, password: str) -> tuple[int, str]:
    recent = _count_recent(ip, seconds=60)
    _record(ip)

    score = 1  # base: failed / attempted login

    if username.lower() in SENSITIVE_USERNAMES:
        score += 5
    if password.lower() in COMMON_PASSWORDS:
        score += 2
    if recent > 5:   # brute-force pattern
        score += 30
    if recent > 10:  # high-frequency
        score += 20

    return score, _level(score)


# ── Command-time scoring ──────────────────────────────────────────────────────

COMMAND_SCORES: dict[str, int] = {
    'sudo':     10,
    'su':        8,
    'wget':     20,
    'curl':     20,
    'chmod':    20,
    'scp':      15,
    'ssh':      10,
    'nc':       25,
    'ncat':     25,
    'netcat':   25,
    'python':   15,
    'python3':  15,
    'perl':     15,
    'ruby':     15,
    'bash':     10,
    'sh':       10,
    'dash':     10,
    'rm':       10,
    'dd':       15,
    'passwd':   10,
    'useradd':  15,
    'usermod':  15,
    'crontab':  20,
    'at':       15,
    'nmap':     20,
    'masscan':  20,
    'hydra':    25,
    'john':     20,
    'hashcat':  20,
    'base64':   10,
    'cat':       2,  # low base; extra added for sensitive paths
}

SENSITIVE_PATHS = {'/etc/shadow', '/etc/passwd', '/root/.ssh/id_rsa', '/home/admin/config.txt'}


def score_command(cmd: str) -> int:
    if not cmd.strip():
        return 0

    parts = cmd.strip().split()
    name  = parts[0].lstrip('./')
    score = COMMAND_SCORES.get(name, 0)

    if name == 'chmod' and '+x' in cmd:
        score += 5

    if name == 'cat':
        for sp in SENSITIVE_PATHS:
            if sp in cmd:
                score += 15
                break

    if name in ('wget', 'curl'):
        if any(ext in cmd for ext in ('.sh', '.py', '.bin', '.elf', '.exe')):
            score += 10

    return score


def _level(score: int) -> str:
    if score > 80:   return 'CRITICAL'
    if score >= 51:  return 'HIGH'
    if score >= 21:  return 'MEDIUM'
    return 'LOW'


def level_from_score(score: int) -> str:
    return _level(score)
