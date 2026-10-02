"""Regression coverage for the narrowly scoped LightDM account correction."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROFILE = (ROOT / 'simple-cdd/profiles/kali.postinst').read_text()
FUNCTION = re.search(r'^configure_lightdm_account\(\) \{\n.*?^\}', PROFILE, re.M | re.S).group()
BASH = os.environ.get('KALI_TEST_BASH') or shutil.which('bash')


@unittest.skipUnless(BASH, 'Bash is required')
class LightdmAccountTests(unittest.TestCase):
    def run_guard(self, version='1.33.1-3', password='!*', expiry='1', shell='/bin/false'):
        script = '''
dpkg-query() { printf '%s' "$TEST_VERSION"; }
getent() {
    case "$1:$2" in
        passwd:lightdm) printf 'lightdm:x:967:967:Light Display Manager:/var/lib/lightdm:%s\\n' "$TEST_SHELL" ;;
        shadow:lightdm) printf 'lightdm:%s:20000:::::%s:\\n' "$TEST_PASSWORD" "$TEST_EXPIRY" ;;
        *) return 1 ;;
    esac
}
usermod() { printf 'USERMOD'; printf ' <%s>' "$@"; printf '\\n'; }
''' + FUNCTION + '\nconfigure_lightdm_account\n'
        result = subprocess.run([BASH, '-c', script], capture_output=True, text=True,
                                env={**os.environ, 'TEST_VERSION': version, 'TEST_PASSWORD': password,
                                     'TEST_EXPIRY': expiry, 'TEST_SHELL': shell})
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_only_known_packaged_expiry_is_changed(self):
        for version in ('1.33.1-2', '1.33.1-3'):
            with self.subTest(version=version):
                mutations = [line for line in self.run_guard(version=version).splitlines()
                             if line.startswith('USERMOD')]
                self.assertEqual(mutations, ['USERMOD <--expiredate> <-1> <lightdm>'])
        for overrides in ({'version': '1.33.1-1'}, {'version': '1.33.1-4'}, {'version': ''},
                          {'password': '$6$existing-hash'}, {'password': ''}, {'password': '*'},
                          {'expiry': ''}, {'expiry': '22000'}, {'shell': '/bin/sh'}):
            with self.subTest(overrides=overrides):
                self.assertNotIn('USERMOD', self.run_guard(**overrides))

if __name__ == '__main__':
    unittest.main(verbosity=2)
