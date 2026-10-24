#!/usr/bin/env python3
"""Tell BOS Lead Dev once when a watch cycle step fails, and once when it passes again.

  cycle_alert.py fail STEP LOG [STATUS] [--continued]
  cycle_alert.py ok STEP [STEP ...]

State: .git/cycle-alerted.json (local, untracked) maps each alerted step to its
first alert time. A step is recorded only after the office confirms delivery,
so a failed delivery retries next cycle; a repeated failure stays silent.
`ok` also records each passed step's time in .git/cycle-last-ok.json, which the
independent dead-man check (deadman.py) reads; the final call of a cycle names
the pseudo-step `cycle`.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
STATE='.git/cycle-alerted.json'
LAST_OK='.git/cycle-last-ok.json'

def last_line(log):
    try:lines=[l for l in Path(log).read_text(errors='replace').splitlines() if l.strip()]
    except OSError:return 'log unavailable'
    # Logs hold counts, tracebacks and repo names; keep one short printable line.
    return re.sub(r'[^\x20-\x7e]','?',lines[-1].strip())[:300] if lines else 'log empty'

def load(root):
    path=root/STATE
    return json.loads(path.read_text()) if path.exists() else {}

def save(root,state):
    path=root/STATE;tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(path)

def fail(step,log,status,continued,send,root=None):
    root=root or ROOT;state=load(root)
    if step in state:return 'already alerted'
    stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
    what=f"Watch step '{step}' failed; the cycle continued without it." if continued else \
         f"Watch cycle stopped at step '{step}' (exit {status}); later steps did not run."
    send(f'{stamp}: {what} Last log line: {last_line(log)} Log: {log}. '
         'Next cycle retries; no repeat alert until this step passes.',f'cycle-fail-{step}-{stamp}')
    state[step]=stamp;save(root,state)
    return 'alerted'

def record_ok(steps,root):
    path=root/LAST_OK
    last=json.loads(path.read_text()) if path.exists() else {}
    stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
    last.update({s:stamp for s in steps})
    tmp=path.with_name(path.name+'.tmp');tmp.write_text(json.dumps(last,indent=2)+'\n');tmp.replace(path)

def ok(steps,send,root=None):
    root=root or ROOT;record_ok(steps,root);state=load(root)
    cleared=[s for s in steps if s in state]
    if not cleared:return 'nothing to clear'
    stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
    try:send(f"{stamp}: Watch step{'s' if len(cleared)>1 else ''} {', '.join(cleared)} passed again.",f'cycle-ok-{stamp}')
    except Exception:pass  # A lost recovery note must not keep the failure state.
    for s in cleared:state.pop(s)
    save(root,state)
    return 'cleared '+','.join(cleared)

def office_send(text,identity):
    from poll import lead_notify
    lead_notify(text,identity,'watch-cycle')

def main(argv):
    if len(argv)>=3 and argv[0]=='fail':
        args=[a for a in argv[1:] if a!='--continued']
        print(fail(args[0],args[1],args[2] if len(args)>2 else '?','--continued' in argv,office_send))
    elif len(argv)>=2 and argv[0]=='ok':print(ok(argv[1:],office_send))
    else:raise SystemExit(__doc__)

if __name__=='__main__':main(sys.argv[1:])
