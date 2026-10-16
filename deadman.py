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
  chatbot-gap-review   Isomux cronjob "BOS chatbot gap review" completed a run
                       without error < 26 h ago (~/.isomux/cronjobs, read-only)
  vps-deploy           self-hosted site on the VPS, read through the forced-command
                       login boshealth (status.json + the site and egress containers):
                       last tick < 45 min, no failed/rolled_back/rollback_failed/stopped/refused
                       result, not held or waiting for over 1 day, containers running
                       and healthy. One failed read is tolerated; two in a row alert.

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
import subprocess
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
VPS_BAD_RESULTS={'failed','rolled_back','rollback_failed','stopped','refused'}
VPS_LINK='ssh boshealth (VPS /opt/bigospeedrun/auto-deploy/status.json); runbook ~/nil/bigospeedrun-notes/phase-c-staging-plan.md'
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
    def vps_health(self):
        known=VPS_SECRETS/'boshealth.known_hosts'
        host=known.read_text().split()[0]
        if host.startswith('|'):raise RuntimeError('hashed known_hosts entry')
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
        last=(status.get('last_attempt') or {}).get('result')
        bad=[r for r in (status.get('result'),last) if r in VPS_BAD_RESULTS]
        if status.get('stopped'):bad.append('stopped')
        if bad:problems.append('deploy '+'/'.join(dict.fromkeys(bad)))
        if status.get('held'):
            since=parse(memory.setdefault('held_since',now.isoformat(timespec='seconds')))
            if now-since>=24*H:problems.append(f'held since {pt(since)}')
        else:memory.pop('held_since',None)
        waiting=parse(status.get('waiting_since'))
        if status.get('waiting') and waiting and now-waiting>=24*H:problems.append(f'green commit waiting since {pt(waiting)}')
    for name,c in sorted((data.get('containers') or {}).items()):
        if not c.get('present') or c.get('error') or c.get('status')!='running' or c.get('health') not in (None,'healthy'):
            problems.append(f"{name} {'missing' if not c.get('present') else str(c.get('status'))+'/'+str(c.get('health'))}")
    if not data.get('containers'):problems.append('no container states')
    return not problems,('; '.join(problems)[:300] or None)

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
        wins=[r for r in done if r.get('conclusion')=='success']
        good=parse(wins[0]['created_at']) if wins else None
        latest=done[0] if done else None
        if not latest:results['site-refresh']=(False,'no completed refresh run',good,'https://github.com/bigospeedrun/site/actions/workflows/refresh-data.yml')
        elif latest.get('conclusion')!='success':results['site-refresh']=(False,f"latest run {latest.get('conclusion')}",good,latest.get('html_url'))
        elif not good or now-good>=2*H:results['site-refresh']=(False,'no successful run in the last 2 h',good,latest.get('html_url'))
        else:results['site-refresh']=(True,None,good,latest.get('html_url'))
    except Exception as error:
        results['site-refresh']=(False,'cannot read GitHub runs: '+type(error).__name__,None,'https://github.com/bigospeedrun/site/actions/workflows/refresh-data.yml')
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
    memory=src.vps_memory()
    try:
        data=src.vps_health()
    except Exception as error:
        # One failed read keeps the last verdict; the second in a row alerts.
        memory['read_failures']=memory.get('read_failures',0)+1
        if memory['read_failures']>=2:results['vps-deploy']=(False,f"cannot read the VPS status ({memory['read_failures']} reads in a row): "+type(error).__name__,None,VPS_LINK)
        else:results['vps-deploy']=(memory.get('last_ok',True),memory.get('last_problem'),None,VPS_LINK)
    else:
        memory['read_failures']=0
        ok,problem=vps_deploy(data,now,memory)
        memory['last_ok']=ok;memory['last_problem']=problem
        results['vps-deploy']=(ok,problem,now if ok else None,VPS_LINK)
    src.remember_vps(memory)
    return results

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
