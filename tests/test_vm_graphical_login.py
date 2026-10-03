"""Focused acceptance and credential-redaction regressions; no guest is started."""
import io
import json
import unittest

from vm_graphical_login import Monitor, accepted_session, credential_keys


class GraphicalAcceptanceTests(unittest.TestCase):
    def observation(self):
        return {'uid': 1000, 'sessions': [{'Id': 'c2', 'User': '1000', 'Name': 'installtest',
                'Seat': 'seat0', 'Class': 'user', 'Type': 'x11', 'Remote': 'no',
                'Active': 'yes', 'State': 'active'}],
                'processes': {'xfce4-session': True, 'xfce4-panel': True}}

    def test_requires_local_authenticated_user_and_desktop(self):
        self.assertEqual(accepted_session(self.observation())['Id'], 'c2')
        for field, value in [('User', '1001'), ('Name', 'lightdm'), ('Seat', ''),
                             ('Class', 'greeter'), ('Type', 'tty'), ('Remote', 'yes'),
                             ('Active', 'no'), ('State', 'closing')]:
            with self.subTest(field=field):
                data = self.observation()
                data['sessions'][0][field] = value
                self.assertIsNone(accepted_session(data))

    def test_rejects_missing_desktop_or_ambiguous_sessions(self):
        for name in ['xfce4-session', 'xfce4-panel']:
            data = self.observation()
            data['processes'][name] = False
            self.assertIsNone(accepted_session(data))
        data = self.observation()
        data['sessions'].append(dict(data['sessions'][0], Id='c3'))
        self.assertIsNone(accepted_session(data))

    def test_generated_password_alphabet_and_no_control_characters(self):
        self.assertEqual(list(credential_keys('aZ09-_')),
                         [['a'], ['shift', 'z'], ['0'], ['9'], ['minus'], ['shift', 'minus']])
        for invalid in ['a\nb', 'a\tb', 'a b', 'é', '']:
            with self.assertRaises(ValueError):
                list(credential_keys(invalid))

    def test_qmp_error_never_echoes_credential_material(self):
        class FakeSocket:
            def settimeout(self, _):
                pass
        monitor = Monitor.__new__(Monitor)
        monitor.sock = FakeSocket()
        monitor.stream = io.BytesIO()
        monitor.sequence = 0
        monitor.remaining = lambda: 1
        monitor.receive = lambda: {'id': 1, 'error': {'desc': 'fixture-secret-do-not-log'}}
        with self.assertRaisesRegex(RuntimeError, '^QMP command rejected$'):
            monitor.command('send-key', {'keys': [{'type': 'qcode', 'data': 'a'}]})
        self.assertEqual(json.loads(monitor.stream.getvalue())['execute'], 'send-key')


if __name__ == '__main__':
    unittest.main()
