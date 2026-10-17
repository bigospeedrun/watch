import json, tempfile, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import race_channels as rc

NOW = datetime(2026, 10, 17, 8, 0, tzinfo=timezone.utc)
BIG_O, OTHER = '1558629622558756944', '1558688026207584347'


class FakeDiscord:
    def __init__(self, channels):
        self.list = [dict(c) for c in channels]; self.made = []
    def channels(self): return [dict(c) for c in self.list]
    orders = None
    def order(self, ids):
        self.orders = (self.orders or []) + [ids]
        for position, i in ids:
            next(c for c in self.list if c['id'] == i)['position'] = position
    def create(self, name, category):
        self.made.append((name, category))
        self.list.append(dict(id=str(100 + len(self.made)), name=name, type=0, parent_id=rc.CATEGORY_IDS[category],
                              position=max(c.get('position') or 0 for c in self.list) + 1))
        return dict(id=self.list[-1]['id'], name=name)


class RaceChannelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name); (self.root / '.git').mkdir()
        self.races = [('exact-dft', 'fourier-transform', 'Big O'), ('other-catalan', 'catalans-constant', 'Other bounds')]
        self.boards = ['exact-dft', 'other-catalan']
        self.discord = FakeDiscord([dict(id='1', name='fourier-transform', type=0, parent_id=BIG_O, position=13),
                                    dict(id='2', name='catalans-constant', type=0, parent_id=OTHER, position=19),
                                    dict(id='4', name='snaky', type=0, parent_id=OTHER, position=20),
                                    dict(id='3', name='general', type=0, parent_id='1558629621208186970', position=7)])
        self.races.append(('other-snaky', 'snaky', 'Other bounds')); self.boards.append('other-snaky')
        self.dispatched = 0
    def tearDown(self): self.tmp.cleanup()
    def dispatch(self): self.dispatched += 1
    def run_at(self, now=NOW, dry_run=False):
        return rc.run(self.root, self.discord, lambda: list(self.races), lambda: list(self.boards), self.dispatch, now, dry_run)

    def test_nothing_to_do_creates_nothing_and_records_a_pass(self):
        report = self.run_at()
        self.assertEqual((report['created'], report['blocked'], self.discord.made, self.dispatched), ([], None, [], 0))
        self.assertEqual(json.loads((self.root / rc.STATE).read_text())['last_ok'], NOW.isoformat(timespec='seconds'))

    def test_a_new_race_gets_its_channel_once_in_the_right_category_and_site_order(self):
        self.races.insert(2, ('other-block-sensitivity', 'block-sensitivity-separation', 'Other bounds'))
        report = self.run_at()
        self.assertEqual(self.discord.made, [('block-sensitivity-separation', 'Other bounds')])
        self.assertEqual(self.discord.list[-1]['parent_id'], OTHER)
        self.assertEqual(report['created'][0]['slug'], 'other-block-sensitivity')
        # Site order: catalans-constant, block-sensitivity-separation, snaky, from position 19.
        self.assertEqual(self.discord.orders, [[(19, '2'), (20, '101'), (21, '4')]])
        self.run_at(NOW + timedelta(hours=1))
        self.assertEqual(len(self.discord.made), 1, 'a second run creates nothing')
        self.assertEqual(len(self.discord.orders), 1, 'and changes no position')

    def test_a_rename_or_an_unknown_channel_creates_nothing(self):
        self.races[0] = ('exact-dft', 'fourier', 'Big O')
        report = self.run_at()
        self.assertEqual(self.discord.made, [])
        self.assertIn('#fourier-transform', report['blocked'])

    def test_more_than_the_cap_creates_nothing(self):
        self.races += [(f'other-r{i}', f'r{i}', 'Other bounds') for i in range(rc.MAX_CREATE + 1)]
        report = self.run_at()
        self.assertEqual(self.discord.made, [])
        self.assertIn('more than', report['blocked'])

    def test_dry_run_creates_and_writes_nothing(self):
        self.races.append(('3sum', '3sum', 'Big O')); self.boards.remove('other-catalan')
        report = self.run_at(dry_run=True)
        self.assertEqual((self.discord.made, self.dispatched), ([], 0))
        self.assertTrue(report['created'][0]['dry_run']); self.assertIn('would start', report['board_sync'])
        self.assertFalse((self.root / rc.STATE).exists())

    def test_a_race_with_no_board_starts_the_board_sync_at_most_every_2_h(self):
        self.boards.remove('other-catalan')
        self.assertIn('started', self.run_at()['board_sync'])
        self.assertIn('started recently', self.run_at(NOW + timedelta(hours=1))['board_sync'])
        self.run_at(NOW + timedelta(hours=2))
        self.assertEqual(self.dispatched, 2)

    def test_a_failed_read_raises_and_records_no_pass(self):
        def broken(): raise OSError('down')
        with self.assertRaises(OSError):
            rc.run(self.root, self.discord, broken, lambda: self.boards, self.dispatch, NOW)
        self.assertFalse((self.root / rc.STATE).exists())


if __name__ == '__main__':
    unittest.main()
