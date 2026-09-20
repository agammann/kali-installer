"""Exercise both download clients against a small real multipart HTTP fixture."""
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
ISO = "kali-linux-rolling-installer-amd64.iso"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class DownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.original = cls.root / ISO
        cls.original.write_bytes(bytes(range(256)) * 11000)
        cls.digest = hashlib.sha256(cls.original.read_bytes()).hexdigest()
        cls.release = cls.root / "release"
        subprocess.run([sys.executable, str(ROOT / "scripts/package-release.py"),
                        str(cls.original), str(cls.release), "--part-mib", "1",
                        "--expected-sha256", cls.digest], check=True, capture_output=True)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(cls.release)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.clients = []
        bash = os.environ.get("KALI_TEST_BASH") or shutil.which("bash")
        powershell = os.environ.get("KALI_TEST_POWERSHELL") or shutil.which("pwsh")
        if bash:
            cls.clients.append(("bash", [bash, str(ROOT / "scripts/download-installer.sh")]))
        if powershell:
            cls.clients.append(("powershell", [powershell, "-NoProfile", "-ExecutionPolicy", "RemoteSigned", "-File", str(ROOT / "scripts/download-installer.ps1")]))
        if not cls.clients:
            raise RuntimeError("Set KALI_TEST_BASH or KALI_TEST_POWERSHELL to a client runtime")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def invoke(self, client, output, offline=False):
        name, command = client
        if name == "bash":
            args = ["--output", str(output), "--base-url", self.url]
            if offline:
                args.append("--offline")
        else:
            args = ["-OutputDirectory", str(output), "-BaseUrl", self.url]
            if offline:
                args.append("-Offline")
        return subprocess.run(command + args, capture_output=True, text=True, timeout=120)

    def test_download_resume_and_exact_reassembly(self):
        for client in self.clients:
            with self.subTest(client=client[0]):
                output = self.root / (client[0] + " download with spaces")
                output.mkdir()
                # Preserve a verified first part; download the other two.
                part = ISO + ".part001"
                shutil.copyfile(self.release / part, output / part)
                result = self.invoke(client, output)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("Verified cached part", result.stdout)
                self.assertEqual((output / ISO).read_bytes(), self.original.read_bytes())
                self.assertEqual(self.invoke(client, output, offline=True).returncode, 0)

    def test_reject_incomplete_corrupt_and_misleading_inputs(self):
        for client in self.clients:
            for case in ("missing", "truncated", "duplicate", "path", "whole-hash", "existing-iso"):
                with self.subTest(client=client[0], case=case):
                    output = self.root / (client[0] + "-" + case)
                    shutil.copytree(self.release, output)
                    manifest = output / "SHA256SUMS"
                    text = manifest.read_text()
                    if case == "missing":
                        (output / (ISO + ".part002")).unlink()
                    elif case == "truncated":
                        (output / (ISO + ".part001")).write_bytes(b"truncated")
                    elif case == "duplicate":
                        manifest.write_bytes((text + text.splitlines()[1] + "\n").encode())
                    elif case == "path":
                        manifest.write_bytes(text.replace(ISO + ".part001", "../outside").encode())
                    elif case == "whole-hash":
                        manifest.write_bytes(text.replace(self.digest, "0" * 64, 1).encode())
                    else:
                        (output / ISO).write_bytes(b"keep this file")
                    result = self.invoke(client, output, offline=True)
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    expected_error = {
                        "missing": "Missing or corrupt part",
                        "truncated": "Missing or corrupt part",
                        "duplicate": "Invalid or out-of-order part name",
                        "path": "Invalid or out-of-order part name",
                        "whole-hash": "Reconstructed ISO checksum mismatch",
                        "existing-iso": "Existing ISO has a different checksum",
                    }[case]
                    self.assertIn(expected_error, result.stdout + result.stderr)
                    if case == "existing-iso":
                        self.assertEqual((output / ISO).read_bytes(), b"keep this file")
                    else:
                        self.assertFalse((output / ISO).exists())
                    self.assertFalse(list(output.glob(".download-*")))
                    self.assertFalse(list(output.glob(".iso.*")))
                    self.assertFalse(list(output.glob(".part.*")))
                    self.assertFalse(list(output.glob(".manifest.*")))

    def test_packager_refuses_wrong_original_checksum(self):
        output = self.root / "bad-package"
        result = subprocess.run([sys.executable, str(ROOT / "scripts/package-release.py"),
                                 str(self.original), str(output), "--expected-sha256", "0" * 64],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((output / "SHA256SUMS").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
