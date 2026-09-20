"""Install an ISO to a new disposable disk and verify its first standalone boot."""
import argparse
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from pathlib import Path
import secrets
import socket
import subprocess
import threading
import time

import paramiko

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--iso', type=Path, required=True)
parser.add_argument('--output', type=Path, default=Path('/out/vm-test'))
parser.add_argument('--expected-sha256', required=True)
args = parser.parse_args()
ROOT = args.output.resolve()
ROOT.mkdir(parents=True, exist_ok=True)
ssh_log = logging.getLogger('paramiko')
ssh_log.addHandler(logging.FileHandler(ROOT / 'ssh-wait.log'))
ssh_log.propagate = False
ISO = args.iso.resolve()
with ISO.open('rb') as stream:
    iso_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
if iso_hash != args.expected_sha256:
    raise SystemExit('ISO checksum does not match the supplied build record')
DISK = ROOT / 'installed.qcow2'
if DISK.exists():
    raise SystemExit('Refusing to overwrite an existing test disk')
HTTP = ROOT / 'http'
HTTP.mkdir(exist_ok=True)
password = secrets.token_urlsafe(24)
password_hash = subprocess.check_output(['openssl', 'passwd', '-6', '-stdin'], input=password.encode()).decode().strip()
finish = '''#!/bin/sh
set -eu
in-target systemctl enable ssh
in-target systemctl enable serial-getty@ttyS0.service
printf '\nGRUB_CMDLINE_LINUX="console=tty0 console=ttyS0,115200n8"\nGRUB_TERMINAL="console serial"\nGRUB_SERIAL_COMMAND="serial --speed=115200"\n' >> /target/etc/default/grub
in-target update-grub
echo VM_INSTALL_FINISHED > /target/var/log/vm-install-finished
'''
(HTTP / 'finish.sh').write_text(finish)
preseed = f'''d-i debian-installer/locale string en_US.UTF-8
d-i keyboard-configuration/xkb-keymap select us
d-i netcfg/choose_interface select auto
d-i netcfg/get_hostname string kali-install-test
d-i netcfg/get_domain string local
d-i netcfg/hostname string kali-install-test
d-i netcfg/wireless_wep string
d-i passwd/root-login boolean false
d-i passwd/user-fullname string Installer Test
d-i passwd/username string installtest
d-i passwd/user-password-crypted password {password_hash}
d-i clock-setup/utc boolean true
d-i time/zone string Etc/UTC
d-i clock-setup/ntp boolean false
d-i partman-auto/disk string /dev/vda
d-i partman-auto/method string regular
d-i partman-auto/choose_recipe select atomic
d-i partman-partitioning/confirm_write_new_label boolean true
d-i partman/choose_partition select finish
d-i partman/confirm boolean true
d-i partman/confirm_nooverwrite boolean true
d-i partman-lvm/device_remove_lvm boolean true
d-i partman-md/device_remove_md boolean true
d-i apt-setup/use_mirror boolean false
d-i apt-setup/cdrom/set-first boolean false
d-i apt-setup/disable-cdrom-entries boolean true
d-i apt-setup/services-select multiselect
tasksel tasksel/first multiselect standard, desktop, xfce-desktop
kali-linux-default kali-linux-default/tools select default
d-i pkgsel/include string openssh-server kali-desktop-xfce kali-linux-default
d-i pkgsel/upgrade select none
popularity-contest popularity-contest/participate boolean false
d-i grub-installer/only_debian boolean true
d-i grub-installer/bootdev string /dev/vda
d-i finish-install/reboot_in_progress note
d-i cdrom-detect/eject boolean false
d-i debian-installer/exit/poweroff boolean true
d-i preseed/late_command string wget -O /tmp/finish.sh http://10.0.2.2:8766/finish.sh; sh /tmp/finish.sh
'''
(HTTP / 'preseed.cfg').write_text(preseed)
server = ThreadingHTTPServer(('127.0.0.1', 8766), functools.partial(SimpleHTTPRequestHandler, directory=str(HTTP)))
threading.Thread(target=server.serve_forever, daemon=True).start()
for source, target in [('/install.amd/vmlinuz', 'vmlinuz'), ('/install.amd/initrd.gz', 'initrd.gz')]:
    subprocess.run(['xorriso', '-osirrox', 'on', '-indev', str(ISO), '-extract', source, str(ROOT / target)], check=True)
subprocess.run(['qemu-img', 'create', '-f', 'qcow2', str(DISK), '64G'], check=True)
base = ['qemu-system-x86_64', '-enable-kvm', '-cpu', 'host', '-m', '4096', '-smp', '4',
        '-drive', f'file={DISK},format=qcow2,if=virtio', '-display', 'none',
        '-netdev', 'user,id=n0,hostfwd=tcp:127.0.0.1:2222-:22', '-device', 'virtio-net-pci,netdev=n0',
        '-qmp', f'unix:{ROOT}/qmp.sock,server=on,wait=off']
install_args = base + ['-cdrom', str(ISO), '-kernel', str(ROOT / 'vmlinuz'), '-initrd', str(ROOT / 'initrd.gz'),
                      '-append', 'auto=true priority=critical preseed/url=http://10.0.2.2:8766/preseed.cfg console=ttyS0,115200n8 DEBIAN_FRONTEND=text net.ifnames=0',
                      '-serial', 'file:' + str(ROOT / 'installer-serial.log'), '-no-reboot']
print('Starting full installation to a new 64 GiB virtual disk', flush=True)
with (ROOT / 'qemu-install.log').open('w') as log:
    vm = subprocess.Popen(install_args, stdout=log, stderr=subprocess.STDOUT)
    try:
        code = vm.wait(timeout=7200)
    except BaseException:
        vm.terminate()
        vm.wait(timeout=30)
        raise
if code:
    raise SystemExit(f'Installer VM exited {code}; inspect qemu-install.log')
print('Installer powered off. Booting installed disk with ISO removed.', flush=True)
with (ROOT / 'qemu-boot.log').open('w') as log:
    vm = subprocess.Popen(base + ['-boot', 'c', '-serial', 'file:' + str(ROOT / 'first-boot-serial.log')], stdout=log, stderr=subprocess.STDOUT)
    try:
        client = paramiko.SSHClient()
        # This endpoint belongs to the new guest in this private test process.
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        deadline = time.monotonic() + 900
        while True:
            try:
                client.connect('127.0.0.1', port=2222, username='installtest', password=password,
                               look_for_keys=False, allow_agent=False, timeout=10, auth_timeout=10)
                break
            except (OSError, paramiko.SSHException):
                if time.monotonic() > deadline or vm.poll() is not None:
                    raise
                time.sleep(10)
        checks = {
            'created_account_login': 'id',
            'installed_root': 'findmnt -n -o SOURCE,FSTYPE /',
            'kali_identity': '. /etc/os-release; test "$ID" = kali; cat /etc/os-release',
            'installer_completed': 'cat /var/log/vm-install-finished',
            'selected_packages': "dpkg-query -W -f='${Package} ${Status} ${Version}\\n' kali-linux-default kali-desktop-xfce openssh-server",
            'package_consistency': 'dpkg --audit',
            'network_address': 'ip -4 address show; ip route',
            'dns': 'getent ahostsv4 http.kali.org',
            'network_http': 'curl --fail --location --retry 3 --max-time 60 --head https://www.kali.org/',
            'desktop_service': 'for attempt in $(seq 1 24); do systemctl is-active --quiet display-manager && exit 0; sleep 5; done; systemctl is-active display-manager',
        }
        results = {}
        for name, command in checks.items():
            _, stdout, stderr = client.exec_command(command, timeout=300)
            out, err = stdout.read().decode(), stderr.read().decode()
            code = stdout.channel.recv_exit_status()
            results[name] = {'exit': code, 'stdout': out, 'stderr': err}
            print(f'{name}: exit {code}', flush=True)
        results['iso_sha256'] = iso_hash
        results['firmware'] = 'SeaBIOS'
        results['installer_boot_method'] = 'ISO kernel and initrd; original ISO attached as installation media'
        results['installed_boot_method'] = 'Virtual disk only; ISO, kernel, and initrd detached'
        (ROOT / 'results.json').write_text(json.dumps(results, indent=2))
        if any(v['exit'] != 0 for v in results.values() if isinstance(v, dict)):
            raise SystemExit('An installed-system check failed')
        if results['package_consistency']['stdout'].strip():
            raise SystemExit('dpkg audit reported a problem')
        if '/dev/vda' not in results['installed_root']['stdout']:
            raise SystemExit('Root filesystem is not the installed virtual disk')
        if 'VM_INSTALL_FINISHED' not in results['installer_completed']['stdout']:
            raise SystemExit('Missing installer completion marker')
        if results['selected_packages']['stdout'].count('install ok installed') != 3:
            raise SystemExit('Selected packages not fully installed')
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as monitor:
            monitor.connect(str(ROOT / 'qmp.sock'))
            stream = monitor.makefile('rwb')
            stream.readline()
            for command in [
                {'execute': 'qmp_capabilities'},
                {'execute': 'screendump', 'arguments': {'filename': str(ROOT / 'desktop-login.png'), 'format': 'png'}},
            ]:
                stream.write(json.dumps(command).encode() + b'\n')
                stream.flush()
                while True:
                    response = json.loads(stream.readline())
                    if 'error' in response:
                        raise RuntimeError('VM screenshot failed: ' + str(response['error']))
                    if 'return' in response:
                        break
        print('PASS: complete installation, ISO-free disk boot, password login, desktop, packages, and networking', flush=True)
        stdin, stdout, stderr = client.exec_command('sudo -S /sbin/poweroff')
        stdin.write(password + '\n')
        stdin.flush()
        try:
            vm.wait(timeout=60)
        except subprocess.TimeoutExpired:
            pass
        client.close()
    finally:
        vm.terminate()
        vm.wait(timeout=30)
        server.shutdown()
        (HTTP / 'preseed.cfg').unlink(missing_ok=True)
