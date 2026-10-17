#!/usr/bin/env python3
"""Dead-man check for Big O Speedrun automation (Nil ruling 2026-10-14: no silent failures).

Runs hourly from the systemd user timer bigospeedrun-deadman.timer, outside the
watch cron and Isomux cronjobs, so it does not depend on what it checks.
Items:
  watch-cycle          last cycle with all steps passed < 4 h (.git/cycle-last-ok.json)
  discord-intake       last passed < 4 h (#submit-a-result intake)
  problem-selection    last passed < 4 h (#problem-selection digest)
  site-refresh         bigospeedrun/site refresh-data.yml: latest completed run
                       succeeded and newest success < 2 h (GitHub GET only)
  verifier-submissions bigospeedrun-submissions.service last run ok and its
                       timer triggered < 75 min ago (systemctl --user show)
  watch-sources        every other-bounds watchlist repo was checked within the
                       last 2 cycles (pivot-watch.json); a repo that errors every
                       cycle stalled silently before 2026-10-16 (slitsey Catalan)
  prove2me-digest      #prove2me reader (bigospeedrun-prove2me.timer) last ran ok
                       < 2 h; checked once that timer unit is installed
  prove2me-import      the prove2.me import step of the newest completed site refresh
                       run (data/prove2me_import.py) did not fail; a held board names
                       its reason from data/prove2me.json on main. A run that failed only
                       in the prove2.me steps counts as a success for site-refresh. Arms
                       itself on the first run with the import step; from then on a run
                       without the step alerts
  chatbot-gap-review   Isomux cronjob "BOS chatbot gap review" completed a run
                       without error < 26 h ago (~/.isomux/cronjobs, read-only)
  vps-deploy           self-hosted site on the VPS, read through the forced-command
                       login boshealth (status.json + the site and egress containers):
                       last tick < 45 min, no failed/failed_target/rolled_back/rollback_failed/stopped/refused
                       result, not held or waiting for over 1 day, ticks not erring for 1 h, units ok, containers running
                       and healthy. One failed read is tolerated; two in a row alert.
  vps-board            the race board on the VPS, the same rules on the "board" section of
                       the same boshealth read (one ssh per run; its own status.json and its
                       db/api/auth/egress containers), plus a wait for an off-box backup
                       before a migration (phase backup) over 1 h. Off until BOARD_DEPLOY_CHECK
                       is True (set after the deploy rehearsals, plan E2); then a missing
                       board section alerts
  board-https          GET the board feed through Cloudflare: not 200 on 2 runs in a row
  board-cert           TLS handshake to the VPS with SNI board.bigospeedrun.com: the
                       origin certificate expires in under 21 days, or 2 failed handshakes
  board-backup         vpsbackup.py fresh bigospeedrun-board exits non-zero (no fresh copy
                       on auntie, or the desktop copy failed), or the newest ACK line in its
                       pull log (store/bigospeedrun-board.log) is ACK FAIL: the VPS did not
                       confirm its pull marker. No log yet = no ACK information.
                       The three board-* items arm themselves on their first success (the
                       board goes live in steps), and from then on a failure alerts.

A failing item messages BOS Lead Dev once (item, problem, last good time in PT,
log or run link), then once more when it recovers. Messages go through a signed
Isomux webhook (config .git/deadman.json; the secret stays in its file). When
that fails or is not set up, the alert goes to .git/deadman-alerts.log and the
item stays unsent, so the next hourly run retries. Output holds no secrets.
"""
import argparse
import hashlib
import hmac
import json
import socket
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
STATE='.git/deadman-state.json'
ALERTS='.git/deadman-alerts.log'
CONFIG='.git/deadman.json'
LAST_OK='.git/cycle-last-ok.json'
CRONJOBS=Path.home()/'.isomux/cronjobs'
GAP_REVIEW_JOB='3f73daae'
# The boshealth key and pinned host key stay outside the repo; the host comes from
# the pinned known_hosts entry, so no address is written here.
VPS_SECRETS=Path.home()/'nil/bigospeedrun-notes/secrets'
VPS_MEMORY='.git/vps-health.json'
# failed_target: the newest green commit failed and stays unretried; every tick shows it until a
# newer commit. A past attempt alone (last_attempt) is not a problem once a tick is up_to_date.
VPS_BAD_RESULTS={'failed','failed_target','rolled_back','rollback_failed','stopped','refused','manual_deploy_needed'}
VPS_LINK='ssh boshealth (VPS /opt/bigospeedrun/auto-deploy/status.json); runbook ~/nil/bigospeedrun-notes/phase-c-staging-plan.md'
# vps-board is checked only after the board's deploy rehearsals (phase E plan, E2): they
# leave rolled_back and manual_deploy_needed results on purpose. Set True in that commit.
BOARD_DEPLOY_CHECK=True
BOARD_MEMORY='.git/board-health.json'
PROVE2ME_MEMORY='.git/prove2me-import.json'
# Step names in bigospeedrun/site .github/workflows/refresh-data.yml.
PROVE2ME_STEP='Import reviewed prove2.me results'
PROVE2ME_FAIL_STEP='Fail the run when the prove2.me import is held'
PROVE2ME_STEPS={PROVE2ME_STEP,PROVE2ME_FAIL_STEP}
BOARD_HOST='board.bigospeedrun.com'
BOARD_FEED=f'https://{BOARD_HOST}/api/posts?board=3sum&limit=1'   # the board is at the root of its host (board 21648c1)
BOARD_LINK='ssh boshealth (VPS /opt/bigospeedrun-board/auto-deploy/status.json); runbook ~/nil/bigospeedrun-notes/phase-e-board-deploy-plan.md'
VPS_BACKUP=Path.home()/'nil/wallgame/ops-private/vps-backup'
PT=ZoneInfo('America/Los_Angeles')
H=timedelta(hours=1)

def pt(when):
    if not when:return 'never recorded'
    t=when.astimezone(PT)
    return t.strftime('%a %b ')+str(t.day)+', '+t.strftime('%I:%M %p').lstrip('0')+' PT'

def parse(stamp):
    return datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone(timezone.utc) if stamp else None

class Sources:
    """Read-only views of the checked systems. Tests replace these methods."""
    def __init__(self,root,persist=True):self.root=root;self.persist=persist
    def last_ok(self):
        path=self.root/LAST_OK
        return json.loads(path.read_text()) if path.exists() else {}
    def log_ok_time(self,name):
        # Before the first marker: a log whose JSON status is ok counts at its mtime.
        path=self.root/'.git'/name
        try:
            line=path.read_text().strip().splitlines()[-1]
            if json.loads(line).get('status')=='ok':return datetime.fromtimestamp(path.stat().st_mtime,timezone.utc)
        except (OSError,ValueError,IndexError,AttributeError):pass
        return None
    def refresh_runs(self):
        out=subprocess.run(['gh','api','-X','GET','repos/bigospeedrun/site/actions/workflows/refresh-data.yml/runs','-f','per_page=20'],
                           capture_output=True,text=True,timeout=60)
        if out.returncode:raise RuntimeError('GitHub runs request failed')
        return json.loads(out.stdout)['workflow_runs']
    def run_steps(self,run):
        out=subprocess.run(['gh','api','-X','GET',f"repos/bigospeedrun/site/actions/runs/{int(run['id'])}/jobs"],
                           capture_output=True,text=True,timeout=60)
        if out.returncode:raise RuntimeError('GitHub jobs request failed')
        return [dict(name=s.get('name'),conclusion=s.get('conclusion')) for job in json.loads(out.stdout)['jobs'] for s in job.get('steps',[])]
    def prove2me_state(self):
        out=subprocess.run(['gh','api','-X','GET','repos/bigospeedrun/site/contents/data/prove2me.json','-H','Accept: application/vnd.github.raw'],
                           capture_output=True,text=True,timeout=60)
        if out.returncode:raise RuntimeError('GitHub contents request failed')
        return json.loads(out.stdout)
    def prove2me_memory(self):
        path=self.root/PROVE2ME_MEMORY
        return json.loads(path.read_text()) if path.exists() else {}
    def remember_prove2me(self,memory):
        if not self.persist:return
        path=self.root/PROVE2ME_MEMORY;tmp=path.with_name(path.name+'.tmp')
        tmp.write_text(json.dumps(memory,indent=2)+'\n');tmp.replace(path)
    def systemd(self,unit,*props):
        out=subprocess.run(['systemctl','--user','show',unit,'--no-pager']+[f'-p{p}' for p in props],
                           capture_output=True,text=True,timeout=30)
        if out.returncode:raise RuntimeError('systemctl show failed for '+unit)
        return dict(line.split('=',1) for line in out.stdout.splitlines() if '=' in line)
    def stalled_sources(self):
        report=json.loads((self.root/'pivot-watch.json').read_text())
        cycle=report['other_bounds_checkpoint']['cycle'];states=report.get('other_bound_states',{})
        repos=dict.fromkeys(c['repo'] for c in json.loads((self.root/'other-bounds-watchlist.json').read_text())['families'])
        return [r for r in repos if (states.get(r,{}).get('checked_cycle') or 0)<cycle-2]
    def digest_last_ok(self,name):
        path=self.root/f'{name}.local.json'
        return parse(json.loads(path.read_text()).get('last_ok')) if path.exists() else None
    def unit_installed(self,unit):return (Path.home()/'.config/systemd/user'/unit).exists()
    def cron_runs(self,job):
        path=CRONJOBS/job/'runs.json'
        return json.loads(path.read_text()) if path.exists() else []
    def vps_host(self):
        host=(VPS_SECRETS/'boshealth.known_hosts').read_text().split()[0]
        if host.startswith('|'):raise RuntimeError('hashed known_hosts entry')
        return host
    def vps_health(self):
        known=VPS_SECRETS/'boshealth.known_hosts'
        host=self.vps_host()
        # The forced command takes no command; stderr is dropped so nothing about the key is printed.
        out=subprocess.run(['ssh','-F','/dev/null','-T','-i',str(VPS_SECRETS/'boshealth.key'),'-o','IdentitiesOnly=yes',
                            '-o','IdentityAgent=none','-o','PreferredAuthentications=publickey','-o','BatchMode=yes',
                            '-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(known),'-o','GlobalKnownHostsFile=/dev/null',
                            '-o','ConnectTimeout=20','boshealth@'+host],
                           stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=60)
        if out.returncode:raise RuntimeError(f'boshealth read exited {out.returncode}')
        return json.loads(out.stdout)
    def vps_memory(self):
        path=self.root/VPS_MEMORY
        return json.loads(path.read_text()) if path.exists() else {}
    def remember_vps(self,memory):
        if not self.persist:return
        path=self.root/VPS_MEMORY;tmp=path.with_name(path.name+'.tmp')
        tmp.write_text(json.dumps(memory,indent=2)+'\n');tmp.replace(path)
    def board_https(self):
        request=urllib.request.Request(BOARD_FEED,headers={'User-Agent':'bos-deadman/1','Accept':'application/json'})
        try:
            with urllib.request.urlopen(request,timeout=30) as response:return response.status
        except urllib.error.HTTPError as error:return error.code
    def board_cert_days(self):
        # Only the TLS handshake: the origin's cloudflare_only gate aborts after it, and no
        # HTTP request is sent. The default context checks the chain and the name.
        with socket.create_connection((self.vps_host(),443),timeout=20) as raw:
            with ssl.create_default_context().wrap_socket(raw,server_hostname=BOARD_HOST) as tls:
                cert=tls.getpeercert()
        return (ssl.cert_time_to_seconds(cert['notAfter'])-time.time())/86400
    def board_backup(self):
        """(exit code, first line) of vpsbackup.py fresh, or None before the first pull."""
        if not (VPS_BACKUP/'store'/'bigospeedrun-board').is_dir():return None
        out=subprocess.run(['python3','-I',str(VPS_BACKUP/'vpsbackup.py'),'fresh','bigospeedrun-board'],
                           capture_output=True,text=True,timeout=300)
        return out.returncode,((out.stdout.strip().splitlines() or [''])[0])[:200]
    def board_ack_log(self):
        """The board's pull log that vpsbackup.py appends to (ACK OK / ACK FAIL lines), or None if it is missing."""
        path=VPS_BACKUP/'store'/'bigospeedrun-board.log'
        return path.read_text(errors='replace') if path.exists() else None
    def board_memory(self):
        path=self.root/BOARD_MEMORY
        return json.loads(path.read_text()) if path.exists() else {}
    def remember_board(self,memory):
        if not self.persist:return
        path=self.root/BOARD_MEMORY;tmp=path.with_name(path.name+'.tmp')
        tmp.write_text(json.dumps(memory,indent=2)+'\n');tmp.replace(path)

def newest_ack(log):
    """('OK'|'FAIL', time or None) of the newest ACK line vpsbackup.py wrote, or None."""
    for line in reversed((log or '').splitlines()):
        words=line.split()
        if len(words)>=4 and words[1]=='bigospeedrun-board' and words[2]=='ACK' and words[3] in ('OK','FAIL'):
            try:when=parse(words[0])
            except ValueError:when=None
            return words[3],when
    return None

def systemd_time(value):
    # systemctl prints e.g. "Thu 2026-10-15 02:47:34 CEST"; "n/a" when never run.
    if not value or value=='n/a':return None
    out=subprocess.run(['date','-u','-d',value,'+%Y-%m-%dT%H:%M:%SZ'],capture_output=True,text=True,timeout=10)
    return parse(out.stdout.strip()) if out.returncode==0 else None

def vps_deploy(data,now,memory):
    """(ok, problem) for the VPS deploy status; updates memory (held_since)."""
    problems=[];status=data.get('auto_deploy') or {}
    if status.get('missing') or status.get('malformed') or not status:
        problems.append('status.json '+('missing' if status.get('missing') else 'unreadable'))
    else:
        tick=parse(status.get('tick_at'))
        if not tick or now-tick>=45*timedelta(minutes=1):problems.append(f'last deploy tick {pt(tick)}')
        bad=[status['result']] if status.get('result') in VPS_BAD_RESULTS else []
        if status.get('stopped'):bad.append('stopped')
        if bad:problems.append('deploy '+'/'.join(dict.fromkeys(bad)))
        if status.get('held'):
            since=parse(memory.setdefault('held_since',now.isoformat(timespec='seconds')))
            if now-since>=24*H:problems.append(f'held since {pt(since)}')
        else:memory.pop('held_since',None)
        waiting=parse(status.get('waiting_since'))
        if status.get('waiting') and waiting and now-waiting>=24*H:problems.append(f'green commit waiting since {pt(waiting)}')
        elif status.get('waiting') and status.get('phase')=='backup' and waiting and now-waiting>=H:
            problems.append(f'waiting for an off-box backup before a migration since {pt(waiting)}')
        # tick_error_since can outlive the error in a held/locked/stopped status; only a tick_error result counts.
        erring=parse(status.get('tick_error_since')) if status.get('result')=='tick_error' else None
        if erring and now-erring>=H:problems.append(f'ticks failing since {pt(erring)}')
        # A tick that found the lock taken ends before the unit check, so its units stay 'unchecked'.
        if status.get('units')!='ok' and not (status.get('result')=='locked' and status.get('units')=='unchecked'):
            problems.append(f"units {status.get('units')}")
    for name,c in sorted((data.get('containers') or {}).items()):
        if not c.get('present') or c.get('error') or c.get('status')!='running' or c.get('health') not in (None,'healthy'):
            problems.append(f"{name} {'missing' if not c.get('present') else str(c.get('status'))+'/'+str(c.get('health'))}")
    if not data.get('containers'):problems.append('no container states')
    return not problems,('; '.join(problems)[:300] or None)

def prove2me_check(src,latest,results):
    memory=src.prove2me_memory();link=(latest or {}).get('html_url') or 'https://github.com/bigospeedrun/site/actions/workflows/refresh-data.yml'
    try:
        if latest is None:raise RuntimeError('no completed refresh run')
        names={s['name']:s.get('conclusion') for s in src.run_steps(latest)}
    except Exception as error:
        if memory.get('armed'):results['prove2me-import']=(False,'cannot read the refresh run steps: '+type(error).__name__,None,link)
        return
    if PROVE2ME_STEP not in names:
        if memory.get('armed'):results['prove2me-import']=(False,'the newest refresh run has no prove2.me import step',None,link)
        return
    memory['armed']=True;src.remember_prove2me(memory)
    if 'failure' not in (names.get(PROVE2ME_STEP),names.get(PROVE2ME_FAIL_STEP)):
        results['prove2me-import']=(True,None,parse(latest.get('created_at')),link)
        return
    try:
        boards=src.prove2me_state().get('boards',{})
        held=[f"{slug}: {b.get('reason')}" for slug,b in sorted(boards.items()) if b.get('status')=='held']
        problem='import held for '+'; '.join(held) if held else 'import step failed without a held board (parse or crash; read the run log)'
    except Exception as error:
        problem='import held or failed; cannot read data/prove2me.json: '+type(error).__name__
    results['prove2me-import']=(False,problem[:400]+' (review data/prove2me-trust.json)',None,link)

def check(src,now,to_time=systemd_time):
    """Return {item: (ok, problem, last_good, link)}."""
    results={}
    last=src.last_ok()
    def marker(item,keys,logname,hours,link):
        good=max((parse(last[k]) for k in keys if last.get(k)),default=None) or (src.log_ok_time(logname) if logname else None)
        fresh=bool(good and now-good<hours*H)
        results[item]=(fresh,None if fresh else f'no passed run in the last {hours} h',good,link)
    # 'push' is the last step of the set -e cycle block, so its pass means a full
    # cycle; blocks pasted before 7a77095 record 'push' but not 'cycle'.
    marker('watch-cycle',('cycle','push'),None,4,'~/nil/bigospeedrun-data/.git/cycle-alert.log and .git/*.log')
    marker('discord-intake',('discord-intake',),'discord-watch.log',4,'~/nil/bigospeedrun-data/.git/discord-watch.log')
    marker('problem-selection',('problem-selection',),'problem-selection.log',4,'~/nil/bigospeedrun-data/.git/problem-selection.log')
    try:
        runs=src.refresh_runs()
        done=[r for r in runs if r.get('status')=='completed']
        steps={}
        def failed_steps(run):
            if id(run) not in steps:steps[id(run)]=[s['name'] for s in src.run_steps(run) if s.get('conclusion')=='failure']
            return steps[id(run)]
        # A run that failed only in the prove2.me steps is a refresh success; prove2me-import reports it.
        def succeeded(run,index):
            if run.get('conclusion')=='success':return True
            return run.get('conclusion')=='failure' and index<6 and bool(failed_steps(run)) and set(failed_steps(run))<=PROVE2ME_STEPS
        wins=[r for i,r in enumerate(done) if succeeded(r,i)]
        good=parse(wins[0]['created_at']) if wins else None
        latest=done[0] if done else None
        if not latest:results['site-refresh']=(False,'no completed refresh run',good,'https://github.com/bigospeedrun/site/actions/workflows/refresh-data.yml')
        elif not succeeded(latest,0):results['site-refresh']=(False,f"latest run {latest.get('conclusion')}",good,latest.get('html_url'))
        elif not good or now-good>=2*H:results['site-refresh']=(False,'no successful run in the last 2 h',good,latest.get('html_url'))
        else:results['site-refresh']=(True,None,good,latest.get('html_url'))
    except Exception as error:
        latest=None
        results['site-refresh']=(False,'cannot read GitHub runs: '+type(error).__name__,None,'https://github.com/bigospeedrun/site/actions/workflows/refresh-data.yml')
    prove2me_check(src,latest,results)
    try:
        service=src.systemd('bigospeedrun-submissions.service','Result','ExecMainStatus','ExecMainExitTimestamp')
        timer=src.systemd('bigospeedrun-submissions.timer','LastTriggerUSec','ActiveState')
        fired=to_time(timer.get('LastTriggerUSec'));ended=to_time(service.get('ExecMainExitTimestamp'))
        link='journalctl --user -u bigospeedrun-submissions.service'
        if timer.get('ActiveState')!='active':results['verifier-submissions']=(False,'timer not active',ended,link)
        elif service.get('Result')!='success' or service.get('ExecMainStatus')!='0':
            results['verifier-submissions']=(False,f"last run {service.get('Result')} (exit {service.get('ExecMainStatus')})",None,link)
        elif not fired or now-fired>=75*timedelta(minutes=1):results['verifier-submissions']=(False,'timer has not fired in 75 min',ended,link)
        else:results['verifier-submissions']=(True,None,ended,link)
    except Exception as error:
        results['verifier-submissions']=(False,'cannot read systemd state: '+type(error).__name__,None,'systemctl --user status bigospeedrun-submissions.timer')
    try:
        stalled=src.stalled_sources()
        results['watch-sources']=(not stalled,f"{len(stalled)} watched repo(s) not checked for over 2 cycles: {', '.join(stalled[:5])}" if stalled else None,
                                  None if stalled else now,'~/nil/bigospeedrun-data/pivot-watch.json (errors)')
    except Exception as error:
        results['watch-sources']=(False,'cannot read pivot-watch.json: '+type(error).__name__,None,'~/nil/bigospeedrun-data/pivot-watch.json')
    if src.unit_installed('bigospeedrun-prove2me.timer'):
        good=src.digest_last_ok('prove2me');fresh=bool(good and now-good<2*H)
        results['prove2me-digest']=(fresh,None if fresh else 'no successful #prove2me read in the last 2 h',good,
                                    'journalctl --user -u bigospeedrun-prove2me.service')
    try:
        runs=src.cron_runs(GAP_REVIEW_JOB)
        ok=[r for r in runs if r.get('status')=='completed' and not r.get('errorReason')]
        good=max((datetime.fromtimestamp(r['startedAt']/1000,timezone.utc) for r in ok),default=None)
        newest=max(runs,key=lambda r:r.get('startedAt',0),default=None)
        link=f"Isomux Automations > BOS chatbot gap review (cronjob {GAP_REVIEW_JOB})"
        if newest and newest.get('errorReason'):results['chatbot-gap-review']=(False,'latest run failed',good,link)
        elif not good or now-good>=26*H:results['chatbot-gap-review']=(False,'no completed run in the last 26 h',good,link)
        else:results['chatbot-gap-review']=(True,None,good,link)
    except Exception as error:
        results['chatbot-gap-review']=(False,'cannot read cronjob runs: '+type(error).__name__,None,f'~/.isomux/cronjobs/{GAP_REVIEW_JOB}/runs.json')
    memory=src.vps_memory();board=src.board_memory();data=None
    try:
        data=src.vps_health()
    except Exception as error:
        # One failed read keeps the last verdict; the second in a row alerts.
        memory['read_failures']=memory.get('read_failures',0)+1
        unread=f"cannot read the VPS status ({memory['read_failures']} reads in a row): "+type(error).__name__
        if memory['read_failures']>=2:results['vps-deploy']=(False,unread,None,VPS_LINK)
        else:results['vps-deploy']=(memory.get('last_ok',True),memory.get('last_problem'),None,VPS_LINK)
        if BOARD_DEPLOY_CHECK:
            if memory['read_failures']>=2:results['vps-board']=(False,unread,None,BOARD_LINK)
            else:results['vps-board']=(board.get('last_ok',True),board.get('last_problem'),None,BOARD_LINK)
    else:
        memory['read_failures']=0
        ok,problem=vps_deploy(data,now,memory)
        memory['last_ok']=ok;memory['last_problem']=problem
        results['vps-deploy']=(ok,problem,now if ok else None,VPS_LINK)
        if BOARD_DEPLOY_CHECK and isinstance(data.get('board'),dict):
            ok,problem=vps_deploy(data['board'],now,board.setdefault('deploy',{}))
            board['last_ok']=ok;board['last_problem']=problem
            results['vps-board']=(ok,problem,now if ok else None,BOARD_LINK)
        elif BOARD_DEPLOY_CHECK:
            results['vps-board']=(False,'the VPS health read has no board section',None,BOARD_LINK)
    src.remember_vps(memory)
    board_checks(src,now,board,results)
    src.remember_board(board)
    return results

def board_checks(src,now,board,results):
    """board-https, board-cert and board-backup: each arms itself on its first success."""
    try:code=src.board_https()
    except Exception as error:code=type(error).__name__
    if code==200:
        board['https_armed']=True;board['https_failures']=0
        results['board-https']=(True,None,now,BOARD_FEED)
    elif board.get('https_armed'):
        board['https_failures']=board.get('https_failures',0)+1
        bad=board['https_failures']>=2
        results['board-https']=(not bad,f"the board feed answered {code} on {board['https_failures']} runs in a row" if bad else None,None,BOARD_FEED)
    link='TLS handshake to the VPS with SNI '+BOARD_HOST+'; journalctl -u wg-caddy on the VPS'
    try:days=src.board_cert_days()
    except Exception as error:days=None;why=type(error).__name__
    if days is not None:
        board['cert_armed']=True;board['cert_failures']=0
        results['board-cert']=(days>=21,None if days>=21 else f'the origin certificate expires in {days:.0f} days',now if days>=21 else None,link)
    elif board.get('cert_armed'):
        board['cert_failures']=board.get('cert_failures',0)+1
        bad=board['cert_failures']>=2
        results['board-cert']=(not bad,f"the origin TLS handshake failed on {board['cert_failures']} runs in a row: {why}" if bad else None,None,link)
    link='python3 -I ~/nil/wallgame/ops-private/vps-backup/vpsbackup.py fresh bigospeedrun-board; journalctl --user -u vps-backup@bigospeedrun-board; grep ACK ~/nil/wallgame/ops-private/vps-backup/store/bigospeedrun-board.log'
    try:fresh=src.board_backup()
    except Exception as error:fresh=(None,'cannot run vpsbackup.py: '+type(error).__name__)
    if fresh is None:
        if board.get('backup_armed'):results['board-backup']=(False,'no backup store for bigospeedrun-board on auntie',None,link)
    else:
        code,line=fresh
        if code==0:board['backup_armed']=True
        if code==0 or board.get('backup_armed'):
            problems=[] if code==0 else [('the desktop copy failed: ' if code==2 else 'no fresh backup: ')+line]
            try:ack=newest_ack(src.board_ack_log())
            except Exception as error:ack=None;problems.append('cannot read the board pull log: '+type(error).__name__)
            if ack and ack[0]=='FAIL':
                problems.append(f'the newest pull was not acknowledged (ACK FAIL at {pt(ack[1])}): the VPS wrote no pull marker')
            results['board-backup']=(not problems,'; '.join(problems)[:300] or None,None if problems else now,link)

def webhook_send(root,event='deadman'):
    # Isomux passes only the rule's args to the agent (payload.text here), in a
    # message capped at 4000 characters; keep payload text well below that.
    config_path=root/CONFIG
    def send(payload):
        if not config_path.exists():raise RuntimeError('dead-man webhook not configured')
        config=json.loads(config_path.read_text())
        secret=Path(config['secret_file']).read_text().strip().encode()
        body=json.dumps(payload).encode()
        signature='sha256='+hmac.new(secret,body,hashlib.sha256).hexdigest()
        request=urllib.request.Request(config['hook_url'],data=body,method='POST',headers={
            'Content-Type':'application/json',config['signature_header']:signature,config['event_header']:event})
        with urllib.request.urlopen(request,timeout=30) as response:
            if response.status>=300:raise RuntimeError(f'webhook HTTP {response.status}')
    return send

def run(src,send,root=None,now=None):
    root=root or ROOT;now=now or datetime.now(timezone.utc)
    state_path=root/STATE
    state=json.loads(state_path.read_text()) if state_path.exists() else {}
    report={}
    for item,(ok,problem,good,link) in check(src,now).items():
        entry=state.get(item,{})
        if good:entry['last_good']=good.isoformat(timespec='seconds')
        good_pt=pt(parse(entry.get('last_good')))
        if ok and entry.get('alerted'):
            payload=dict(kind='bos-deadman',event='recovered',item=item,text=f'Dead-man check: {item} recovered (last good {good_pt}).')
        elif not ok and not entry.get('alerted'):
            payload=dict(kind='bos-deadman',event='alert',item=item,problem=problem,last_good=good_pt,link=link,
                         text=f'Dead-man check: {item} is failing or stale: {problem}. Last good: {good_pt}. See: {link}.')
        else:
            payload=None
        status='ok' if ok else 'failing'
        if payload:
            try:
                send(payload);entry['alerted']=not ok;entry.pop('local_only',None)
                status+=', '+payload['event']+' sent'
            except Exception as error:
                # Lead unreachable: keep the item unsent and leave a local trace once per episode.
                if entry.get('local_only')!=payload['event']:
                    with (root/ALERTS).open('a') as f:f.write(now.isoformat(timespec='seconds')+' '+payload['text']+'\n')
                    entry['local_only']=payload['event']
                status+=', '+payload['event']+' not delivered ('+type(error).__name__+'), written to '+ALERTS
        state[item]=entry;report[item]=status
    tmp=state_path.with_name(state_path.name+'.tmp');tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(state_path)
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--dry-run',action='store_true',help='check only: print item status, send and write nothing')
    args=parser.parse_args()
    src=Sources(ROOT,persist=not args.dry_run);now=datetime.now(timezone.utc)
    if args.dry_run:
        for item,(ok,problem,good,link) in check(src,now).items():
            print(f"{item}: {'ok' if ok else 'FAILING: '+problem}; last good {pt(good)}")
        return
    try:report=run(src,webhook_send(ROOT),now=now)
    except Exception as error:
        # The check itself must not fail silently: leave a local trace, fail the unit.
        # The watch cycle also alerts when .git/deadman-state.json goes stale.
        with (ROOT/ALERTS).open('a') as f:f.write(now.isoformat(timespec='seconds')+' Dead-man check crashed: '+type(error).__name__+'\n')
        print('Dead-man check crashed: '+type(error).__name__)
        raise SystemExit(1)
    for item,status in report.items():print(f'{item}: {status}')

if __name__=='__main__':main()
