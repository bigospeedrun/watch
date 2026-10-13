import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import random
import tempfile
import unittest
import chat_gaps as g

NOW=datetime(2026,10,13,12,0,tzinfo=timezone.utc)

class API:
    """Fixture channel. It has no write method, so any write attempt fails."""
    def __init__(self,rows):self.rows=rows;self.reads=[]
    def check_channel(self):pass
    def messages(self,after):
        self.reads.append(after)
        return list(reversed([m for m in self.rows if int(m['id'])>int(after)][:100]))

def at(minutes_ago):return (NOW-timedelta(minutes=minutes_ago)).isoformat().replace('+00:00','Z')

def visitor(n,question,page='/3sum',minutes_ago=60,ip='203.0.113.7'):
    content=f'{g.VISITOR}{question}\nIP: {ip}\nBrowser: Mozilla/5.0 (X11; Linux x86_64) SecretUA/1.2\nPage: {page}'
    return dict(id=str(n),type=0,webhook_id='9',timestamp=at(minutes_ago),content=content[:2000],author=dict(id='9',bot=True,username='Chat log'))

def bot(n,answer,minutes_ago=59):
    return dict(id=str(n),type=0,webhook_id='9',timestamp=at(minutes_ago),content=(g.BOT+answer)[:2000],author=dict(id='9',bot=True,username='Chat log'))

def run(api,root,**kw):return g.run(api,root,now=NOW,rng=random.Random(1),**kw)

class ChatGapTests(unittest.TestCase):
    def test_pairs_flags_and_drops_personal_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            api=API([visitor(1,'Who holds the APSP record? mail me at jo.doe@example.com or +1 (503) 555-0199',page='/apsp'),
                bot(2,'The record is on the [APSP page](/apsp).'),
                visitor(3,'Is sorting tracked?',page='/'),
                bot(4,'Sorting is not a tracked problem. I don’t have facts on it.'),
                dict(id='5',type=0,timestamp=at(1),content='human note in the channel',author=dict(id='44',username='nil'))])
            result=run(api,root)
            self.assertEqual((result['status'],result['pairs'],result['flagged']),('ok',2,1))
            raw=(root/g.OUTPUT).read_text();report=json.loads(raw)
            self.assertEqual(report['flagged'],[dict(time='2026-10-13T11:00Z',page='/',question='Is sorting tracked?',
                answer='Sorting is not a tracked problem. I don’t have facts on it.',matched=['i don\'t have','not a tracked problem'])])
            self.assertEqual(report['sample'][0]['question'],'Who holds the APSP record? mail me at [email] or [phone]')
            self.assertEqual(report['sample'][0]['page'],'/apsp')
            for secret in ('203.0.113','SecretUA','Mozilla','jo.doe','555-0199','human note','IP:','Browser:'):self.assertNotIn(secret,raw)
            self.assertEqual(oct((root/g.OUTPUT).stat().st_mode&0o777),'0o600')
            self.assertEqual(json.loads((root/g.STATE).read_text()),{'last_seen':'5','consumed':[]})

    def test_scrub_and_truncate(self):
        text=g.clean('see https://x.com/a?token=abc#f, ip 2001:db8::1 or fe80:0:0:0:1:2:3:4, <@123>, 10:30:45, 2555269/2500000000 '+'y'*600)
        self.assertTrue(text.startswith('see https://x.com/a, ip [ip] or [ip], [mention], 10:30:45, 2555269/2500000000 '))
        self.assertEqual(len(text),g.MAX_CHARS);self.assertTrue(text.endswith('…'))

    def test_cut_off_visitor_tail_never_leaks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);long='q'*1980
            run(API([visitor(1,long),bot(2,'I have nothing on that.')]),root)
            pair=json.loads((root/g.OUTPUT).read_text())['flagged'][0]
            self.assertEqual(pair['page'],'unknown');self.assertNotIn('203',pair['question'])
            self.assertEqual(set(pair['question'][:-1]),{'q'})

    def test_recent_unanswered_is_held_and_reread_without_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            rows=[visitor(1,'old lost question',minutes_ago=90),visitor(2,'first',minutes_ago=3),
                visitor(3,'second',minutes_ago=2),bot(4,'answer to first',minutes_ago=1)]
            api=API(rows);result=run(api,root)
            self.assertEqual((result['pairs'],result['held'],result['unanswered'],result['ambiguous']),(1,1,1,1))
            self.assertEqual(json.loads((root/g.OUTPUT).read_text())['sample'][0]['ambiguous_pairing'],True)
            self.assertEqual(json.loads((root/g.STATE).read_text()),{'last_seen':'2','consumed':['4']})
            api.rows.append(bot(5,'I do not have that.',minutes_ago=0))
            result=run(api,root)
            report=json.loads((root/g.OUTPUT).read_text())
            self.assertEqual((result['pairs'],result['flagged']),(1,1))
            self.assertEqual(report['flagged'][0]['question'],'second');self.assertNotIn('ambiguous_pairing',report['flagged'][0])
            self.assertEqual(json.loads((root/g.STATE).read_text()),{'last_seen':'5','consumed':[]})

    def test_orphan_reply_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=run(API([bot(7,'reply whose question is lost')]),Path(tmp))
            self.assertEqual((result['orphan_replies'],result['pairs']),(1,0))

    def test_content_unavailable_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);hidden=bot(2,'x');hidden['content']=''
            self.assertEqual(run(API([visitor(1,'q'),hidden]),root)['status'],'content unavailable')
            self.assertEqual(list(root.iterdir()),[])

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            result=run(API([visitor(1,'q'),bot(2,'not in the site facts')]),root,dry_run=True)
            self.assertEqual(result['flagged'],1);self.assertEqual(list(root.iterdir()),[])

    def test_pagination_and_sample_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);rows=[]
            for i in range(1,206,2):rows+=[visitor(i,f'q{i}'),bot(i+1,f'a{i}')]
            api=API(rows);result=run(api,root,sample=3)
            self.assertEqual((result['messages'],result['pairs'],result['sampled']),(206,103,3))
            self.assertEqual(api.reads,['0','100','200'])
            self.assertEqual(len(json.loads((root/g.OUTPUT).read_text())['sample']),3)

if __name__=='__main__':unittest.main()
