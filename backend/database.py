import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DB_PATH

_lock = threading.Lock()


@contextmanager
def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db() -> None:
    with _get_conn() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS attacks (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                ip            TEXT    NOT NULL,
                username      TEXT    NOT NULL,
                password      TEXT    NOT NULL,
                timestamp     TEXT    NOT NULL,
                threat_score  INTEGER DEFAULT 0,
                threat_level  TEXT    DEFAULT 'LOW'
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id       TEXT PRIMARY KEY,
                ip               TEXT    NOT NULL,
                username         TEXT    NOT NULL,
                password         TEXT    NOT NULL,
                login_time       TEXT    NOT NULL,
                end_time         TEXT,
                threat_score     INTEGER DEFAULT 0,
                threat_level     TEXT    DEFAULT 'LOW',
                duration_seconds INTEGER DEFAULT 0,
                command_count    INTEGER DEFAULT 0
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS commands (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT    NOT NULL,
                command     TEXT    NOT NULL,
                timestamp   TEXT    NOT NULL,
                score_delta INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')


# ── Attacks ───────────────────────────────────────────────────────────────────

def save_attack(ip: str, username: str, password: str,
                timestamp: str, threat_score: int, threat_level: str) -> None:
    with _lock:
        with _get_conn() as conn:
            conn.execute(
                'INSERT INTO attacks (ip, username, password, timestamp, threat_score, threat_level)'
                ' VALUES (?, ?, ?, ?, ?, ?)',
                (ip, username, password, timestamp, threat_score, threat_level),
            )


def get_recent_attacks(limit: int = 50) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM attacks ORDER BY id DESC LIMIT ?', (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_stats() -> dict:
    today = datetime.now().strftime('%Y-%m-%d')
    with _get_conn() as conn:
        total = conn.execute('SELECT COUNT(*) as cnt FROM attacks').fetchone()['cnt']

        today_count = conn.execute(
            'SELECT COUNT(*) as cnt FROM attacks WHERE timestamp LIKE ?',
            (f'{today}%',),
        ).fetchone()['cnt']

        top_user = conn.execute(
            'SELECT username, COUNT(*) as cnt FROM attacks GROUP BY username ORDER BY cnt DESC LIMIT 1'
        ).fetchone()
        top_pass = conn.execute(
            'SELECT password, COUNT(*) as cnt FROM attacks GROUP BY password ORDER BY cnt DESC LIMIT 1'
        ).fetchone()

        by_hour = conn.execute(
            "SELECT substr(timestamp,12,2) as hour, COUNT(*) as cnt"
            " FROM attacks WHERE timestamp LIKE ? GROUP BY hour ORDER BY hour",
            (f'{today}%',),
        ).fetchall()
        top_ips = conn.execute(
            'SELECT ip, COUNT(*) as cnt FROM attacks GROUP BY ip ORDER BY cnt DESC LIMIT 5'
        ).fetchall()
        top_creds = conn.execute(
            "SELECT username||'/'||password as cred, COUNT(*) as cnt"
            " FROM attacks GROUP BY cred ORDER BY cnt DESC LIMIT 5"
        ).fetchall()

        return {
            'total':        total,
            'today':        today_count,
            'top_username': top_user['username'] if top_user else '-',
            'top_password': top_pass['password'] if top_pass else '-',
            'by_hour':      [dict(r) for r in by_hour],
            'top_ips':      [dict(r) for r in top_ips],
            'top_creds':    [dict(r) for r in top_creds],
        }


# ── Sessions ──────────────────────────────────────────────────────────────────

def save_session(data: dict) -> None:
    with _lock:
        with _get_conn() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO sessions
                  (session_id, ip, username, password, login_time, end_time,
                   threat_score, threat_level, duration_seconds, command_count)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            ''', (
                data['session_id'], data['ip'], data['username'], data['password'],
                data['login_time'], data.get('end_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                data['threat_score'], data['threat_level'],
                data.get('duration_seconds', 0), data.get('command_count', 0),
            ))


def save_commands(session_id: str, commands: list[dict]) -> None:
    with _lock:
        with _get_conn() as conn:
            conn.executemany(
                'INSERT INTO commands (session_id, command, timestamp, score_delta) VALUES (?,?,?,?)',
                [(session_id, c['cmd'], c['time'], c['score_delta']) for c in commands],
            )


def get_recent_sessions(limit: int = 20) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM sessions ORDER BY login_time DESC LIMIT ?', (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_session_commands(session_id: str) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            'SELECT command, timestamp, score_delta FROM commands WHERE session_id = ? ORDER BY id',
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]
