import unittest
import subprocess
from unittest.mock import patch
from crocswap_pr_watch import collect, source_claims, REPO
import crocswap_pr_watch as cw
from pivot_watch import alert_candidate
import github_read

SINCE='2026-10-08T00:00:00Z'

def pull(number=363,body='Exact DFT bound improves to 0.001.',**changes):
    row=dict(number=number,title='Circuit update',body=body,head={'sha':'head1'},user={'login':'unwatched-author'},created_at='2026-10-01T00:00:00Z',updated_at='2026-10-11T03:24:58Z',html_url=f'https://github.com/{REPO}/pull/{number}',state='closed')
    row.update(changes)
    return row

class CrocSwapPRTests(unittest.TestCase):
    def run_watch(self,pulls,files=(),previous=None):
        def api(path,params,**kwargs):
            if path.endswith('/pulls'):
                self.assertEqual(params['state'],'all')
                self.assertEqual(params['sort'],'updated')
                return pulls
            return list(files)
        with patch('crocswap_pr_watch.api',side_effect=api):return collect(SINCE,previous or {})

    def test_all_authors_and_updated_old_closed_prs(self):
        result=self.run_watch([pull()])
        row=result['candidates'][0]
        self.assertEqual(row['author'],'unwatched-author')
        self.assertEqual(row['problem_guess'],'exact DFT')
        self.assertEqual(row['url'],pull()['html_url'])
        self.assertTrue(alert_candidate(row,{REPO},set()))

    def test_integer_only_suppressed_but_mixed_claim_retained(self):
        result=self.run_watch([pull(body='Integer multiplication bound improves to 0.002.'),pull(365,'Integer multiplication bound improves to 0.003.\nExact DFT bound improves to 0.001.')])
        self.assertEqual([r['pr_number'] for r in result['candidates']],[365])
        claims=source_claims('# DFT\nThe bound improves to 0.001.\nInteger multiplication bound improves to 0.003.')
        self.assertEqual(claims['exact DFT'],['The bound improves to 0.001.'])

    def test_added_file_claim_and_removed_lines(self):
        files=[dict(filename='research/note.md',status='modified',patch='@@ -1 +1 @@\n-APSP exponent improves to 2.4.\n+# Exact DFT\n+The bound improves to 0.001.')]
        result=self.run_watch([pull(body='Integer multiplication cleanup')],files)
        self.assertEqual([r['problem_guess'] for r in result['candidates']],['exact DFT'])

    def test_vendored_theorems_do_not_become_new_claims(self):
        files=[dict(filename='research/complex/inputs/upstream/Fourier.lean',status='added',patch='+Exact DFT bound 0.0007.'),dict(filename='research/complex/inputs/large.lean',status='added')]
        result=self.run_watch([pull(body='Finite complex supplier saving 0.0009')],files)
        self.assertEqual(result['candidates'],[]);self.assertEqual(result['errors'],[])
        self.assertEqual(source_claims('# DFT\n| kappa | 1/1000 |')['exact DFT'],['| kappa | 1/1000 |'])

    def test_dedup_repeated_claim_changed_bound_and_separate_pr(self):
        first=self.run_watch([pull()]);previous={'crocswap_pr_states':first['states']}
        self.assertEqual(self.run_watch([pull()],previous=previous)['candidates'],[])
        prose=pull(body='Exact DFT bound now improves to 0.001.',head={'sha':'head2'})
        self.assertEqual(self.run_watch([prose],previous=previous)['candidates'],[])
        changed=pull(body='Exact DFT bound improves to 0.002.',head={'sha':'head3'})
        result=self.run_watch([changed,pull(365)],previous=previous)
        self.assertEqual([r['pr_number'] for r in result['candidates']],[363,365])

    def test_all_other_families_and_five_other_boards(self):
        for family in ['003','005','029','111','115','127','160','161','167','187','190','191','268']:
            with self.subTest(family=family):
                row=self.run_watch([pull(body=f'Family {family}: improved bound 0.01.')])['candidates'][0]
                self.assertEqual(row['other_family'],family)
                self.assertTrue(alert_candidate(row,set(),set()))
        for name in ['DFT','3SUM','APSP','Subset Sum','Matrix Multiplication']:
            self.assertEqual(len(self.run_watch([pull(body=f'{name} exponent improves to 0.5.')])['candidates']),1)

    def test_unrelated_wht_and_citation_are_not_dft_claims(self):
        for text in ['WHT bound improves to 0.001.', 'SSSP exponent improves to 0.5.',
                     'Source: https://github.com/author/exact-dft/blob/123/README.md\nInteger multiplication bound improves to 0.003.']:
            self.assertEqual(source_claims(text),{})

    def test_missing_patch_is_reported_and_revision_change_rechecks(self):
        result=self.run_watch([pull()],[dict(filename='note.md',status='added')])
        self.assertTrue(result['errors']);self.assertFalse(result['candidates'][0]['coverage_complete'])
        self.assertIsNotNone(result['states']['363']['revision'])
        again=self.run_watch([pull(head={'sha':'head2'})],[dict(filename='note.md',status='added',patch='+Subset Sum exponent improves to 0.49.')],{'crocswap_pr_states':result['states']})
        self.assertEqual([r['problem_guess'] for r in again['candidates']],['subset sum'])

    def test_pagination_and_cutoff(self):
        old=pull(999,updated_at='2026-10-07T00:00:00Z')
        calls=[]
        def api(path,params,**kwargs):
            if path.endswith('/pulls'):
                calls.append(params['page'])
                return [pull(n,body='Integer multiplication bound 0.001') for n in range(100)] if params['page']==1 else [pull(101),old]
            return []
        with patch('crocswap_pr_watch.api',side_effect=api),patch('crocswap_pr_watch.MAX_REQUESTS',200):result=collect(SINCE,{})
        self.assertEqual(calls,[1,2]);self.assertEqual([r['pr_number'] for r in result['candidates']],[101])
        self.assertNotIn('999',result['states'])

    def test_api_failure_and_file_cap_report_partial_coverage(self):
        with patch('crocswap_pr_watch.api',side_effect=RuntimeError('API failed')):
            result=collect(SINCE,{})
        self.assertEqual(result['errors'],['API failed'])
        files=[dict(filename=f'code{i}.py',status='added') for i in range(100)]
        result=self.run_watch([pull()],files)
        self.assertTrue(result['truncated']);self.assertIsNone(result['states']['363']['revision'])
        self.assertEqual(result['states']['363']['next_file_page'],4)

    def test_file_pages_resume_instead_of_repeating_first_chunk(self):
        pages=[]
        previous={'crocswap_pr_states':self.run_watch([pull()],[dict(filename='code.py',status='added')]*100)['states']}
        def api(path,params,**kwargs):
            if path.endswith('/pulls'):return [pull()]
            pages.append(params['page']);return []
        with patch('crocswap_pr_watch.api',side_effect=api):result=collect(SINCE,previous)
        self.assertEqual(pages,[4]);self.assertIsNotNone(result['states']['363']['revision'])

    def test_request_budget_resumes_after_completed_prs(self):
        with patch('crocswap_pr_watch.MAX_REQUESTS',2):
            first=self.run_watch([pull(1),pull(2)])
            self.assertEqual(first['checked'],[1]);self.assertTrue(first['truncated'])
            second=self.run_watch([pull(1),pull(2)],previous={'crocswap_pr_states':first['states']})
            self.assertEqual(second['checked'],[2])

    def test_time_budget_stops_without_network_call(self):
        with patch('crocswap_pr_watch.time.monotonic',side_effect=[0,121]),patch('crocswap_pr_watch.api') as api:
            result=collect(SINCE,{})
        api.assert_not_called();self.assertIn('budget exhausted',result['errors'][0])

    def test_slow_request_cannot_exceed_remaining_budget(self):
        with patch('github_read.time.monotonic',return_value=100),patch('github_read.subprocess.run',side_effect=subprocess.TimeoutExpired('gh',2)) as run:
            with self.assertRaisesRegex(RuntimeError,'timed out'):github_read.api('repos/test/repo',deadline=102)
        self.assertEqual(run.call_args.kwargs['timeout'],2)

    def test_bounded_rate_limit_does_not_sleep_and_retry(self):
        response=subprocess.CompletedProcess('gh',1,stdout='',stderr='429 rate limit')
        with patch('github_read.time.monotonic',return_value=100),patch('github_read.subprocess.run',return_value=response) as run,patch('github_read.time.sleep') as sleep:
            with self.assertRaises(RuntimeError):github_read.api('repos/test/repo',deadline=220)
        self.assertEqual(run.call_count,1);sleep.assert_not_called()

class FamilyPRTests(unittest.TestCase):
    VDW='rohanarun/van-der-waerden-refinement';QRT='GTimG/QuasiRiemannTracker'
    def fake(self,prs,calls):
        def api(path,params,**kwargs):
            calls.append((path,params.get('state')))
            repo='/'.join(path.split('/')[1:3])
            if path.endswith('/pulls'):
                rows=[p for p in prs.get(repo,[]) if params['state']=='all' or p['state']=='open']
                return rows if params.get('page',1)==1 else []
            return [dict(filename='notes.md',status='added',patch='+Exact coefficient bound 1/19 for the cover.\n+Fourier transform bound 0.5.'),
                    dict(filename='Proof.lean',status='added',patch='+theorem cover_bound : (1 / 19 : ℝ) ≤ 2 := by')]
        return api

    def test_open_pr_outside_window_gets_family_label(self):
        # artuskg's 1/19 sat in open PR #4 for 3 days (2026-10-14).
        old_open=pull(4,body='Add a certificate cover.',title='Coefficient 1/19',state='open',updated_at='2026-10-01T00:00:00Z',
                      html_url=f'https://github.com/{self.VDW}/pull/4',user={'login':'artuskg'})
        old_closed=pull(3,body='Bound 1/24.',state='closed',updated_at='2026-10-01T00:00:00Z')
        calls=[]
        with patch('crocswap_pr_watch.api',side_effect=self.fake({self.VDW:[old_open,old_closed]},calls)):
            result=cw.collect_all(SINCE,{})
        rows=[r for r in result['candidates'] if r['repo']==self.VDW]
        self.assertEqual([(r['pr_number'],r['other_family'],r['evidence']) for r in rows],[(4,'160',['recent-family-pr'])])
        # Cross-board words count for the repo's family; Lean diffs are not read.
        self.assertIn('Fourier transform bound 0.5.',rows[0]['source_claim_evidence'])
        self.assertFalse(any('theorem' in line for line in rows[0]['source_claim_evidence']))
        self.assertTrue(alert_candidate(rows[0],set(),set()))
        self.assertIn('4',result['family_states'][self.VDW]);self.assertNotIn('3',result['family_states'][self.VDW])
        self.assertIn(('repos/'+REPO+'/pulls','all'),calls)
        # An unchanged PR is skipped on the next cycle: no files request.
        calls.clear()
        with patch('crocswap_pr_watch.api',side_effect=self.fake({self.VDW:[old_open]},calls)):
            again=cw.collect_all(SINCE,{'family_pr_states':result['family_states']})
        self.assertEqual(again['candidates'],[]);self.assertFalse(any('/files' in c[0] for c in calls))

    def test_family_share_of_budget_leaves_rest_for_crocswap(self):
        many=[pull(n,body='Proof notes.',state='open',html_url=f'https://github.com/{self.QRT}/pull/{n}') for n in range(1,41)]
        calls=[]
        with patch('crocswap_pr_watch.api',side_effect=self.fake({self.QRT:many,REPO:[pull(900)]},calls)):
            result=cw.collect_all(SINCE,{})
        family_calls=[c for c in calls if not c[0].startswith('repos/'+REPO)]
        self.assertEqual(len(family_calls),cw.FAMILY_MAX_REQUESTS)
        self.assertIn(('repos/'+REPO+'/pulls/900/files',None),calls)
        self.assertLessEqual(result['requests'],cw.MAX_REQUESTS)
        self.assertTrue(any(t['query']==self.QRT+' PR inspection budget' for t in result['truncated']))

if __name__=='__main__':unittest.main()
