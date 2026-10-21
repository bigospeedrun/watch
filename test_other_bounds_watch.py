import unittest
import json
from unittest.mock import patch
import other_bounds_watch as o
from pivot_watch import alert_candidate

class OtherBoundsTests(unittest.TestCase):
    def test_untouched_list_and_queued_forks_need_no_repository_get(self):
        old=self.fork('old/math');old['pushed_at']='2026-10-10'
        equal=self.fork('equal/math');equal['pushed_at']=equal['created_at']
        calls=[]
        def api(path,params=None,**kwargs):
            calls.append(path)
            self.assertEqual(path,'repos/openai/math/forks')
            return [old,equal]
        with patch.object(o,'CONFIG',[]),patch.object(o,'api',api):
            result=o.collect('2026-10-10',{'other_bounds_checkpoint':{'pending':[old,equal]}})
        self.assertEqual(len(calls),1)
        self.assertEqual(result['checkpoint']['pending'],[])
        self.assertEqual(result['usage']['untouched_forks_skipped'],2)

    def test_synced_fork_has_no_claim_text_inspection(self):
        meta=self.fork('synced/math')
        def api(path,params=None,**kwargs):
            return {'files':[],'status':'identical'} if '/compare/' in path else {'sha':'head'}
        with patch.object(o,'CONFIG',[]),patch.object(o,'api',api),patch.object(o,'content') as read,patch.object(o,'scoped_claims') as claims:
            result=o.collect('2026-10-10',{'other_bounds_checkpoint':{'pending':[meta]}},search=False)
        read.assert_not_called();claims.assert_not_called()
        self.assertEqual(result['usage']['forks_without_changed_files'],1)
        self.assertEqual(result['checkpoint']['pending'],[])

    def test_later_push_makes_previously_untouched_fork_eligible(self):
        old=self.fork('person/math');old['pushed_at']=old['created_at']
        new=dict(old,pushed_at='2026-10-12')
        def api(path,params=None,**kwargs):
            if path.endswith('/forks'):return [new]
            if '/compare/' in path:return {'files':[{'filename':'notes/007.md','patch':'+Family 007: improved bound from 0.8 to 0.7.'}]}
            return {'sha':'head'}
        with patch.object(o,'CONFIG',[]),patch.object(o,'api',api):
            result=o.collect('2026-10-10',{'other_bounds_checkpoint':{'pending':[old]}})
        self.assertEqual(len(result['candidates']),1)
        self.assertEqual(result['usage']['forks_with_changed_files'],1)

    def fork(self,name,date='2026-10-11'):
        return dict(full_name=name,html_url='https://github.com/'+name,created_at=date,pushed_at=date+'T01:00:00Z',default_branch='main',fork=True,_openai_fork=True)

    def test_request_budget_resumes_pending_claims_without_duplicates(self):
        metas=[self.fork('person'+str(n)+'/math','2026-10-1'+str(n)) for n in [1,2,3]]
        previous={'other_bounds_checkpoint':{'pending':metas}}
        found=[]
        def api(path,params=None,**kwargs):
            if path=='repos/openai/math/commits/main':return {'sha':'upstream'}
            if '/commits/' in path:return {'sha':path.split('/')[1]}
            if '/compare/' in path:return {'files':[{'filename':'notes/007.md','patch':'+Family 007: improved bound from 0.8 to 0.7.'}]}
            raise AssertionError(path)
        with patch.object(o,'CONFIG',[]),patch.object(o,'MAX_REQUESTS',4),patch.object(o,'api',api):
            for _ in range(3):
                result=o.collect('2026-10-20',previous,search=False)
                self.assertLessEqual(result['usage']['requests'],4)
                found.extend(r['repo'] for r in result['candidates'])
                previous=json.loads(json.dumps({'other_bound_states':result['states'],'other_bounds_checkpoint':result['checkpoint']}))
        self.assertEqual(found,['person3/math','person2/math','person1/math'])
        self.assertEqual(len(result['states']),3)

    def test_newest_forks_precede_saved_older_forks(self):
        old=self.fork('old/math','2026-10-10');new=self.fork('new/math','2026-10-11')
        order=[]
        def api(path,params=None,**kwargs):
            if path.endswith('/forks'):return [new]
            if '/commits/' in path:
                if 'openai/math' not in path:order.append(path.split('/')[1])
                return {'sha':'head'}
            return {'files':[]}
        with patch.object(o,'CONFIG',[]),patch.object(o,'api',api):
            result=o.collect('2026-10-09',{'other_bounds_checkpoint':{'pending':[old]}})
        self.assertEqual(order,['new','old']);self.assertEqual(result['checkpoint']['pending'],[])

    def test_fork_page_cursor_resumes_and_retains_original_cutoff(self):
        calls=[]
        def api(path,params=None,**kwargs):
            self.assertTrue(path.endswith('/forks'));calls.append(params['page'])
            return [self.fork(f'page{params["page"]}user{n}/math') for n in range(100)]
        with patch.object(o,'CONFIG',[]),patch.object(o,'MAX_REQUESTS',3),patch.object(o,'FORK_PAGES_PER_CYCLE',3),patch.object(o,'api',api):
            first=o.collect('2026-10-10',{})
            second=o.collect('2026-10-12',{'other_bounds_checkpoint':first['checkpoint']})
        self.assertEqual(calls,[1,2,3,1,4,5])
        self.assertEqual(second['checkpoint']['fork_page'],6)
        self.assertEqual(second['checkpoint']['fork_since'],'2026-10-10')
        self.assertEqual(len(second['checkpoint']['pending']),500)

    def test_search_cursor_resumes_after_discovery_quota(self):
        # Rotation covers every distinct alias, not only the first per family.
        config=[dict(family='003',title='Q',aliases=['quasi Riemann','quasi-Riemann','QuasiRiemann'],repo='a/q',baseline_commit='b'*40),
                dict(family='005',title='C',aliases=['Catalan constant'],repo='a/c',baseline_commit='b'*40)];queries=[]
        def api(path,params=None,**kwargs):
            if path.endswith('/forks'):return []
            if path=='search/repositories':
                queries.append(params['q']);return {'items':[],'total_count':0}
            raise RuntimeError('source unavailable')
        with patch.object(o,'CONFIG',config),patch.object(o,'DISCOVERY_REQUESTS',2),patch.object(o,'api',api),patch('watch_budget.time.sleep'):
            first=o.collect('2026-10-10',{'other_bounds_checkpoint':{'search_cursor':1}})
            second=o.collect('2026-10-10',{'other_bounds_checkpoint':first['checkpoint']})
        self.assertEqual(first['checkpoint']['search_cursor'],2);self.assertEqual(second['checkpoint']['search_cursor'],0)
        self.assertEqual([q.split('"')[1] for q in queries],['QuasiRiemann','Catalan constant'])

    def test_unfinished_reviewed_sources_precede_completed_source_rechecks(self):
        config=[dict(family='187',repo=n,baseline_commit='base',aliases=['Snaky']) for n in ['a/snaky','b/snaky']]
        pending=dict(full_name='b/snaky',default_branch='main',html_url='https://github.com/b/snaky')
        previous={'other_bound_states':{'a/snaky':{'head':'head','meta':dict(pending,full_name='a/snaky')}},'other_bounds_checkpoint':{'pending':[pending]}}
        calls=[]
        def api(path,params=None,**kwargs):calls.append(path);return {'sha':'base'}
        with patch.object(o,'CONFIG',config),patch.object(o,'MAX_REQUESTS',3),patch.object(o,'api',api),patch.object(o,'content',return_value=b'Snaky bound 20 moves.'):
            result=o.collect('2026-10-10',previous,search=False)
        self.assertEqual(calls[0],'repos/b/snaky/commits/main')
        self.assertIn('b/snaky',result['states'])

    def test_budget_expiry_preserves_unfinished_repository(self):
        clock=[100.0];meta=self.fork('person/math')
        def api(path,params=None,**kwargs):
            self.assertLessEqual(kwargs['deadline'],105)
            clock[0]=106;return {'sha':'head'}
        with patch.object(o,'CONFIG',[]),patch.object(o,'MAX_SECONDS',5),patch.object(o,'api',api),patch('watch_budget.time.monotonic',side_effect=lambda:clock[0]):
            result=o.collect('2026-10-10',{'other_bounds_checkpoint':{'pending':[meta]}},search=False)
        self.assertEqual(result['states'],{});self.assertEqual(result['usage']['requests'],1)
        self.assertEqual(result['checkpoint']['pending'][0]['full_name'],'person/math')
        self.assertTrue(result['errors'])

    def test_fork_and_other_source_queues_both_make_progress(self):
        source=dict(full_name='person/snaky',default_branch='main',html_url='https://github.com/person/snaky')
        previous={'other_bounds_checkpoint':{'pending':[self.fork('new/math'),self.fork('older/math','2026-10-10'),source]}}
        order=[]
        def api(path,params=None,**kwargs):
            if '/commits/' in path:
                if 'openai/math' not in path:order.append(path.split('/')[1])
                return {'sha':'head'}
            return {'files':[]}
        with patch.object(o,'CONFIG',[]),patch.object(o,'api',api),patch.object(o,'content',return_value=b'Snaky upper bound 19 moves.'):
            o.collect('2026-10-10',previous,search=False)
        self.assertEqual(order,['new','person','older'])

    def test_unchanged_search_hits_do_not_refill_completed_work(self):
        meta=dict(full_name='person/snaky',default_branch='main',html_url='https://github.com/person/snaky',pushed_at='2026-10-11')
        cfg=dict(family='187',repo='reviewed/snaky',baseline_commit='base',aliases=['Snaky'])
        previous={'other_bound_states':{'person/snaky':{'head':'head','meta':meta}}}
        calls=[]
        def api(path,params=None,**kwargs):
            calls.append(path)
            if path.endswith('/forks'):return []
            if path=='search/repositories':return {'items':[meta],'total_count':1}
            raise RuntimeError('reviewed source unavailable')
        with patch.object(o,'CONFIG',[cfg]),patch.object(o,'api',api),patch('watch_budget.time.sleep'):
            result=o.collect('2026-10-10',previous)
        self.assertFalse(any('person/snaky' in call for call in calls))
        self.assertNotIn('person/snaky',[p['full_name'] for p in result['checkpoint']['pending']])

    def test_exact_family_scope_and_big_o_filter_unchanged(self):
        from watch_policy import visible_problem
        self.assertEqual(set(o.FAMILIES),{'003','005','029','111','115','127','160','161','167','187','190','191','268'})
        for family,cfg in o.FAMILIES.items():
            self.assertIn(family,o.family_matches(cfg['aliases'][0]))
        self.assertFalse(o.other_problem('edit distance SSSP'))
        self.assertFalse(visible_problem('van der Waerden'))
        self.assertTrue(o.other_problem('van-der-Waerden-refinement'))
        self.assertTrue(visible_problem('matrix multiplication'))

    def test_new_claim_alerts_in_known_repo_but_not_same_number_prose(self):
        meta=dict(full_name='person/snaky',html_url='https://github.com/person/snaky')
        lines=o.claim_lines('New upper bound: 20 Maker moves.')
        row,key=o.candidate(meta,'a'*40,'187',lines,{},'other-bounds')
        self.assertTrue(alert_candidate(row,{'person/snaky'},set()))
        repeated,_=o.candidate(meta,'b'*40,'187',o.claim_lines('Our proven upper bound is 20 moves.'),{'seen_claims':[key]},'other-bounds')
        self.assertIsNone(repeated)
        self.assertFalse(alert_candidate({**row,'source_claim_evidence':[]},set(),set()))

    def test_fork_requires_added_improvement_not_inherited_baseline(self):
        self.assertTrue(o.openai_fork({'fork':True,'source':{'full_name':'openai/math'}}))
        self.assertFalse(o.openai_fork({'fork':True,'source':{'full_name':'CrocSwap/integer-mult-bounds'}}))
        self.assertEqual(o.claim_lines('Original family 003 threshold = 7/8.',True),[])
        self.assertEqual(o.claim_lines('No improvement to the bound 7/8.',True),[])
        self.assertEqual(o.claim_lines('README cleanup in 2026.',True),[])
        lines=o.claim_lines('Family 007: improved bound from 0.8 to 0.7.',True)
        row,_=o.candidate({'full_name':'person/math','html_url':'https://github.com/person/math'},'a'*40,'007',lines,{},'openai-math-fork')
        self.assertTrue(alert_candidate(row,{'person/math'},set()))

    def test_collect_checks_new_fork_patch_and_deduplicates(self):
        meta=dict(full_name='person/math',html_url='https://github.com/person/math',created_at='2026-10-11T00:00:00Z',pushed_at='2026-10-11T01:00:00Z',default_branch='main',fork=True)
        def api(path,params=None,**kwargs):
            if path=='repos/openai/math/forks':return [meta]
            if path=='repos/person/math/commits/main':return {'sha':'a'*40}
            if path=='repos/openai/math/commits/main':return {'sha':'b'*40}
            if '/compare/' in path:return {'files':[{'filename':'notes/007-improvement.md','patch':'+Family 007: improved bound from 0.8 to 0.7.'}]}
            if path=='repos/person/math':return meta
            raise AssertionError(path)
        with patch.object(o,'CONFIG',[]),patch.object(o,'api',api):
            first=o.collect('2026-10-10',{});second=o.collect('2026-10-10',{'other_bound_states':first['states']})
        self.assertEqual(first['candidates'][0]['other_family'],None)
        self.assertEqual(first['candidates'][0]['problem_guess'],'Family 007: OpenAI family 007')
        self.assertEqual(second['candidates'],[])
        self.assertEqual(first['errors'],[])

    def test_reviewed_source_baseline_suppresses_known_claim_and_detects_new_one(self):
        cfg={'family':'187','title':'Snaky','aliases':['Snaky'],'repo':'person/snaky','baseline_commit':'b'*40}
        meta=dict(full_name='person/snaky',html_url='https://github.com/person/snaky',default_branch='main')
        def api(path,params=None,**kwargs):
            if '/compare/' in path:return {'files':[]}
            return {'sha':'a'*40} if '/commits/' in path else meta
        def content(repo,path,pin,**kwargs):return b'Snaky upper bound 20 moves.' if pin=='b'*40 else b'Snaky improved bound 19 moves.'
        with patch.object(o,'CONFIG',[cfg]),patch.object(o,'api',api),patch.object(o,'content',content):
            result=o.collect('2026-10-10',{},search=False)
        self.assertEqual(len(result['candidates']),1);self.assertIn('19',result['candidates'][0]['source_claim_evidence'][0])
        self.assertEqual(result['errors'],[])

    def test_family_aliases_are_the_union_of_its_entries(self):
        cfgs=[dict(family='190',title='O',aliases=['ordered matrix removal'],repo='a/x',baseline_commit='b'*40),
              dict(family='190',title='O',aliases=['binary matrix removal','ordered matrix removal'],repo='b/y',baseline_commit='b'*40)]
        with patch.object(o,'CONFIG',cfgs):
            self.assertEqual(o.family_configs()[0]['aliases'],['ordered matrix removal','binary matrix removal'])
            self.assertEqual([a for _,a in o.search_phrases()],['ordered matrix removal','binary matrix removal'])
            self.assertEqual(o.family_matches('an ordered binary matrix removal repo'),['190'])
        self.assertEqual(cfgs[0]['aliases'],['ordered matrix removal'])

    def test_second_repo_of_a_family_is_watched_without_alias_in_readme(self):
        # Family 190 lists erebos and shea256 (2026-10-14); one search per family.
        cfgs=[{'family':'190','title':'Ordered matrix removal','aliases':['ordered matrix removal'],'repo':r,'baseline_commit':'b'*40}
              for r in ['erebos/removal','shea/binary-removal']]
        with patch.object(o,'CONFIG',cfgs):
            self.assertEqual(o.family_matches('ordered matrix removal'),['190'])
            self.assertEqual(len(o.family_configs()),1)
        queries=[]
        def api(path,params=None,**kwargs):
            if path=='search/repositories':queries.append(params['q']);return {'items':[],'total_count':0}
            if path.endswith('/forks'):return []
            if '/compare/' in path:return {'files':[]}
            if '/commits/' in path:return {'sha':'a'*40}
            name=path.removeprefix('repos/');return dict(full_name=name,html_url='https://github.com/'+name,default_branch='main')
        def content(repo,path,pin,**kwargs):
            if repo=='shea/binary-removal':return b'Pattern bound: 12 cells.' if pin=='b'*40 else b'New bound: 9 cells.'
            return b'Ordered matrix removal bound: 16 cells.'
        with patch.object(o,'CONFIG',cfgs),patch.object(o,'api',api),patch.object(o,'content',content),patch('watch_budget.time.sleep'):
            result=o.collect('2026-10-10',{})
        self.assertEqual(len(queries),1)
        self.assertEqual([(c['repo'],c['source_claim_evidence']) for c in result['candidates']],[('shea/binary-removal',['New bound: 9 cells.'])])
        self.assertEqual(result['errors'],[])

    def test_rewritten_history_still_reads_the_new_readme_claim(self):
        # slitsey/catalan-irrationality-measure, 2026-10-12..15: the stored head 41531d6
        # was orphaned by a history rewrite, compare returned 404 "No common ancestor"
        # every cycle, and the 7891..1281 records were never read. Real README lines.
        repo='slitsey/catalan-irrationality-measure'
        cfg={'family':'005','title':'Irrationality of Catalan’s constant','aliases':['Catalan irrationality','Catalan constant'],'repo':repo,'baseline_commit':'5'*40}
        old_readme=("# An irrationality measure for Catalan's constant\n\n> `|G - a/b| > b^(-8720)`.\n>\n"
                    "> So the irrationality exponent of `G` is at most `8720`. With Chebyshev's bounds in place of\n"
                    "> the prime number theorem in the final step, the argument gives `b^(-24850)`.\n")
        new_readme=("# An irrationality measure for Catalan's constant\n\n> `a` and every sufficiently large integer `b`,\n>\n"
                    "> `|G - a/b| > b^(-1281)`.\n>\n"
                    "> So the irrationality exponent of `G` is at most `1281`. With Chebyshev's bounds in place of\n"
                    "> the prime number theorem in the final step, the argument gives `b^(-3662)`.\n")
        orphan='4'*40;head='c'*40
        meta=dict(full_name=repo,html_url='https://github.com/'+repo,default_branch='main',pushed_at='2026-10-14T01:14:32Z')
        seen=o.claim_key('005',o.scoped_claims(old_readme,'005'))
        previous={'other_bound_states':{repo:{'head':orphan,'seen_claims':[seen],'meta':meta,'checked_cycle':8}}}
        def api(path,params=None,**kwargs):
            if '/compare/' in path:raise RuntimeError(f'GitHub GET failed: repos/{repo}/compare/{orphan}...{head} (exit 1)')
            return {'sha':head}
        with patch.object(o,'CONFIG',[cfg]),patch.object(o,'api',api),patch.object(o,'content',return_value=new_readme.encode()):
            result=o.collect('2026-10-13',previous,search=False)
        rows=[r for r in result['candidates'] if r['repo']==repo]
        self.assertEqual(len(rows),1);self.assertIn('> `|G - a/b| > b^(-1281)`.',rows[0]['source_claim_evidence'])
        self.assertTrue(alert_candidate(rows[0],set(),set()))
        self.assertEqual(result['states'][repo]['head'],head)
        self.assertTrue(any('history may be rewritten' in e for e in result['errors']))

    def test_configured_bound_alerts_only_when_the_stated_bound_changes(self):
        # slitsey/catalan-irrationality-measure, 2026-10-20 07:04Z and 10:04Z: two alerts on
        # companion constants (L(2,chi_-3), G +/- 5pi^2/48) while G stayed b^(-740). Real README lines.
        repo='slitsey/catalan-irrationality-measure'
        cfg={'family':'005','title':'Irrationality of Catalan’s constant','aliases':['Catalan irrationality','Catalan constant'],'repo':repo,'baseline_commit':'5'*40,
             'bound_pattern':r'\|G\s*-\s*a/b\|\s*>\s*b\^\(-\s*(?P<num>\d+(?:\.\d+)?)\)','reviewed_bound':'740'}
        def readme(g,companion):
            return ("# An irrationality measure for Catalan's constant\n\n> `a` and every sufficiently large integer `b`,\n>\n"
                    f"> `|G - a/b| > b^(-{g})`.\n>\n> So the irrationality exponent of `G` is at most `{g}`. Chebyshev's bounds\n\n"
                    "## Companion result: G ± 5π²/48 and L(2, χ₋₃)\n\n"
                    f"- μ(G − 5π²/48) ≤ {companion};\n- μ(L(2, χ₋₃)) ≤ 18.50 (earlier 23.82 and 21.16 exports retained).\n")
        meta=dict(full_name=repo,html_url='https://github.com/'+repo,default_branch='main',pushed_at='2026-10-20T09:00:00Z')
        # State before this change: the key of the whole README at the 07:04Z head.
        previous={'other_bound_states':{repo:{'head':'a'*40,'seen_claims':[o.claim_key('005',o.scoped_claims(readme(740,38.35),'005'))],'meta':meta,'checked_cycle':8}}}
        def run(text,previous,head):
            def api(path,params=None,**kwargs):
                if '/compare/' in path:return {'files':[{'filename':'paper/catalan.tex','status':'modified','patch':'+lowers the exponent from about $50.0$ to $38.35$ for Catalan constant.'}]}
                return {'sha':head}
            with patch.object(o,'CONFIG',[cfg]),patch.object(o,'api',api),patch.object(o,'content',return_value=text.encode()):
                result=o.collect('2026-10-20',previous,search=False)
            return [r for r in result['candidates'] if r['repo']==repo],result
        # Companion constants change, G stays 740 (reviewed): silent, also for the .tex diff.
        rows,result=run(readme(740,34.74),previous,'b'*40);self.assertEqual(rows,[])
        previous={'other_bound_states':result['states']}
        # G itself changes: one alert with the G line, then silent at the same value.
        rows,result=run(readme(700,34.74),previous,'c'*40)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['source_claim_evidence'],['> `|G - a/b| > b^(-700)`.'])
        self.assertTrue(alert_candidate(rows[0],set(),set()))
        rows,result=run(readme(700,30.1),{'other_bound_states':result['states']},'d'*40);self.assertEqual(rows,[])
        # A README without the configured statement alerts on all its claims and logs why.
        rows,result=run(readme(700,30.1).replace('|G - a/b| >','|G-p/q| >'),{'other_bound_states':result['states']},'e'*40)
        self.assertTrue(any('> `|G-p/q| > b^(-700)`.' in r['source_claim_evidence'] for r in rows))
        self.assertTrue(any('configured bound not found' in e for e in result['errors']))

    def test_a_bound_flags_only_when_it_beats_the_site_leader(self):
        # MarcosCarreira/catalan-designs v2, 2026-10-21: mu(G) < 2 294, down from his own
        # 2 715, while the Catalan leader is slitsey's 740. Real README lines.
        repo='MarcosCarreira/catalan-designs'
        cfg=next(c for c in o.CONFIG if c['repo']==repo)
        def readme(new):
            return ("This repository holds the note *General designs and an irrationality exponent for Catalan's constant*\n"
                    "   (github.com/slitsey/catalan-irrationality-measure), and with nonvanishing at prime scales p whose square\n"
                    f"   does not divide the denominator (Lemma 29), give mu(G) < {new} for (36, 6, 2, 3, 2) and mu(G) < 2 426 for\n"
                    "Theorem 35, mu(G) < 2 715) now gives 2 294. The numbering after Section 4 has shifted by one section.\n")
        site={'families':[{'slug':'catalan','direction':'lower','claims':[{'value':'8720'},{'value':'2715'},{'value':'740'}]}]}
        meta=dict(full_name=repo,html_url='https://github.com/'+repo,default_branch='main',pushed_at='2026-10-21T12:00:00Z')
        def run(text,head,previous,site_error=None,paper='+we now prove mu(G) < 2 294 for Catalan constant, improving 2 715.'):
            def content(r,path,ref,**kwargs):
                if r==o.SITE:
                    if site_error:raise site_error
                    self.assertEqual((path,ref),(o.SITE_BOUNDS,'main'));return json.dumps(site).encode()
                return text.encode()
            def api(path,params=None,**kwargs):
                if '/compare/' in path:return {'files':[{'filename':'paper/main.tex','status':'modified','patch':paper}]}
                return {'sha':head}
            with patch.object(o,'CONFIG',[cfg]),patch.object(o,'api',api),patch.object(o,'content',content):
                result=o.collect('2026-10-21',previous,search=False)
            return [r for r in result['candidates'] if r['repo']==repo],result
        previous={'other_bound_states':{repo:{'head':'a'*40,'seen_claims':[],'meta':meta,'checked_cycle':1}}}
        # His own improvement that stays behind the leader 740: silent, also for the .tex diff.
        rows,result=run(readme('2 294'),'b'*40,previous);self.assertEqual(rows,[])
        self.assertEqual(o.stated_values(cfg['bound_pattern'],readme('2 294')),[2294,2426,2715])
        # A value that beats the leader: one alert with its line, then silent at the same value.
        rows,result=run(readme('699'),'c'*40,{'other_bound_states':result['states']})
        self.assertEqual(len(rows),1);self.assertIn('mu(G) < 699 for (36, 6, 2, 3, 2)',rows[0]['source_claim_evidence'][0])
        rows,result=run(readme('699'),'d'*40,{'other_bound_states':result['states']});self.assertEqual(rows,[])
        # The leader is read from the site: when it falls to 600, 699 no longer beats it.
        site['families'][0]['claims'].append({'value':'600'})
        rows,_=run(readme('650'),'e'*40,{'other_bound_states':result['states']});self.assertEqual(rows,[])
        # An unreadable leader logs why and alerts on the stated bound.
        rows,result=run(readme('2 100'),'f'*40,{'other_bound_states':result['states']},site_error=RuntimeError('GitHub GET failed (HTTP 404)'))
        self.assertEqual(len(rows),1);self.assertTrue(any('cannot read the catalan leader' in e for e in result['errors']))
        # Reviewer FIX 2: with the leader unreadable, a better value on a later line (the first
        # line unchanged) changes the set of stated values, so it alerts too.
        state={'other_bound_states':result['states']}
        rows,_=run(readme('2 100')+'Corollary: mu(G) < 1 900.\n','g'*40,state,site_error=RuntimeError('GitHub GET failed (HTTP 404)'))
        self.assertEqual(len(rows),1);self.assertIn('Corollary: mu(G) < 1 900.',rows[0]['source_claim_evidence'])

    def test_a_record_stated_only_in_the_paper_alerts(self):
        # Reviewer FIX 1, 2026-10-21: the README still shows 2 294 (behind the leader 740), and
        # the .tex diff states 699: the record alerts from the diff.
        repo='MarcosCarreira/catalan-designs'
        cfg=next(c for c in o.CONFIG if c['repo']==repo)
        text="give mu(G) < 2 294 for (36, 6, 2, 3, 2) and mu(G) < 2 426 for\n"
        site={'families':[{'slug':'catalan','direction':'lower','claims':[{'value':'740'}]}]}
        meta=dict(full_name=repo,html_url='https://github.com/'+repo,default_branch='main',pushed_at='2026-10-21T12:00:00Z')
        compares=[]
        def content(r,path,ref,**kwargs):return json.dumps(site).encode() if r==o.SITE else text.encode()
        def api(path,params=None,**kwargs):
            if '/compare/' in path:
                compares.append(path)
                return {'files':[{'filename':'paper/main.tex','status':'modified','patch':'@@ -1 +1 @@\n-old\n+Theorem 36. We now prove $\\mu(G) \\le 699$ for the design (40, 6, 2).'},
                                 {'filename':'README.md','status':'modified','patch':'+mu(G) < 5'}]}
            return {'sha':'b'*40}
        previous={'other_bound_states':{repo:{'head':'a'*40,'seen_claims':[],'meta':meta,'checked_cycle':1}}}
        with patch.object(o,'CONFIG',[cfg]),patch.object(o,'api',api),patch.object(o,'content',content):
            result=o.collect('2026-10-21',previous,search=False)
        rows=[r for r in result['candidates'] if r['repo']==repo]
        self.assertEqual(len(rows),1);self.assertIn('699',rows[0]['source_claim_evidence'][0])
        self.assertEqual(rows[0]['claim_signature'],o.bound_key('005',699));self.assertEqual(len(compares),1)
        # README.md lines in the diff are not read twice: its whole text is read at head.
        self.assertNotIn('mu(G) < 5',rows[0]['source_claim_evidence'][0])
        # A list with a comma is two values, not 650700.
        self.assertEqual(o.stated_values(cfg['bound_pattern'],'mu(G) < 650,700'),[650])

    def test_repo_without_readme_is_not_stalled(self):
        # karirogg/QuasiRiemannTracker (a fork without README.md) failed every cycle, 2026-10-15.
        repo='karirogg/QuasiRiemannTracker'
        cfg={'family':'003','title':'Q','aliases':['quasi Riemann'],'repo':repo,'baseline_commit':'b'*40}
        meta=dict(full_name=repo,html_url='https://github.com/'+repo,default_branch='main')
        def api(path,params=None,**kwargs):
            if path.endswith('/git/trees/'+'a'*40):return {'tree':[{'path':'proofs'},{'path':'src'}]}
            if '/compare/' in path:return {'files':[dict(filename='proofs/notes.md',status='added',patch='+Quasi Riemann zero-free bound 0.87486 improved.')]}
            return {'sha':'a'*40}
        def content(repo,path,pin,**kwargs):raise RuntimeError('GitHub GET failed: contents/README.md (exit 1)')
        with patch.object(o,'CONFIG',[cfg]),patch.object(o,'api',api),patch.object(o,'content',content):
            result=o.collect('2026-10-13',{'other_bound_states':{repo:{'head':'b'*40,'meta':meta}}},search=False)
        self.assertEqual(result['states'][repo]['head'],'a'*40)
        self.assertEqual([r['source_claim_evidence'] for r in result['candidates']],[['Quasi Riemann zero-free bound 0.87486 improved.']])
        # A README that exists but cannot be read now is transient: the head does not move.
        def api2(path,params=None,**kwargs):
            if '/git/trees/' in path:return {'tree':[{'path':'README.md'}]}
            return {'sha':'a'*40}
        with patch.object(o,'CONFIG',[cfg]),patch.object(o,'api',api2),patch.object(o,'content',content):
            result=o.collect('2026-10-13',{'other_bound_states':{repo:{'head':'b'*40,'meta':meta}}},search=False)
        self.assertEqual(result['states'].get(repo,{}).get('head'),'b'*40)

    def test_first_check_of_a_repo_without_readme_is_not_stalled(self):
        # karirogg/QuasiRiemannTracker had no state yet: the first-run baseline README read
        # also 404'd and was not guarded by 64a3b09, so the repo stayed stalled (cycle 38).
        repo='karirogg/QuasiRiemannTracker'
        cfg={'family':'003','title':'Q','aliases':['quasi Riemann'],'repo':repo,'baseline_commit':'b'*40}
        trees=[]
        def api(path,params=None,**kwargs):
            if '/git/trees/' in path:trees.append(path.rsplit('/',1)[1]);return {'tree':[{'path':'proofs'},{'path':'src'}]}
            if '/compare/' in path:return {'files':[dict(filename='proofs/notes.md',status='added',patch='+Quasi Riemann zero-free bound 0.87486 improved.')]}
            if path=='repos/'+repo:return dict(full_name=repo,html_url='https://github.com/'+repo,default_branch='main')
            return {'sha':'a'*40}
        def content(repo,path,pin,**kwargs):raise RuntimeError('GitHub GET failed: contents/README.md (exit 1)')
        with patch.object(o,'CONFIG',[cfg]),patch.object(o,'api',api),patch.object(o,'content',content):
            result=o.collect('2026-10-13',{},search=False)
        self.assertEqual(result['errors'],[])
        self.assertEqual(result['states'][repo]['head'],'a'*40)
        self.assertEqual(sorted(set(trees)),['a'*40,'b'*40])
        self.assertEqual([r['source_claim_evidence'] for r in result['candidates']],[['Quasi Riemann zero-free bound 0.87486 improved.']])

    def test_api_failure_preserves_prior_claim_state(self):
        previous={'other_bound_states':{'person/math':{'head':'a'*40,'seen_claims':['known'],'openai_fork':True}}}
        with patch.object(o,'CONFIG',[]),patch.object(o,'api',side_effect=RuntimeError('GitHub unavailable')):
            result=o.collect('2026-10-10',previous,search=False)
        self.assertEqual(result['states'],previous['other_bound_states'])
        self.assertEqual(result['candidates'],[]);self.assertTrue(result['errors'])

    def test_multi_family_readme_does_not_mix_claim_numbers(self):
        text='# Family 003\nImproved threshold bound 0.87.\n# Family 187\nImproved Snaky upper bound 19 moves.'
        self.assertEqual(o.scoped_claims(text,'003'),['Improved threshold bound 0.87.'])
        self.assertEqual(o.scoped_claims(text,'187'),['Improved Snaky upper bound 19 moves.'])
