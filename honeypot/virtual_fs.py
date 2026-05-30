"""
In-memory virtual filesystem.
Reads NOTHING from the real host filesystem.
"""
from __future__ import annotations

# ── Fake file contents ────────────────────────────────────────────────────────

_PASSWD = """\
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
admin:x:1000:1000:Ubuntu,,,:/home/admin:/bin/bash
"""

_SHADOW = """\
root:$6$9Qs4q/rC$RPUV8QFVZ7lKdRh5RX2A3jO4bO5eY6jO7pQ8rS9tU0vW1x:19000:0:99999:7:::
admin:$6$abc123de$zY9xW8vU7tS6rQ5pO4nM3lK2jI1hG0fE9dD8cC7bB6aA5yY:19000:0:99999:7:::
"""

_HOSTS = """\
127.0.0.1   localhost
127.0.1.1   ubuntu-server
::1         ip6-localhost ip6-loopback
"""

_CRONTAB = """\
# m h dom mon dow command
*/5 * * * * /usr/bin/backup.sh
0   2 *   *   * /usr/bin/update.sh
"""

_NOTES = """\
TODO:
- Change default password
- Setup firewall rules
- Backup database weekly
"""

_CONFIG = """\
[database]
host     = localhost
port     = 5432
name     = production_db
user     = dbadmin
password = P@ssw0rd_2024!

[api]
secret_key = s3cr3t_k3y_d0_n0t_sh4r3
debug      = false
"""

_AUTH_LOG = """\
May 29 16:55:01 ubuntu-server sshd[1234]: Failed password for root from 192.168.1.1 port 54321 ssh2
May 29 16:58:12 ubuntu-server sshd[1235]: Failed password for admin from 192.168.1.2 port 43210 ssh2
May 29 17:00:00 ubuntu-server sshd[1236]: Accepted password for admin from 192.168.1.100 port 55001 ssh2
"""

_SYSLOG = """\
May 29 17:00:00 ubuntu-server systemd[1]: Started OpenSSH Server Daemon.
May 29 17:05:00 ubuntu-server cron[567]: (root) CMD (/usr/bin/backup.sh)
May 29 17:10:00 ubuntu-server kernel: [12345.678] eth0: renamed from veth3abc
"""

_ID_RSA = """\
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0Z3VS5JJcds3xHn/ygWep4x6pJGNS4sGnEGKfQfRGFrA...
[REDACTED FOR SECURITY]
-----END RSA PRIVATE KEY-----
"""

# ── Directory tree ────────────────────────────────────────────────────────────

_DIRS: dict[str, list[str]] = {
    '/':                     ['bin', 'etc', 'home', 'root', 'tmp', 'usr', 'var'],
    '/bin':                  [],
    '/etc':                  ['cron.d', 'passwd', 'shadow', 'hosts', 'hostname'],
    '/etc/cron.d':           ['backup'],
    '/home':                 ['admin'],
    '/home/admin':           ['Documents', 'Downloads', '.bash_history', 'notes.txt', 'config.txt'],
    '/home/admin/Documents': ['report_q1.pdf', 'budget_2026.xlsx'],
    '/home/admin/Downloads': [],
    '/root':                 ['.bash_history', '.ssh'],
    '/root/.ssh':            ['authorized_keys', 'id_rsa'],
    '/tmp':                  ['tmpfile', 'sess_a1b2c3'],
    '/usr':                  ['bin', 'local'],
    '/usr/bin':              [],
    '/usr/local':            [],
    '/var':                  ['log', 'www'],
    '/var/log':              ['auth.log', 'syslog'],
    '/var/www':              ['html'],
    '/var/www/html':         ['index.html'],
}

_FILES: dict[str, str] = {
    '/etc/passwd':               _PASSWD,
    '/etc/shadow':               _SHADOW,
    '/etc/hosts':                _HOSTS,
    '/etc/hostname':             'ubuntu-server\n',
    '/etc/cron.d/backup':        _CRONTAB,
    '/home/admin/notes.txt':     _NOTES,
    '/home/admin/config.txt':    _CONFIG,
    '/home/admin/.bash_history': 'ls\npwd\ncat /etc/passwd\nwhoami\nifconfig\n',
    '/root/.bash_history':       'sudo su\nls /home\ncat /etc/shadow\nhistory\n',
    '/root/.ssh/authorized_keys':'ssh-rsa AAAAB3NzaC1yc2EAAA...REDACTED admin@workstation\n',
    '/root/.ssh/id_rsa':         _ID_RSA,
    '/var/log/auth.log':         _AUTH_LOG,
    '/var/log/syslog':           _SYSLOG,
    '/var/www/html/index.html':  '<html><body><h1>Under Construction</h1></body></html>\n',
    '/tmp/tmpfile':              '',
    '/tmp/sess_a1b2c3':         'session_token=abc123xyz\n',
}


# ── VirtualFS class ───────────────────────────────────────────────────────────

class VirtualFS:
    def __init__(self) -> None:
        self._dirs  = {k: list(v) for k, v in _DIRS.items()}
        self._files = dict(_FILES)

    # ── Query ─────────────────────────────────────────────────────────────────

    def is_dir(self, path: str) -> bool:
        return path in self._dirs

    def is_file(self, path: str) -> bool:
        return path in self._files

    def exists(self, path: str) -> bool:
        return self.is_dir(path) or self.is_file(path)

    def listdir(self, path: str) -> list[str]:
        return list(self._dirs.get(path, []))

    def read(self, path: str) -> str | None:
        return self._files.get(path)

    # ── Path resolution ────────────────────────────────────────────────────────

    @staticmethod
    def resolve(cwd: str, path: str) -> str:
        """Resolve relative or absolute path against cwd. Pure string logic."""
        if not path:
            return cwd
        parts = path.split('/') if path.startswith('/') else cwd.split('/') + path.split('/')
        resolved: list[str] = []
        for part in parts:
            if part in ('', '.'):
                continue
            if part == '..':
                if resolved:
                    resolved.pop()
            else:
                resolved.append(part)
        return '/' + '/'.join(resolved) if resolved else '/'
