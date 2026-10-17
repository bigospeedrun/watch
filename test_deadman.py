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
        self.vps=vps_fixture(now);self.vps['board']=board_section(now);self.vps_error=None;self.memory={}
        self.issues={};self.knowledge=json.loads(json.dumps(self.knowledge));self.boards=list(self.boards);self.channels=[dict(c) for c in self.channels]
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
    # The board is not live by default: no DNS, no certificate, no backup store yet.
    board_code=OSError('board.bigospeedrun.com does not resolve');cert_days=OSError('no certificate for the name');backup=None
    board_mem={}
    def board_https(self):
        if isinstance(self.board_code,Exception):raise self.board_code
        return self.board_code
    def board_cert_days(self):
        if isinstance(self.cert_days,Exception):raise self.cert_days
        return self.cert_days
    def board_backup(self):return self.backup
    ack_log=None
    def board_ack_log(self):
        if isinstance(self.ack_log,Exception):raise self.ack_log
        return self.ack_log
    def board_memory(self):return json.loads(json.dumps(self.board_mem))
    def remember_board(self,memory):self.board_mem=json.loads(json.dumps(memory))
    # Refresh run steps by run URL; runs from before the prove2.me import have no such step.
    steps={};p2m_state={'boards':{}};p2m_mem={}
    def run_steps(self,run):return self.steps.get(run['html_url'],[dict(name='Refresh data through GitHub GET requests',conclusion='success')])
    def prove2me_state(self):
        if isinstance(self.p2m_state,Exception):raise self.p2m_state
        return self.p2m_state
    def prove2me_memory(self):return dict(self.p2m_mem)
    # Race parity: one problem and one Other bounds row, each with a board and a channel.
    knowledge={'problems':[{'path':'/exact-dft','name':'Fourier Transform','title':'Exact discrete Fourier transform'}],
               'otherBounds':{'rows':[{'path':'/other/catalan','title':'Catalan\u2019s constant'}]}}
    boards=['exact-dft','other-catalan']
    channels=[dict(id='1',name='fourier-transform',type=0,parent_id='1558629622558756944'),
              dict(id='2',name='catalans-constant',type=0,parent_id='1558688026207584347'),
              dict(id='3',name='general',type=0,parent_id='1558629621208186970'),
              dict(id='4',name='Other bounds',type=4,parent_id=None)]
    parity_error=None;parity_mem={}
    def site_races(self):
        if self.parity_error:raise self.parity_error
        return d.races_from(self.knowledge)
    def board_slugs(self):return list(self.boards)
    def discord_channels(self):return [dict(c) for c in self.channels]
    def parity_memory(self):return dict(self.parity_mem)
    issues={};issue_error=None;issue_mem={}
    def open_issues(self,repo):
        if self.issue_error:raise self.issue_error
        return [dict(i) for i in self.issues.get(repo,[])]
    def issue_memory(self):return dict(self.issue_mem)
    def remember_issues(self,memory):self.issue_mem=dict(memory)
    def remember_parity(self,memory):self.parity_mem=dict(memory)
    def remember_prove2me(self,memory):self.p2m_mem=dict(memory)

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
        self.assertEqual(set(report),{'watch-cycle','discord-intake','problem-selection','site-refresh','verifier-submissions','chatbot-gap-review','watch-sources','vps-deploy','vps-board','race-parity','stale-issues'})
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

    def p2m_run(self,f,url,import_ok=True,fail_step=None,other_failure=False):
        steps=[dict(name='Validate refreshed bundle',conclusion='failure' if other_failure else 'success'),
               dict(name=d.PROVE2ME_STEP,conclusion='success' if import_ok else 'failure'),
               dict(name=d.PROVE2ME_FAIL_STEP,conclusion=fail_step or ('skipped' if import_ok else 'failure'))]
        f.steps=dict(f.steps,**{url:steps})

    def test_prove2me_import_arms_on_its_first_step_and_then_alerts_without_it(self):
        f=Fake();self.assertNotIn('prove2me-import',d.check(f,NOW))
        self.p2m_run(f,f.runs[0]['html_url'])
        self.assertEqual(d.check(f,NOW)['prove2me-import'][0],True);self.assertTrue(f.p2m_mem['armed'])
        f.steps={};self.assertEqual(self.failing(f),{'prove2me-import'})

    def test_a_held_import_alerts_with_its_reason_and_does_not_fail_site_refresh(self):
        f=Fake();f.runs[0]['conclusion']='failure';f.runs[0]['id']=2
        self.p2m_run(f,f.runs[0]['html_url'],import_ok=False)
        f.p2m_state={'boards':{'apsp':{'status':'held','reason':'unreviewed proved entry 2.99 (mission m9)'},'3sum':{'status':'ok'}}}
        result=d.check(f,NOW)
        self.assertEqual(self.failing(f),{'prove2me-import'})
        self.assertIn('apsp: unreviewed proved entry 2.99',result['prove2me-import'][1])
        # Another failed step is still a refresh failure.
        self.p2m_run(f,f.runs[0]['html_url'],import_ok=False,other_failure=True)
        self.assertEqual(self.failing(f),{'prove2me-import','site-refresh'})

    def test_held_reasons_are_ascii_one_line_and_capped(self):
        f=Fake();f.runs[0]['conclusion']='failure'
        self.p2m_run(f,f.runs[0]['html_url'],import_ok=False)
        f.p2m_state={'boards':{'apsp\n::x':{'status':'held','reason':'é\n::error::'+'x'*900}}}
        problem=d.check(f,NOW)['prove2me-import'][1]
        self.assertTrue(problem.isascii());self.assertNotIn('\n',problem);self.assertNotIn('\\n',problem)
        self.assertLess(len(problem),600);self.assertIn('\\xe9',problem)

    def test_soft_step_failures_in_a_held_run_do_not_fail_site_refresh(self):
        f=Fake();f.runs[0]['conclusion']='failure'
        self.p2m_run(f,f.runs[0]['html_url'],import_ok=False)
        f.steps[f.runs[0]['html_url']].append(dict(name='Post Discord record notifications',conclusion='failure'))
        self.assertEqual(self.failing(f),{'prove2me-import'})
        # A failed soft step alone does not make a failed run a success.
        f.steps[f.runs[0]['html_url']]=[dict(name='Post Discord record notifications',conclusion='failure'),dict(name=d.PROVE2ME_STEP,conclusion='success')]
        self.assertIn('site-refresh',self.failing(f))

    def test_a_new_prove2me_reason_alerts_again_and_the_same_reason_does_not(self):
        f=Fake();f.runs[0]['conclusion']='failure'
        self.p2m_run(f,f.runs[0]['html_url'],import_ok=False)
        f.p2m_state={'boards':{'apsp':{'status':'held','reason':'first reason'}}}
        self.run_at(f);self.run_at(f)
        alerts=[p for p in self.sent if p.get('item')=='prove2me-import']
        self.assertEqual(len(alerts),1)
        f.p2m_state={'boards':{'apsp':{'status':'held','reason':'second reason'}}}
        self.run_at(f)
        alerts=[p for p in self.sent if p.get('item')=='prove2me-import']
        self.assertEqual(len(alerts),2);self.assertIn('second reason',alerts[1]['text'])
        self.p2m_run(f,f.runs[0]['html_url']);f.runs[0]['conclusion']='success'
        self.run_at(f)
        self.assertEqual([p['event'] for p in self.sent if p.get('item')=='prove2me-import'],['alert','alert','recovered'])

    def test_a_parse_failure_or_crash_alerts_without_a_held_board(self):
        f=Fake();f.runs[0]['conclusion']='failure'
        self.p2m_run(f,f.runs[0]['html_url'],import_ok=False)
        self.assertIn('without a held board',d.check(f,NOW)['prove2me-import'][1])
        f.p2m_state=RuntimeError('404')
        self.assertIn('cannot read data/prove2me.json',d.check(f,NOW)['prove2me-import'][1])
        self.assertNotIn('site-refresh',self.failing(f))

    def test_held_runs_still_count_for_site_refresh_freshness(self):
        f=Fake()
        for run in f.runs:
            run['conclusion']='failure';self.p2m_run(f,run['html_url'],import_ok=False)
        self.assertEqual(self.failing(f),{'prove2me-import'})
        f.runs=[dict(r,created_at=iso(3)) for r in f.runs]
        self.assertEqual(self.failing(f),{'prove2me-import','site-refresh'})

    def test_race_parity_names_each_missing_or_extra_board_and_channel(self):
        f=Fake();self.assertEqual(d.check(f,NOW)['race-parity'][:2],(True,None))
        f.knowledge['otherBounds']['rows'].append({'path':'/other/snaky','title':'Snaky'})
        problem=d.check(f,NOW)['race-parity'][1]
        self.assertIn('no board for other-snaky',problem);self.assertIn('no Discord channel #snaky in Other bounds for other-snaky',problem)
        f=Fake();f.boards.append('other-old');f.channels.append(dict(id='9',name='old-race',type=0,parent_id='1558629622558756944'))
        problem=d.check(f,NOW)['race-parity'][1]
        self.assertIn('extra board other-old',problem);self.assertIn('extra Discord channel #old-race in Big O',problem)
        f=Fake();f.channels.append(dict(f.channels[0],id='8'))
        self.assertIn('2 Discord channels #fourier-transform in Big O',d.check(f,NOW)['race-parity'][1])
        # A channel in the wrong category, or a renamed race, is a gap until the channel matches.
        f=Fake();f.knowledge['problems'][0]['name']='Fourier'
        problem=d.check(f,NOW)['race-parity'][1]
        self.assertIn('no Discord channel #fourier in Big O for exact-dft',problem);self.assertIn('extra Discord channel #fourier-transform',problem)

    def test_race_parity_tolerates_one_failed_read_and_alerts_on_two(self):
        f=Fake();f.parity_error=OSError('down')
        self.assertNotIn('race-parity',self.failing(f))
        self.assertIn('race-parity',self.failing(f))
        f.parity_error=None;self.assertNotIn('race-parity',self.failing(f))

    def test_a_new_parity_gap_alerts_again(self):
        f=Fake();f.boards.remove('other-catalan')
        self.run_at(f);self.run_at(f)
        f.channels=[c for c in f.channels if c['name']!='fourier-transform']
        self.run_at(f)
        self.assertEqual([p['event'] for p in self.sent if p.get('item')=='race-parity'],['alert','alert'])

    def test_race_channel_names_follow_the_site_names(self):
        for title,name in [('Fourier Transform','fourier-transform'),('Catalan\u2019s constant','catalans-constant'),('3SUM','3sum'),
                           ('Spin-one Haldane gap','spin-one-haldane-gap'),('One-sample matroid prophet inequality','one-sample-matroid-prophet-inequality')]:
            self.assertEqual(d.race_channel_name(title),name)
        llms='### Problems\n\n- [3SUM](https://board.bigospeedrun.com/3sum): race page x\n- [Catalan](https://board.bigospeedrun.com/other-catalan): y\n- How an agent reads: https://board.bigospeedrun.com/llms.txt\n'
        self.assertEqual(d.boards_from(llms),['3sum','other-catalan'])

    def issue(self,number,hours,title='Lean submission'):
        return dict(number=number,title=title,html_url=f'https://github.com/bigospeedrun/verifier/issues/{number}',created_at=iso(hours))

    def test_issues_open_24_h_or_more_alert_with_name_link_and_age(self):
        f=Fake();f.issues={'bigospeedrun/verifier':[self.issue(4,23.5)]}
        self.assertNotIn('stale-issues',self.failing(f))
        f.issues={'bigospeedrun/verifier':[self.issue(4,49),self.issue(5,2)],'bigospeedrun/site':[dict(self.issue(2,24),html_url='https://github.com/bigospeedrun/site/issues/2')]}
        problem=d.check(f,NOW)['stale-issues'][1]
        self.assertIn('2 issue(s) open for 24 h or more',problem)
        self.assertIn('verifier#4 "Lean submission" open 2 d 1 h https://github.com/bigospeedrun/verifier/issues/4',problem)
        self.assertIn('site#2',problem);self.assertNotIn('#5',problem)

    def test_issue_titles_are_sanitized_and_ages_alone_do_not_realert(self):
        f=Fake();f.issues={'bigospeedrun/watch':[self.issue(7,30,'\u00e9\n::error::'+'x'*300)]}
        problem=d.check(f,NOW)['stale-issues'][1]
        self.assertTrue(problem.isascii());self.assertNotIn('\n',problem);self.assertLess(len(problem),400)
        self.run_at(f,NOW);self.run_at(f,NOW+timedelta(hours=1))
        f.issues['bigospeedrun/watch'].append(self.issue(8,25));self.run_at(f,NOW+timedelta(hours=2))
        f.issues={};self.run_at(f,NOW+timedelta(hours=3))
        self.assertEqual([p['event'] for p in self.sent if p.get('item')=='stale-issues'],['alert','alert','recovered'])

    def test_issue_read_failures_alert_on_the_second_run(self):
        f=Fake();f.issue_error=RuntimeError('GitHub issues request failed')
        self.assertNotIn('stale-issues',self.failing(f));self.assertIn('stale-issues',self.failing(f))

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
               'refused':with_status(result='refused'),'rolled back':with_status(result='rolled_back'),'tick errors':with_status(result='tick_error',tick_error_since=iso(1.5)),'units error':with_status(units='error'),'units absent':with_status(units='absent'),
               'failed target':with_status(result='failed_target'),
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
        ok,*_=self.item(with_status(result='tick_error',tick_error_since=iso(0.5)));self.assertTrue(ok)
        ok,*_=self.item(with_status(result='locked',units='unchecked'));self.assertTrue(ok)

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

def board_section(now=NOW):
    """The "board" section of bos-health-read v2 (2026-10-16), healthy."""
    status=dict(vps_fixture(now)['auto_deploy'],deployed='7de9531')
    names=[f'bigospeedrun-board-board-{s}-1' for s in ('db','api','auth','egress')]
    return {'auto_deploy':status,'containers':{n:{'present':True,'status':'running','health':None if n.endswith('egress-1') else 'healthy',
                                                   'started_at':iso(1,now),'restart_count':0} for n in names}}

class BoardTests(unittest.TestCase):
    def setUp(self):
        self.flag=d.BOARD_DEPLOY_CHECK;d.BOARD_DEPLOY_CHECK=True
    def tearDown(self):d.BOARD_DEPLOY_CHECK=self.flag
    def live(self):
        f=Fake();f.vps['board']=board_section();f.board_code=200;f.cert_days=80.0;f.backup=(0,'FRESH OK product=bigospeedrun-board')
        return f
    def failing(self,src,now=NOW):return {k for k,(ok,*_) in d.check(src,now).items() if not ok}

    def test_not_live_yet_checks_nothing(self):
        d.BOARD_DEPLOY_CHECK=False
        f=Fake();f.vps['board']=board_section();f.vps['board']['auto_deploy']['result']='rolled_back'   # a rehearsal
        report=d.check(f,NOW)
        for item in ('vps-board','board-https','board-cert','board-backup'):self.assertNotIn(item,report)

    def test_the_check_is_on_after_the_rehearsals(self):
        self.assertTrue(self.flag)

    def test_an_old_failed_attempt_is_fine_once_up_to_date(self):
        f=self.live();f.vps['board']['auto_deploy']['last_attempt']={'at':iso(2),'target':'bad','result':'rolled_back'}
        self.assertNotIn('vps-board',self.failing(f))

    def test_one_ssh_read_per_run(self):
        f=self.live();calls=[];read=f.vps_health
        f.vps_health=lambda:calls.append(1) or read()
        d.check(f,NOW);self.assertEqual(calls,[1])

    def test_a_long_wait_for_the_premigration_backup_alerts(self):
        f=self.live();f.vps['board']['auto_deploy'].update(result='waiting',phase='backup',waiting=True,waiting_since=iso(0.5))
        self.assertEqual(self.failing(f),set())
        f.vps['board']['auto_deploy']['waiting_since']=iso(1.5)
        ok,problem,*_=d.check(f,NOW)['vps-board'];self.assertFalse(ok);self.assertIn('off-box backup',problem)

    def test_live_and_healthy(self):
        f=self.live();report=d.check(f,NOW)
        for item in ('vps-board','board-https','board-cert','board-backup'):self.assertTrue(report[item][0],item)
        self.assertEqual(self.failing(f),set())

    def test_board_deploy_states_use_the_site_rules(self):
        cases={}
        f=self.live();f.vps['board']['auto_deploy']['result']='rolled_back';cases['rolled back']=f
        f=self.live();f.vps['board']['auto_deploy']['result']='manual_deploy_needed';cases['manual']=f
        f=self.live();f.vps['board']['auto_deploy']['result']='failed_target';cases['failed target']=f
        f=self.live();f.vps['board']['auto_deploy']['tick_at']=iso(1);cases['stale tick']=f
        f=self.live();f.vps['board']['auto_deploy']={'missing':True};cases['no status']=f
        f=self.live();f.vps['board']['containers']['bigospeedrun-board-board-api-1']['health']='unhealthy';cases['api unhealthy']=f
        f=self.live();f.vps['board']['containers']['bigospeedrun-board-board-db-1']={'present':False};cases['db missing']=f
        for name,src in cases.items():
            with self.subTest(name):self.assertEqual(self.failing(src),{'vps-board'})

    def test_a_missing_board_section_alerts_once_the_check_is_on(self):
        f=self.live();del f.vps['board'];self.assertEqual(self.failing(f),{'vps-board'})

    def test_https_alerts_on_the_second_bad_run(self):
        f=self.live();d.check(f,NOW)
        f.board_code=502;self.assertEqual(self.failing(f),set())
        ok,problem,*_=d.check(f,NOW)['board-https'];self.assertFalse(ok);self.assertIn('502',problem)
        f.board_code=200;self.assertTrue(d.check(f,NOW)['board-https'][0])
        f.board_code=OSError('timeout');d.check(f,NOW);self.assertIn('board-https',self.failing(f))

    def test_https_reads_the_feed_at_the_root_of_the_board_host(self):
        self.assertEqual(d.BOARD_FEED,'https://board.bigospeedrun.com/api/posts?board=3sum&limit=1')

    def test_certificate_under_21_days_or_two_failed_handshakes(self):
        f=self.live();f.cert_days=20.4
        ok,problem,*_=d.check(f,NOW)['board-cert'];self.assertFalse(ok);self.assertIn('20 days',problem)
        f=self.live();d.check(f,NOW);f.cert_days=OSError('handshake')
        self.assertEqual(self.failing(f),set());self.assertEqual(self.failing(f),{'board-cert'})

    def test_backup_freshness(self):
        f=self.live();d.check(f,NOW)
        f.backup=(1,'FRESH FAIL product=bigospeedrun-board reason=stale');ok,problem,*_=d.check(f,NOW)['board-backup']
        self.assertFalse(ok);self.assertIn('no fresh backup',problem)
        f.backup=(2,'DESKTOP FAIL reason=unreachable');self.assertIn('desktop',d.check(f,NOW)['board-backup'][1])
        f.backup=None;self.assertIn('no backup store',d.check(f,NOW)['board-backup'][1])

    def test_backup_alerts_when_the_newest_ack_failed(self):
        ok_line='2026-10-15T00:10:00Z bigospeedrun-board ACK OK sha256=%s: the VPS wrote its pull marker\n'%('a'*64)
        fail_line='2026-10-15T00:20:00Z bigospeedrun-board ACK FAIL ssh exit=3: no marker\n'
        pull_line='2026-10-15T00:19:00Z bigospeedrun-board PULL OK artifact=20261015T001900Z\n'
        f=self.live();f.ack_log=None;self.assertTrue(d.check(f,NOW)['board-backup'][0])   # no log yet: no ACK information
        f.ack_log=ok_line+pull_line+fail_line+'2026-10-15T00:21:00Z bigospeedrun-board PRUNE kept=1 removed=0\n'
        ok,problem,good,_=d.check(f,NOW)['board-backup'];self.assertFalse(ok);self.assertIn('ACK FAIL',problem);self.assertIsNone(good)
        f.ack_log=fail_line+ok_line.replace('00:10','00:30');self.assertTrue(d.check(f,NOW)['board-backup'][0])   # a later OK clears it
        f.ack_log=fail_line;f.backup=(1,'FRESH FAIL reason=stale')
        problem=d.check(f,NOW)['board-backup'][1];self.assertIn('no fresh backup',problem);self.assertIn('ACK FAIL',problem)
        # Not armed yet (no fresh copy ever): an ACK FAIL alone does not alert.
        f=self.live();f.backup=(1,'FRESH FAIL reason=none');f.ack_log=fail_line
        self.assertNotIn('board-backup',d.check(f,NOW))
        f=self.live();f.ack_log=OSError('denied');self.assertFalse(d.check(f,NOW)['board-backup'][0])

    def test_held_board_with_an_old_tick_error_since_is_not_ticks_failing(self):
        f=self.live();f.vps['board']['auto_deploy'].update(result='held',held=True,tick_error_since=iso(5))
        ok,problem,*_=d.check(f,NOW)['vps-board'];self.assertTrue(ok,problem)
        for result in ('locked','stopped'):
            f.vps['board']['auto_deploy'].update(result=result,held=False)
            self.assertNotIn('ticks failing',d.check(f,NOW)['vps-board'][1] or '')
        f.vps['board']['auto_deploy'].update(result='tick_error',stopped=False)
        ok,problem,*_=d.check(f,NOW)['vps-board'];self.assertFalse(ok);self.assertIn('ticks failing',problem)
        f.vps['board']['auto_deploy']['tick_error_since']=iso(0.5);self.assertTrue(d.check(f,NOW)['vps-board'][0])

    def test_read_failures_keep_then_alert_for_the_board_too(self):
        f=self.live();d.check(f,NOW)
        f.vps_error=RuntimeError('boshealth read exited 255')
        self.assertTrue(d.check(f,NOW)['vps-board'][0])
        ok,problem,*_=d.check(f,NOW)['vps-board'];self.assertFalse(ok);self.assertIn('2 reads in a row',problem)

    def test_the_site_item_ignores_the_board_section(self):
        f=self.live();f.vps['board']['containers']['bigospeedrun-board-board-api-1']['status']='exited'
        report=d.check(f,NOW);self.assertTrue(report['vps-deploy'][0]);self.assertFalse(report['vps-board'][0])

if __name__=='__main__':unittest.main()
