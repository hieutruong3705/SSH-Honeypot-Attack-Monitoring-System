"""Telegram alerts with per-IP cooldown to avoid spam during brute-force."""
from __future__ import annotations

import threading
from datetime import datetime

import requests

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

_session = requests.Session()
_last_alert: dict[str, float] = {}
_lock = threading.Lock()
_COOLDOWN = 30  # seconds

_EMOJI = {'LOW': '🟡', 'MEDIUM': '🟠', 'HIGH': '🔴', 'CRITICAL': '🚨'}


def _throttled(ip: str) -> bool:
    now = datetime.now().timestamp()
    with _lock:
        if now - _last_alert.get(ip, 0) < _COOLDOWN:
            return True
        _last_alert[ip] = now
    return False


def _post(text: str) -> None:
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    try:
        _session.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': text}, timeout=5)
    except Exception:
        pass


def send_login_alert(attack: dict) -> None:
    if _throttled(attack['ip']):
        return
    emoji = _EMOJI.get(attack['threat_level'], '⚠️')
    _post(
        f"{emoji} SSH HONEYPOT — LOGIN\n\n"
        f"IP:   {attack['ip']}\n"
        f"User: {attack['username']}\n"
        f"Pass: {attack['password']}\n"
        f"Risk: {attack['threat_level']} (score {attack['threat_score']})\n"
        f"Time: {attack['timestamp']}"
    )


def send_shell_alert(session_id: str, ip: str, username: str,
                     cmd: str, score: int, level: str) -> None:
    if level not in ('HIGH', 'CRITICAL'):
        return
    if _throttled(ip):
        return
    emoji = _EMOJI.get(level, '🔴')
    _post(
        f"{emoji} ATTACKER IN SHELL\n\n"
        f"IP:      {ip}  ({username})\n"
        f"CMD:     {cmd}\n"
        f"Score:   {score} ({level})\n"
        f"Session: {session_id}"
    )
