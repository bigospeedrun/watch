import contextlib, io, json, tempfile, unittest, urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import x_watch
from refresh import git_state_dir

class XWatchTests(unittest.TestCase):
    def fixture(self,tmp):
        root=Path(tmp);(root/'x-watchlist.local.json').write_text(json.dumps({'accounts':['0xdoug'],'max_posts_per_profile':2,'first_run_hours':72}));return root

    def test_no_offer_has_no_navigation_or_alert(self):
        with tempfile.TemporaryDirectory(dir=git_state_dir()) as tmp:
            root=self.fixture(tmp);actions=[]
            def browser(action,**kwargs):actions.append(action);return {'tabs':[]}
            with patch.object(x_watch,'ROOT',root),patch.object(x_watch,'git_state_dir',lambda:root),patch.object(x_watch,'browser',browser),patch.object(x_watch,'office') as office,contextlib.redirect_stdout(io.StringIO()):result=x_watch.run()
            self.assertEqual(result['status'],'skipped-no-offered-tab');self.assertEqual(actions,['tabs']);office.assert_not_called()

    def test_wall_alert_once_and_restore(self):
        with tempfile.TemporaryDirectory(dir=git_state_dir()) as tmp:
            root=self.fixture(tmp);actions=[];current=['https://example.org/start']
            def browser(action,**kwargs):
                actions.append((action,kwargs))
                if action=='tabs':return {'tabs':[{'target':'tab1','scope':'agent'}]}
                if action=='goto':current[0]=kwargs['url'];return {'ok':True}
                return {'url':current[0],'text':'Log in to X' if 'x.com' in current[0] else 'original'}
            with patch.object(x_watch,'ROOT',root),patch.object(x_watch,'git_state_dir',lambda:root),patch.object(x_watch,'browser',browser),patch.object(x_watch,'office') as office,contextlib.redirect_stdout(io.StringIO()):
                first=x_watch.run();second=x_watch.run()
            self.assertTrue(first['tab_restored']);self.assertTrue(second['tab_restored']);self.assertEqual(office.call_count,1)
            self.assertEqual(current[0],'https://example.org/start');self.assertFalse((root/'x-watch-restore.json').exists())
            self.assertTrue(all(a in ('tabs','text','goto') for a,_ in actions))

    def test_end_of_profile_timeout_continues_and_restores(self):
        with tempfile.TemporaryDirectory(dir=git_state_dir()) as tmp:
            root=self.fixture(tmp)
            (root/'x-watchlist.local.json').write_text(json.dumps({'accounts':['0xdoug','RohanArun'],'max_posts_per_profile':2,'first_run_hours':72}))
            current=['https://example.org/start']
            def browser(action,**kwargs):
                if action=='tabs':return {'tabs':[{'target':'tab1','scope':'agent'}]}
                if action=='goto':current[0]=kwargs['url'];return {'ok':True}
                selector=kwargs.get('selector','')
                if 'nth=1' in selector:raise TimeoutError('No further article')
                text='A bound without a visible link' if 'tweetText' in selector else 'Researcher\n1h\nA bound without a visible link'
                return {'url':current[0],'text':text}
            with patch.object(x_watch,'ROOT',root),patch.object(x_watch,'git_state_dir',lambda:root),patch.object(x_watch,'browser',browser),patch.object(x_watch,'office') as office,contextlib.redirect_stdout(io.StringIO()):result=x_watch.run()
            self.assertEqual(set(result['profiles']),{'0xdoug','RohanArun'})
            state=json.loads((root/'x-watch-state.json').read_text())
            self.assertIsNone(state['accounts']['0xdoug']['checked_at'])
            self.assertTrue(result['tab_restored']);self.assertEqual(current[0],'https://example.org/start');office.assert_not_called()

    def test_unexpected_profile_is_rejected(self):
        with patch.object(x_watch,'browser',return_value={'url':'https://x.com/messages','text':'unrelated page'}):
            with self.assertRaises(ValueError):x_watch.profile_text('tab1','0xdoug')

    def test_visible_links_and_relative_time(self):
        self.assertEqual(x_watch.visible_links('github.com/a/b?tracking=x arxiv.org/abs/2610.12345 github.com/a/truncated…'),['https://github.com/a/b','https://arxiv.org/abs/2610.12345'])
        now=datetime(2026,10,9,18,tzinfo=timezone.utc);raw,early,late=x_watch.post_time('Someone\n@person\n·\n1h\nA bound',now)
        self.assertEqual(raw,'1h');self.assertEqual(early.hour,16);self.assertEqual(late.hour,17)
if __name__=='__main__':unittest.main()
