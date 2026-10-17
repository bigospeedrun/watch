#!/usr/bin/env python3
"""Create the Discord channel of each race that bigospeedrun.com lists (Nil rule 2026-10-16).

Every listed race has exactly one board and exactly one Discord channel. Each hour, the
systemd user timer bigospeedrun-race-channels.timer runs this script. It reads the site's
public race list (chat-knowledge.json) and the guild channels, and it creates each missing
race channel: a text channel in category Big O (problems) or Other bounds (Other bounds
rows), named by deadman.race_channel_name, with no permission overwrites, so it has the
permissions of its category.

It only creates. It never deletes or renames a channel, and never moves one to another
category. After it creates a channel, it sorts the race channels of that category in the
site's order (positions only). When a race category holds
a channel that no listed race explains (a renamed or removed race), it creates nothing, so
a rename never makes a second channel; the race-parity dead-man item alerts the lead, and
a person renames or deletes the channel. It creates at most MAX_CREATE channels in one run;
more missing channels mean a data or rule problem, so it creates none and the item alerts.

When a listed race has no board yet, it starts the board sync workflow of bigospeedrun/board
(scripts/sync-boards.ts), at most once every 2 h.

The bot token is read from the file named in .git/watch-office.json and never printed.
Output and .git/race-channels.json (read by the dead-man item race-channels) hold no secret.
"""
import argparse
import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import deadman as d

ROOT = Path(__file__).resolve().parent
STATE = '.git/race-channels.json'
MAX_CREATE = 3
DISPATCH_EVERY = timedelta(hours=2)
BOARD_SYNC = ['gh', 'workflow', 'run', 'sync-boards.yml', '-R', 'bigospeedrun/board']
CATEGORY_IDS = {name: category for category, name in d.RACE_CATEGORIES.items()}


class Discord:
    def __init__(self, root):
        config = json.loads((root / d.WATCH_OFFICE).read_text())
        self.guild = config['discord_guild']
        self.token_file = Path(config['discord_token_file'])

    def call(self, path, method='GET', body=None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request('https://discord.com/api/v10/' + path, data=data, method=method, headers={
            'Authorization': 'Bot ' + self.token_file.read_text().strip(),
            'User-Agent': 'DiscordBot (https://bigospeedrun.com, 1)', 'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())

    def channels(self):
        return [dict(id=c.get('id'), name=c.get('name'), type=c.get('type'), parent_id=c.get('parent_id'), position=c.get('position'))
                for c in self.call(f'guilds/{self.guild}/channels')]

    def order(self, ids):
        # One bulk position update: the given channels in this order, from the first position.
        self.call(f'guilds/{self.guild}/channels', 'PATCH', [dict(id=i, position=n) for n, i in ids])

    def create(self, name, category):
        # No permission_overwrites: the channel has the permissions of its category.
        made = self.call(f'guilds/{self.guild}/channels', 'POST', dict(name=name, type=0, parent_id=CATEGORY_IDS[category]))
        return dict(id=made.get('id'), name=made.get('name'))


def plan(races, channels):
    """Return (channels to create as (name, category, slug), reason when none may be created)."""
    have = {(d.RACE_CATEGORIES[c['parent_id']], c['name']) for c in channels
            if c.get('type') == 0 and c.get('parent_id') in d.RACE_CATEGORIES}
    expected = {(category, name): slug for slug, name, category in races}
    missing = [(name, category, slug) for (category, name), slug in expected.items() if (category, name) not in have]
    extra = sorted(have - set(expected))
    if not missing:
        return [], None
    if extra:
        return [], 'a race category has a channel with no listed race (' + ', '.join('#' + n for _, n in extra[:5]) + '); a person decides'
    if len(missing) > MAX_CREATE:
        return [], f'{len(missing)} channels are missing, more than {MAX_CREATE}; a person checks the race list and the name rule'
    return missing, None


def site_order(races, channels, category):
    """[(position, id)] for the race channels of one category, in the site's order, from the
    category's lowest current position."""
    ids = {c['name']: c for c in channels if c.get('type') == 0 and d.RACE_CATEGORIES.get(c.get('parent_id')) == category}
    ordered = [ids[name] for _, name, cat in races if cat == category and name in ids]
    positions = [c['position'] for c in ordered if isinstance(c.get('position'), int)]
    base = min(positions) if positions else 0
    return [(base + n, c['id']) for n, c in enumerate(ordered)]


def run(root, discord, site_races, board_slugs, dispatch, now=None, dry_run=False):
    now = now or datetime.now(timezone.utc)
    state_path = root / STATE
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    races = site_races()
    report = dict(races=len(races), created=[], blocked=None, board_sync=None)
    missing, blocked = plan(races, discord.channels())
    report['blocked'] = blocked
    for name, category, slug in missing:
        if dry_run:
            report['created'].append(dict(name=name, category=category, slug=slug, dry_run=True))
            continue
        made = discord.create(name, category)
        report['created'].append(dict(name=made['name'], id=made['id'], category=category, slug=slug))
    for category in sorted({c['category'] for c in report['created'] if not c.get('dry_run')}):
        report['ordered'] = report.get('ordered', []) + [category]
        discord.order(site_order(races, discord.channels(), category))
    no_board = sorted({slug for slug, _, _ in races} - set(board_slugs()))
    if no_board:
        last = d.parse(state.get('board_sync_at'))
        if dry_run:
            report['board_sync'] = 'would start (no board for ' + ', '.join(no_board) + ')'
        elif not last or now - last >= DISPATCH_EVERY:
            dispatch()
            state['board_sync_at'] = now.isoformat(timespec='seconds')
            report['board_sync'] = 'started (no board for ' + ', '.join(no_board) + ')'
        else:
            report['board_sync'] = 'started recently (no board for ' + ', '.join(no_board) + ')'
    if not dry_run:
        state['last_ok'] = now.isoformat(timespec='seconds')
        state['last_report'] = report
        tmp = state_path.with_name(state_path.name + '.tmp')
        tmp.write_text(json.dumps(state, indent=2) + '\n')
        tmp.replace(state_path)
    return report


def dispatch_board_sync():
    out = subprocess.run(BOARD_SYNC, capture_output=True, text=True, timeout=60)
    if out.returncode:
        raise RuntimeError('board sync dispatch failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--dry-run', action='store_true', help='read only: print what it would create or start')
    args = parser.parse_args()
    sources = d.Sources(ROOT, persist=False)
    try:
        report = run(ROOT, Discord(ROOT), sources.site_races, sources.board_slugs, dispatch_board_sync, dry_run=args.dry_run)
    except Exception as error:
        # No traceback: it could quote fetched text. The race-channels item alerts when runs stop passing.
        print('race channels: failed: ' + d.safe_text(type(error).__name__ + ': ' + str(error), 300))
        sys.exit(1)
    print('race channels: ' + d.safe_text(json.dumps(report), 1500))


if __name__ == '__main__':
    main()
