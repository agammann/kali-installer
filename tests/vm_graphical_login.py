"""Bounded graphical acceptance for the disposable, exact-image test guest."""
import hashlib
import json
import re
import shlex
import socket
import struct
import time


PREVIEW_SHA256 = '63cb32037e6d8c4e590f8f8f727aecddedab7fd131f0b92eb5895373b50227df'

SESSION_QUERY = r'''
import json, os, subprocess
uid = os.getuid()
sessions = []
for line in subprocess.check_output(['loginctl', 'list-sessions', '--no-legend', '--no-pager'], text=True, timeout=4).splitlines():
    sid = line.split()[0]
    data = subprocess.check_output(['loginctl', 'show-session', sid, '--no-pager',
        '-p', 'User', '-p', 'Name', '-p', 'Seat', '-p', 'Type', '-p', 'Class',
        '-p', 'Active', '-p', 'State', '-p', 'Remote', '-p', 'Display'], text=True, timeout=4)
    item = dict(line.split('=', 1) for line in data.splitlines() if '=' in line)
    item['Id'] = sid
    sessions.append(item)
processes = {}
for name in ['xfce4-session', 'xfce4-panel']:
    processes[name] = subprocess.run(['pgrep', '-u', str(uid), '-x', name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4).returncode == 0
print(json.dumps({'uid': uid, 'sessions': sessions, 'processes': processes}))
'''

BASELINE = {
    'mounts': 'findmnt --all --output TARGET,SOURCE,FSTYPE,OPTIONS; cat /proc/1/mountinfo; lsblk --output NAME,TYPE,FSTYPE,SIZE,RO,MOUNTPOINTS',
    'configuration': 'cat /etc/fstab; cat /proc/cmdline',
    'root_var': 'for p in / /var /var/lib /var/log /var/cache; do printf "Path: %s\\n" "$p"; findmnt --target "$p" --output TARGET,SOURCE,FSTYPE,OPTIONS; done',
    'mount_units': 'systemctl status --no-pager --full -- systemd-remount-fs.service -.mount var.mount systemd-fsck-root.service local-fs.target; journalctl --boot --no-pager --output=short-monotonic --unit=systemd-remount-fs.service --unit=-.mount --unit=var.mount --unit=systemd-fsck-root.service --unit=local-fs.target',
    'kernel': 'journalctl --boot --dmesg --no-pager --output=short-monotonic',
}


def guest_command(client, command, seconds, password=None):
    """Bound output and elapsed time; never return a credential-bearing request."""
    limit = 2 * 1024 * 1024
    deadline = time.monotonic() + seconds
    shell = 'timeout ' + str(max(1, int(seconds) - 1)) + ' sh -c ' + shlex.quote(command)
    if password is not None:
        shell = 'sudo -S -p "" -- ' + shell
    stdin, stdout, _ = client.exec_command(shell, timeout=seconds)
    channel = stdout.channel
    if password is not None:
        stdin.write(password + '\n')
        stdin.flush()
    stdin.channel.shutdown_write()
    out, err = bytearray(), bytearray()
    try:
        while True:
            if channel.recv_ready():
                out.extend(channel.recv(65536))
            if channel.recv_stderr_ready():
                err.extend(channel.recv_stderr(65536))
            if len(out) + len(err) > limit:
                raise RuntimeError('Guest evidence output exceeded the bound')
            if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
                return {'exit': channel.recv_exit_status(), 'stdout': out.decode(errors='replace'),
                        'stderr': err.decode(errors='replace')}
            if time.monotonic() >= deadline:
                raise TimeoutError('Guest evidence command exceeded the deadline')
            time.sleep(0.05)
    finally:
        channel.close()


def capture_filesystem_baseline(client, password, root):
    record = {'purpose': 'Current guest baseline only; does not explain the historical failure', 'commands': {}}
    for name, command in BASELINE.items():
        try:
            record['commands'][name] = guest_command(client, command, 30, password)
        except Exception as error:
            record['commands'][name] = {'error_type': type(error).__name__}
    (root / 'filesystem-baseline.log').write_text(json.dumps(record, indent=2))


def accepted_session(observation):
    uid = str(observation['uid'])
    sessions = [item for item in observation['sessions']
                if item.get('User') == uid and item.get('Name') == 'installtest'
                and item.get('Seat') == 'seat0' and item.get('Class') == 'user'
                and item.get('Type') in ('x11', 'wayland') and item.get('Remote') == 'no'
                and item.get('Active') == 'yes' and item.get('State') == 'active']
    if len(sessions) != 1 or not all(observation['processes'].get(name) is True
                                   for name in ('xfce4-session', 'xfce4-panel')):
        return None
    return sessions[0]


def credential_keys(value):
    # secrets.token_urlsafe(24) and the fixed fixture username use only these keys.
    if not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise ValueError('Unsupported fixture keyboard character')
    for char in value:
        if char == '_':
            yield ['shift', 'minus']
        elif char == '-':
            yield ['minus']
        elif char.isupper():
            yield ['shift', char.lower()]
        else:
            yield [char]


class Monitor:
    def __init__(self, path, deadline):
        self.deadline = deadline
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.stream = None
        self.sequence = 0
        try:
            self.sock.settimeout(self.remaining())
            self.sock.connect(str(path))
            self.stream = self.sock.makefile('rwb')
            greeting = self.receive()
            if 'QMP' not in greeting:
                raise RuntimeError('Unexpected QMP greeting')
            self.command('qmp_capabilities')
        except Exception:
            self.close()
            raise

    def remaining(self):
        seconds = self.deadline - time.monotonic()
        if seconds <= 0:
            raise TimeoutError('Graphical login deadline exceeded')
        return min(5, seconds)

    def receive(self):
        self.sock.settimeout(self.remaining())
        line = self.stream.readline(65537)
        if not line or len(line) > 65536:
            raise RuntimeError('Invalid QMP response length')
        return json.loads(line)

    def command(self, name, arguments=None):
        self.sequence += 1
        request = {'execute': name, 'id': self.sequence}
        if arguments is not None:
            request['arguments'] = arguments
        self.sock.settimeout(self.remaining())
        self.stream.write(json.dumps(request).encode() + b'\n')
        self.stream.flush()
        while True:
            response = self.receive()
            if response.get('id') != self.sequence:
                continue
            if 'error' in response:
                # Do not include server replies or requests: key events contain the fixture password.
                raise RuntimeError('QMP command rejected')
            if 'return' in response:
                return response['return']

    def key(self, *codes):
        self.command('send-key', {'keys': [{'type': 'qcode', 'data': code} for code in codes], 'hold-time': 40})
        time.sleep(0.08)  # Release each chord before the next, including shifted characters.

    def close(self):
        if self.stream is not None:
            self.stream.close()
        self.sock.close()


def verify_graphical_login(client, password, root):
    deadline = time.monotonic() + 120
    record = {'status': 'running', 'attempts': 0, 'deadline_seconds': 120,
              'stage': 'greeter_geometry',
              'method': 'QMP keyboard and pointer input to the unchanged LightDM greeter',
              'observations': []}
    monitor = None
    try:
        # The fixed ISO's reviewed greeter is 1280x800. Refuse other geometry before typing.
        header = (root / 'desktop-login.png').read_bytes()[:24]
        if header[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>II', header[16:24]) != (1280, 800):
            raise RuntimeError('Unreviewed greeter dimensions')
        query = 'python3 -c ' + shlex.quote(SESSION_QUERY)
        record['stage'] = 'initial_sessions'
        initial = guest_command(client, query, 10)
        if initial['exit'] != 0:
            raise RuntimeError('Unable to inspect graphical sessions')
        before = json.loads(initial['stdout'])
        record['before'] = before
        if any(item.get('Class') == 'user' and item.get('Seat') == 'seat0' for item in before['sessions']):
            raise RuntimeError('A local user session already exists')
        monitor = Monitor(root / 'qmp.sock', deadline)
        record['stage'] = 'greeter_focus'
        monitor.command('input-send-event', {'events': [
            {'type': 'abs', 'data': {'axis': 'x', 'value': round(690 * 32767 / 1279)}},
            {'type': 'abs', 'data': {'axis': 'y', 'value': round(353 * 32767 / 799)}},
            {'type': 'btn', 'data': {'down': True, 'button': 'left'}},
            {'type': 'btn', 'data': {'down': False, 'button': 'left'}},
        ]})
        monitor.key('ctrl', 'a')
        record['stage'] = 'fixture_credentials'
        for keys in credential_keys('installtest'):
            monitor.key(*keys)
        monitor.key('tab')
        monitor.key('ctrl', 'a')
        for keys in credential_keys(password):
            monitor.key(*keys)
        record['attempts'] = 1
        monitor.key('ret')
        record['stage'] = 'authenticated_session'
        stable = None
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining < 2:
                break
            response = guest_command(client, query, min(10, remaining))
            if response['exit'] != 0:
                raise RuntimeError('Unable to inspect post-login sessions')
            observation = json.loads(response['stdout'])
            record['observations'].append(observation)
            session = accepted_session(observation)
            if session is not None and session['Id'] == stable:
                record['stage'] = 'authenticated_screenshot'
                monitor.command('screendump', {'filename': str(root / 'authenticated-desktop.png'), 'format': 'png'})
                record.update(status='passed', session=session,
                              screenshot_sha256=hashlib.sha256((root / 'authenticated-desktop.png').read_bytes()).hexdigest())
                return
            stable = session['Id'] if session is not None else None
            time.sleep(min(3, max(0, deadline - time.monotonic())))
        raise TimeoutError('No stable authenticated XFCE session before deadline')
    except Exception as error:
        record.update(status='failed', error_type=type(error).__name__)
        # No post-typing failure screenshot: a misplaced credential must never become an artifact.
        raise RuntimeError('Graphical login verification failed; inspect the bounded session record') from None
    finally:
        if monitor is not None:
            try:
                monitor.close()
            except OSError:
                record['monitor_close_error'] = True
        record['finished_monotonic'] = time.monotonic()
        (root / 'graphical-login.json').write_text(json.dumps(record, indent=2))
