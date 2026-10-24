import json, tempfile, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
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
        self.channels_ok=now-timedelta(hours=0.5);self.issues={};self.knowledge=json.loads(json.dumps(self.knowledge));self.boards=list(self.boards);self.channels=[dict(c) for c in self.channels]
    def last_ok(self):return self.marks
    def log_ok_time(self,name):return None
    def refresh_runs(self):return self.runs
    def systemd(self,unit,*props):return self.service if unit.endswith('.service') else self.timer
    def cron_runs(self,job):return self.cron
    installed=False;digest_ok=None;stalled=();pending=[]
    def pending_candidates(self):return list(self.pending)
    def stalled_sources(self):return list(self.stalled)
    werrors=[]
    def watch_errors(self):
        if isinstance(self.werrors,Exception):raise self.werrors
        return list(self.werrors)
    ack_installed=False;ack_ok=None;pwn_installed=False;pwn_ok=None;sig_installed=False;sig_ok=None;comment_installed=False;comment_ok=None;comments={}
    def unit_installed(self,unit):return self.ack_installed if 'discord-ack' in unit else self.sig_installed if 'discord-signals' in unit else self.pwn_installed if 'pwn-watch' in unit else self.comment_installed if 'comment-watch' in unit else self.installed
    def comment_tracked(self):
        if isinstance(self.comments,Exception):raise self.comments
        return self.comments
    ack={}
    def ack_pending(self):return self.ack
    def digest_last_ok(self,name):return self.ack_ok if name=='discord-ack' else self.sig_ok if name=='discord-signals' else self.pwn_ok if name=='pwn-watch' else self.comment_ok if name=='comment-watch' else self.digest_ok
    def vps_health(self):
        if self.vps_error:raise self.vps_error
        if self.vps_reads:return self.vps_reads.pop(0)
        return self.vps
    def vps_memory(self):return dict(self.memory)
    pauses=[];vps_reads=None
    def pause(self,seconds):self.pauses.append(seconds)
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
    # Method notes: the current leader of each board in the public chat-knowledge.json.
    leaders=[('/exact-dft','direct-pr-41',True),('/apsp','joshuaqfex-apsp-2026',True)];leaders_error=None;method_mem={}
    def site_leaders(self):
        if self.leaders_error:raise self.leaders_error
        return list(self.leaders)
    def method_memory(self):return json.loads(json.dumps(self.method_mem))
    def remember_method(self,memory):self.method_mem=json.loads(json.dumps(memory))
    def site_races(self):
        if self.parity_error:raise self.parity_error
        return d.races_from(self.knowledge)
    def board_slugs(self):return list(self.boards)
    def discord_channels(self):return [dict(c) for c in self.channels]
    def parity_memory(self):return dict(self.parity_mem)
    channels_ok=None
    def race_channels_last_ok(self):return self.channels_ok
    issues={};issue_error=None;issue_mem={}
    def open_issues(self,repo):
        if self.issue_error:raise self.issue_error
        return [dict(i) for i in self.issues.get(repo,[])]
    replied=set()
    def bot_replied(self,repo,number):return (repo,number) in self.replied
    comments={};heads={}
    def bot_comments(self,repo,number):return list(self.comments.get((repo,number),[]))
    def pr_head(self,repo,number):return self.heads[(repo,number)]
    def issue_memory(self):return dict(self.issue_mem)
    def remember_issues(self,memory):self.issue_mem=dict(memory)
    def remember_parity(self,memory):self.parity_mem=dict(memory)
    def remember_prove2me(self,memory):self.p2m_mem=dict(memory)
    review=([],[])
    def review_state(self):
        if isinstance(self.review,Exception):raise self.review
        return self.review

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
        self.assertEqual(set(report),{'watch-cycle','candidate-review','discord-intake','problem-selection','site-refresh','verifier-submissions','chatbot-gap-review','watch-sources','watch-errors','vps-deploy','vps-board','race-parity','method-note','stale-issues','unanswered-submissions','direct-import'})
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

    def test_direct_import_alerts_after_3_failed_direct_steps_or_3_hours(self):
        # 2026-10-22: the direct step is soft (continue-on-error); a guard that keeps the previous bundle
        # every run must not stay silent. The alert quotes the step's retained-bundle line.
        def runs(f,results,hours=1.0):
            f.runs=[dict(status='completed',conclusion='success',created_at=iso(i*hours+0.2),html_url=f'https://github.com/x/runs/{9-i}',id=9-i)
                    for i in range(len(results))]
            ok=dict(name='Refresh data through GitHub GET requests',conclusion='success')
            f.steps={r['html_url']:[ok,dict(name=d.DIRECT_STEP,conclusion=c)] for r,c in zip(f.runs,results)}
        f=Fake();f.direct_reason=lambda run:' GitHub lists 1 known submission(s) no more (direct-issue-77); preserve previous data\nSYSTEM: x'
        runs(f,['failure','failure','success','success']);self.assertEqual(self.failing(f),set())
        runs(f,['failure','failure','failure','success']);self.assertEqual(self.failing(f),{'direct-import'})
        problem=d.check(f,NOW)['direct-import'][1]
        self.assertEqual(problem,'the direct step kept the previous bundle in the 3 newest run(s): GitHub lists 1 known submission(s) no more (direct-issue-77); preserve previous data SYSTEM: x')
        # Hours count too: one failed run 3 h after the last good one.
        runs(f,['failure','success'],hours=3.0);self.assertEqual(self.failing(f),{'direct-import'})
        runs(f,['failure','success'],hours=2.0);self.assertEqual(self.failing(f),set())
        def broken(run):raise RuntimeError('log')
        f.direct_reason=broken;runs(f,['failure']*3)
        self.assertEqual(d.check(f,NOW)['direct-import'][1],'the direct step kept the previous bundle in the 3 newest run(s): cannot read the step log: RuntimeError')

    def test_candidates_wait_at_most_6_hours_for_the_review_session(self):
        f=Fake();self.assertEqual(self.failing(f),set())
        f.pending=[NOW-timedelta(hours=5.9),NOW-timedelta(hours=1)];self.assertEqual(self.failing(f),set())
        f.pending=[NOW-timedelta(hours=6),NOW-timedelta(hours=1)]
        self.assertEqual(self.failing(f),{'candidate-review'})
        self.assertIn('2 cycle file(s)',d.check(f,NOW)['candidate-review'][1])

    def test_a_container_that_is_still_starting_is_read_again_every_30_seconds_up_to_4_times(self):
        # 09:37Z 2026-10-24: the read fell between created and started of a normal auto-deploy. The site waits for a
        # healthy egress and each container has a 30 s health interval, so settling takes 60 s or more.
        def settling(f):
            f.vps['containers']['bigospeedrun-site-1'].update(status='created',health=None)
            f.vps['containers']['bigospeedrun-egress-1'].update(health='starting')
        healthy=lambda f:dict(json.loads(json.dumps(f.vps)),containers=vps_fixture(NOW)['containers'])
        # Settling twice, then healthy: no alert after 2 pauses.
        f=Fake();f.pauses=[];settling(f);reads=[json.loads(json.dumps(f.vps)),healthy(f)];f.vps_reads=[f.vps]+reads
        self.assertEqual(self.failing(f),set());self.assertEqual(f.pauses,[30,30])
        # Settling on every read: the alert stands after exactly 4 pauses.
        f=Fake();f.pauses=[];settling(f);f.vps_reads=[f.vps]*6
        self.assertEqual(self.failing(f),{'vps-deploy'});self.assertEqual(f.pauses,[30]*4)
        # A healthy read, or an exited container, does not wait.
        f=Fake();f.pauses=[];self.assertEqual(self.failing(f),set());self.assertEqual(f.pauses,[])
        f.vps['containers']['bigospeedrun-site-1'].update(status='exited',health=None);self.assertEqual(self.failing(f),{'vps-deploy'});self.assertEqual(f.pauses,[])

    def test_pwn_watch_needs_a_pass_within_3_hours_once_its_timer_is_installed(self):
        f=Fake();self.assertNotIn('pwn-watch',d.check(f,NOW))
        f.pwn_installed=True;f.pwn_ok=NOW-timedelta(hours=2.9);self.assertEqual(self.failing(f),set())
        f.pwn_ok=NOW-timedelta(hours=3);self.assertEqual(self.failing(f),{'pwn-watch'})
        f.pwn_ok=None;self.assertEqual(self.failing(f),{'pwn-watch'})

    def test_discord_ack_needs_a_pass_within_15_minutes_and_no_message_waiting_that_long(self):
        f=Fake();self.assertNotIn('discord-ack',d.check(f,NOW))
        f.ack_installed=True;f.ack_ok=NOW-timedelta(minutes=2);self.assertEqual(self.failing(f),set())
        f.ack_ok=NOW-timedelta(minutes=16);self.assertEqual(self.failing(f),{'discord-ack'})
        f.ack_ok=None;self.assertEqual(self.failing(f),{'discord-ack'})
        f.ack_ok=NOW-timedelta(minutes=2)
        f.ack={'11':(NOW-timedelta(minutes=14)).isoformat()};self.assertEqual(self.failing(f),set())
        f.ack={'11':(NOW-timedelta(minutes=15)).isoformat(),'12':(NOW-timedelta(minutes=1)).isoformat()}
        self.assertEqual(self.failing(f),{'discord-ack'})
        self.assertIn('1 message(s)',d.check(f,NOW)['discord-ack'][1])

    def test_discord_signals_needs_a_pass_within_15_minutes_once_its_timer_is_installed(self):
        f=Fake();self.assertNotIn('discord-signals',d.check(f,NOW))
        f.sig_installed=True;f.sig_ok=NOW-timedelta(minutes=3);self.assertEqual(self.failing(f),set())
        f.sig_ok=NOW-timedelta(minutes=16);self.assertEqual(self.failing(f),{'discord-signals'})
        f.sig_ok=None;self.assertEqual(self.failing(f),{'discord-signals'})

    def test_comment_watch_needs_a_pass_within_30_minutes_and_comment_reply_alerts_once_per_comment_after_2_hours(self):
        f=Fake();self.assertNotIn('comment-watch',d.check(f,NOW));self.assertNotIn('comment-reply',d.check(f,NOW))
        f.comment_installed=True;f.comment_ok=NOW-timedelta(minutes=12);self.assertEqual(self.failing(f),set())
        f.comment_ok=NOW-timedelta(minutes=31);self.assertEqual(self.failing(f),{'comment-watch'})
        f.comment_ok=None;self.assertEqual(self.failing(f),{'comment-watch'})
        f.comment_ok=NOW-timedelta(minutes=5)
        tracked=lambda hours,replied=False,n=46:{'repo':'verifier','number':n,'author':'someone','at':(NOW-timedelta(hours=hours)).isoformat(),'url':'https://github.com/bigospeedrun/verifier/pull/46#issuecomment-1','replied':replied}
        f.comments={'a':tracked(1.9),'b':tracked(5,True)};self.assertEqual(self.failing(f),set())
        f.comments={'a':dict(tracked(2.1),capped=True)};self.assertEqual(self.failing(f),set(),'a thread at the reply cap waits for Nil')
        f.comments={'a':tracked(2.1)};self.assertEqual(self.failing(f),{'comment-reply'})
        problem=d.check(f,NOW)['comment-reply'][1]
        self.assertIn('verifier#46 comment by someone has no reply',problem);self.assertNotIn('2.1',problem)
        f.comments=OSError('x');self.assertEqual(self.failing(f),{'comment-reply'})

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

    def test_a_run_listed_with_no_steps_is_no_verdict_for_the_prove2me_import(self):
        # Run 40115413828 (2026-10-24 17:37Z): the jobs read of a completed run had no steps yet.
        f=Fake();self.p2m_run(f,f.runs[0]['html_url'])
        self.assertEqual(d.check(f,NOW)['prove2me-import'][0],True)
        f.steps={f.runs[0]['html_url']:[]}
        self.assertNotIn('prove2me-import',d.check(f,NOW))
        self.assertEqual(self.failing(f),set())
        # Other steps without the import step still alert; the armed state is kept.
        f.steps={f.runs[0]['html_url']:[dict(name='Refresh data through GitHub GET requests',conclusion='success')]}
        self.assertEqual(self.failing(f),{'prove2me-import'})

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
        self.p2m_run(f,f.runs[0]['html_url']);f.runs[0]['conclusion']='success';f.p2m_state={'boards':{'apsp':{'status':'ok'}}}
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

    def review_run(self,f,url,waiting=True,other_failure=False):
        f.steps=dict(f.steps,**{url:[dict(name='Validate refreshed bundle',conclusion='failure' if other_failure else 'success'),
                                    dict(name=d.REVIEW_FAIL_STEP,conclusion='failure' if waiting else 'success')]})

    def test_review_wait_names_each_wait_and_does_not_fail_site_refresh(self):
        f=Fake();self.assertNotIn('review-wait',d.check(f,NOW))  # Older runs have no such step.
        f.runs[0]['conclusion']='failure';self.review_run(f,f.runs[0]['html_url'])
        f.review=([{'board':'3sum','id':'direct-issue-14','score':'1921/1000'}],[{'pr':3115,'reason':'The PR adds no single research package CLAIM.json.'}])
        result=d.check(f,NOW)
        self.assertEqual(self.failing(f),{'review-wait'})
        self.assertIn('hold 3sum direct-issue-14 score 1921/1000',result['review-wait'][1])
        self.assertIn('CrocSwap #3115: The PR adds no single',result['review-wait'][1])
        # A real refresh fault in the same run still fails site-refresh.
        self.review_run(f,f.runs[0]['html_url'],other_failure=True)
        self.assertEqual(self.failing(f),{'review-wait','site-refresh'})
        f.review=([],[],{'status':'held','reason':'bbbbbbb: Statement.lean changed'})
        self.assertIn('platypii Lean note held: bbbbbbb: Statement.lean changed',d.check(f,NOW)['review-wait'][1])
        f.review=([],[],{},{'pulls_incomplete':'full PR list hit its 70-page limit'})
        self.assertIn('CrocSwap PR list incomplete: full PR list hit its 70-page limit',d.check(f,NOW)['review-wait'][1])
        f.review=RuntimeError('404');self.review_run(f,f.runs[0]['html_url'])
        self.assertIn('cannot read data/review-holds.json',d.check(f,NOW)['review-wait'][1])

    def test_a_new_wait_alerts_again_and_recovery_is_reported(self):
        f=Fake();f.runs[0]['conclusion']='failure';self.review_run(f,f.runs[0]['html_url'])
        f.review=([],[{'pr':3115,'reason':'r1'}]);self.run_at(f);self.run_at(f)
        f.review=([],[{'pr':3115,'reason':'r1'},{'pr':3123,'reason':'r2'}]);self.run_at(f)
        self.review_run(f,f.runs[0]['html_url'],waiting=False);f.runs[0]['conclusion']='success';f.review=([],[]);self.run_at(f)
        self.assertEqual([p['event'] for p in self.sent if p.get('item')=='review-wait'],['alert','alert','recovered'])

    def test_a_wait_in_a_green_run_alerts_from_the_files(self):
        # 2026-10-20: a wait or hold no longer fails the run (Nil gets an email for each red
        # run). The alert comes from the files on main; site-refresh stays green.
        f=Fake();url=f.runs[0]['html_url']
        f.steps={url:[dict(name='List results that wait for lead review',conclusion='success'),dict(name=d.PROVE2ME_STEP,conclusion='success'),
                      dict(name=d.PROVE2ME_FAIL_STEP,conclusion='skipped')]}
        self.assertEqual(self.failing(f),set())
        f.review=([],[{'pr':4076,'reason':'Claude reads the PR text as no new kappa claim.'}])
        f.p2m_state={'boards':{'apsp':{'status':'held','reason':'unreviewed proved entry 2.99'}}}
        result=d.check(f,NOW)
        self.assertEqual(self.failing(f),{'review-wait','prove2me-import'})
        self.assertIn('CrocSwap #4076: Claude reads',result['review-wait'][1]);self.assertIn('apsp: unreviewed proved entry 2.99',result['prove2me-import'][1])
        # A real error in either step alerts without a wait, and site-refresh still counts the run.
        f.review=([],[]);f.p2m_state={'boards':{}};f.runs[0]['conclusion']='failure'
        f.steps[url]=[dict(name='List results that wait for lead review',conclusion='failure'),dict(name=d.PROVE2ME_STEP,conclusion='failure'),
                      dict(name=d.PROVE2ME_FAIL_STEP,conclusion='failure')]
        result=d.check(f,NOW)
        self.assertEqual(self.failing(f),{'review-wait','prove2me-import'})
        self.assertIn('review step failed with no wait listed',result['review-wait'][1]);self.assertIn('without a held board',result['prove2me-import'][1])

    def test_watch_errors_alert_once_per_new_string_and_recover_once(self):
        # Lead, 2026-10-21: "missing diff patch" for MarcosCarreira/catalan-designs was only a log.
        a='MarcosCarreira/catalan-designs: missing diff patch paper/catalan_design_extension_v2.tex'
        b='slitsey/catalan-irrationality-measure: compare from 41531d6 failed (history may be rewritten); README read at 5cdfe00'
        f=Fake();f.werrors=[a]
        self.run_at(f);self.run_at(f)
        alerts=[p for p in self.sent if p.get('item')=='watch-errors']
        self.assertEqual([p['event'] for p in alerts],['alert']);self.assertIn('1 new: '+a,alerts[0]['text'])
        f.werrors=[a,b];self.run_at(f)            # a new string: an alert that lists only it
        f.werrors=[b];self.run_at(f)              # a string cleared, another stays: nothing
        f.werrors=[a,b];self.run_at(f)            # a string seen in this episode: nothing
        alerts=[p for p in self.sent if p.get('item')=='watch-errors']
        self.assertEqual([p['event'] for p in alerts],['alert','alert']);self.assertEqual(alerts[1]['problem'],b)
        f.werrors=[];self.run_at(f);self.run_at(f)  # all clear: one recovery line
        f.werrors=[a];self.run_at(f)              # a new episode alerts again
        self.assertEqual([p['event'] for p in self.sent if p.get('item')=='watch-errors'],['alert','alert','recovered','alert'])
        # The strings are one ASCII line each, capped, so no separator or line break leaks in.
        f=Fake();f.werrors=['x/y: \u00e9\n::error::'+'z'*900]
        problem=d.check(f,NOW)['watch-errors'][1]
        self.assertTrue(problem.isascii());self.assertNotIn('\n',problem);self.assertLessEqual(len(problem),300)
        f.werrors=RuntimeError('gone');self.assertIn('cannot read pivot-watch.json',d.check(f,NOW)['watch-errors'][1])

    def test_watch_errors_reads_only_watchlist_repos(self):
        (self.root/'pivot-watch.json').write_text(json.dumps({'errors':[
            'MarcosCarreira/catalan-designs: missing diff patch paper/v2.tex','simon-oz/AI-News: Unsupported content: simon-oz/AI-News/README.md',
            'eumemic/exact-dft-bounds: Configured headline bound was not found; no change inferred','GitHub search failed; query=x',
            'CrocSwap/integer-mult-bounds PR #4270: missing diff patch research/x/ADMISSION.md']}))
        (self.root/'other-bounds-watchlist.json').write_text(json.dumps({'families':[{'repo':'MarcosCarreira/catalan-designs'}]}))
        (self.root/'pivot-watchlist.json').write_text(json.dumps({'repositories':[{'repo':'eumemic/exact-dft-bounds'}]}))
        self.assertEqual(d.Sources(self.root,persist=False).watch_errors(),
                         ['MarcosCarreira/catalan-designs: missing diff patch paper/v2.tex','eumemic/exact-dft-bounds: Configured headline bound was not found; no change inferred'])

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

    def test_method_note_alerts_only_after_a_leader_lacked_one_for_24_hours(self):
        f=Fake();self.assertEqual(d.check(f,NOW)['method-note'][:2],(True,None))
        f.leaders=[('/exact-dft','direct-pr-41',True),('/apsp','new-leader',False)]
        self.assertEqual(d.check(f,NOW)['method-note'][:2],(True,None),'first sight starts the clock')
        self.assertEqual(d.check(f,NOW+timedelta(hours=23))['method-note'][:2],(True,None))
        ok,problem=d.check(f,NOW+timedelta(hours=24))['method-note'][:2]
        self.assertFalse(ok);self.assertIn('new-leader',problem);self.assertIn('/apsp',problem)
        f.leaders=[('/exact-dft','direct-pr-41',True),('/apsp','new-leader',True)]
        self.assertEqual(d.check(f,NOW+timedelta(hours=25))['method-note'][:2],(True,None),'a note clears the alert')
        f.leaders=[('/exact-dft','direct-pr-41',True),('/apsp','newer-leader',False)]
        self.assertEqual(d.check(f,NOW+timedelta(hours=26))['method-note'][:2],(True,None),'another leader starts its own clock')
        self.assertEqual(f.method_mem['missing'],{'/apsp newer-leader':(NOW+timedelta(hours=26)).isoformat()})

    def test_method_note_tolerates_one_failed_read_and_alerts_on_two(self):
        f=Fake();f.leaders_error=OSError('down')
        self.assertNotIn('method-note',self.failing(f))
        self.assertIn('method-note',self.failing(f))
        f.leaders_error=None;self.assertNotIn('method-note',self.failing(f))

    def test_a_leader_covered_by_a_board_note_counts_as_noted(self):
        # The site puts the board note of the leader's repository in `method`, so no row note is needed.
        knowledge={'problems':[{'path':'/integer-multiplication','current':[{'id':'crocswap-pr-9999','method':'Records from this repository build on OpenAI.'}]}]}
        f=Fake();f.leaders=d.leaders_from(knowledge)
        self.assertEqual(d.check(f,NOW+timedelta(hours=48))['method-note'][:2],(True,None))

    def test_leaders_come_from_the_public_knowledge_and_an_empty_list_is_an_error(self):
        knowledge={'problems':[{'path':'/apsp','current':[{'id':'a','method':'A note.'},{'id':'b'},{'id':'c','method':'  '}]},{'path':'/3sum','current':[]}]}
        self.assertEqual(d.leaders_from(knowledge),[('/apsp','a',True),('/apsp','b',False),('/apsp','c',False)])
        with self.assertRaises(ValueError):d.leaders_from({'problems':[{'path':'/apsp','current':[]}]})

    def test_the_boshealth_read_goes_over_the_tailnet_with_the_pinned_host_key(self):
        command=d.boshealth_command(Path('/x/known'),'66.94.120.107',d.VPS_TAILNET)
        self.assertEqual(command[-1],'boshealth@100.115.7.104')
        self.assertIn('HostKeyAlias=66.94.120.107',command)
        self.assertIn('StrictHostKeyChecking=yes',command)
        self.assertNotIn('boshealth@66.94.120.107',command)

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
        self.assertIn('2 issue(s) or PR(s) open for 24 h or more',problem)
        self.assertIn('verifier#4 "Lean submission" open 2 d 1 h https://github.com/bigospeedrun/verifier/issues/4',problem)
        self.assertIn('site#2',problem);self.assertNotIn('#5',problem)

    def test_a_claimed_only_verifier_item_is_not_stale_for_its_current_version(self):
        # Lead, 2026-10-23 (interim): the bot's claimed-only result for the current version is an answer.
        V='bigospeedrun/verifier';f=Fake()
        f.issues={V:[dict(self.issue(4,49),body_sha256='b'*64),dict(self.issue(6,49),pr=True)]}
        f.comments={(V,4):[('2026-10-21T00:00:00Z','<!-- bos-ack-v1 4 '+'b'*64+' -->\nReceived.'),('2026-10-21T00:05:00Z','<!-- bos-claimed-v1 4 '+'d'*64+' -->\nClaimed.')],
                    (V,6):[('2026-10-21T00:00:00Z','<!-- bos-pr-v2 6 '+'a'*40+' -->\nPR proof result: **claimed_only**. Bound below the record')]}
        f.heads={(V,6):'a'*40}
        self.assertNotIn('stale-issues',self.failing(f))
        # A new head, or an edited issue body (a new version, acked again), is stale again.
        f.heads={(V,6):'c'*40};f.issues[V][0]['body_sha256']='e'*64
        problem=d.check(f,NOW)['stale-issues'][1]
        self.assertIn('verifier#4',problem);self.assertIn('verifier#6',problem)
        # A claimed-only comment older than the acknowledgement of the current body does not count.
        f.issues[V][0]['body_sha256']='b'*64;f.comments[(V,4)]=[f.comments[(V,4)][1],('2026-10-21T01:00:00Z','<!-- bos-ack-v1 4 '+'b'*64+' -->')]
        self.assertIn('verifier#4',d.check(f,NOW)['stale-issues'][1])
        # A snoozed item is skipped until its date, then alerts again.
        f.issues={V:[dict(self.issue(52,49),pr=True)]};f.heads={(V,52):'a'*40};f.comments={}
        with patch.dict(d.SNOOZED,{(V,52):'2026-10-25T00:00:00+00:00'}):
            self.assertNotIn('stale-issues',self.failing(f))
            self.assertIn('verifier#52',d.check(f,d.parse('2026-10-25T00:00:00+00:00'))['stale-issues'][1])
        self.assertIn('verifier#52',d.check(f,NOW)['stale-issues'][1])

    def test_issue_titles_are_sanitized_and_ages_alone_do_not_realert(self):
        f=Fake();f.issues={'bigospeedrun/watch':[self.issue(7,30,'\u00e9\n::error::'+'x'*300)]}
        problem=d.check(f,NOW)['stale-issues'][1]
        self.assertTrue(problem.isascii());self.assertNotIn('\n',problem);self.assertLess(len(problem),400)
        self.run_at(f,NOW);self.run_at(f,NOW+timedelta(hours=1))
        f.issues['bigospeedrun/watch'].append(self.issue(8,25));self.run_at(f,NOW+timedelta(hours=2))
        f.issues={};self.run_at(f,NOW+timedelta(hours=3))
        self.assertEqual([p['event'] for p in self.sent if p.get('item')=='stale-issues'],['alert','alert','recovered'])

    def test_prs_count_as_stale_items(self):
        f=Fake();f.issues={'bigospeedrun/verifier':[dict(self.issue(11,24*6,'Matrix multiplication statement'),pr=True)]}
        problem=d.check(f,NOW)['stale-issues'][1]
        self.assertIn('1 issue(s) or PR(s) open for 24 h or more',problem);self.assertIn('verifier#11 (PR) "Matrix multiplication statement" open 6 d 0 h',problem)

    def test_a_submission_without_a_bot_reply_alerts_once_per_item(self):
        # Issue #35, 2026-10-21: a form error got no reply for 10 h.
        f=Fake();f.issues={'bigospeedrun/verifier':[self.issue(35,0.5,'[Lean submission] 3SUM: x'),self.issue(36,10,'A question'),
                                                    dict(self.issue(37,2,'audit: y'),pr=True),self.issue(38,3,'[Lean submission] DFT: z')]}
        f.replied={('bigospeedrun/verifier',38)}
        ok,problem,_,_=d.check(f,NOW)['unanswered-submissions']
        self.assertFalse(ok);self.assertNotIn('#35',problem);self.assertNotIn('#36',problem);self.assertNotIn('#38',problem)
        self.assertIn('verifier#37 (PR) "audit: y" has no bot reply',problem)
        f.issues['bigospeedrun/verifier'][0]=self.issue(35,10,'[Lean submission] 3SUM: x')
        self.run_at(f,NOW);self.run_at(f,NOW+timedelta(hours=1))
        f.replied|={('bigospeedrun/verifier',35),('bigospeedrun/verifier',37)};self.run_at(f,NOW+timedelta(hours=2))
        events=[p['event'] for p in self.sent if p.get('item')=='unanswered-submissions']
        self.assertEqual(events,['alert','recovered'])

    def test_unreadable_replies_alert(self):
        f=Fake();f.issues={'bigospeedrun/verifier':[self.issue(35,10,'[Lean submission] x')]}
        f.bot_replied=lambda repo,number:(_ for _ in ()).throw(RuntimeError('down'))
        ok,problem,_,_=d.check(f,NOW)['unanswered-submissions']
        self.assertFalse(ok);self.assertIn('cannot read the verifier issues and replies: RuntimeError',problem)

    def test_issue_read_failures_alert_on_the_second_run(self):
        f=Fake();f.issue_error=RuntimeError('GitHub issues request failed')
        self.assertNotIn('stale-issues',self.failing(f));self.assertIn('stale-issues',self.failing(f))

    def test_race_channels_checked_only_once_its_timer_is_installed(self):
        f=Fake();self.assertNotIn('race-channels',d.check(f,NOW))
        f.installed=True;f.digest_ok=NOW;f.channels_ok=NOW-timedelta(hours=1)
        self.assertNotIn('race-channels',self.failing(f))
        f.channels_ok=NOW-timedelta(hours=2.5);self.assertIn('race-channels',self.failing(f))

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
