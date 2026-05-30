from collections import defaultdict
from datetime import datetime
import threading

_attempt_times: dict[str, list] = defaultdict(list)
_lock = threading.Lock()

SENSITIVE_USERNAMES = {'root', 'admin', 'administrator', 'ubuntu', 'pi', 'vagrant', 'user'}
COMMON_PASSWORDS = {'123456', 'password', 'admin', 'root', '12345', '12345678', 'qwerty', ''}


def _count_recent(ip: str, seconds: int = 60) -> int:
    cutoff = datetime.now().timestamp() - seconds
    with _lock:
        times = _attempt_times[ip]
        times[:] = [t for t in times if t > cutoff]
        return len(times)


def _record(ip: str):
    with _lock:
        _attempt_times[ip].append(datetime.now().timestamp())


def calculate_threat(ip: str, username: str, password: str) -> tuple[int, str]:
    recent = _count_recent(ip, seconds=60)
    _record(ip)

    score = 1  # base: failed login

    if username.lower() in SENSITIVE_USERNAMES:
        score += 5

    if password.lower() in COMMON_PASSWORDS:
        score += 2

    # brute force pattern: >5 attempts/minute
    if recent > 5:
        score += 30

    # high frequency: >10 attempts/minute
    if recent > 10:
        score += 20

    if score > 80:
        level = 'CRITICAL'
    elif score >= 51:
        level = 'HIGH'
    elif score >= 21:
        level = 'MEDIUM'
    else:
        level = 'LOW'

    return score, level
