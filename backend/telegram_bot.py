import requests
import threading
from datetime import datetime

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

_session = requests.Session()
_last_alert: dict[str, float] = {}
_lock = threading.Lock()
_COOLDOWN_SECONDS = 30

LEVEL_EMOJI = {
    'LOW': '🟡',
    'MEDIUM': '🟠',
    'HIGH': '🔴',
    'CRITICAL': '🚨',
}


def send_telegram_alert(attack: dict):
    ip = attack['ip']
    now = datetime.now().timestamp()

    with _lock:
        if now - _last_alert.get(ip, 0) < _COOLDOWN_SECONDS:
            return
        _last_alert[ip] = now

    level = attack['threat_level']
    emoji = LEVEL_EMOJI.get(level, '⚠️')
    message = (
        f"{emoji} SSH ATTACK DETECTED\n\n"
        f"IP: {ip}\n"
        f"Username: {attack['username']}\n"
        f"Password: {attack['password']}\n"
        f"Risk: {level} (Score: {attack['threat_score']})\n"
        f"Time: {attack['timestamp']}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        _session.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': message}, timeout=5)
    except Exception:
        pass
