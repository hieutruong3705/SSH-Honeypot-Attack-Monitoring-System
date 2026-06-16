"""
Threat Scoring Engine — MITRE ATT&CK Framework Mapping

Mỗi hành vi của attacker được map sang MITRE ATT&CK Technique ID.
Trọng số dựa trên mức độ nghiêm trọng theo CVSS v3 severity scale:
  - CRITICAL (9.0-10.0): 30+ pts
  - HIGH     (7.0-8.9):  20-25 pts
  - MEDIUM   (4.0-6.9):  10-15 pts
  - LOW      (0.1-3.9):  3-5 pts

Reference: https://attack.mitre.org/
"""
from __future__ import annotations

import threading
from collections import defaultdict
from datetime import datetime

# ── MITRE ATT&CK Rule Definitions ────────────────────────────────────────────

MITRE_RULES = [
    # -- Initial Access --
    {
        'id': 'T1078',
        'tactic': 'Initial Access',
        'technique': 'Valid Accounts',
        'trigger': 'sensitive_username',
        'base_score': 5,
        'severity': 'LOW',
        'cvss': 3.1,
    },
    # -- Credential Access --
    {
        'id': 'T1110',
        'tactic': 'Credential Access',
        'technique': 'Brute Force',
        'trigger': 'login_rate',
        'base_score': 30,
        'severity': 'HIGH',
        'cvss': 7.5,
    },
    {
        'id': 'T1003',
        'tactic': 'Credential Access',
        'technique': 'OS Credential Dumping',
        'file_access': ['/etc/shadow', '/etc/passwd', '/root/.ssh/id_rsa',
                        '/home/admin/config.txt', '.ssh/authorized_keys'],
        'base_score': 25,
        'severity': 'HIGH',
        'cvss': 8.1,
    },
    # -- Execution --
    {
        'id': 'T1059.004',
        'tactic': 'Execution',
        'technique': 'Unix Shell',
        'commands': ['bash', 'sh', 'dash'],
        'base_score': 10,
        'severity': 'MEDIUM',
        'cvss': 5.3,
    },
    {
        'id': 'T1059.006',
        'tactic': 'Execution',
        'technique': 'Python',
        'commands': ['python', 'python3'],
        'base_score': 15,
        'severity': 'MEDIUM',
        'cvss': 6.1,
    },
    {
        'id': 'T1059.001',
        'tactic': 'Execution',
        'technique': 'Scripting (Perl/Ruby)',
        'commands': ['perl', 'ruby'],
        'base_score': 15,
        'severity': 'MEDIUM',
        'cvss': 6.1,
    },
    # -- Persistence --
    {
        'id': 'T1053.003',
        'tactic': 'Persistence',
        'technique': 'Scheduled Task: Cron',
        'commands': ['crontab', 'at'],
        'base_score': 20,
        'severity': 'HIGH',
        'cvss': 7.2,
    },
    {
        'id': 'T1098',
        'tactic': 'Persistence',
        'technique': 'Account Manipulation',
        'commands': ['useradd', 'usermod', 'passwd', 'adduser'],
        'base_score': 20,
        'severity': 'HIGH',
        'cvss': 7.5,
    },
    # -- Privilege Escalation --
    {
        'id': 'T1548',
        'tactic': 'Privilege Escalation',
        'technique': 'Abuse Elevation Control',
        'commands': ['sudo', 'su'],
        'base_score': 15,
        'severity': 'MEDIUM',
        'cvss': 6.7,
    },
    # -- Defense Evasion --
    {
        'id': 'T1222.002',
        'tactic': 'Defense Evasion',
        'technique': 'Linux File Permissions Mod',
        'commands': ['chmod'],
        'base_score': 15,
        'severity': 'MEDIUM',
        'cvss': 5.9,
    },
    {
        'id': 'T1070',
        'tactic': 'Defense Evasion',
        'technique': 'Indicator Removal',
        'commands': ['rm', 'unset', 'history'],
        'base_score': 15,
        'severity': 'MEDIUM',
        'cvss': 5.5,
    },
    # -- Discovery --
    {
        'id': 'T1082',
        'tactic': 'Discovery',
        'technique': 'System Information Discovery',
        'commands': ['uname', 'whoami', 'id', 'hostname'],
        'base_score': 5,
        'severity': 'LOW',
        'cvss': 2.3,
    },
    {
        'id': 'T1046',
        'tactic': 'Discovery',
        'technique': 'Network Service Discovery',
        'commands': ['nmap', 'masscan', 'netstat', 'ss', 'ifconfig', 'ip'],
        'base_score': 15,
        'severity': 'MEDIUM',
        'cvss': 5.8,
    },
    {
        'id': 'T1057',
        'tactic': 'Discovery',
        'technique': 'Process Discovery',
        'commands': ['ps', 'top', 'htop'],
        'base_score': 3,
        'severity': 'LOW',
        'cvss': 1.8,
    },
    # -- Command and Control --
    {
        'id': 'T1105',
        'tactic': 'Command and Control',
        'technique': 'Ingress Tool Transfer',
        'commands': ['wget', 'curl', 'scp', 'tftp'],
        'base_score': 25,
        'severity': 'HIGH',
        'cvss': 7.8,
    },
    {
        'id': 'T1095',
        'tactic': 'Command and Control',
        'technique': 'Non-Application Layer Protocol',
        'commands': ['nc', 'ncat', 'netcat'],
        'base_score': 25,
        'severity': 'HIGH',
        'cvss': 7.5,
    },
    # -- Impact --
    {
        'id': 'T1485',
        'tactic': 'Impact',
        'technique': 'Data Destruction',
        'commands': ['dd'],
        'base_score': 20,
        'severity': 'HIGH',
        'cvss': 8.0,
    },
    # -- Credential Access (tools) --
    {
        'id': 'T1110.002',
        'tactic': 'Credential Access',
        'technique': 'Password Cracking',
        'commands': ['hydra', 'john', 'hashcat'],
        'base_score': 25,
        'severity': 'HIGH',
        'cvss': 7.5,
    },
    # -- Defense Evasion (encoding) --
    {
        'id': 'T1027',
        'tactic': 'Defense Evasion',
        'technique': 'Obfuscated Files/Information',
        'commands': ['base64'],
        'base_score': 10,
        'severity': 'MEDIUM',
        'cvss': 4.5,
    },
]

# Build fast lookup: command_name -> rule
_CMD_RULE_MAP: dict[str, dict] = {}
for _rule in MITRE_RULES:
    for _cmd in _rule.get('commands', []):
        _CMD_RULE_MAP[_cmd] = _rule

# Build file access rules
_FILE_RULES = [r for r in MITRE_RULES if 'file_access' in r]

SENSITIVE_USERNAMES = {'root', 'admin', 'administrator', 'ubuntu', 'pi',
                       'vagrant', 'user', 'test'}
COMMON_PASSWORDS = {'123456', 'password', 'admin', 'root', '12345',
                    '12345678', 'qwerty', ''}

# ── Login-time scoring ────────────────────────────────────────────────────────

_attempt_times: dict[str, list[float]] = defaultdict(list)
_lock = threading.Lock()


def _count_recent(ip: str, seconds: int = 60) -> int:
    cutoff = datetime.now().timestamp() - seconds
    with _lock:
        times = _attempt_times[ip]
        times[:] = [t for t in times if t > cutoff]
        return len(times)


def _record(ip: str) -> None:
    with _lock:
        _attempt_times[ip].append(datetime.now().timestamp())


def calculate_login_threat(ip: str, username: str, password: str,
                           fingerprint: str = None) -> tuple[int, str, str]:
    recent = _count_recent(ip, seconds=60)
    _record(ip)

    score = 1  # base: login attempt
    client_tool = None

    # Fingerprint analysis — chỉ gắn nhãn, KHÔNG cộng điểm
    # Score phải phản ánh hành vi, không phải loại SSH client
    if fingerprint:
        fp_lower = fingerprint.lower()
        if any(s in fp_lower for s in ('libssh', 'nmap', 'zmap')):
            client_tool = 'SCANNER'
        elif any(s in fp_lower for s in ('paramiko', 'python')):
            client_tool = 'SCRIPT: PYTHON'
        elif 'putty' in fp_lower:
            client_tool = 'PUTTY'
        elif 'openssh' in fp_lower:
            client_tool = 'OPENSSH'
        elif any(s in fp_lower for s in ('3des-cbc', 'ssh-rsa')):
            client_tool = 'BOTNET/IOT'

    # T1078 — Valid Accounts
    if username.lower() in SENSITIVE_USERNAMES:
        score += 5

    # Common password
    if password.lower() in COMMON_PASSWORDS:
        score += 2

    # T1110 — Brute Force
    if recent > 5:
        score += 30
    if recent > 10:
        score += 20

    return score, _level(score), client_tool


# ── Command-time scoring (MITRE ATT&CK mapped) ──────────────────────────────

def score_command(cmd: str) -> int:
    """Backward-compatible: returns just the score int."""
    result = score_command_mitre(cmd)
    return result['score']


def score_command_mitre(cmd: str) -> dict:
    """
    Score a command and return MITRE ATT&CK mapping.

    Returns:
        {
            'score': int,
            'mitre_id': str | None,      # e.g. 'T1105'
            'technique': str | None,      # e.g. 'Ingress Tool Transfer'
            'tactic': str | None,         # e.g. 'Command and Control'
            'severity': str | None,       # LOW/MEDIUM/HIGH/CRITICAL
        }
    """
    if not cmd.strip():
        return {'score': 0, 'mitre_id': None, 'technique': None,
                'tactic': None, 'severity': None}

    parts = cmd.strip().split()
    name = parts[0].lstrip('./')
    total_score = 0
    matched_rule = None

    # 1. Match command name
    rule = _CMD_RULE_MAP.get(name)
    if rule:
        total_score += rule['base_score']
        matched_rule = rule

    # 2. Check file access patterns (T1003)
    for fr in _FILE_RULES:
        for path in fr['file_access']:
            if path in cmd:
                bonus = fr['base_score']
                total_score += bonus
                if not matched_rule or fr['base_score'] > matched_rule['base_score']:
                    matched_rule = fr
                break

    # 3. Context bonuses
    if name == 'chmod' and '+x' in cmd:
        total_score += 5  # making payload executable
    if name in ('wget', 'curl'):
        if any(ext in cmd for ext in ('.sh', '.py', '.bin', '.elf', '.exe')):
            total_score += 10  # downloading executable payload

    if matched_rule:
        return {
            'score': total_score,
            'mitre_id': matched_rule['id'],
            'technique': matched_rule['technique'],
            'tactic': matched_rule['tactic'],
            'severity': matched_rule['severity'],
        }

    return {'score': total_score, 'mitre_id': None, 'technique': None,
            'tactic': None, 'severity': None}


# ── Session classification ───────────────────────────────────────────────────

# Patterns: set of MITRE tactic names -> session label
SESSION_PATTERNS = [
    ({'Command and Control', 'Defense Evasion', 'Persistence'},
     'BOTNET DROPPER'),
    ({'Command and Control', 'Defense Evasion'},
     'MALWARE DEPLOYER'),
    ({'Credential Access'},
     'CREDENTIAL HARVESTER'),
    ({'Discovery', 'Credential Access'},
     'RECON & STEAL'),
    ({'Persistence', 'Privilege Escalation'},
     'PERSISTENCE INSTALLER'),
    ({'Discovery'},
     'RECON SCOUT'),
]


def classify_session(commands: list[str]) -> str | None:
    """
    Given a list of commands from a session, classify the attacker behavior.
    Returns a label like 'BOTNET DROPPER' or None if unclassifiable.
    """
    tactics_seen: set[str] = set()
    for cmd in commands:
        result = score_command_mitre(cmd)
        if result['tactic']:
            tactics_seen.add(result['tactic'])

    for required_tactics, label in SESSION_PATTERNS:
        if required_tactics.issubset(tactics_seen):
            return label

    return None


# ── Level helpers ─────────────────────────────────────────────────────────────

def _level(score: int) -> str:
    if score > 80:
        return 'CRITICAL'
    if score >= 51:
        return 'HIGH'
    if score >= 21:
        return 'MEDIUM'
    return 'LOW'


def level_from_score(score: int) -> str:
    return _level(score)
