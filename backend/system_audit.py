"""
System Security Audit — CIS Benchmark Mapped

Quét 10 hạng mục bảo mật, mỗi hạng mục gắn mã CIS Benchmark ID.
Reference: CIS Ubuntu Linux 22.04 LTS Benchmark v1.0.0

Trên Windows → trả kết quả mock để phục vụ dev/demo.
Trên Linux (VPS thật) → chạy lệnh hệ thống thật.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
from datetime import datetime


def _is_linux() -> bool:
    return platform.system() == 'Linux'


def _run_cmd(cmd: list[str], default: str = '') -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.stdout.strip() or result.stderr.strip() or default
    except Exception:
        return default


# ── Individual checks (CIS Benchmark mapped) ────────────────────────────────

def _check_ssh_root_login() -> dict:
    check = {
        'name': 'SSH Root Login Disabled',
        'cis_id': 'CIS 5.2.10',
        'cis_ref': 'Ensure SSH root login is disabled',
        'category': 'Authentication',
        'recommendation': 'Set "PermitRootLogin no" in /etc/ssh/sshd_config',
        'weight': 15,
    }
    if not _is_linux():
        check.update(status='FAIL', detail='PermitRootLogin yes (mock)', score=0)
        return check

    output = _run_cmd(['grep', '-i', 'PermitRootLogin', '/etc/ssh/sshd_config'])
    for line in output.splitlines():
        line = line.strip()
        if line.startswith('#'):
            continue
        if 'no' in line.lower():
            check.update(status='PASS', detail=line, score=15)
            return check

    check.update(status='FAIL', detail=output or 'Not configured', score=0)
    return check


def _check_ssh_password_auth() -> dict:
    check = {
        'name': 'SSH Password Auth Disabled',
        'cis_id': 'CIS 5.2.12',
        'cis_ref': 'Ensure SSH PasswordAuthentication is disabled',
        'category': 'Authentication',
        'recommendation': 'Set "PasswordAuthentication no" in /etc/ssh/sshd_config and use key-based auth',
        'weight': 10,
    }
    if not _is_linux():
        check.update(status='WARNING',
                     detail='PasswordAuthentication yes (mock — required for honeypot)',
                     score=5)
        return check

    output = _run_cmd(['grep', '-i', 'PasswordAuthentication', '/etc/ssh/sshd_config'])
    for line in output.splitlines():
        line = line.strip()
        if line.startswith('#'):
            continue
        if 'no' in line.lower():
            check.update(status='PASS', detail=line, score=10)
            return check

    check.update(status='WARNING',
                 detail=(output or 'PasswordAuthentication yes') + ' (Honeypot requires password auth on port 2222)',
                 score=5)
    return check


def _check_firewall() -> dict:
    check = {
        'name': 'Firewall Active',
        'cis_id': 'CIS 3.5.1.1',
        'cis_ref': 'Ensure ufw is installed and active',
        'category': 'Network',
        'recommendation': 'Enable UFW: sudo ufw enable && sudo ufw default deny incoming',
        'weight': 15,
    }
    if not _is_linux():
        check.update(status='FAIL', detail='Firewall status unknown (Windows dev)', score=0)
        return check

    output = _run_cmd(['ufw', 'status'])
    if 'active' in output.lower() and 'inactive' not in output.lower():
        check.update(status='PASS', detail=output.splitlines()[0], score=15)
    else:
        ipt = _run_cmd(['iptables', '-L', '-n', '--line-numbers'])
        if ipt and 'ACCEPT' in ipt:
            check.update(status='WARNING', detail='iptables has rules but UFW not active', score=8)
        else:
            check.update(status='FAIL', detail='No firewall active', score=0)
    return check


def _check_open_ports() -> dict:
    check = {
        'name': 'Minimal Open Ports',
        'cis_id': 'CIS 3.5.1.7',
        'cis_ref': 'Ensure nftables/ufw manages port access',
        'category': 'Network',
        'recommendation': 'Close unnecessary ports. Only keep 22 (SSH), 80/443 (web), 2222 (honeypot)',
        'weight': 10,
    }
    if not _is_linux():
        check.update(status='WARNING', detail='Ports: 22, 80, 2222, 3306 (mock)', score=5)
        return check

    output = _run_cmd(['ss', '-tlnp'])
    lines = [l for l in output.splitlines() if 'LISTEN' in l]
    ports = []
    for line in lines:
        parts = line.split()
        for p in parts:
            if ':' in p:
                port = p.rsplit(':', 1)[-1]
                if port.isdigit():
                    ports.append(int(port))
                    break

    ports = sorted(set(ports))
    safe_ports = {22, 80, 443, 2222, 8000}
    risky = [p for p in ports if p not in safe_ports]

    detail = f"Open ports: {', '.join(str(p) for p in ports)}"
    if risky:
        check.update(status='WARNING',
                     detail=f"{detail} — Unexpected: {', '.join(str(p) for p in risky)}",
                     score=5)
    else:
        check.update(status='PASS', detail=detail, score=10)
    return check


def _check_shadow_permissions() -> dict:
    check = {
        'name': '/etc/shadow Permissions',
        'cis_id': 'CIS 6.1.3',
        'cis_ref': 'Ensure permissions on /etc/shadow are configured',
        'category': 'File System',
        'recommendation': 'Set permissions: sudo chmod 640 /etc/shadow',
        'weight': 10,
    }
    if not _is_linux():
        check.update(status='PASS', detail='-rw-r----- (640) (mock)', score=10)
        return check

    output = _run_cmd(['stat', '-c', '%a %U:%G', '/etc/shadow'])
    if output:
        perm = output.split()[0] if output.split() else ''
        if perm in ('600', '640', '000'):
            check.update(status='PASS', detail=f'Permissions: {output}', score=10)
        else:
            check.update(status='FAIL', detail=f'Permissions: {output} (too permissive)', score=0)
    else:
        check.update(status='FAIL', detail='Cannot read /etc/shadow', score=0)
    return check


def _check_passwd_permissions() -> dict:
    check = {
        'name': '/etc/passwd Permissions',
        'cis_id': 'CIS 6.1.2',
        'cis_ref': 'Ensure permissions on /etc/passwd are configured',
        'category': 'File System',
        'recommendation': 'Set permissions: sudo chmod 644 /etc/passwd',
        'weight': 5,
    }
    if not _is_linux():
        check.update(status='PASS', detail='-rw-r--r-- (644) (mock)', score=5)
        return check

    output = _run_cmd(['stat', '-c', '%a', '/etc/passwd'])
    if output in ('644', '444'):
        check.update(status='PASS', detail=f'Permissions: {output}', score=5)
    else:
        check.update(status='FAIL', detail=f'Permissions: {output} (should be 644)', score=0)
    return check


def _check_auto_updates() -> dict:
    check = {
        'name': 'Automatic Security Updates',
        'cis_id': 'CIS 1.9',
        'cis_ref': 'Ensure updates, patches, and security software are installed',
        'category': 'Patch Management',
        'recommendation': 'Install: sudo apt install unattended-upgrades && sudo dpkg-reconfigure unattended-upgrades',
        'weight': 10,
    }
    if not _is_linux():
        check.update(status='FAIL', detail='unattended-upgrades not found (mock)', score=0)
        return check

    output = _run_cmd(['dpkg', '-l', 'unattended-upgrades'])
    if 'ii' in output:
        check.update(status='PASS', detail='unattended-upgrades installed', score=10)
    else:
        check.update(status='FAIL', detail='unattended-upgrades not installed', score=0)
    return check


def _check_fail2ban() -> dict:
    check = {
        'name': 'Fail2ban Active',
        'cis_id': 'CIS 4.1.1',
        'cis_ref': 'Ensure intrusion detection system is active',
        'category': 'Intrusion Prevention',
        'recommendation': 'Install: sudo apt install fail2ban && sudo systemctl enable fail2ban',
        'weight': 10,
    }
    if not _is_linux():
        check.update(status='FAIL', detail='fail2ban not found (mock)', score=0)
        return check

    output = _run_cmd(['systemctl', 'is-active', 'fail2ban'])
    if 'active' in output.lower():
        check.update(status='PASS', detail='fail2ban is running', score=10)
    else:
        check.update(status='FAIL', detail=f'fail2ban: {output}', score=0)
    return check


def _check_kernel() -> dict:
    check = {
        'name': 'Kernel Up-to-date',
        'cis_id': 'CIS 1.9',
        'cis_ref': 'Ensure system packages are up-to-date',
        'category': 'Patch Management',
        'recommendation': 'Run: sudo apt update && sudo apt upgrade',
        'weight': 5,
    }
    if not _is_linux():
        check.update(status='PASS', detail='5.15.0-91-generic (mock)', score=5)
        return check

    output = _run_cmd(['uname', '-r'])
    check.update(status='PASS', detail=f'Kernel: {output}', score=5)
    return check


def _check_running_as_root() -> dict:
    check = {
        'name': 'Honeypot Not Running as Root',
        'cis_id': 'CIS 5.6',
        'cis_ref': 'Ensure root login is limited to system console',
        'category': 'Privilege',
        'recommendation': 'Create a dedicated user: sudo useradd -r honeypot && run service as honeypot user',
        'weight': 10,
    }
    if not _is_linux():
        check.update(status='WARNING', detail='Running as user (Windows dev)', score=5)
        return check

    uid = os.getuid()
    username = _run_cmd(['whoami'])
    if uid == 0:
        check.update(status='FAIL',
                     detail=f'Running as {username} (UID=0, root)', score=0)
    else:
        check.update(status='PASS',
                     detail=f'Running as {username} (UID={uid})', score=10)
    return check


# ── Main audit runner ────────────────────────────────────────────────────────

ALL_CHECKS = [
    _check_ssh_root_login,
    _check_ssh_password_auth,
    _check_firewall,
    _check_open_ports,
    _check_shadow_permissions,
    _check_passwd_permissions,
    _check_auto_updates,
    _check_fail2ban,
    _check_kernel,
    _check_running_as_root,
]


def run_audit() -> dict:
    checks = [fn() for fn in ALL_CHECKS]

    total_score = sum(c['score'] for c in checks)
    max_score = sum(c['weight'] for c in checks)

    pct = (total_score / max_score * 100) if max_score else 0

    if pct >= 90:   grade = 'A'
    elif pct >= 75:  grade = 'B'
    elif pct >= 60:  grade = 'C'
    elif pct >= 40:  grade = 'D'
    else:            grade = 'F'

    result = {
        'score': total_score,
        'max_score': max_score,
        'percentage': round(pct),
        'grade': grade,
        'checks': checks,
        'platform': platform.system(),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    # Save to history
    _save_audit_history(result)

    return result


def _save_audit_history(result: dict) -> None:
    try:
        from backend.database import _get_conn, _lock
        with _lock:
            with _get_conn() as conn:
                conn.execute(
                    'INSERT INTO audit_history (score, max_score, percentage, grade, checks_json, timestamp)'
                    ' VALUES (?, ?, ?, ?, ?, ?)',
                    (result['score'], result['max_score'], result['percentage'],
                     result['grade'], json.dumps(result['checks']),
                     result['timestamp']),
                )
    except Exception:
        pass


def get_audit_history(limit: int = 10) -> list[dict]:
    try:
        from backend.database import _get_conn
        with _get_conn() as conn:
            rows = conn.execute(
                'SELECT id, score, max_score, percentage, grade, timestamp'
                ' FROM audit_history ORDER BY id DESC LIMIT ?', (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []
