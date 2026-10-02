"""Check the narrow debian-cd backport without changing system build tools."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    'checksum_fix', Path(__file__).resolve().parents[1] / 'scripts/fix-debian-cd-checksums.py')
checksum_fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checksum_fix)

# Relevant end of checksum_files_for_release in debian-cd 3.2.3.
SECTION = '''sub checksum_files_for_release {
\tprint RELEASE "SHA256:\\n";
\t$current_checksum_type = "sha256";
\tfind (\\&find_and_checksum_files_for_release, ".");
\tprint RELEASE "SHA512:\\n";
\t$current_checksum_type = "sha512";
\tfind (\\&find_and_checksum_files_for_release, ".");
}
'''


class ChecksumBackportTests(unittest.TestCase):
    def test_exact_upstream_removal_and_repeat(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'make_disc_trees.pl'
            path.write_text('# prefix\n' + SECTION + '# suffix\n')
            checksum_fix.fix(path)
            updated = path.read_text()
            self.assertEqual(updated, '# prefix\n' + SECTION[:SECTION.index('\tprint RELEASE "SHA512:')] + '}\n# suffix\n')
            checksum_fix.fix(path)
            self.assertEqual(path.read_text(), updated)

    def test_unknown_checksum_code_leaves_file_unchanged(self):
        for source in [SECTION.replace('sha512"', 'sha512-extra"'),
                       SECTION.replace('SHA256:', 'SHA256-renamed:')]:
            with self.subTest(source=source), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'make_disc_trees.pl'
                path.write_text(source)
                with self.assertRaises(ValueError):
                    checksum_fix.fix(path)
                self.assertEqual(path.read_text(), source)


if __name__ == '__main__':
    unittest.main()
