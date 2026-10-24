#!/usr/bin/env python3
"""One local polling cycle. Schedule the next cycle before doing network work."""
import fcntl, json, os, subprocess, sys, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LOCAL_CONFIG=ROOT/'.git/watch-office.json'
LOCAL_OFFICE=json.loads(LOCAL_CONFIG.read_text()) if LOCAL_CONFIG.exists() else {}
SELF=LOCAL_OFFICE.get('self')
LEAD=LOCAL_OFFICE.get('lead')
MARKER='Big O data poll every 3 hours'

def office(route,data=None):
    if not all(LOCAL_OFFICE.get(k) for k in ('self','lead','token_env')):
        raise RuntimeError('Configure the local office adapter in .git/watch-office.json')
    req=urllib.request.Request('http://localhost:4000'+route, data=json.dumps(data).encode() if data is not None else None, headers={'Authorization':'Bearer '+os.environ[LOCAL_OFFICE['token_env']],'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)

def lead_notify(text,identity,channel='watch-cycle'):
    """Send one message to the lead. With the office token in the environment (a cycle started by the
    agent session) it goes through the office API; without it (the systemd timer bos-watch-cycle.timer,
    which has no token) through the signed Isomux webhook, like the other timers (Lead, 2026-10-24)."""
    if os.environ.get(LOCAL_OFFICE.get('token_env') or ''):
        result=office(f'/api/agents/{LEAD}/messages',{'text':text,'clientMessageId':identity})
        if not result.get('messageId'):raise RuntimeError('Delivery unconfirmed')
        return
    import digest_size
    from deadman import webhook_send
    webhook_send(ROOT,'digest')(dict(kind='bos-digest',channel=channel,text=digest_size.fit(text,digest_size.LIMIT)))

def schedule():
    pending=office(f'/api/agents/{SELF}/scheduled-messages')['scheduled']
    if any(x['receiverAgentId']==SELF and x['text'].startswith(MARKER) for x in pending):return
    at=(datetime.now(timezone.utc)+timedelta(hours=3)).isoformat(timespec='seconds')
    result=office(f'/api/agents/{SELF}/messages',{'deliverAt':at,'text':MARKER+'. Run python3 poll.py from the watch repository root. It schedules the next cycle, runs pivot and GitHub people watches only; commits watch reports locally, and sends approved internal notifications. Report only integer multiplication, Fourier transform, 3SUM, APSP and Subset Sum leads to BOS Lead Dev. Ignore all other problems. GitHub Actions owns data refresh; do not run local refresh.py or import board data. No push, deploy, outside contact, or upstream code execution. Continue until BOS Lead Dev or Nil says stop. If the cycle fails, inspect .git/poll.log and retain the scheduled retry.'})
    print('Next cycle:',at,'scheduled:',result['scheduledId'])

def run():
    with (ROOT/'.git/poll.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        schedule()
        if '--schedule-only' in sys.argv:return
        # Refuse to mix user edits with an automatic watch report commit.
        if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise RuntimeError('Worktree has edits; watches paused for review')
        previous=json.loads((ROOT/'pivot-watch.json').read_text()) if (ROOT/'pivot-watch.json').exists() else {}
        with (ROOT/'.git/poll.log').open('w') as log:
            subprocess.run(['python3','people_watch.py'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
            people=json.loads((ROOT/'people-watch.json').read_text())
            subprocess.run(['git','add','--','people-watch.json'],cwd=ROOT,check=True)
            if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:
                subprocess.run(['git','commit','-m','Update GitHub people watch '+people['checked_at']],cwd=ROOT,check=True,stdout=log)
            subprocess.run(['python3','pivot_watch.py'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
            watch=json.loads((ROOT/'pivot-watch.json').read_text())
            subprocess.run(['git','add','--','pivot-watch.json'],cwd=ROOT,check=True)
            if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:
                subprocess.run(['git','commit','-m','Update GitHub pivot watch '+watch['checked_at']],cwd=ROOT,check=True,stdout=log)
            known={r['repo'] for r in previous.get('candidates',[]) if r['likely_new_race'] or r.get('likely_pivot') or r.get('likely_tracked_source')}
            changed_heads={r['repo'] for r in watch.get('watched_repositories',[]) if r['new_commit']}
            from pivot_watch import alert_candidate
            new=[r for r in watch['candidates'] if alert_candidate(r,known,changed_heads)]
            if new:office(f'/api/agents/{LEAD}/messages',{'text':watch['checked_at']+': Possible new bound race or problem pivot; README signals need review: '+'; '.join(r['url']+' ('+r['problem_guess']+')' for r in new)})
if __name__=='__main__':run()
