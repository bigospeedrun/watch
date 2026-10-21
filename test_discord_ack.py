import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

import discord_ack as a

T0 = datetime(2026, 10, 21, 18, 0, tzinfo=timezone.utc)


class API:
    channel = '1'

    def __init__(self, messages):
        self.rows = messages
        self.reactions = []
        self.fail = {}  # message id -> exception to raise (once per entry in the list)

    def check_channel(self):
        pass

    def request(self, path):
        assert path.endswith('limit=1')
        return [max(self.rows, key=lambda m: int(m['id']))] if self.rows else []

    def messages(self, after):
        return list(reversed([m for m in self.rows if int(m['id']) > int(after)][:100]))

    def react(self, mid):
        errors = self.fail.get(mid)
        if errors:
            raise errors.pop(0)
        self.reactions.append(mid)


def msg(n, content='secret prose', **extra):
    return dict(id=str(n), type=0, content=content, author=dict(id='44', username='private-name'), **extra)


def http(code, retry=None):
    headers = {'Retry-After': retry} if retry else {}
    return HTTPError('https://discord.com/x', code, 'x', headers, None)


class AckTests(unittest.TestCase):
    def go(self, api, root, now=T0, alerts=None):
        alerts = [] if alerts is None else alerts
        return a.run(api, lambda *x: alerts.append(x), root, now=now, sleep=lambda s: None), alerts

    def test_the_first_run_starts_at_the_newest_message_and_reacts_to_nothing_old(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api = API([msg(1), msg(2)])
            result, _ = self.go(api, root)
            # The newest message itself is acknowledged (a human may have just posted it); older ones are not.
            self.assertEqual((result['first_run'], result['reacted'], api.reactions), (True, 1, ['2']))
            self.assertEqual(json.loads((root / a.STATE).read_text())['last_seen'], '2')
            api.rows.append(msg(3))
            self.assertEqual(self.go(api, root)[0]['reacted'], 1)
            self.assertEqual(api.reactions, ['2', '3'])

    def test_retries_are_capped_and_spaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api = API([msg(1)])
            self.go(api, root)
            api.reactions.clear()  # the first run acknowledged message 1
            api.rows += [msg(n) for n in range(2, 62)]
            for n in range(2, 62):
                api.fail[str(n)] = [http(403)] * 100
            self.go(api, root)
            self.assertEqual(len(json.loads((root / a.STATE).read_text())['pending']), 60)
            waits = []
            calls = []
            real = api.react
            api.react = lambda mid: (calls.append(mid), real(mid))[1]
            a.run(api, lambda *x: None, root, now=T0 + timedelta(minutes=1), sleep=waits.append)
            self.assertEqual(len(calls), a.RETRIES)
            self.assertEqual(calls, [str(n) for n in range(2, 2 + a.RETRIES)], 'the oldest first')
            self.assertEqual(waits, [0.3] * a.RETRIES)

    def test_every_new_human_message_gets_one_reaction_and_bots_do_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api = API([msg(1)])
            self.go(api, root)
            api.reactions.clear()  # the first run acknowledged message 1
            bot = msg(2)
            bot['author']['bot'] = True
            hook = msg(3, webhook_id='9')
            pin = msg(4)
            pin['type'] = 6
            reply = msg(5)
            reply['type'] = 19
            api.rows += [bot, hook, pin, reply, msg(6, 'a question, no link'), msg(7, 'see https://github.com/bigospeedrun/verifier/pull/1')]
            self.assertEqual(self.go(api, root)[0]['reacted'], 3)
            self.assertEqual(api.reactions, ['5', '6', '7'])
            self.assertEqual(self.go(api, root)[0]['reacted'], 0, 'a second run reacts to nothing')
            self.assertEqual(api.reactions, ['5', '6', '7'])

    def test_the_state_holds_no_message_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api = API([msg(1)])
            self.go(api, root)
            api.reactions.clear()  # the first run acknowledged message 1
            api.rows.append(msg(2, 'secret prose'))
            api.fail['2'] = [http(500)]
            self.go(api, root)
            text = (root / a.STATE).read_text()
            self.assertNotIn('secret', text)
            self.assertNotIn('private-name', text)
            self.assertEqual(set(json.loads(text)), {'last_seen', 'pending', 'alerted', 'last_ok'})

    def test_a_failed_reaction_is_retried_and_alerts_once_after_15_minutes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api = API([msg(1)])
            self.go(api, root)
            api.reactions.clear()  # the first run acknowledged message 1
            api.rows.append(msg(2))
            api.fail['2'] = [http(403)] * 30
            result, alerts = self.go(api, root)
            self.assertEqual((result['pending'], alerts), (1, []))
            result, alerts = self.go(api, root, now=T0 + timedelta(minutes=14))
            self.assertEqual((result['pending'], alerts), (1, []))
            result, alerts = self.go(api, root, now=T0 + timedelta(minutes=15))
            self.assertEqual(len(alerts), 1)
            self.assertIn('2', alerts[0][0])
            result, alerts = self.go(api, root, now=T0 + timedelta(minutes=20), alerts=alerts)
            self.assertEqual(len(alerts), 1, 'one alert per message')
            api.fail['2'] = []
            result, alerts = self.go(api, root, now=T0 + timedelta(minutes=21), alerts=alerts)
            self.assertEqual((result['pending'], api.reactions), (0, ['2']))
            self.assertEqual(json.loads((root / a.STATE).read_text())['alerted'], [])

    def test_a_rate_limit_waits_and_retries_once_and_a_deleted_message_needs_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api = API([msg(1)])
            self.go(api, root)
            api.reactions.clear()  # the first run acknowledged message 1
            api.rows += [msg(2), msg(3)]
            api.fail['2'] = [http(429, '2')]
            api.fail['3'] = [http(404)]
            waits = []
            result = a.run(api, lambda *x: None, root, now=T0, sleep=waits.append)
            self.assertEqual((result['pending'], api.reactions), (0, ['2']))
            self.assertIn(2.2, waits)

    def test_a_network_error_leaves_the_message_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api = API([msg(1)])
            self.go(api, root)
            api.reactions.clear()  # the first run acknowledged message 1
            api.rows.append(msg(2))
            api.fail['2'] = [URLError('down')]
            self.assertEqual(self.go(api, root)[0]['pending'], 1)
            self.assertEqual(self.go(api, root, now=T0 + timedelta(minutes=1))[0]['pending'], 0)

    def test_the_dry_run_writes_and_reacts_to_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api = API([msg(1)])
            self.go(api, root)
            api.reactions.clear()  # the first run acknowledged message 1
            api.rows.append(msg(2))
            before = (root / a.STATE).read_text()
            result = a.run(api, lambda *x: None, root, dry_run=True, now=T0, sleep=lambda s: None)
            self.assertEqual((result['reacted'], api.reactions, (root / a.STATE).read_text()), (0, [], before))

    def test_a_bad_message_order_stops_the_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api = API([msg(5)])
            self.go(api, root)
            api.messages = lambda after: [msg(4)]
            with self.assertRaises(ValueError):
                self.go(api, root)


if __name__ == '__main__':
    unittest.main()
