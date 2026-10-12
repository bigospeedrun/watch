import contextlib, io, json, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import people_watch
from refresh import git_state_dir

class PeopleWatchTests(unittest.TestCase):
    def test_crocswap_pr_body_keeps_cross_problem_lead(self):
        with tempfile.TemporaryDirectory(dir=git_state_dir()) as tmp:
            root=Path(tmp)
            docs={'people-watchlist.json':{'people':[{'github':'researcher'}],'active_author_count':0},'submissions.json':{'items':[]},'registry.json':{'repositories':[{'repo':'CrocSwap/integer-mult-bounds'}]},'pivot-watchlist.json':{'repositories':[]}}
            for name,data in docs.items():(root/name).write_text(json.dumps(data))
            stamp=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
            def api(path,params=None):
                if path.endswith('/events/public'):
                    return [dict(id=str(n),type='PullRequestEvent',created_at=stamp,repo={'name':'CrocSwap/integer-mult-bounds'},payload={'action':'opened','number':n}) for n in [1,2]]
                if path.endswith('/repos'):return []
                if '/pulls/' in path:return dict(title='Integer multiplication circuit',body='Exact DFT bound improves to 0.001.' if path.endswith('/2') else 'Integer multiplication kappa = 0.001.')
                return dict(login='researcher',html_url='https://github.com/researcher')
            with patch.object(people_watch,'ROOT',root),patch.object(people_watch,'api',api),contextlib.redirect_stdout(io.StringIO()):people_watch.main()
            hits=json.loads((root/'people-watch.json').read_text())['hits']
            self.assertEqual([h['url'] for h in hits],['https://github.com/CrocSwap/integer-mult-bounds/pull/2'])

    def test_event_scope(self):
        def event(kind,repo,payload):return {'type':kind,'repo':{'name':repo},'payload':payload}
        known={'crocswap/integer-mult-bounds'}
        self.assertIsNone(people_watch.classify({'type':'PushEvent','repo':{'id':123},'payload':{}},known))
        self.assertIsNone(people_watch.classify(event('PushEvent','CrocSwap/integer-mult-bounds',{}),known))
        self.assertEqual(people_watch.classify(event('PushEvent','person/new-bounds',{}),known),('push-outside-watchlist','person/new-bounds'))
        self.assertIsNone(people_watch.classify(event('PullRequestEvent','person/notes',{'action':'opened'}),known))
        self.assertIsNone(people_watch.classify(event('PullRequestEvent','CrocSwap/integer-mult-bounds',{'action':'closed'}),known))
        self.assertEqual(people_watch.classify(event('CreateEvent','person/new-repo',{'ref_type':'repository'}),known),('new-repository','person/new-repo'))

    def test_first_branch_is_a_lead(self):
        event={'type':'CreateEvent','repo':{'name':'Swapnil-jain/threesum-derand'},'payload':{'ref_type':'branch'}}
        self.assertEqual(people_watch.classify(event,set()),('branch-outside-watchlist','Swapnil-jain/threesum-derand'))
        self.assertTrue(people_watch.WORDS.search('threesum-derand'))

    def test_inventory_recovers_missing_events_once(self):
        with tempfile.TemporaryDirectory(dir=git_state_dir()) as tmp:
            root=Path(tmp)
            for name,data in {'people-watchlist.json':{'people':[{'github':'researcher'}],'active_author_count':0},'submissions.json':{'items':[]},'registry.json':{'repositories':[]},'pivot-watchlist.json':{'repositories':[]}}.items():(root/name).write_text(json.dumps(data))
            stamp=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
            def api(path,params=None):
                if path.endswith('/events/public'):return []
                if path.endswith('/repos'):return [{'full_name':'researcher/threesum-derand','pushed_at':stamp,'html_url':'https://github.com/researcher/threesum-derand','description':'Deterministic 3SUM'}]
                return {'login':'researcher','name':'Researcher','html_url':'https://github.com/researcher'}
            with patch.object(people_watch,'ROOT',root),patch.object(people_watch,'api',api),contextlib.redirect_stdout(io.StringIO()):
                people_watch.main();first=json.loads((root/'people-watch.json').read_text())
                people_watch.main();second=json.loads((root/'people-watch.json').read_text())
            self.assertEqual(first['hits'][0]['kind'],'repository-inventory-change')
            self.assertEqual(second['hits'],[])

    def test_second_run_deduplicates_public_events(self):
        with tempfile.TemporaryDirectory(dir=git_state_dir()) as tmp:
            root=Path(tmp)
            for name,data in {'people-watchlist.json':{'people':[{'github':'researcher'}],'active_author_count':10},'submissions.json':{'items':[]},'registry.json':{'repositories':[]},'pivot-watchlist.json':{'repositories':[]}}.items():(root/name).write_text(json.dumps(data))
            event={'id':'101','type':'CreateEvent','created_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'repo':{'name':'researcher/dft-bounds'},'payload':{'ref_type':'repository'}}
            def api(path,params=None):
                if path.endswith('/events/public'):return [event]
                if path.endswith('/repos'):return []
                return {'login':'researcher','name':'Researcher','html_url':'https://github.com/researcher'}
            with patch.object(people_watch,'ROOT',root),patch.object(people_watch,'api',api),contextlib.redirect_stdout(io.StringIO()):
                people_watch.main();first=json.loads((root/'people-watch.json').read_text())
                people_watch.main();second=json.loads((root/'people-watch.json').read_text())
            self.assertEqual(len(first['hits']),1);self.assertEqual(second['hits'],[])
            self.assertEqual(second['users']['researcher']['seen_ids'],['101'])
    def test_other_family_and_openai_fork_survive_people_filter(self):
        for repo,description,fork in [('researcher/snaky','Snaky improved bound 19 moves',False),('researcher/math','formal mathematics',True)]:
            with self.subTest(repo=repo),tempfile.TemporaryDirectory(dir=git_state_dir()) as tmp:
                root=Path(tmp)
                docs={'people-watchlist.json':{'people':[{'github':'researcher'}],'active_author_count':0},'submissions.json':{'items':[]},'registry.json':{'repositories':[{'repo':'openai/math'}]},'pivot-watchlist.json':{'repositories':[]}}
                for name,data in docs.items():(root/name).write_text(json.dumps(data))
                stamp=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
                meta=dict(full_name=repo,pushed_at=stamp,html_url='https://github.com/'+repo,description=description,fork=fork,source={'full_name':'openai/math'})
                def api(path,params=None):
                    if path.endswith('/events/public'):return []
                    if path.endswith('/repos'):return [meta]
                    if path.startswith('repos/'):return meta
                    return {'login':'researcher','name':'Researcher','html_url':'https://github.com/researcher'}
                with patch.object(people_watch,'ROOT',root),patch.object(people_watch,'api',api),contextlib.redirect_stdout(io.StringIO()):people_watch.main()
                hits=json.loads((root/'people-watch.json').read_text())['hits']
                self.assertEqual(len(hits),1);self.assertEqual(hits[0]['openai_math_fork'],fork)

if __name__=='__main__':unittest.main()
