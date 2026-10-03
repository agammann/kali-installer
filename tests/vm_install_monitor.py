"""Bounded installer wait with early detection of a fatal package prompt."""
import re
import subprocess
import time


def corrupt_package_prompt(text):
    plain = re.sub(r'\x1b(?:\[[0-?]*[ -/]*[@-~]|[()][A-Z0-9]|=)', '', text)
    warning = plain.find('!! ERROR: Debootstrap warning')
    return warning >= 0 and bool(re.search(
        r'was\s+corrupt\s*\[Press enter to continue\]', plain[warning:warning + 2000]))


def wait_for_installer(vm, serial_log, timeout=7200):
    started = time.monotonic()
    deadline = started + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(vm.args, timeout)
        try:
            return vm.wait(timeout=min(30, remaining))
        except subprocess.TimeoutExpired:
            if serial_log.exists():
                # Inspect locally; do not copy guest console contents into CI logs.
                with serial_log.open('rb') as stream:
                    stream.seek(0, 2)
                    size = stream.tell()
                    stream.seek(max(0, size - 65536))
                    tail = stream.read().decode(errors='replace')
                if corrupt_package_prompt(tail):
                    raise RuntimeError('Installer rejected a package as corrupt; inspect installer-serial.log')
                print(f'Installer still running after {int(time.monotonic() - started)}s; '
                      f'serial log contains {size} bytes', flush=True)
