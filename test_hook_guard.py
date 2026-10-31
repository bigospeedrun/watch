"""Offline checks for the dead-man webhook guard (hook_guard.py)."""
import hashlib
import hmac
import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import hook_guard as g

T0 = datetime(2026, 10, 31, 15, 0, tzinfo=timezone.utc)
SECRET = 'good-secret'


class Hook(BaseHTTPRequestHandler):
    """A stand-in for the Isomux hook: 200 for a good signature and an unmatched event, 401 for a bad one."""
    mode = 'hook'
    seen = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        Hook.seen.append((self.headers['X-Sig'], self.headers['X-Event'], body))
        good = 'sha256=' + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
        code = 500 if Hook.mode == 'down' else 200 if self.headers['X-Sig'] == good else 401
        self.send_response(code)
        self.end_headers()
        self.wfile.write(b'SECRET BODY')

    def log_message(self, *args):
        pass


class GuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(('127.0.0.1', 0), Hook)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)
        (self.root / '.git').mkdir()
        self.write_config(SECRET)
        Hook.mode, Hook.seen = 'hook', []
        self.pages, self.resolves = [], []

    def tearDown(self):
        self.dir.cleanup()

    def write_config(self, secret):
        (self.root / 'secret').write_text(secret + '\n')
        (self.root / g.CONFIG).write_text(json.dumps(dict(
            hook_url=f'http://127.0.0.1:{self.server.server_port}/hooks/x', secret_file=str(self.root / 'secret'),
            signature_header='X-Sig', event_header='X-Event')))

    def go(self, check, minutes=0, **kw):
        return g.run(check, lambda title, body: self.pages.append((title, body)), lambda: self.resolves.append(1),
                     root=self.root, now=T0 + timedelta(minutes=minutes), **kw)

    def state(self):
        return json.loads((self.root / g.STATE).read_text())

    def test_the_probe_signs_like_webhook_send_and_uses_an_event_no_rule_matches(self):
        self.assertEqual(g.probe(self.root), ('ok', None))
        sig, event, body = Hook.seen[0]
        self.assertEqual((event, sig), (g.EVENT, 'sha256=' + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()))
        self.assertNotIn(event, ('deadman', 'digest'), 'the hook rules match these two; a probe must not start a turn')

    def test_a_stale_secret_is_refused_and_a_down_office_or_missing_file_is_a_failure(self):
        self.write_config('old-secret')
        self.assertEqual(g.probe(self.root), ('refused', 401))
        Hook.mode = 'down'
        self.write_config(SECRET)
        self.assertEqual(g.probe(self.root), ('failed', 500))
        self.assertEqual(g.probe(self.root / 'missing'), ('config', 'FileNotFoundError'))
        (self.root / g.CONFIG).write_text(json.dumps(dict(hook_url='http://127.0.0.1:9/h', secret_file=str(self.root / 'secret'),
                                                          signature_header='X-Sig', event_header='X-Event')))
        self.assertEqual(g.probe(self.root, timeout=2)[0], 'failed')

    def test_a_good_probe_pages_nothing_and_writes_the_state(self):
        result = self.go(lambda: ('ok', None))
        self.assertEqual((result['status'], self.pages, self.resolves), ('ok', [], []))
        self.assertEqual(self.state()['last_ok'], T0.isoformat(timespec='seconds'))

    def test_a_refused_secret_pages_at_once_with_the_fix_and_no_secret(self):
        result = self.go(lambda: ('refused', 401))
        self.assertTrue(result['paged'])
        title, body = self.pages[0]
        self.assertIn('401', title)
        self.assertIn('rotates the secret', body)
        self.assertIn('/.git/deadman.json', body)
        self.assertNotIn(SECRET, title + body)

    def test_another_failure_pages_after_two_failed_passes_in_a_row_whatever_the_detail(self):
        self.go(lambda: ('failed', 'URLError'))
        self.assertEqual(self.pages, [])
        result = self.go(lambda: ('failed', 500), minutes=60)  # a flapping outage is still an outage
        self.assertEqual((len(self.pages), result['paged'], result['failures']), (1, True, 2))

    def test_one_good_pass_between_two_failures_starts_the_count_again(self):
        self.go(lambda: ('failed', 500))
        self.go(lambda: ('ok', None), minutes=60)
        self.go(lambda: ('failed', 500), minutes=120)
        self.assertEqual((self.pages, self.state()['failures']), ([], 1))

    def test_a_good_probe_resolves_the_page_once(self):
        self.go(lambda: ('refused', 401))
        self.go(lambda: ('ok', None), minutes=60)
        self.go(lambda: ('ok', None), minutes=120)
        self.assertEqual((len(self.resolves), self.state()['paged'], self.state()['failures']), (1, False, 0))

    def test_a_page_that_cannot_be_sent_is_tried_again_next_pass(self):
        calls = []
        def broken(title, body):
            calls.append(1)
            raise OSError('office down')
        result = g.run(lambda: ('refused', 401), broken, lambda: None, root=self.root, now=T0)
        self.assertEqual((result['paged'], result['status']), (False, 'problem: refused:401; page failed: OSError'))
        g.run(lambda: ('refused', 401), lambda t, b: self.pages.append(1), lambda: None, root=self.root, now=T0 + timedelta(minutes=60))
        self.assertEqual((len(calls), len(self.pages)), (1, 1))

    def test_a_failed_re_raise_keeps_an_open_page_so_a_good_probe_still_resolves_it(self):
        self.go(lambda: ('refused', 401))
        def broken(title, body):
            raise OSError('office down')
        self.assertTrue(g.run(lambda: ('refused', 401), broken, lambda: None, root=self.root, now=T0 + timedelta(minutes=60))['paged'])
        self.go(lambda: ('ok', None), minutes=120)
        self.assertEqual((len(self.resolves), self.state()['paged']), (1, False))

    def test_the_lead_gets_one_message_for_the_first_page_and_one_for_the_recovery(self):
        told = []
        def go(check, minutes, tell=told.append):
            return g.run(check, lambda t, b: self.pages.append(t), lambda: self.resolves.append(1), root=self.root,
                         now=T0 + timedelta(minutes=minutes), tell=tell)
        go(lambda: ('refused', 401), 0)
        go(lambda: ('refused', 401), 60)
        self.assertEqual((len(self.pages), len(told)), (2, 1), 'each pass raises the page; the lead hears it once')
        self.assertIn('rotates the secret', told[0])
        self.assertNotIn(SECRET, told[0])
        go(lambda: ('ok', None), 120)
        go(lambda: ('ok', None), 180)
        self.assertEqual((len(told), 'accepts our alerts again' in told[1]), (2, True))

    def test_a_message_to_the_lead_that_fails_never_blocks_the_page_or_the_state(self):
        def broken(text):
            raise OSError('office down')
        result = g.run(lambda: ('refused', 401), lambda t, b: self.pages.append(t), lambda: None, root=self.root, now=T0, tell=broken)
        self.assertEqual((len(self.pages), result['paged'], self.state()['paged']), (1, True, True))

    def test_an_unreadable_state_file_starts_again_instead_of_failing_every_pass(self):
        (self.root / g.STATE).write_text('{not json')
        result = self.go(lambda: ('refused', 401))
        self.assertEqual((result['paged'], result['failures']), (True, 1))
        self.assertEqual(self.state()['paged'], True)

    def test_the_office_address_is_fixed_and_the_lead_comes_from_the_office_config(self):
        self.assertEqual(g.OFFICE, 'http://localhost:4000')
        self.assertNotIn('environ.get(\'ISOMUX_OFFICE', Path(g.__file__).read_text(), 'the bearer token must not follow an environment variable')
        (self.root / g.LEAD_CONFIG).write_text(json.dumps(dict(lead='agent-1')))
        self.assertEqual(g.lead_id(self.root), 'agent-1')
        (self.root / g.LEAD_CONFIG).write_text('{}')
        with self.assertRaises(RuntimeError):
            g.lead_id(self.root)

    def test_a_repeated_problem_raises_the_same_page_key_each_pass(self):
        self.go(lambda: ('refused', 401))
        self.go(lambda: ('refused', 401), minutes=60)
        self.assertEqual(len(self.pages), 2, 'each pass raises; the pager folds raises of one key into one page')

    def test_dry_run_pages_resolves_and_writes_nothing(self):
        self.go(lambda: ('refused', 401), dry_run=True)
        self.assertEqual((self.pages, self.resolves, (self.root / g.STATE).exists()), ([], [], False))


if __name__ == '__main__':
    unittest.main()
