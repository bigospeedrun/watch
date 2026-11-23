import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError, URLError
import discord_watch as w

class API:
    guild='G';channel='C'
    def __init__(self,messages):self.rows=messages;self.reactions=[];self.reads=[]
    def check_channel(self):pass
    def messages(self,after):
        self.reads.append(after)
        return list(reversed([m for m in self.rows if int(m['id'])>int(after)][:100]))
    def react(self,mid):self.reactions.append(mid)

def msg(n,content):return dict(id=str(n),type=0,content=content,author=dict(id='44',username='private-name'))

class DiscordTests(unittest.TestCase):
    def test_strict_urls(self):
        text=' '.join(['https://github.com/owner/repo','https://github.com/owner/repo/pull/7?x=1',
            'https://github.com/owner/repo/blob/main/a.md#L3','https://github.com/owner/repo/tree/dev',
            'https://github.com/owner/repo/commit/abcdef1','https://github.com/owner/repo/issues/1',
            'https://github.com.evil/owner/repo','https://github.com@evil/owner/repo',
            'https://evil@github.com/owner/repo','https://github.com:443/owner/repo',
            'https://github.com/owner/repo/blob/main/../secret','https://github.com/owner/repo%2fextra',
            'https://github.com/owner/repo/pull/7/extra','http://github.com/owner/repo'])
        self.assertEqual(len(w.github_urls(text)),5)
        self.assertEqual(w.github_urls('<https://github.com/a/b> https://github.com/a/b.'),['https://github.com/a/b'])

    def test_bots_and_webhooks_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bot=msg(1,'https://github.com/a/b');bot['author']['bot']=True
            webhook=msg(2,'https://github.com/a/b');webhook['webhook_id']='99'
            emptybot=msg(3,'');emptybot['author']['bot']=True
            api=API([bot,webhook,emptybot]);alerts=[]
            result=w.run(api,lambda *x:alerts.append(x),root)
            self.assertEqual(result['status'],'ok');self.assertEqual(result['hits'],0)
            self.assertEqual(alerts,[]);self.assertEqual(api.reactions,[])
            self.assertFalse((root/w.PUBLIC).exists())
            state=json.loads((root/w.PRIVATE).read_text())
            self.assertEqual(state['messages'],{});self.assertEqual(state['last_seen'],'3')

    def test_a_link_to_our_own_organization_alerts_the_lead_and_stays_out_of_the_public_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);alerts=[]
            api=API([msg(4,'Formalization PR https://github.com/BigOSpeedrun/verifier/pull/7?x=1 and a run https://github.com/fringewidth/verifier/actions/runs/1')])
            result=w.run(api,lambda *x:alerts.append(x),root)
            self.assertEqual((result['status'],result['hits']),('ok',1))
            self.assertEqual(len(alerts),1);self.assertIn('our own repository',alerts[0][0]);self.assertIn('https://github.com/BigOSpeedrun/verifier/pull/7',alerts[0][0])
            self.assertTrue(alerts[0][1].startswith('discord-intake-'));self.assertEqual(api.reactions,['4'])
            self.assertIn('https://discord.com/channels/G/C/4',alerts[0][0])
            self.assertFalse((root/w.PUBLIC).exists(),'an own repository is not a new race to review')
            state=json.loads((root/w.PRIVATE).read_text())
            self.assertTrue(state['messages']['4']['own_alerted']);self.assertEqual(state['last_seen'],'4')
            # A second pass over the same message alerts again for nothing.
            state['last_seen']='0';(root/w.PRIVATE).write_text(json.dumps(state))
            w.run(api,lambda *x:alerts.append(x),root);self.assertEqual(len(alerts),1)

    def test_a_message_with_an_own_link_and_a_foreign_repo_gets_both_lines_in_one_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);alerts=[]
            api=API([msg(5,'https://github.com/bigospeedrun/site/issues/3 https://github.com/a/b')])
            w.run(api,lambda *x:alerts.append(x),root)
            self.assertEqual(len(alerts),1);text=alerts[0][0]
            self.assertIn('New repo: https://github.com/a/b (Discord submission)',text)
            self.assertIn('our own repository; read it and answer: https://github.com/bigospeedrun/site/issues/3',text)
            self.assertEqual(api.reactions,['5'])
            self.assertEqual(json.loads((root/w.PUBLIC).read_text())['submissions'],[dict(message_id='5',repo_urls=['https://github.com/a/b'])])

    def test_private_public_split_reaction_and_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);api=API([msg(1,'secret prose https://github.com/a/b/pull/7'),msg(2,'no link')]);alerts=[]
            w.run(api,lambda *x:alerts.append(x),root)
            public=json.loads((root/w.PUBLIC).read_text());private=json.loads((root/w.PRIVATE).read_text())
            self.assertEqual(public,{'submissions':[{'message_id':'1','repo_urls':['https://github.com/a/b']}]})
            self.assertEqual(private['messages']['1']['username'],'private-name')
            self.assertEqual(private['last_seen'],'2');self.assertEqual(api.reactions,['1'])
            self.assertNotIn('secret prose',(root/w.PRIVATE).read_text()+str(alerts))
            w.run(api,lambda *x:alerts.append(x),root);self.assertEqual(len(alerts),1)

    def test_unavailable_alert_once_cursor_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);api=API([msg(1,'https://github.com/a/b'),msg(2,'')]);alerts=[]
            for _ in range(2):self.assertEqual(w.run(api,lambda *x:alerts.append(x),root)['status'],'content unavailable')
            self.assertEqual(len(alerts),1);self.assertEqual(api.reactions,[])
            self.assertEqual(json.loads((root/w.PRIVATE).read_text())['last_seen'],'0')
            self.assertFalse((root/w.PUBLIC).exists())

    def test_dry_run_has_no_writes_reactions_or_alerts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);api=API([msg(1,'https://github.com/a/b')]);alerts=[]
            self.assertEqual(w.run(api,lambda *x:alerts.append(x),root,True)['hits'],1)
            self.assertEqual(list(root.iterdir()),[]);self.assertEqual(api.reactions,[]);self.assertEqual(alerts,[])

    def test_pagination_no_skips(self):
        with tempfile.TemporaryDirectory() as tmp:
            api=API([msg(i,'no URL') for i in range(1,206)])
            result=w.run(api,lambda *x:None,Path(tmp))
            self.assertEqual(result['messages'],205);self.assertEqual(api.reads,['0','100','200'])

    def test_delivery_failure_keeps_the_record_pending_for_the_next_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);api=API([msg(1,'https://github.com/a/b')]);alerts=[]
            def fail(*args):alerts.append(args);raise RuntimeError('failed')
            with self.assertRaises(RuntimeError):w.run(api,fail,root)
            state=json.loads((root/w.PRIVATE).read_text())
            self.assertEqual(state['last_seen'],'1');self.assertFalse(state['messages']['1']['alerted'])
            self.assertEqual(api.reactions,[])
            # The next run reads no new message and still sends the pending alert.
            w.run(api,lambda *x:alerts.append(x),root)
            self.assertEqual(len(alerts),2);self.assertIn('https://discord.com/channels/G/C/1',alerts[1][0])
            # The resend has the identity of the failed attempt: if that one was delivered, the office drops this one.
            self.assertEqual(alerts[0][1],alerts[1][1])
            self.assertEqual(api.reactions,['1'])
            self.assertEqual(len(json.loads((root/w.PUBLIC).read_text())['submissions']),1)

    def test_reaction_failure_does_not_repeat_delivered_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);api=API([msg(1,'https://github.com/a/b')]);alerts=[];react=api.react
            api.react=lambda _:(_ for _ in ()).throw(RuntimeError())
            with self.assertRaises(RuntimeError):w.run(api,lambda *x:alerts.append(x),root)
            api.react=react;w.run(api,lambda *x:alerts.append(x),root)
            self.assertEqual(len(alerts),1);self.assertEqual(api.reactions,['1'])

    def test_one_alert_per_run_with_new_and_known_repos(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);alerts=[]
            api=API([msg(1,'https://github.com/old/repo')])
            w.run(api,lambda *x:alerts.append(x),root)
            api.rows+=[msg(2,'claim one https://github.com/old/repo/blob/main/A.lean'),msg(3,'claim two https://github.com/old/repo'),
                msg(4,'https://github.com/new/repo/pull/2 and https://github.com/old/repo'),msg(5,'no link')]
            w.run(api,lambda *x:alerts.append(x),root)
            self.assertEqual(len(alerts),2);text=alerts[1][0]
            self.assertIn('3 new messages with GitHub links',text)
            self.assertIn('Known repo, already flagged: https://github.com/old/repo (Discord submission). 3 new messages: '+
                ' '.join('https://discord.com/channels/G/C/'+n for n in '234'),text)
            self.assertIn('New repo: https://github.com/new/repo (Discord submission). 1 new message: https://discord.com/channels/G/C/4',text)
            self.assertNotIn('claim',text)
            self.assertEqual(api.reactions,['1','2','3','4'])
            self.assertEqual([r['message_id'] for r in json.loads((root/w.PUBLIC).read_text())['submissions']],['1','2','3','4'])
            # Each alert has its own identity (the office drops a message whose identity it already has).
            self.assertNotEqual(alerts[0][1],alerts[1][1])

    def test_message_links_per_repo_are_capped(self):
        with tempfile.TemporaryDirectory() as tmp:
            api=API([msg(i,'https://github.com/a/b') for i in range(1,13)]);alerts=[]
            w.run(api,lambda *x:alerts.append(x),Path(tmp))
            self.assertEqual(len(alerts),1);text=alerts[0][0]
            self.assertIn('12 new messages: ',text);self.assertIn('/C/10 and 2 more',text);self.assertNotIn('/C/11',text)
            self.assertEqual(len(api.reactions),12)

    def test_a_record_from_before_the_change_is_not_reacted_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);api=API([]);alerts=[]
            (root/w.PRIVATE).write_text(json.dumps({'last_seen':'9','content_alerted':False,'messages':{'9':dict(
                author_id='44',username='x',urls=['https://github.com/a/b'],alerted=True)}}))
            self.assertEqual(w.run(api,lambda *x:alerts.append(x),root)['status'],'ok')
            self.assertEqual((alerts,api.reactions),([],[]))

class RequestRetryTests(unittest.TestCase):
    def client(self):
        client=w.Discord.__new__(w.Discord);client.token='t';return client
    def opener(self,*outcomes):
        calls=[]
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):return False
            def read(self,n):return b'{"ok": 1}'
        def open_(request,timeout):
            calls.append(request.full_url);outcome=outcomes[len(calls)-1]
            if isinstance(outcome,Exception):raise outcome
            return Response()
        return calls,mock.patch.object(w,'build_opener',lambda *_:mock.Mock(open=open_))

    def test_one_transport_failure_is_retried(self):
        calls,patch=self.opener(URLError('reset'),None)
        with patch,mock.patch.object(w.time,'sleep') as sleep:
            self.assertEqual(self.client().request('channels/1'),{'ok':1})
        self.assertEqual(len(calls),2);sleep.assert_called_once_with(w.RETRY_DELAY)

    def test_a_second_transport_failure_stops(self):
        calls,patch=self.opener(URLError('reset'),URLError('reset'),None)
        with patch,mock.patch.object(w.time,'sleep'),self.assertRaises(URLError):self.client().request('channels/1')
        self.assertEqual(len(calls),2)

    def test_an_http_status_is_not_retried(self):
        calls,patch=self.opener(HTTPError('u',429,'slow down',{},None),None)
        with patch,mock.patch.object(w.time,'sleep') as sleep,self.assertRaises(HTTPError):self.client().request('channels/1')
        self.assertEqual(len(calls),1);sleep.assert_not_called()

if __name__=='__main__':unittest.main()
