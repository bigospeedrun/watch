import unittest, json, tempfile
from pathlib import Path
from unittest.mock import patch
from pivot_watch import stated_bound,alert_candidate,board_snapshot

class BoundAlertTests(unittest.TestCase):
    def test_site_related_listing_suppresses_new_source_but_not_changed_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);site=root/'site';(site/'data').mkdir(parents=True)
            (root/'registry.json').write_text(json.dumps({'repositories':[], 'problems':[]}))
            (site/'data/registry.json').write_text(json.dumps({'repositories':[{'repo':'Swapnil-jain/subsetsum-derand'}]}))
            with patch('pivot_watch.ROOT',root),patch('pivot_watch.SITE_ROOT',site):
                board,_=board_snapshot()
            row={'repo':'Swapnil-jain/subsetsum-derand','problem_guess':'subset sum','on_board':'Swapnil-jain/subsetsum-derand' in board,'likely_tracked_source':True}
            self.assertFalse(alert_candidate(row,set(),set()))
            row['stated_bound_changed']=True
            self.assertTrue(alert_candidate(row,set(),set()))
    def test_known_board_head_change_is_silent(self):
        self.assertFalse(alert_candidate({'repo':'a/b','problem_guess':'exact DFT','on_board':True,'stated_bound_changed':False,'likely_pivot':True},set(),{'a/b'}))
    def test_known_board_changed_bound_alerts(self):
        self.assertTrue(alert_candidate({'repo':'a/b','problem_guess':'exact DFT','on_board':True,'stated_bound_changed':True},{'a/b'},set()))
    def test_unknown_pivot_alerts_once(self):
        row={'repo':'a/b','problem_guess':'exact DFT','on_board':False,'likely_pivot':True}
        self.assertTrue(alert_candidate(row,set(),set()))
        self.assertFalse(alert_candidate(row,{'a/b'},set()))
    def test_rational_normalization_and_unrelated_numbers(self):
        p=r'\\delta\s*=\s*(?P<num>0\.\d+)'
        self.assertEqual(stated_bound('2026: \\delta=0.00067; 17 million checks',p),'67/100000')
        with self.assertRaises(ValueError):stated_bound('no current bound; historical 0.00067',p)
if __name__=='__main__':unittest.main()
