import unittest

import digest_size as d


class DigestSizeTests(unittest.TestCase):
    def test_the_limit_is_under_what_isomux_does_not_cut(self):
        # 1827 characters: the longest text the digest rule of the bos-deadman hook (two args, channel and text) passes
        # uncut, measured on 2026-10-24 with the dry-run route of the hook.
        self.assertLessEqual(d.LIMIT, 1827 - 100)

    def test_angle_brackets_and_ampersands_cost_six(self):
        self.assertEqual((d.escaped('abc'), d.escaped('<'), d.escaped('a&b>')), (3, 6, 4 + 5 + 5))

    def test_an_entry_is_cut_to_the_room_and_keeps_its_first_line(self):
        entry = 'first line https://x/1\n  \u2502 ' + '<' * 1000
        cut = d.fit(entry, 500)
        self.assertLessEqual(d.escaped(cut), 500)
        self.assertTrue(cut.startswith('first line https://x/1\n'))
        self.assertTrue(cut.endswith('[cut]'))

    def test_a_first_line_over_the_room_is_cut(self):
        self.assertLessEqual(d.escaped(d.fit('<' * 1000 + '\n  \u2502 quoted', 500)), 500)

    def test_a_first_line_within_a_few_characters_of_the_room_is_kept_alone(self):
        for size in (1693, 1695, 1700):
            cut = d.fit('h' * size + '\n  \u2502 quoted', 1700)
            self.assertLessEqual(d.escaped(cut), 1700)

    def test_groups_fit_the_room(self):
        groups = list(d.chunks([(str(n), 'x' * 300 + '<' * 20) for n in range(10)], 1000))
        self.assertGreater(len(groups), 3)
        for g in groups:
            self.assertLessEqual(sum(d.escaped(t) + d.SEPARATOR for _, t in g), 1000)
        self.assertEqual(sum(len(g) for g in groups), 10)


if __name__ == '__main__':
    unittest.main()
