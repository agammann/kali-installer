"""Check informational build commands without Debian packages or privileges."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = os.environ.get("KALI_TEST_BASH") or shutil.which("bash")


@unittest.skipUnless(BASH, "Bash is required")
class BuildQueryTests(unittest.TestCase):
    def test_image_queries_preserve_logs_without_running_build_commands(self):
        with tempfile.TemporaryDirectory(prefix="kali build query ") as temp:
            copy = Path(temp)
            for name in ("build.sh", ".getopt.sh"):
                shutil.copyfile(ROOT / name, copy / name)
            for variant in ("default", "netinst"):
                (copy / "kali-config" / f"installer-{variant}").mkdir(parents=True)
            env_file = copy / "env.sh"
            env_file.write_text('''dpkg() { printf '%s\\n' amd64; }
dpkg-query() { echo 'Unexpected package lookup' >&2; exit 90; }
whoami() { echo 'Unexpected privilege check' >&2; exit 91; }
sudo() { echo 'Unexpected sudo' >&2; exit 92; }
rm() { echo 'Unexpected removal' >&2; exit 93; }
cp() { echo 'Unexpected copy' >&2; exit 94; }
build-simple-cdd() { echo 'Unexpected build' >&2; exit 95; }
''', encoding="utf-8", newline="\n")
            env = os.environ | {"BASH_ENV": env_file.as_posix()}
            log = copy / "build.log"
            cases = [
                ([], "kali-linux-rolling-installer-amd64.iso", 0),
                (["--arch", "x64", "--variant", "netinst", "--version", "2026.3",
                  "--subdir", "release candidate"],
                 "release candidate/kali-linux-2026.3-installer-netinst-amd64.iso", 0),
                (["--variant", "missing"], "Unknown variant", 1),
            ]
            for options, expected, code in cases:
                with self.subTest(options=options):
                    log.write_bytes(b"Previous build evidence\n")
                    result = subprocess.run([BASH, str(copy / "build.sh"),
                                             "--get-image-path", *options], env=env,
                                            capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                    self.assertIn(expected, result.stdout + result.stderr)
                    self.assertNotIn("Unexpected", result.stdout + result.stderr)
                    self.assertEqual(log.read_bytes(), b"Previous build evidence\n")
            log.unlink()
            result = subprocess.run([BASH, str(copy / "build.sh"), "--get-image-path"],
                                    env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(log.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
