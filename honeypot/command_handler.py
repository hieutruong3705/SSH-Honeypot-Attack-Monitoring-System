"""
Extensible command registry for the fake shell.
All handlers return plain strings — no OS calls, no subprocess, no exec.
"""
from __future__ import annotations

import re
import shlex
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from honeypot.fake_shell import ShellSession

from honeypot.virtual_fs import VirtualFS

_UNAME_A = 'Linux ubuntu-server 5.15.0-91-generic #101-Ubuntu SMP Tue Nov 14 13:30:08 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux'

Handler = Callable[[list[str], 'ShellSession', VirtualFS], str]

_REDIRECT_TOKENS = {'>', '>>', '<', '2>', '2>>', '&>', '>&'}
_WRAPPER_COMMANDS = {
    'command', 'builtin', 'env', 'nohup', 'timeout', 'time',
    'setsid', 'nice', 'ionice', 'stdbuf', 'xargs',
}


def _strip_redirections(parts: list[str]) -> list[str]:
    cleaned: list[str] = []
    skip_next = False
    for part in parts:
        if skip_next:
            skip_next = False
            continue
        if part in _REDIRECT_TOKENS:
            skip_next = True
            continue
        if re.match(r'^(?:\d?>|&>|<)', part):
            continue
        cleaned.append(part)
    return cleaned


def _looks_like_assignment(part: str) -> bool:
    return bool(re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', part))


class CommandRegistry:
    def __init__(self, fs: VirtualFS) -> None:
        self._fs: VirtualFS = fs
        self._handlers: dict[str, Handler] = {}
        self._register_defaults()

    # ── Public API ────────────────────────────────────────────────────────────

    def register(self, *names: str) -> Callable:
        """Decorator to add a handler for one or more command names."""
        def decorator(fn: Handler) -> Handler:
            for name in names:
                self._handlers[name] = fn
            return fn
        return decorator

    def handle(self, raw: str, session: 'ShellSession') -> str:
        cmd = raw.strip()
        if not cmd:
            return ''
        try:
            parts = shlex.split(cmd)
        except ValueError:
            parts = cmd.split()
        parts = _strip_redirections(parts)
        while parts and _looks_like_assignment(parts[0]):
            parts = parts[1:]
        if not parts:
            return ''

        name    = parts[0].lstrip('./')
        args    = parts[1:]

        if name in _WRAPPER_COMMANDS and args:
            if name == 'env':
                while args and (args[0].startswith('-') or _looks_like_assignment(args[0])):
                    args = args[1:]
            elif name in ('timeout', 'time', 'nice', 'ionice', 'stdbuf') and args and args[0].startswith('-'):
                while args and args[0].startswith('-'):
                    args = args[1:]
                if name == 'timeout' and args:
                    args = args[1:]
            if args:
                return self.handle(' '.join(shlex.quote(a) for a in args), session)

        if name == 'busybox' and args:
            return self.handle(' '.join(shlex.quote(a) for a in args), session)

        if name == 'sudo' and args:
            sudo_args = [a for a in args if a not in ('-S', '-n', '-E', '-H')]
            if sudo_args and session.username == 'root':
                return self.handle(' '.join(shlex.quote(a) for a in sudo_args), session)

        handler = self._handlers.get(name)
        if handler:
            return handler(args, session, self._fs)
        return f'-bash: {parts[0]}: command not found'

    # ── Default command implementations ──────────────────────────────────────

    def _register_defaults(self) -> None:
        h = self._handlers
        fs = self._fs

        # ── filesystem ────────────────────────────────────────────────────────

        def _ls(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            # Tách riêng flag (như -l, -a) và tên thư mục
            flags = [a for a in args if a.startswith('-')]
            non_flags = [a for a in args if not a.startswith('-')]
            path = fs.resolve(s.cwd, non_flags[-1]) if non_flags else s.cwd

            if not fs.is_dir(path):
                if fs.is_file(path):
                    return path.split('/')[-1]
                return f"ls: cannot access '{non_flags[-1] if non_flags else path}': No such file or directory"

            items = fs.listdir(path)
            if not items:
                return ''

            # Kiểm tra xem hacker có dùng cờ '-l' (hoặc gọi qua lệnh ll) không
            is_detailed = any('l' in flag for flag in flags)

            if is_detailed:
                # Trả về danh sách DỌC chi tiết (Fake permission, size, date)
                parts = ["total 12"]
                # Thêm thư mục hiện tại (.) và thư mục cha (..) cho giống thật
                parts.append("drwxr-xr-x 1 root root 4096 May 29 17:30 .")
                parts.append("drwxr-xr-x 1 root root 4096 May 29 17:00 ..")
                
                for item in items:
                    child = (path.rstrip('/') + '/' + item)
                    if fs.is_dir(child):
                        parts.append(f"drwxr-xr-x 1 root root 4096 May 29 17:30 {item}")
                    else:
                        parts.append(f"-rw-r--r-- 1 root root 1024 May 29 17:30 {item}")
                return '\n'.join(parts)
            else:
                # Trả về danh sách NGANG bình thường
                parts = []
                for item in items:
                    child = (path.rstrip('/') + '/' + item)
                    parts.append(item + '/' if fs.is_dir(child) else item)
                return '  '.join(parts)

        def _cd(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            if not args:
                s.cwd = '/root' if s.username == 'root' else f'/home/{s.username}'
                return ''
            target = fs.resolve(s.cwd, args[0])
            if fs.is_dir(target):
                s.cwd = target
                return ''
            if fs.is_file(target):
                return f'bash: cd: {args[0]}: Not a directory'
            return f'bash: cd: {args[0]}: No such file or directory'

        def _cat(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            if not args:
                return ''
            path    = fs.resolve(s.cwd, args[0])
            content = fs.read(path)
            if content is None:
                return f'cat: {args[0]}: No such file or directory'
            return content.rstrip('\n')

        def _echo(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            env = {
                '$USER': s.username, '$HOME': f'/home/{s.username}',
                '$SHELL': '/bin/bash',
                '$PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                '$HOSTNAME': 'ubuntu-server', '$PWD': s.cwd,
            }
            return ' '.join(env.get(a, a) for a in args)

        def _file(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            if not args:
                return 'Usage: file filename'
            path = fs.resolve(s.cwd, args[0])
            if fs.is_dir(path):
                return f'{args[0]}: directory'
            if fs.is_file(path):
                content = fs.read(path) or ''
                t = 'ASCII text' if content.isprintable() else 'data'
                return f'{args[0]}: {t}'
            return f'{args[0]}: ERROR: No such file or directory'

        # ── system info ───────────────────────────────────────────────────────

        def _uname(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            if '-a' in args: return _UNAME_A
            if '-r' in args: return '5.15.0-91-generic'
            if '-n' in args: return 'ubuntu-server'
            if '-s' in args: return 'Linux'
            return 'Linux'

        def _ps(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            if any(a in ('aux', 'ax', '-aux', '-ax') for a in args):
                return (
                    'USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n'
                    'root           1  0.0  0.1 169984 13064 ?        Ss   May29   0:03 /sbin/init\n'
                    'root         234  0.0  0.0  72296  3580 ?        Ss   May29   0:00 /usr/sbin/sshd\n'
                    f'{s.username}        1234  0.0  0.1  21888  5296 pts/0    Ss   17:30   0:00 -bash\n'
                    f'{s.username}        1337  0.0  0.0  21104  3372 pts/0    R+   17:31   0:00 ps'
                )
            return (
                '  PID TTY          TIME CMD\n'
                ' 1234 pts/0    00:00:00 bash\n'
                ' 1337 pts/0    00:00:00 ps'
            )

        def _ifconfig(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return (
                'eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\n'
                '        inet 192.168.1.10  netmask 255.255.255.0  broadcast 192.168.1.255\n'
                '        inet6 fe80::1  prefixlen 64\n'
                '        ether 00:11:22:33:44:55  txqueuelen 1000  (Ethernet)\n'
                '        RX packets 12345  bytes 1234567 (1.2 MB)\n\n'
                'lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536\n'
                '        inet 127.0.0.1  netmask 255.0.0.0'
            )

        def _ip(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            if args and args[0] in ('a', 'addr', 'address'):
                return _ifconfig([], s, fs)
            return ''

        def _netstat(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return (
                'Active Internet connections (only servers)\n'
                'Proto Recv-Q Send-Q Local Address    Foreign Address  State\n'
                'tcp        0      0 0.0.0.0:22       0.0.0.0:* LISTEN\n'
                'tcp        0      0 0.0.0.0:80       0.0.0.0:* LISTEN\n'
                'tcp        0      0 127.0.0.1:5432   0.0.0.0:* LISTEN'
            )

        def _df(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return (
                'Filesystem      Size  Used Avail Use% Mounted on\n'
                '/dev/sda1        20G   14G  4.8G  75% /\n'
                'tmpfs           2.0G     0  2.0G   0% /dev/shm\n'
                '/dev/sdb1       100G   60G   36G  63% /data'
            )

        def _free(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return (
                '               total        used        free      shared  buff/cache   available\n'
                'Mem:         4096000     2048000      512000       51200     1536000     1792000\n'
                'Swap:        2097152      102400     1994752'
            )

        def _env(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return (
                f'USER={s.username}\nHOME=/home/{s.username}\n'
                'SHELL=/bin/bash\n'
                'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n'
                'TERM=xterm-256color\nLANG=en_US.UTF-8\n'
                f'PWD={s.cwd}'
            )

        def _history(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return '\n'.join(f'  {i+1:4d}  {c}' for i, c in enumerate(s.command_history))

        # ── network / discovery ────────────────────────────────────────────────

        def _nmap(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return (
                'Starting Nmap 7.80 ( https://nmap.org )\n'
                'Note: Host seems down. If it is really up, but blocking our ping probes, try -Pn\n'
                'Nmap done: 1 IP address (0 hosts up) scanned in 3.05 seconds'
            )

        def _wget(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            url = next((a for a in args if not a.startswith('-')), None)
            if not url:
                return 'wget: missing URL'
            host = url.split('/')[2] if '/' in url else url
            return (
                f'--2026-05-29 17:31:00--  {url}\n'
                f'Resolving {host}... failed: Name or service not known.\n'
                f'wget: unable to resolve host address \'{host}\''
            )

        def _curl(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            url = next((a for a in args if not a.startswith('-')), None)
            if not url:
                return 'curl: no URL specified!'
            host = url.split('/')[2] if url.count('/') >= 2 else url
            return f'curl: (6) Could not resolve host: {host}'

        def _nc(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return ''

        def _ssh_cmd(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return 'ssh: connect to host ... port 22: Connection refused'

        def _scp(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return 'ssh: connect to host ... port 22: Connection refused'

        # ── privilege / user management ────────────────────────────────────────

        def _sudo(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            if not args:
                return 'usage: sudo command'
            if s.username == 'root':
                return ''
            return (
                f'[sudo] password for {s.username}: \n'
                'Sorry, try again.\n'
                f'[sudo] password for {s.username}: \n'
                'Sorry, try again.\n'
                'sudo: 3 incorrect password attempts'
            )

        def _passwd(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return 'passwd: Authentication token manipulation error\npasswd: password unchanged'

        def _useradd(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return 'useradd: Permission denied.'

        def _last(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return (
                'admin    pts/0        192.168.1.100    Thu May 29 17:00   still logged in\n'
                'root     pts/1        192.168.1.50     Thu May 29 16:00 - 16:30  (00:30)\n\n'
                'wtmp begins Mon Apr 15 09:00:00 2024'
            )

        # ── package managers ──────────────────────────────────────────────────

        def _apt(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            if not args:
                return ''
            sub = args[0]
            if sub in ('update', 'upgrade'):
                return 'E: Could not open lock file /var/lib/dpkg/lock-frontend - open (13: Permission denied)'
            if sub == 'install':
                return 'E: Could not open lock file /var/lib/dpkg/lock - open (13: Permission denied)'
            return ''

        # ── misc ──────────────────────────────────────────────────────────────

        def _chmod(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            if len(args) < 2:
                return 'chmod: missing operand'
            return ''

        def _crontab(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            if '-l' in args:
                return f'# no crontab for {s.username}'
            return ''

        def _python(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            if not args:
                return (
                    'Python 3.8.10 (default, Nov 14 2022, 12:59:47)\n'
                    'Type "help", "copyright", "credits" or "license" for more information.\n'
                    '>>>'
                )
            return ''

        def _which(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            known = {
                'bash': '/bin/bash', 'sh': '/bin/sh',
                'python': '/usr/bin/python3', 'python3': '/usr/bin/python3',
                'wget': '/usr/bin/wget', 'curl': '/usr/bin/curl',
                'nc': '/usr/bin/nc', 'nmap': '/usr/bin/nmap',
                'cat': '/bin/cat', 'ls': '/bin/ls',
                'id': '/usr/bin/id', 'whoami': '/usr/bin/whoami',
                'grep': '/bin/grep', 'find': '/usr/bin/find',
                'systemctl': '/bin/systemctl', 'service': '/usr/sbin/service',
            }
            return known.get(args[0], '') if args else ''

        def _exit(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            s.should_exit = True
            return ''

        def _clear(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return '\x1b[2J\x1b[H'   # ANSI clear screen + cursor home

        def _mkdir(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return '' if args else 'mkdir: missing operand'

        def _touch(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return ''

        def _rm(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            real = [a for a in args if not a.startswith('-')]
            if not real:
                return '' if args else 'rm: missing operand'
            path = fs.resolve(s.cwd, real[0])
            if not fs.exists(path):
                return f"rm: cannot remove '{real[0]}': No such file or directory"
            return ''

        def _cp(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            if len([a for a in args if not a.startswith('-')]) < 2:
                return 'cp: missing file operand'
            return ''

        def _mv(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            if len([a for a in args if not a.startswith('-')]) < 2:
                return 'mv: missing file operand'
            return ''

        def _head_tail(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            targets = [a for a in args if not a.startswith('-')]
            if not targets:
                return ''
            path = fs.resolve(s.cwd, targets[-1])
            content = fs.read(path)
            if content is None:
                return f"head: cannot open '{targets[-1]}' for reading: No such file or directory"
            lines = content.rstrip('\n').splitlines()
            return '\n'.join(lines[-10:] if 'tail' in targets[0:1] else lines[:10])

        def _wc(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            targets = [a for a in args if not a.startswith('-')]
            if not targets:
                return '0 0 0'
            path = fs.resolve(s.cwd, targets[-1])
            content = fs.read(path)
            if content is None:
                return f"wc: {targets[-1]}: No such file or directory"
            lines = content.splitlines()
            words = content.split()
            return f'{len(lines):7d} {len(words):7d} {len(content):7d} {targets[-1]}'

        def _grep(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            real = [a for a in args if not a.startswith('-')]
            if len(real) < 2:
                return ''
            pattern, target = real[0], real[-1]
            content = fs.read(fs.resolve(s.cwd, target))
            if content is None:
                return f"grep: {target}: No such file or directory"
            return '\n'.join(line for line in content.splitlines() if pattern.strip('"\'') in line)

        def _find(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            start = args[0] if args and not args[0].startswith('-') else s.cwd
            path = fs.resolve(s.cwd, start)
            if not fs.exists(path):
                return f"find: '{start}': No such file or directory"
            if path == '/':
                return '/etc/passwd\n/etc/shadow\n/root/.ssh/id_rsa\n/tmp/tmpfile\n/var/log/auth.log'
            if fs.is_dir(path):
                return '\n'.join(path.rstrip('/') + '/' + item for item in fs.listdir(path))
            return path

        def _who(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return f'{s.username}    pts/0        2026-05-29 17:30 (192.168.1.50)'

        def _w(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return (
                ' 17:30:00 up 42 days,  1 user,  load average: 0.12, 0.08, 0.05\n'
                'USER     TTY      FROM             LOGIN@   IDLE   JCPU   PCPU WHAT\n'
                f'{s.username:<8} pts/0    192.168.1.50     17:30    1.00s  0.01s  0.00s -bash'
            )

        def _systemctl(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            if not args or args[0] in ('status', 'list-units'):
                return (
                    'ssh.service loaded active running OpenBSD Secure Shell server\n'
                    'cron.service loaded active running Regular background program processing daemon\n'
                    'nginx.service loaded active running A high performance web server'
                )
            if args[0] in ('start', 'stop', 'restart', 'enable', 'disable'):
                return 'Failed to connect to bus: Permission denied'
            return ''

        def _service(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            if not args or '--status-all' in args:
                return ' [ + ]  cron\n [ + ]  ssh\n [ + ]  nginx\n [ - ]  apache2'
            return ''

        def _iptables(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            if '-L' in args or not args:
                return (
                    'Chain INPUT (policy ACCEPT)\n'
                    'target     prot opt source               destination\n'
                    'ACCEPT     tcp  --  anywhere             anywhere             tcp dpt:ssh'
                )
            return 'iptables v1.8.4: Permission denied (you must be root)'

        def _docker(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return 'Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?'

        def _uname_like(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return 'Ubuntu 20.04.6 LTS'

        def _man(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return f'No manual entry for {args[0]}' if args else 'What manual page do you want?'

        def _help(args: list[str], s: 'ShellSession', fs: VirtualFS) -> str:
            return (
                'GNU bash, version 5.0.17(1)-release (x86_64-pc-linux-gnu)\n'
                'Available: ls  cd  pwd  cat  echo  whoami  id  uname  ps  ifconfig\n'
                '           netstat  ss  df  free  env  history  last  wget  curl\n'
                '           nmap  nc  ssh  scp  sudo  passwd  chmod  crontab  exit'
            )

        # ── register all ──────────────────────────────────────────────────────

        h.update({
            'ls': _ls, 'll': lambda a,s,f: _ls(['-la']+a,s,f), 'la': lambda a,s,f: _ls(['-a']+a,s,f),
            'cd': _cd,
            'pwd':   lambda a,s,f: s.cwd,
            'whoami':lambda a,s,f: s.username,
            'id':    lambda a,s,f: (
                'uid=0(root) gid=0(root) groups=0(root)' if s.username == 'root'
                else f'uid=1000({s.username}) gid=1000({s.username}) groups=1000({s.username}),27(sudo)'
            ),
            'hostname': lambda a,s,f: 'ubuntu-server',
            'uptime':   lambda a,s,f: ' 17:30:00 up 42 days,  3:15,  1 user,  load average: 0.12, 0.08, 0.05',
            'uname': _uname, 'cat': _cat, 'echo': _echo, 'file': _file,
            'ps': _ps, 'ifconfig': _ifconfig, 'ip': _ip,
            'netstat': _netstat, 'ss': _netstat,
            'df': _df, 'free': _free, 'env': _env, 'printenv': _env,
            'history': _history,
            'nmap': _nmap, 'wget': _wget, 'curl': _curl,
            'nc': _nc, 'ncat': _nc, 'netcat': _nc,
            'ssh': _ssh_cmd, 'scp': _scp,
            'sudo': _sudo, 'su': _sudo,
            'passwd': _passwd, 'useradd': _useradd, 'usermod': _useradd,
            'last': _last,
            'apt': _apt, 'apt-get': _apt,
            'chmod': _chmod, 'chown': lambda a,s,f: '',
            'crontab': _crontab,
            'python': _python, 'python3': _python,
            'which': _which, 'whereis': _which,
            'mkdir': _mkdir, 'touch': _touch, 'rm': _rm, 'rmdir': _rm,
            'cp': _cp, 'mv': _mv,
            'head': _head_tail, 'tail': lambda a,s,f: _head_tail(['__tail__'] + a, s, f),
            'wc': _wc, 'grep': _grep, 'find': _find,
            'who': _who, 'users': lambda a,s,f: s.username, 'w': _w,
            'systemctl': _systemctl, 'service': _service,
            'iptables': _iptables, 'ufw': lambda a,s,f: 'Status: inactive',
            'docker': _docker, 'podman': _docker,
            'lsb_release': _uname_like, 'hostnamectl': lambda a,s,f: 'Static hostname: ubuntu-server\nOperating System: Ubuntu 20.04.6 LTS\nKernel: Linux 5.15.0-91-generic',
            'kill': lambda a,s,f: '', 'pkill': lambda a,s,f: '',
            'tar': lambda a,s,f: '', 'gzip': lambda a,s,f: '', 'gunzip': lambda a,s,f: '',
            'tee': lambda a,s,f: '',
            'base64': lambda a,s,f: '',
            'man': _man, 'help': _help,
            'exit': _exit, 'logout': _exit, 'quit': _exit,
            'clear': _clear, 'reset': _clear,
        })
