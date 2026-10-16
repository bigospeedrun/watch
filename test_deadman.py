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
        self.vps=vps_fixture(now);self.vps_error=None;self.memory={}
    def last_ok(self):return self.marks
    def log_ok_time(self,name):return None
    def refresh_runs(self):return self.runs
    def systemd(self,unit,*props):return self.service if unit.endswith('.service') else self.timer
    def cron_runs(self,job):return self.cron
    installed=False;digest_ok=None;stalled=()
    def stalled_sources(self):return list(self.stalled)
    def unit_installed(self,unit):return self.installed
    def digest_last_ok(self,name):return self.digest_ok
    def vps_health(self):
        if self.vps_error:raise self.vps_error
        return self.vps
    def vps_memory(self):return dict(self.memory)
    def remember_vps(self,memory):self.memory=dict(memory)

def vps_fixture(now=NOW):
    """The boshealth read output shape (bos-health-read, 2026-10-15), healthy."""
    return {'generated_at':iso(0,now),
            'auto_deploy':{'tick_at':iso(0.05,now),'deployed':'bee5335','result':'up_to_date','phase':'select','target':None,
                           'stopped':False,'held':False,'waiting':False,'waiting_since':None,'tick_error_since':None,'units':'ok',
                           'last_attempt':{'at':iso(1,now),'target':'bee5335','result':'deployed'}},
            'containers':{'bigospeedrun-site-1':{'present':True,'status':'running','health':'healthy','started_at':iso(1,now),'restart_count':0},
                          'bigospeedrun-egress-1':{'present':True,'status':'running','health':None,'started_at':iso(1,now),'restart_count':0}}}

class DeadmanTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'.git').mkdir();self.sent=[]
    def tearDown(self):self.tmp.cleanup()
    def send(self,payload):self.sent.append(payload)
    def run_at(self,src,now=NOW,send=None):return d.run(src,send or self.send,self.root,now)
    def failing(self,src):return {k for k,(ok,*_) in d.check(src,NOW).items() if not ok}

    def test_all_healthy_sends_nothing(self):
        report=self.run_at(Fake())
        self.assertEqual(set(report),{'watch-cycle','discord-intake','problem-selection','site-refresh','verifier-submissions','chatbot-gap-review','watch-sources','vps-deploy'})
        self.assertTrue(all(v=='ok' for v in report.values()));self.assertEqual(self.sent,[])

    def test_each_simulated_stale_or_failed_state_is_caught(self):
        cases={}
        f=Fake();f.marks['cycle']=iso(5);cases['watch-cycle']=f
        f=Fake();del f.marks['cycle'];f.marks['push']=iso(4.5);cases['watch-cycle ']=f
        f=Fake();del f.marks['discord-intake'];cases['discord-intake']=f
        f=Fake();f.marks['problem-selection']=iso(4.1);cases['problem-selection']=f
        f=Fake();f.stalled=['slitsey/catalan-irrationality-measure'];cases['watch-sources']=f
        f=Fake();f.runs[0]['conclusion']='failure';cases['site-refresh']=f
        f=Fake();f.runs=[dict(r,created_at=iso(3)) for r in f.runs];cases['site-refresh ']=f
        f=Fake();f.service['Result']='exit-code';f.service['ExecMainStatus']='1';cases['verifier-submissions']=f
        f=Fake();f.timer['LastTriggerUSec']=systemd(2);cases['verifier-submissions ']=f
        f=Fake();f.timer['ActiveState']='inactive';cases['verifier-submissions  ']=f
        f=Fake();f.cron=[dict(f.cron[0],startedAt=(NOW-timedelta(hours=27)).timestamp()*1000)];cases['chatbot-gap-review']=f
        f=Fake();f.cron.append(dict(status='failed',errorReason='session crashed',startedAt=(NOW-timedelta(hours=1)).timestamp()*1000));cases['chatbot-gap-review ']=f
        for item,src in cases.items():
            with self.subTest(item=item):self.assertEqual(self.failing(src),{item.strip()})

    def test_prove2me_digest_checked_only_once_its_timer_is_installed(self):
        f=Fake();self.assertNotIn('prove2me-digest',d.check(f,NOW))
        f.installed=True;f.digest_ok=NOW-timedelta(hours=1);self.assertEqual(self.failing(f),set())
        f.digest_ok=NOW-timedelta(hours=2.5);self.assertEqual(self.failing(f),{'prove2me-digest'})
        f.digest_ok=None;self.assertEqual(self.failing(f),{'prove2me-digest'})

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


class VpsDeployTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'.git').mkdir();self.sent=[]
    def tearDown(self):self.tmp.cleanup()
    def item(self,src,now=NOW):
        src.vps['auto_deploy']['tick_at']=src.vps['auto_deploy'].get('tick_at') and iso(0.05,now)  # the timer keeps ticking
        return d.check(src,now)['vps-deploy']

    def test_each_bad_state_alerts(self):
        def with_status(**kw):
            f=Fake();f.vps['auto_deploy'].update(kw);return f
        stale=Fake();stale.vps['auto_deploy']['tick_at']=iso(0.8)
        cases={
               'failed':with_status(result='failed'),'rollback_failed':with_status(result='rollback_failed'),
               'stopped result':with_status(result='stopped'),'stopped marker':with_status(stopped=True),
               'refused':with_status(result='refused'),'rolled back':with_status(result='rolled_back'),
               'last attempt failed':with_status(last_attempt={'at':iso(0.5),'target':'abc','result':'rollback_failed'}),
               'waiting a day':with_status(waiting=True,waiting_since=iso(25))}
        f=Fake();f.vps['containers']['bigospeedrun-site-1']['health']='unhealthy';cases['unhealthy']=f
        f=Fake();f.vps['containers']['bigospeedrun-egress-1']={'present':False};cases['missing container']=f
        f=Fake();f.vps['containers']['bigospeedrun-site-1']['status']='restarting';cases['restarting']=f
        f=Fake();f.vps['auto_deploy']={'missing':True};cases['no status']=f
        ok,problem,*_=d.check(stale,NOW)['vps-deploy'];self.assertFalse(ok);self.assertIn('last deploy tick',problem)
        for name,src in cases.items():
            ok,problem,*_=self.item(src)
            self.assertFalse(ok,name);self.assertTrue(problem,name)
        ok,problem,good,_=self.item(Fake());self.assertTrue(ok);self.assertIsNone(problem);self.assertEqual(good,NOW)
        ok,*_=self.item(with_status(waiting=True,waiting_since=iso(20)));self.assertTrue(ok)

    def test_held_alerts_only_after_a_day(self):
        f=Fake();f.vps['auto_deploy']['held']=True
        self.assertTrue(self.item(f)[0])
        self.assertTrue(self.item(f,NOW+timedelta(hours=23))[0])
        ok,problem,*_=self.item(f,NOW+timedelta(hours=24.5));self.assertFalse(ok);self.assertIn('held since',problem)
        f.vps['auto_deploy']['held']=False;self.assertTrue(self.item(f,NOW+timedelta(hours=25))[0]);self.assertNotIn('held_since',f.memory)

    def test_one_failed_read_is_tolerated_two_alert(self):
        f=Fake();f.vps_error=RuntimeError('boshealth read exited 255')
        self.assertTrue(self.item(f)[0]);self.assertEqual(f.memory['read_failures'],1)
        ok,problem,*_=self.item(f);self.assertFalse(ok);self.assertIn('2 reads in a row',problem)
        f.vps_error=None;self.assertTrue(self.item(f)[0]);self.assertEqual(f.memory['read_failures'],0)

    def test_single_failed_read_keeps_a_failing_verdict(self):
        f=Fake();f.vps['auto_deploy']['result']='failed'
        self.assertFalse(self.item(f)[0])
        f.vps_error=RuntimeError('x');ok,problem,*_=self.item(f);self.assertFalse(ok);self.assertIn('failed',problem)

    def test_alert_once_then_recovered_line(self):
        f=Fake();f.vps['containers']['bigospeedrun-site-1']['health']='unhealthy'
        d.run(f,self.sent.append,self.root,NOW);d.run(f,self.sent.append,self.root,NOW+timedelta(hours=1))
        alerts=[p for p in self.sent if p['item']=='vps-deploy']
        self.assertEqual([p['event'] for p in alerts],['alert'])
        f.vps['containers']['bigospeedrun-site-1']['health']='healthy';f.vps['auto_deploy']['tick_at']=iso(0.05,NOW+timedelta(hours=2))
        f.marks={k:iso(1,NOW+timedelta(hours=2)) for k in f.marks}
        d.run(f,self.sent.append,self.root,NOW+timedelta(hours=2))
        alerts=[p for p in self.sent if p['item']=='vps-deploy']
        self.assertEqual([p['event'] for p in alerts],['alert','recovered'])
        self.assertNotIn('boshealth.key',json.dumps(self.sent))

if __name__=='__main__':unittest.main()
