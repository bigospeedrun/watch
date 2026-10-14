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
        config=[o.FAMILIES['003'],o.FAMILIES['005']];queries=[]
        def api(path,params=None,**kwargs):
            if path.endswith('/forks'):return []
            if path=='search/repositories':
                queries.append(params['q']);return {'items':[],'total_count':0}
            raise RuntimeError('source unavailable')
        with patch.object(o,'CONFIG',config),patch.object(o,'DISCOVERY_REQUESTS',2),patch.object(o,'api',api),patch('watch_budget.time.sleep'):
            first=o.collect('2026-10-10',{'other_bounds_checkpoint':{'search_cursor':1}})
            second=o.collect('2026-10-10',{'other_bounds_checkpoint':first['checkpoint']})
        self.assertEqual(first['checkpoint']['search_cursor'],0)
        self.assertIn(config[1]['aliases'][0],queries[0]);self.assertIn(config[0]['aliases'][0],queries[1])

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
