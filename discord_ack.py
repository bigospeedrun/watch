#!/usr/bin/env python3
"""Acknowledge every new human message in #submit-a-result with an eyes reaction, within a minute.

Runs from the systemd user timer bigospeedrun-discord-ack.timer (every minute). Nil, 2026-10-21: "We
should acknowledge messages quickly." Before this, discord_watch.py reacted only to messages with an
accepted GitHub link, and only inside the watch cycle.

This reader sends only PUT reactions (the bot's own, idempotent) and GET reads. It never reads the text
of a message into its state: the state file holds the cursor, the ids of messages whose reaction failed
and the time of the last good pass. A message whose reaction keeps failing for 15 minutes alerts BOS Lead
Dev once through the signed Isomux webhook; the dead-man item discord-ack (deadman.py) alerts when this
reader has not passed for 15 minutes.
"""
import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

import discord_watch as dw

ROOT = Path(__file__).resolve().parent
STATE = 'discord-ack.local.json'
ALERT_AFTER = timedelta(minutes=15)
PAGES = 5
HUMAN_TYPES = (0, 19)  # a message and a reply


def human(message):
    return not dw.excluded_message(message) and message.get('type', 0) in HUMAN_TYPES


def parse_stamp(stamp):
    return datetime.fromisoformat(stamp)


def react(api, mid, sleep):
    """Add the eyes reaction. Return None when done (a deleted message needs none), else a short reason."""
    for attempt in range(2):
        try:
            api.react(mid)
            return None
        except HTTPError as error:
            if error.code == 404:
                return None
            if error.code == 429 and attempt == 0:
                try:
                    wait = float(error.headers.get('Retry-After', '1'))
                except (TypeError, ValueError):
                    wait = 1.0
                sleep(min(max(wait, 0.0), 5.0) + 0.2)
                continue
            return f'HTTP {error.code}'
        except (URLError, OSError, ValueError) as error:
            return type(error).__name__
    return 'HTTP 429'


def run(api, notify, root=None, dry_run=False, now=None, sleep=time.sleep):
    # Resolve ROOT at call time (a default bound at definition time ignores a patched ROOT).
    root = root or ROOT
    now = now or datetime.now(timezone.utc)
    state = dw.load(root / STATE, None)
    api.check_channel()
    fresh = state is None
    if fresh:
        # A first run starts at the newest message: older ones are not this reader's job.
        newest = api.request('channels/' + api.channel + '/messages?limit=1') or []
        state = dict(last_seen=newest[0]['id'] if newest else '0', pending={}, alerted=[], last_ok=None)
    reacted = 0
    # Retry reactions that failed before.
    for mid in sorted(state['pending'], key=int):
        if dry_run:
            continue
        if react(api, mid, sleep) is None:
            del state['pending'][mid]
            reacted += 1
    cursor = state['last_seen']
    for _ in range(PAGES):
        batch = api.messages(cursor)
        if not batch:
            break
        batch = sorted(batch, key=lambda m: int(m['id']))
        if any(not m['id'].isdigit() or int(m['id']) <= int(cursor) for m in batch):
            raise ValueError('Invalid message order')
        for message in batch:
            mid = message['id']
            if human(message) and not dry_run:
                reason = react(api, mid, sleep)
                if reason is None:
                    reacted += 1
                else:
                    state['pending'].setdefault(mid, now.isoformat(timespec='seconds'))
                sleep(0.3)  # Discord spaces reactions on one channel by about 250 ms.
            cursor = mid
            if not dry_run:
                state['last_seen'] = cursor
        if len(batch) < 100:
            break
    # A reaction that keeps failing is a missed acknowledgement: tell the lead once per message.
    late = [mid for mid, first in state['pending'].items()
            if now - parse_stamp(first) >= ALERT_AFTER and mid not in state['alerted']]
    if late and not dry_run:
        notify('Discord #submit-a-result: ' + str(len(late)) + ' message(s) still without the eyes reaction after 15 min '
               '(the reaction request fails). Message ids: ' + ', '.join(late[:10]) + '. Check the bot permissions and '
               'journalctl --user -u bigospeedrun-discord-ack.service.', 'discord-ack-' + late[0] + '-' + str(len(late)))
        state['alerted'] = sorted(set(state['alerted']) | set(late), key=int)
    state['alerted'] = [mid for mid in state['alerted'] if mid in state['pending']]
    if not dry_run:
        state['last_ok'] = now.isoformat(timespec='seconds')
        dw.save(root / STATE, state)
    return dict(status='ok', reacted=reacted, pending=len(state['pending']), first_run=fresh)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--dry-run', action='store_true', help='read Discord; react and write nothing')
    args = parser.parse_args()
    config = dw.load(ROOT / '.git/watch-office.json', {})

    def notify(text, identity):
        from deadman import webhook_send
        webhook_send(ROOT, 'digest')(dict(kind='bos-digest', channel='submit-a-result', text=text))

    try:
        print(json.dumps(run(dw.Discord(config), notify, dry_run=args.dry_run)))
    except Exception as error:
        # Exception text can hold response data. Never print it.
        print('Discord acknowledgement failed: ' + type(error).__name__)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
