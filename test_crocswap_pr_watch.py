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

# Lead, 2026-10-24: GTimG/QuasiRiemannTracker #71 is a draft (created 14:16:57Z, head checks failed) and was flagged as a
# new bound. A draft created from DRAFT_SINCE on is "draft, waiting"; it alerts once when marked ready, with its head checks.
class DraftPRTests(unittest.TestCase):
    QRT='GTimG/QuasiRiemannTracker'
    CHECKS=[dict(name='admission',status='completed',conclusion='failure',output=dict(title=None)),
            dict(name='verify (slayer-recost-0p87477290596)',status='completed',conclusion='failure',output={}),
            dict(name='qrh/pr-admission',status='completed',conclusion='failure',output=dict(title='PR admission failed')),
            dict(name='prepare',status='completed',conclusion='success',output={})]
    def pr(self,draft=True,head='h1',body='Prove the Dirichlet boundary.',created='2026-10-24T14:16:57Z',repo=None):
        repo=repo or self.QRT
        return dict(number=71,title='Prove the Dirichlet boundary',body=body,head={'sha':head},user={'login':'Rexyysilent'},created_at=created,
                    updated_at='2026-10-24T14:17:37Z',html_url=f'https://github.com/{repo}/pull/71',state='open',draft=draft)
    def watch(self,pr,previous=None,checks=None,claim='Quasi-Riemann bound mu 0.87477290596 improved.',repo=None,check_error=None):
        self.calls=[]
        def api(path,params,**kwargs):
            self.calls.append(path)
            if path.endswith('/pulls'):return [pr] if '/'+(repo or self.QRT)+'/' in '/'+path else []
            if '/check-runs' in path:
                if check_error:raise check_error
                return dict(total_count=len(checks if checks is not None else self.CHECKS),check_runs=checks if checks is not None else self.CHECKS)
            return [dict(filename='notes.md',status='added',patch='+'+claim)]
        with patch('crocswap_pr_watch.api',side_effect=api):
            return cw.collect_all(SINCE,previous or {}) if repo is None else cw.collect(SINCE,previous or {})
    def carry(self,result):return {'family_pr_states':result.get('family_states',{}),'crocswap_pr_states':result['states']}

    def test_a_new_draft_waits_and_alerts_once_when_ready_with_its_head_checks(self):
        draft=self.watch(self.pr())
        self.assertEqual(draft['candidates'],[])
        self.assertEqual([(w['repo'],w['pr_number'],w['status'],w['head']) for w in draft['waiting']],[(self.QRT,71,'draft, waiting','h1')])
        self.assertFalse(any('/files' in c or '/check-runs' in c for c in self.calls))
        self.assertEqual(draft['family_states'][self.QRT]['71']['seen_claims'],[])
        # Still a draft, also after a head change: listed again, no alert, no request for its files.
        again=self.watch(self.pr(),self.carry(draft));moved=self.watch(self.pr(head='h2',body='A new claim 0.5.'),self.carry(again))
        self.assertEqual([len(r['waiting']) for r in (again,moved)],[1,1]);self.assertEqual(again['candidates']+moved['candidates'],[])
        # Marked ready for review: one alert, with the draft flag and the failed head checks.
        ready=self.watch(self.pr(draft=False,head='h2',body='A new claim 0.5.'),self.carry(moved))
        self.assertEqual(ready['waiting'],[])
        row,=ready['candidates']
        self.assertEqual((row['pr_number'],row['draft'],row['head_check_state']),(71,False,'failed'))
        self.assertEqual(row['head_checks'],'failed: 3 of 4 checks failed; admission; verify (slayer-recost-0p87477290596); qrh/pr-admission - PR admission failed')
        self.assertTrue(alert_candidate(row,set(),set()))
        # Once: the same ready head alerts no more; a head that changes while ready, with a new claim, alerts again.
        same=self.watch(self.pr(draft=False,head='h2',body='A new claim 0.5.'),self.carry(ready))
        self.assertEqual(same['candidates'],[])
        moved_ready=self.watch(self.pr(draft=False,head='h3',body='A new claim 0.5.'),self.carry(ready),claim='Quasi-Riemann bound mu 0.4 improved.')
        self.assertEqual(len(moved_ready['candidates']),1)

    def test_an_earlier_alert_of_a_draft_is_forgotten_so_it_alerts_when_ready(self):
        # PR #71 alerted as a ready PR before the rule; the next read finds a draft, and its keys are dropped.
        first=self.watch(self.pr(draft=False));self.assertEqual(len(first['candidates']),1)
        drafted=self.watch(self.pr(),self.carry(first))
        self.assertEqual((drafted['candidates'],len(drafted['waiting']),drafted['family_states'][self.QRT]['71']['seen_claims']),([],1,[]))
        ready=self.watch(self.pr(draft=False),self.carry(drafted))
        self.assertEqual(len(ready['candidates']),1)

    def test_a_draft_before_the_cut_keeps_its_row_and_a_closed_draft_is_not_listed(self):
        old=self.watch(self.pr(created='2026-10-01T00:00:00Z'))
        row,=old['candidates'];self.assertEqual((row['draft'],old['waiting']),(True,[]))
        closed=dict(self.pr(),state='closed')
        self.assertEqual(self.watch(closed)['waiting'],[])

    def test_crocswap_drafts_follow_the_same_rule(self):
        pr=dict(self.pr(repo=REPO),html_url=f'https://github.com/{REPO}/pull/71',updated_at='2026-10-24T14:17:37Z')
        result=self.watch(pr,repo=REPO,claim='Exact DFT bound improves to 0.001.')
        self.assertEqual(result['candidates'],[]);self.assertEqual([w['repo'] for w in result['waiting']],[REPO])
        ready=self.watch(dict(pr,draft=False),self.carry(result),repo=REPO,claim='Exact DFT bound improves to 0.001.')
        self.assertEqual([(r['problem_guess'],r['draft']) for r in ready['candidates']],[('exact DFT',False)])

    def test_head_check_summaries_are_short_plain_and_never_stop_an_alert(self):
        weird=[dict(name='x'*100+'<script>@everyone',status='completed',conclusion='timed_out',output=dict(title='Bad\nline `code` '+'y'*100))]
        row,=self.watch(self.pr(draft=False),checks=weird)['candidates']
        self.assertEqual(row['head_check_state'],'failed');self.assertNotRegex(row['head_checks'],r'[<>@`\n]');self.assertLess(len(row['head_checks']),200)
        for checks,state in (([],'none'),([dict(status='in_progress',conclusion=None)],'pending'),([dict(name='ok',status='completed',conclusion='success')],'passed')):
            row,=self.watch(self.pr(draft=False),checks=checks)['candidates'];self.assertEqual(row['head_check_state'],state)
        # A failed read is unread, with the alert still sent, and adds no report error.
        result=self.watch(self.pr(draft=False),check_error=RuntimeError('GitHub GET failed'))
        row,=result['candidates'];self.assertEqual(row['head_check_state'],'unread');self.assertEqual(result['errors'],[])

    # GTimG/QuasiRiemannTracker #73 (2026-10-25): alerted while its checks ran, then moved its head. The claim alerts once
    # more when the checks of the CURRENT head have a verdict, and not before.
    RUNNING=[dict(name='verify',status='in_progress',conclusion=None,output={})]
    PASSED=[dict(name='verify',status='completed',conclusion='success',output={})]
    def test_a_claim_alerted_with_pending_checks_alerts_again_when_the_checks_of_the_current_head_finish(self):
        first=self.watch(self.pr(draft=False),checks=self.RUNNING)
        row,=first['candidates'];self.assertEqual((row['head_check_state'],row['checks_final']),('pending',False))
        self.assertEqual(len(first['family_states'][self.QRT]['71']['awaiting_checks']),1)
        # Same head, checks still running: no alert, and the checks are read again.
        again=self.watch(self.pr(draft=False),self.carry(first),checks=self.RUNNING)
        self.assertEqual(again['candidates'],[]);self.assertTrue(any('/check-runs' in c for c in self.calls))
        # The head moves while the checks run: the same bound does not alert again, the wait stays.
        moved=self.watch(self.pr(draft=False,head='h2'),self.carry(again),checks=self.RUNNING)
        self.assertEqual(moved['candidates'],[]);self.assertEqual(len(moved['family_states'][self.QRT]['71']['awaiting_checks']),1)
        self.assertTrue(any(c.endswith('/commits/h2/check-runs') for c in self.calls))
        # The checks of the current head finish: one alert, with that head and its verdict; the wait ends.
        done=self.watch(self.pr(draft=False,head='h2'),self.carry(moved),checks=self.PASSED)
        row,=done['candidates'];self.assertEqual((row['readme_commit'],row['head_check_state'],row['checks_final']),('h2','passed',True))
        self.assertNotIn('awaiting_checks',done['family_states'][self.QRT]['71'])
        self.assertTrue(alert_candidate(row,set(),set()))
        self.assertEqual(self.watch(self.pr(draft=False,head='h2'),self.carry(done),checks=self.PASSED)['candidates'],[])
        # A failed verdict alerts too, and a PR whose first alert already had a verdict never waits.
        failed=self.watch(self.pr(draft=False,head='h2'),self.carry(moved))
        self.assertEqual([r['head_check_state'] for r in failed['candidates']],['failed'])
        final=self.watch(self.pr(draft=False),checks=self.PASSED);self.assertNotIn('awaiting_checks',final['family_states'][self.QRT]['71'])

    def test_a_new_bound_on_a_moved_head_alerts_at_once_and_unread_checks_keep_waiting(self):
        first=self.watch(self.pr(draft=False),checks=self.RUNNING)
        changed=self.watch(self.pr(draft=False,head='h2'),self.carry(first),checks=self.RUNNING,claim='Quasi-Riemann bound mu 0.4 improved.')
        row,=changed['candidates'];self.assertEqual(row['head_check_state'],'pending')
        # A check read that fails is no verdict: nothing alerts, the wait stays, and the scan reports no error.
        unread=self.watch(self.pr(draft=False),self.carry(first),check_error=RuntimeError('GitHub GET failed'))
        self.assertEqual((unread['candidates'],unread['errors']),([],[]))
        self.assertEqual(len(unread['family_states'][self.QRT]['71']['awaiting_checks']),1)
        # A closed PR is not read for checks.
        closed=self.watch(dict(self.pr(draft=False),state='closed'),self.carry(first),checks=self.PASSED)
        self.assertEqual(closed['candidates'],[])
        # ... and its wait ends at once, so a merged PR (#74) does not stay in the state as waiting.
        self.assertNotIn('awaiting_checks',closed['family_states'][self.QRT]['71'])
        self.assertEqual(closed['family_states'][self.QRT]['71']['seen_claims'],first['family_states'][self.QRT]['71']['seen_claims'])
        self.assertEqual(self.watch(dict(self.pr(draft=False),state='closed'),self.carry(closed),checks=self.PASSED)['candidates'],[])

    def test_the_verdict_on_the_same_head_reads_the_files_from_page_one(self):
        # Reviewer probe (2026-10-25): the saved revision is unchanged, so a resume at next_file_page would miss the claim.
        pages=[]
        def watch(checks,previous=None):
            def api(path,params,**kwargs):
                if path.endswith('/pulls'):return [self.pr(draft=False)] if self.QRT in path else []
                if '/check-runs' in path:return dict(total_count=len(checks),check_runs=checks)
                pages.append(params.get('page'))
                return [dict(filename='notes.md',status='added',patch='+Quasi-Riemann bound mu 0.87477290596 improved.')] if params.get('page')==1 else []
            with patch('crocswap_pr_watch.api',side_effect=api):
                return cw.collect_all(SINCE,previous or {})
        first=watch(self.RUNNING);self.assertEqual(len(first['candidates']),1)
        state=first['family_states'][self.QRT]['71'];state['next_file_page']=4;state['revision']=state['pending_revision']
        del pages[:]
        done=watch(self.PASSED,self.carry(first))
        self.assertEqual(pages[:1],[1]);row,=done['candidates'];self.assertEqual((row['head_check_state'],row['checks_final']),('passed',True))

if __name__=='__main__':unittest.main()
