import sqlite3
import threading
import requests
import ipaddress
from contextlib import contextmanager
from datetime import datetime

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DB_PATH

_lock = threading.Lock()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {
        row['name']
        for row in conn.execute(f'PRAGMA table_info({table})').fetchall()
    }
    if column not in columns:
        conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')


@contextmanager
def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# â”€â”€ Schema â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
                threat_level  TEXT    DEFAULT 'LOW',
                fingerprint   TEXT,
                client_tool   TEXT
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
                command_count    INTEGER DEFAULT 0,
                fingerprint      TEXT,
                client_tool      TEXT
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
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ip_locations (
                ip      TEXT PRIMARY KEY,
                country TEXT,
                city    TEXT,
                lat     REAL,
                lon     REAL,
                proxy_type TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS malware_captures (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT    NOT NULL,
                filename    TEXT,
                sha256      TEXT,
                file_size   INTEGER DEFAULT 0,
                vt_malicious INTEGER DEFAULT -1,
                vt_total     INTEGER DEFAULT 0,
                status      TEXT    DEFAULT 'DOWNLOADING',
                session_ip  TEXT,
                session_user TEXT,
                timestamp   TEXT    NOT NULL
            )
        ''')
        _ensure_column(conn, 'attacks', 'fingerprint', 'TEXT')
        _ensure_column(conn, 'attacks', 'client_tool', 'TEXT')
        _ensure_column(conn, 'sessions', 'fingerprint', 'TEXT')
        _ensure_column(conn, 'sessions', 'client_tool', 'TEXT')

def get_or_fetch_ip_location(ip: str):
    try:
        parsed_ip = ipaddress.ip_address(ip)
        if (
            parsed_ip.is_private
            or parsed_ip.is_loopback
            or parsed_ip.is_link_local
            or parsed_ip.is_multicast
            or parsed_ip.is_reserved
            or parsed_ip.is_unspecified
        ):
            return None
    except ValueError:
        if ip != 'localhost':
            return None

    with _lock:
        with _get_conn() as conn:
            row = conn.execute('SELECT * FROM ip_locations WHERE ip = ?', (ip,)).fetchone()
            if row:
                return dict(row)

    try:
        r = requests.get(f"http://ip-api.com/json/{ip}", timeout=3)
        data = r.json()
        if data.get("status") == "success":
            # Check proxy
            proxy_type = None
            try:
                pr = requests.get(f"https://proxycheck.io/v2/{ip}?vpn=1&asn=1", timeout=3)
                pdata = pr.json()
                if pdata.get("status") == "ok" and ip in pdata:
                    info = pdata[ip]
                    if info.get("proxy") == "yes":
                        proxy_type = info.get("type", "Proxy")
            except Exception:
                pass

            data["proxy_type"] = proxy_type

            with _lock:
                with _get_conn() as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO ip_locations (ip, country, city, lat, lon, proxy_type)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (ip, data.get("country"), data.get("city"), data.get("lat"), data.get("lon"), proxy_type))
            return data
    except Exception:
        pass

    if ip == '127.0.0.1' or ip == 'localhost':
        with _lock:
            with _get_conn() as conn:
                conn.execute('''
                    INSERT OR IGNORE INTO ip_locations (ip, country, city, lat, lon, proxy_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (ip, 'Localhost', 'Hanoi (Test)', 21.0285, 105.8542, 'VPN'))
        return {
            "status": "success",
            "country": "Localhost",
            "city": "Hanoi (Test)",
            "lat": 21.0285,
            "lon": 105.8542,
            "proxy_type": "VPN"
        }

    return None

def get_map_data() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute('''
            SELECT a.ip, COUNT(*) as cnt, l.lat, l.lon, l.country, l.city
            FROM attacks a
            JOIN ip_locations l ON a.ip = l.ip
            WHERE l.lat IS NOT NULL AND l.lon IS NOT NULL
            GROUP BY a.ip
            ORDER BY cnt DESC
            LIMIT 100
        ''').fetchall()
        return [dict(r) for r in rows]


# â”€â”€ Attacks â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def save_attack(ip: str, username: str, password: str,
                timestamp: str, threat_score: int, threat_level: str,
                fingerprint: str = None, client_tool: str = None) -> None:
    with _lock:
        with _get_conn() as conn:
            conn.execute(
                'INSERT INTO attacks (ip, username, password, timestamp, threat_score, threat_level, fingerprint, client_tool)'
                ' VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (ip, username, password, timestamp, threat_score, threat_level, fingerprint, client_tool),
            )


def get_recent_attacks(limit: int = 50) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute('''
            SELECT a.*, l.proxy_type
            FROM attacks a
            LEFT JOIN ip_locations l ON a.ip = l.ip
            ORDER BY a.id DESC LIMIT ?
        ''', (limit,)).fetchall()
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


# â”€â”€ Sessions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def save_session(data: dict) -> None:
    with _lock:
        with _get_conn() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO sessions
                  (session_id, ip, username, password, login_time, end_time,
                   threat_score, threat_level, duration_seconds, command_count, fingerprint, client_tool)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                data['session_id'], data['ip'], data['username'], data['password'],
                data['login_time'], data.get('end_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                data['threat_score'], data['threat_level'],
                data.get('duration_seconds', 0), data.get('command_count', 0),
                data.get('fingerprint'), data.get('client_tool')
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
        rows = conn.execute('''
            SELECT s.*, l.proxy_type
            FROM sessions s
            LEFT JOIN ip_locations l ON s.ip = l.ip
            ORDER BY s.login_time DESC LIMIT ?
        ''', (limit,)).fetchall()

        result = []
        for r in rows:
            s_dict = dict(r)
            cmds = conn.execute(
                'SELECT command as cmd, timestamp as time, score_delta FROM commands WHERE session_id = ? ORDER BY id',
                (s_dict['session_id'],),
            ).fetchall()
            s_dict['commands'] = [dict(c) for c in cmds]
            result.append(s_dict)

        return result


def get_session_commands(session_id: str) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            'SELECT command, timestamp, score_delta FROM commands WHERE session_id = ? ORDER BY id',
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# â”€â”€ Malware Captures â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def save_malware_capture(url: str, filename: str, sha256: str, file_size: int,
                        vt_malicious: int, vt_total: int, status: str,
                        session_ip: str, session_user: str) -> None:
    with _lock:
        with _get_conn() as conn:
            conn.execute(
                'INSERT INTO malware_captures (url, filename, sha256, file_size, vt_malicious, vt_total, status, session_ip, session_user, timestamp)'
                ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (url, filename, sha256, file_size, vt_malicious, vt_total, status,
                 session_ip, session_user, datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            )


def get_malware_captures(limit: int = 20) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM malware_captures ORDER BY id DESC LIMIT ?', (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
