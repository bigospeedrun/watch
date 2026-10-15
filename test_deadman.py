import json, tempfile, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import deadman as d

NOW=datetime(2026,10,15,1,0,tzinfo=timezone.utc)
def iso(hours_ago,now=NOW):return (now-timedelta(hours=hours_ago)).isoformat()
def systemd(hours_ago,now=NOW):return (now-timedelta(hours=hours_ago)).strftime('%a %Y-%m-%d %H:%M:%S UTC')

class Fake:
    """All six items healthy; each test makes one item stale or failed."""
    def __init__(self,now=NOW):
        self.marks={'cycle':iso(1,now),'discord-intake':iso(1,now),'problem-selection':iso(1,now)}
        self.runs=[dict(status='completed',conclusion='success',created_at=iso(0.5,now),html_url='https://github.com/x/runs/2'),
                   dict(status='completed',conclusion='success',created_at=iso(1.5,now),html_url='https://github.com/x/runs/1')]
        self.service={'Result':'success','ExecMainStatus':'0','ExecMainExitTimestamp':systemd(0.3,now)}
        self.timer={'LastTriggerUSec':systemd(0.3,now),'ActiveState':'active'}
        self.cron=[dict(status='completed',errorReason=None,startedAt=(now-timedelta(hours=8)).timestamp()*1000)]
    def last_ok(self):return self.marks
    def log_ok_time(self,name):return None
    def refresh_runs(self):return self.runs
    def systemd(self,unit,*props):return self.service if unit.endswith('.service') else self.timer
    def cron_runs(self,job):return self.cron

class DeadmanTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'.git').mkdir();self.sent=[]
    def tearDown(self):self.tmp.cleanup()
    def send(self,payload):self.sent.append(payload)
    def run_at(self,src,now=NOW,send=None):return d.run(src,send or self.send,self.root,now)
    def failing(self,src):return {k for k,(ok,*_) in d.check(src,NOW).items() if not ok}

    def test_all_healthy_sends_nothing(self):
        report=self.run_at(Fake())
        self.assertEqual(set(report),{'watch-cycle','discord-intake','problem-selection','site-refresh','verifier-submissions','chatbot-gap-review'})
        self.assertTrue(all(v=='ok' for v in report.values()));self.assertEqual(self.sent,[])

    def test_each_simulated_stale_or_failed_state_is_caught(self):
        cases={}
        f=Fake();f.marks['cycle']=iso(5);cases['watch-cycle']=f
        f=Fake();del f.marks['cycle'];f.marks['push']=iso(4.5);cases['watch-cycle ']=f
        f=Fake();del f.marks['discord-intake'];cases['discord-intake']=f
        f=Fake();f.marks['problem-selection']=iso(4.1);cases['problem-selection']=f
        f=Fake();f.runs[0]['conclusion']='failure';cases['site-refresh']=f
        f=Fake();f.runs=[dict(r,created_at=iso(3)) for r in f.runs];cases['site-refresh ']=f
        f=Fake();f.service['Result']='exit-code';f.service['ExecMainStatus']='1';cases['verifier-submissions']=f
        f=Fake();f.timer['LastTriggerUSec']=systemd(2);cases['verifier-submissions ']=f
        f=Fake();f.timer['ActiveState']='inactive';cases['verifier-submissions  ']=f
        f=Fake();f.cron=[dict(f.cron[0],startedAt=(NOW-timedelta(hours=27)).timestamp()*1000)];cases['chatbot-gap-review']=f
        f=Fake();f.cron.append(dict(status='failed',errorReason='session crashed',startedAt=(NOW-timedelta(hours=1)).timestamp()*1000));cases['chatbot-gap-review ']=f
        for item,src in cases.items():
            with self.subTest(item=item):self.assertEqual(self.failing(src),{item.strip()})

    def test_push_marker_counts_as_a_full_cycle(self):
        f=Fake();del f.marks['cycle'];f.marks['push']=iso(1)
        self.assertEqual(self.failing(f),set())

    def test_one_alert_per_item_then_one_recovery(self):
        stale=Fake();stale.runs[0]['conclusion']='failure'
        later=Fake(NOW+timedelta(hours=1));later.runs[0]['conclusion']='failure'
        self.run_at(stale);self.run_at(later,NOW+timedelta(hours=1))
        self.assertEqual([(p['event'],p['item']) for p in self.sent],[('alert','site-refresh')])
        p=self.sent[0];self.assertIn('latest run failure',p['text']);self.assertIn('https://github.com/x/runs/2',p['text'])
        self.assertIn('Last good: Wed Oct 14, 4:30 PM PT',p['text']);self.assertEqual(p['kind'],'bos-deadman')
        self.run_at(Fake());self.run_at(Fake())
        self.assertEqual([(p['event'],p['item']) for p in self.sent],[('alert','site-refresh'),('recovered','site-refresh')])

    def test_unreachable_lead_writes_local_file_once_and_retries(self):
        def stale(hour):
            f=Fake(NOW+timedelta(hours=hour));f.marks['cycle']=iso(6);return f
        def down(payload):raise OSError('office down')
        for hour in range(3):self.run_at(stale(hour),NOW+timedelta(hours=hour),down)
        lines=(self.root/d.ALERTS).read_text().splitlines()
        self.assertEqual(len(lines),1);self.assertIn('watch-cycle is failing or stale',lines[0])
        self.run_at(stale(3),NOW+timedelta(hours=3))  # the lead is reachable again
        self.assertEqual([(p['event'],p['item']) for p in self.sent],[('alert','watch-cycle')])
        self.run_at(stale(4),NOW+timedelta(hours=4));self.assertEqual(len(self.sent),1)

    def test_source_errors_are_failures_without_detail_leak(self):
        class Broken(Fake):
            def refresh_runs(self):raise RuntimeError('token ghp_secret in message')
            def systemd(self,unit,*props):raise RuntimeError('boom')
        report=self.run_at(Broken())
        self.assertIn('alert sent',report['site-refresh']);self.assertIn('alert sent',report['verifier-submissions'])
        self.assertTrue(all('ghp_secret' not in p['text'] for p in self.sent))
        self.assertIn('cannot read GitHub runs: RuntimeError',self.sent[[p['item'] for p in self.sent].index('site-refresh')]['text'])

    def test_unconfigured_webhook_counts_as_unreachable(self):
        with self.assertRaises(RuntimeError):d.webhook_send(self.root)(dict(text='x'))

    def test_webhook_signature_matches_isomux_verify(self):
        import hashlib,hmac,http.server,threading
        got={}
        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                got['body']=self.rfile.read(int(self.headers['Content-Length']));got['sig']=self.headers['X-Deadman-Signature']
                got['event']=self.headers['X-Deadman-Event'];self.send_response(202);self.end_headers()
            def log_message(self,*a):pass
        server=http.server.HTTPServer(('127.0.0.1',0),H);threading.Thread(target=server.handle_request,daemon=True).start()
        (self.root/'secret').write_text('s3cret\n')
        (self.root/d.CONFIG).write_text(json.dumps(dict(hook_url=f'http://127.0.0.1:{server.server_port}/hooks/wh_x',secret_file=str(self.root/'secret'),
                                                         signature_header='X-Deadman-Signature',event_header='X-Deadman-Event')))
        d.webhook_send(self.root)(dict(kind='bos-deadman',text='t'));server.server_close()
        self.assertEqual(got['sig'],'sha256='+hmac.new(b's3cret',got['body'],hashlib.sha256).hexdigest())
        self.assertEqual(got['event'],'deadman');self.assertEqual(json.loads(got['body'])['kind'],'bos-deadman')

if __name__=='__main__':unittest.main()
