import unittest
from watch_policy import wht_only, board_fork, new_research_source, hourly_imported
from pivot_watch import alert_candidate
class ScopeTests(unittest.TestCase):
    def test_hourly_suppression_is_problem_specific(self):
        repo='CrocSwap/integer-mult-bounds'
        self.assertTrue(hourly_imported(repo,'Integer multiplication kappa = 0.001'))
        self.assertFalse(hourly_imported(repo,'Integer multiplication and exact DFT bound = 0.002'))
        self.assertFalse(hourly_imported(repo,'Family 268 Haldane gap bound 0.01'))
        self.assertFalse(hourly_imported(repo,'Unclassified source'))
        self.assertTrue(alert_candidate(dict(repo=repo,problem_guess='exact DFT',on_board=True,stated_bound_changed=True),set(),set()))
    def test_wht_only_is_suppressed_but_mixed_dft_is_retained(self):
        self.assertTrue(wht_only('Walsh-Hadamard exponent improvement'))
        self.assertTrue(wht_only('owner/wht-power-saving-lean'))
        self.assertFalse(wht_only('WHT and all-length DFT bound'))
        self.assertFalse(alert_candidate({'repo':'r','problem_guess':'Walsh-Hadamard transform','on_board':True,'stated_bound_changed':True},set(),{'r'}))
        self.assertTrue(alert_candidate({'repo':'r','problem_guess':'DFT and WHT','on_board':True,'stated_bound_changed':True},set(),{'r'}))

    def test_board_fork_and_hourly_noise(self):
        self.assertTrue(board_fork({'fork':True,'parent':{'full_name':'CrocSwap/integer-mult-bounds'}},{'crocswap/integer-mult-bounds'}))
        self.assertFalse(board_fork({'fork':True,'parent':{'full_name':'person/new-race'}},{'crocswap/integer-mult-bounds'}))
        self.assertFalse(alert_candidate({'repo':'CrocSwap/integer-mult-bounds','on_board':True,'stated_bound_changed':True},set(),set()))
        self.assertFalse(alert_candidate({'repo':'person/notes'},set(),{'person/notes'}))
        self.assertTrue(alert_candidate({'repo':'person/new-dft','problem_guess':'DFT','likely_tracked_source':True},set(),set()))
        self.assertFalse(alert_candidate({'repo':'person/new-dft','problem_guess':'DFT','likely_tracked_source':True},{'person/new-dft'},set()))

    def test_broad_readme_matches_are_not_new_sources(self):
        def row(repo,description,problem,date='2026-10-10'):
            return dict(repo=repo,description=description,problem_guess=problem,created_at=date)
        self.assertFalse(new_research_source(row('person/tracker','Integer multiplication tracker','integer multiplication'),'2026-10-07'))
        self.assertFalse(new_research_source(row('person/apap','Roth numbers','DFT','2023-03-15'),'2026-10-07'))
        self.assertFalse(new_research_source(row('person/LeetCode','Daily challenge solutions','edit distance'),'2026-10-07'))
        self.assertTrue(new_research_source(row('person/3sum-bounds','Improved 3SUM bound','3sum'),'2026-10-07'))

    def test_only_visible_problems_can_alert(self):
        for problem in ['edit distance','SSSP','shortest paths','van der Waerden lower bound','Walsh-Hadamard transform']:
            with self.subTest(problem=problem):
                self.assertFalse(alert_candidate(dict(repo='person/new',problem_guess=problem,on_board=True,stated_bound_changed=True,likely_pivot=True),set(),{'person/new'}))
        for problem in ['integer multiplication','exact DFT','Fourier transform','3SUM','APSP','subset sum','matrix multiplication','matrix-multiplication','matrix-mult']:
            with self.subTest(problem=problem):
                self.assertTrue(alert_candidate(dict(repo='person/new',problem_guess=problem,likely_new_race=True),set(),set()))
