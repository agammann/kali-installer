"""Boot an unchanged installer ISO through its menu, without disks or networking."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess
import time


class Monitor:
    def __init__(self, path, vm, deadline):
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.settimeout(5)
        while True:
            try:
                self.socket.connect(str(path))
                break
            except (FileNotFoundError, ConnectionRefusedError):
                if vm.poll() is not None or time.monotonic() >= deadline:
                    self.socket.close()
                    raise RuntimeError('QEMU did not expose its private QMP socket')
                time.sleep(0.1)
        self.stream = self.socket.makefile('rwb')
        greeting = json.loads(self.stream.readline())
        if 'QMP' not in greeting:
            raise RuntimeError('Unexpected QMP greeting')
        self.call('qmp_capabilities')

    def call(self, command, arguments=None):
        request = {'execute': command}
        if arguments is not None:
            request['arguments'] = arguments
        self.stream.write(json.dumps(request).encode() + b'\n')
        self.stream.flush()
        while True:
            response = json.loads(self.stream.readline())
            if 'error' in response:
                raise RuntimeError(f'QMP {command} failed: {response["error"]}')
            if 'return' in response:
                return response['return']

    def close(self):
        self.stream.close()
        self.socket.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--firmware', choices=('bios', 'uefi'), required=True)
    args = parser.parse_args()
    iso = args.iso.resolve()
    with iso.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != args.expected_sha256:
        raise SystemExit('ISO checksum differs from the independent expected digest')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    result = {'iso_sha256': digest, 'iso_bytes': iso.stat().st_size,
              'firmware': args.firmware, 'attached_hard_disks': 0, 'network_devices': 0,
              'external_kernel_or_initrd': False, 'screens': [], 'passed': False}
    firmware = []
    if args.firmware == 'uefi':
        code = Path('/usr/share/OVMF/OVMF_CODE_4M.fd')
        template = Path('/usr/share/OVMF/OVMF_VARS_4M.fd')
        if not code.is_file() or not template.is_file():
            raise SystemExit('Plain OVMF firmware templates are required')
        variables = output / 'uefi-vars.fd'
        shutil.copyfile(template, variables)
        firmware = ['-machine', 'q35', '-drive', f'if=pflash,format=raw,readonly=on,file={code}',
                    '-drive', f'if=pflash,format=raw,file={variables}']
        result['secure_boot'] = 'disabled: plain OVMF templates'
        result['uefi_firmware'] = {}
        for path in (code, template):
            with path.open('rb') as stream:
                result['uefi_firmware'][str(path)] = hashlib.file_digest(stream, 'sha256').hexdigest()
    command = ['qemu-system-x86_64', '-enable-kvm', '-cpu', 'host', '-m', '2048', '-smp', '2',
               '-drive', f'file={iso},format=raw,media=cdrom,readonly=on',
               '-boot', 'order=d,strict=on', '-nic', 'none', '-display', 'none',
               '-serial', f'file:{output / "serial.log"}',
               '-qmp', f'unix:{output / "qmp.sock"},server=on,wait=off', '-no-reboot'] + firmware
    result['qemu_command'] = command
    result['qemu_version'] = subprocess.check_output(['qemu-system-x86_64', '--version'], text=True).splitlines()[0]
    started = time.monotonic()
    monitor = None
    with (output / 'qemu.log').open('w') as log:
        vm = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            monitor = Monitor(output / 'qmp.sock', vm, started + 10)

            def wait_screen(stage, deadline, phrases):
                last_saved = 0
                while time.monotonic() < deadline:
                    if vm.poll() is not None:
                        raise RuntimeError(f'QEMU exited before {stage}')
                    screenshot = output / f'{stage}-latest.png'
                    monitor.call('screendump', {'filename': str(screenshot), 'format': 'png'})
                    text = subprocess.check_output(['tesseract', str(screenshot), 'stdout', '--psm', '11'],
                                                   text=True, stderr=subprocess.DEVNULL, timeout=10)
                    normalized = ' '.join(text.lower().split())
                    elapsed = round(time.monotonic() - started, 2)
                    (output / f'{stage}-latest.txt').write_text(text, encoding='utf-8')
                    result['screens'].append({'stage': stage, 'seconds': elapsed, 'text': text})
                    if time.monotonic() >= deadline:
                        break
                    if all(phrase in normalized for phrase in phrases):
                        shutil.copyfile(screenshot, output / f'{stage}.png')
                        (output / f'{stage}.txt').write_text(text, encoding='utf-8')
                        print(f'{stage}: matching screen at {elapsed}s', flush=True)
                        return
                    if elapsed - last_saved >= 30:
                        shutil.copyfile(screenshot, output / f'{stage}-{int(elapsed)}s.png')
                        last_saved = elapsed
                    time.sleep(0.5)
                raise RuntimeError(f'Timed out waiting for {stage}; inspect the original screenshots')

            # This ISO's BIOS menu times out to speech installation after 30 seconds.
            # Require the original Graphical install menu early, before sending Enter.
            wait_screen('boot-menu', started + 25, ['graphical install'])
            result['enter_sent_seconds'] = round(time.monotonic() - started, 2)
            if result['enter_sent_seconds'] >= 25:
                raise RuntimeError('Refusing to select after the BIOS menu deadline')
            monitor.call('send-key', {'keys': [{'type': 'qcode', 'data': 'ret'}], 'hold-time': 100})
            wait_screen('installer-language', started + 270, ['select a language', 'english'])
            result['passed'] = True
            result['scope'] = 'Original ISO menu to graphical language selection only; no disk installation'
        except BaseException as error:
            result['error'] = str(error)
            raise
        finally:
            if monitor is not None:
                monitor.close()
            vm.terminate()
            try:
                vm.wait(timeout=10)
            except subprocess.TimeoutExpired:
                vm.kill()
                vm.wait(timeout=5)
            with iso.open('rb') as stream:
                result['iso_sha256_after'] = hashlib.file_digest(stream, 'sha256').hexdigest()
            if result['iso_sha256_after'] != digest:
                result['passed'] = False
                result['error'] = 'ISO bytes changed during the boot check'
            result['duration_seconds'] = round(time.monotonic() - started, 2)
            (output / 'results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            if result['iso_sha256_after'] != digest:
                raise SystemExit(result['error'])


if __name__ == '__main__':
    main()
