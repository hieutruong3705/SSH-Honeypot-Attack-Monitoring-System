"""Telegram alerts with per-IP cooldown to avoid spam during brute-force."""
from __future__ import annotations

import queue
import threading
import time
from datetime import datetime

import requests

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

_session = requests.Session()
_last_alert: dict[str, float] = {}
_lock = threading.Lock()
_alert_queue: queue.Queue[str | None] = queue.Queue(maxsize=1000)
_worker_started = False
_WORKER_LOCK = threading.Lock()
_MAX_RETRIES = 3
_REQUEST_TIMEOUT = 3
_COMMAND_COOLDOWN = 3  # seconds, only suppresses duplicate shell commands

_EMOJI = {'LOW': '🟡', 'MEDIUM': '🟠', 'HIGH': '🔴', 'CRITICAL': '🚨'}


def _throttled(key: str, cooldown: int) -> bool:
    now = datetime.now().timestamp()
    with _lock:
        if now - _last_alert.get(key, 0) < cooldown:
            return True
        _last_alert[key] = now
    return False


def _post_now(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print('[!] Telegram alert skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is empty')
        return False

    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = _session.post(
                url,
                json={'chat_id': TELEGRAM_CHAT_ID, 'text': text},
                timeout=_REQUEST_TIMEOUT,
            )
            if response.ok:
                return True

            retry_after = 0
            if response.status_code == 429:
                try:
                    retry_after = int(response.json().get('parameters', {}).get('retry_after', 1))
                except Exception:
                    retry_after = 1

            print(f'[!] Telegram alert failed: {response.status_code} {response.text}')
            if attempt < _MAX_RETRIES:
                time.sleep(max(retry_after, attempt))
        except Exception as exc:
            print(f'[!] Telegram alert error: {exc}')
            if attempt < _MAX_RETRIES:
                time.sleep(attempt)
    return False


def _worker() -> None:
    while True:
        text = _alert_queue.get()
        try:
            if text is not None:
                _post_now(text)
        finally:
            _alert_queue.task_done()


def _ensure_worker() -> None:
    global _worker_started
    if _worker_started:
        return
    with _WORKER_LOCK:
        if _worker_started:
            return
        threading.Thread(target=_worker, daemon=True).start()
        _worker_started = True


def _post(text: str) -> None:
    _ensure_worker()
    try:
        _alert_queue.put_nowait(text)
    except queue.Full:
        print('[!] Telegram alert queue full, sending synchronously')
        _post_now(text)


def send_login_alert(attack: dict) -> None:
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
    if _throttled(f'{ip}:{cmd}', _COMMAND_COOLDOWN):
        return
    emoji = _EMOJI.get(level, '🔴')
    _post(
        f"{emoji} ATTACKER IN SHELL\n\n"
        f"IP:      {ip}  ({username})\n"
        f"CMD:     {cmd}\n"
        f"Score:   {score} ({level})\n"
        f"Session: {session_id}"
    )
