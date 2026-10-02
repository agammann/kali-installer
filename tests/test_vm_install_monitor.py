import unittest

from vm_install_monitor import corrupt_package_prompt


class InstallerPromptTests(unittest.TestCase):
    def test_corrupt_package_prompt_with_serial_control_sequences(self):
        self.assertTrue(corrupt_package_prompt(
            '!! ERROR: Debootstrap warning\x1b[24;1H\x1b[22A\x1b[M\x1b[22B'
            'Warning: file:///cdrom/pool/example.deb was \x1b[24;1H'
            'corrupt\x1b[24;1H[Press enter to continue]'))

    def test_progress_and_incomplete_or_unrelated_warnings_are_not_fatal(self):
        for text in ['Installing the base system ... 50%',
                     '!! ERROR: Debootstrap warning',
                     'Warning: example was corrupt [Press enter to continue]',
                     '!! ERROR: Debootstrap warning\nRetrying download']:
            with self.subTest(text=text):
                self.assertFalse(corrupt_package_prompt(text))


if __name__ == '__main__':
    unittest.main()
