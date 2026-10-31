#!/usr/bin/env python3
"""Page the manager when the dead-man webhook no longer takes our alerts.

Every BOS timer (dead-man, pwn-watch, comment-watch, discord-signals, the watch cycle) reports through
one signed Isomux webhook. On 2026-10-26 its secret changed (a change of manager rotates a hook's
secret); our secret file went stale, every send got HTTP 401, and nothing reached the lead for five
days. The lead saw it only because systemd showed a unit as failed (BOS Lead Dev, 2026-10-31).

This guard sends a signed probe through the same path each hour: the same URL, secret file and
signature as webhook_send (deadman.py), with an event name that no rule matches. The hook answers 200
{"ok":true} to a good signature and does nothing else (no turn is billed); it answers 401 to a bad one.
It reports through the Isomux pager (POST /api/app/pager), a separate path, so a broken webhook cannot
hide its own failure. That is a stronger check than "the last accepted delivery is older than a limit":
a quiet week has no deliveries and is no fault, and the probe tests the whole path now.

* HTTP 401 (the secret is refused), a missing or unreadable config or secret file: page at once.
* Any other failure (the office is down, a timeout, HTTP 5xx): page after 2 failed passes in a row, whatever
  their detail (a flapping outage counts).
* A good probe after a page resolves the page. One page per problem (key bos-hook-guard).
* The lead is the one who can rotate the secret and nobody reads the manager's inbox, so the first page of a
  problem is also sent to the lead as an app message (POST /api/app/message with targetAgentId, from
  .git/watch-office.json), and so is the recovery. A failed message never blocks the page.

It runs as an Isomux app (the token, ISOMUX_APP_TOKEN, is in the app's environment and never on disk):
    python3 hook_guard.py --loop       # one pass now and then every hour, forever
    python3 hook_guard.py              # one pass
    python3 hook_guard.py --dry-run    # probe only: no page, no state write
Output holds a status word and an HTTP status or exception type, never a body or a secret.
"""
import argparse
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = '.git/deadman.json'  # the file webhook_send reads: hook_url, secret_file and the two header names
STATE = '.git/hook-guard.json'
EVENT = 'hook-guard'  # no rule of the hook matches it
KEY = 'bos-hook-guard'
INTERVAL = 3600
CONSECUTIVE = 2  # passes with the same non-definitive failure before a page
OFFICE = 'http://localhost:4000'
LEAD_CONFIG = '.git/watch-office.json'  # the same file poll.py reads (key lead)

FIX = ('Fix: the hook\'s creator (BOS Lead Dev) rotates the secret with POST /api/webhooks/<hook id>/secret and saves '
       'the new secret as the raw string (mode 600) in the file named by secret_file in ~/nil/bigospeedrun-data/.git/deadman.json. '
       'Until then no BOS timer can alert the lead (dead-man, pwn-watch, comment-watch, discord-signals, watch cycle); '
       'the dead-man writes its alerts to ~/nil/bigospeedrun-data/.git/deadman-alerts.log.')


def probe(root=None, timeout=20):
    """('ok', None), ('refused', 401) or ('failed', <status or exception type>). Never raises, never returns a body."""
    root = Path(root or ROOT)
    try:
        config = json.loads((root / CONFIG).read_text())
        secret = Path(config['secret_file']).read_text().strip().encode()
        body = json.dumps(dict(kind='hook-guard-probe')).encode()
        signature = 'sha256=' + hmac.new(secret, body, hashlib.sha256).hexdigest()
        request = urllib.request.Request(config['hook_url'], data=body, method='POST', headers={
            'Content-Type': 'application/json', config['signature_header']: signature, config['event_header']: EVENT})
    except Exception as error:
        return 'config', type(error).__name__
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return ('ok', None) if response.status == 200 else ('failed', response.status)
    except urllib.error.HTTPError as error:
        return ('refused', 401) if error.code == 401 else ('failed', error.code)
    except Exception as error:
        return 'failed', type(error).__name__


def describe(kind, detail):
    if kind == 'refused':
        return 'the dead-man webhook refuses our signature (HTTP 401): its secret changed and our secret file is stale'
    if kind == 'config':
        return f'the dead-man webhook config or secret file cannot be read ({detail})'
    return f'the dead-man webhook does not answer as expected ({detail})'


def safely(call, *args):
    """A message to the lead must never block the page or the state write."""
    try:
        call(*args)
    except Exception:
        pass


def run(check, page, resolve, root=None, now=None, dry_run=False, tell=None):
    """One pass. check() -> (kind, detail); page(title, body) and resolve() talk to the pager and may raise.
    tell(text) sends the lead one message; it is called on the first page of a problem and on recovery."""
    root = Path(root or ROOT)
    now = (now or datetime.now(timezone.utc)).isoformat(timespec='seconds')
    path = root / STATE
    try:
        state = json.loads(path.read_text()) if path.exists() else {}
        state = state if isinstance(state, dict) else {}
    except ValueError:
        state = {}  # an unreadable state file must not fail every pass in silence: start again
    state = dict(dict(failures=0, paged=False, last_ok=None, last_problem=None), **state)
    kind, detail = check()
    problem = None if kind == 'ok' else f'{kind}:{detail}'
    status = 'ok'
    title = None
    if problem is None:
        if state['paged'] and not dry_run:
            try:
                resolve()
                state['paged'] = False
                if tell:
                    safely(tell, 'BOS hook guard: the dead-man webhook accepts our alerts again (checked ' + now + '); its page is resolved.')
            except Exception as error:
                status = 'ok; resolve failed: ' + type(error).__name__
        state.update(failures=0, last_ok=now, last_problem=None)
    else:
        # Consecutive failed passes, whatever their detail: a flapping outage (a timeout, then a refused connection,
        # then a 502) is still an outage.
        state.update(failures=state['failures'] + 1, last_problem=problem)
        status = 'problem: ' + problem
        due = kind in ('refused', 'config') or state['failures'] >= CONSECUTIVE
        if due and not dry_run:
            title = f'BOS: the dead-man webhook is broken ({detail}); no BOS alert reaches the lead'
            body = f'{describe(kind, detail)}. Seen {state["failures"]} pass(es) in a row, last at {now}. {FIX}'
            try:
                # The same key updates the open page (a new problem text) and does not re-open an acked one.
                page(title, body)
                if tell and not state['paged']:
                    safely(tell, title + '. ' + body)
                state['paged'] = True
                status += '; paged'
            except Exception as error:
                # A page that is already open stays open (paged stays True), so a good probe still resolves it.
                status += '; page failed: ' + type(error).__name__
    if not dry_run:
        tmp = path.with_name(path.name + '.tmp')
        tmp.write_text(json.dumps(state, indent=1, sort_keys=True) + '\n')
        tmp.chmod(0o600)
        tmp.replace(path)
    return dict(status=status, failures=state['failures'], paged=state['paged'])


def office(route, data):
    """One POST to the local office with the app token. The office address is fixed: the token never leaves localhost."""
    token = os.environ.get('ISOMUX_APP_TOKEN')
    if not token:
        raise RuntimeError('no app token')
    request = urllib.request.Request(OFFICE + route, data=json.dumps(data).encode(), method='POST',
                                     headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status >= 300:
            raise RuntimeError(f'office HTTP {response.status}')


def lead_id(root=None):
    lead = json.loads((Path(root or ROOT) / LEAD_CONFIG).read_text()).get('lead')
    if not isinstance(lead, str) or not lead:
        raise RuntimeError('no lead in the office config')
    return lead


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--loop', action='store_true', help='one pass now, then one every hour')
    parser.add_argument('--dry-run', action='store_true', help='probe only: no page, no state write')
    args = parser.parse_args()
    while True:
        try:
            print(datetime.now(timezone.utc).isoformat(timespec='seconds'), json.dumps(run(
                probe, lambda title, body: office('/api/app/pager', dict(title=title, body=body, key=KEY)),
                lambda: office('/api/app/pager/resolve', dict(key=KEY)), dry_run=args.dry_run,
                tell=lambda text: office('/api/app/message', dict(targetAgentId=lead_id(), text=text)))), flush=True)
        except Exception as error:
            print('hook guard pass failed: ' + type(error).__name__, flush=True)
            if not args.loop:
                raise SystemExit(1)
        if not args.loop:
            return
        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()
