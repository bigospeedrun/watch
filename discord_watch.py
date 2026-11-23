#!/usr/bin/env python3
"""Data-only Discord intake. Message bodies never leave process memory."""
import argparse
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, quote
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT=Path(__file__).resolve().parent
PUBLIC='discord-submissions.json'
PRIVATE='discord-submissions.local.json'
RETRY_DELAY=3 # seconds before the one retry of a request that failed in transport
MAX_LINKS=10 # message links per repository paragraph of the Lead alert

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def github_urls(content,include_own=False):
    urls=set()
    for token in re.findall(r'https?://[^\s<>"\x00-\x20]+',content):
        token=token.rstrip('.,;:!?)]}')
        try:
            u=urlsplit(token)
            if u.scheme!='https' or u.netloc!='github.com' or u.username or u.password:continue
            parts=u.path.strip('/').split('/')
            if len(parts)<2 or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})',parts[0]):continue
            if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',parts[1]) or parts[1] in ('.','..'):continue
            if parts[0].lower()=='bigospeedrun' and not include_own:continue
            tail=parts[2:]
            if tail:
                if tail[0]=='pull':
                    if len(tail)!=2 or not re.fullmatch(r'[1-9][0-9]*',tail[1]):continue
                elif tail[0]=='commit':
                    if len(tail)!=2 or not re.fullmatch(r'[0-9a-fA-F]{7,40}',tail[1]):continue
                elif tail[0]=='issues':
                    # An issue link counts only for our own organization (the lead answers those).
                    if not(include_own and parts[0].lower()=='bigospeedrun') or len(tail)!=2 or not re.fullmatch(r'[1-9][0-9]*',tail[1]):continue
                elif tail[0] in ('tree','blob'):
                    if len(tail)<2 or (tail[0]=='blob' and len(tail)<3):continue
                    if any(not re.fullmatch(r'[A-Za-z0-9_.-]+',p) or p in ('.','..') for p in tail[1:]):continue
                else:continue
            urls.add('https://github.com/'+'/'.join(parts))
        except ValueError:continue
    return sorted(urls)

def own_url(url):return url.split('/')[3].lower()=='bigospeedrun'

def excluded_message(message):
    return bool(message.get('author',{}).get('bot') or message.get('webhook_id'))

def repo_url(url):return '/'.join(url.split('/')[:5])

def save(path,value):
    temp=path.with_name(path.name+'.tmp')
    with temp.open('w') as f:
        os.chmod(temp,0o600)
        json.dump(value,f,indent=2,ensure_ascii=False);f.write('\n')
    os.replace(temp,path)

def load(path,default):return json.loads(path.read_text()) if path.exists() else default

class Discord:
    def __init__(self,config):
        self.channel=config['discord_channel'];self.guild=config['discord_guild']
        self.token=Path(config['discord_token_file']).read_text().strip()
    def request(self,path,method='GET'):
        request=Request('https://discord.com/api/v10/'+path,method=method,
            headers={'Authorization':'Bot '+self.token,'User-Agent':'BigOSpeedrunWatch/1.0'})
        # One retry after a transport failure (2026-11-23 08:05Z: one URLError stopped the intake for a
        # cycle). An HTTP status is an answer from Discord, so it is not retried. Every request here is a
        # GET or the idempotent PUT of the bot's own reaction, so a second attempt is safe.
        for attempt in (1,2):
            try:
                with build_opener(NoRedirect).open(request,timeout=20) as response:
                    raw=response.read(4_000_001)
                    if len(raw)>4_000_000:raise ValueError('Discord response too large')
                    return json.loads(raw) if raw else None
            except HTTPError:raise
            except URLError:
                if attempt==2:raise
                time.sleep(RETRY_DELAY)
    def check_channel(self):
        channel=self.request('channels/'+self.channel)
        if channel.get('guild_id')!=self.guild or channel.get('type')!=0:raise ValueError('Unexpected channel')
    def messages(self,after):
        return self.request('channels/'+self.channel+'/messages?limit=100&after='+after)
    def react(self,message):
        self.request('channels/'+self.channel+'/messages/'+message+'/reactions/'+quote('👀',safe='')+'/@me','PUT')

def message_link(api,mid):return f'https://discord.com/channels/{api.guild}/{api.channel}/{mid}'

def alert_text(api,public,pending,own):
    """One Lead alert for all pending messages of a cycle (Lead GO, 2026-11-23: four messages linking one
    repository gave four alerts). Each repository is one paragraph with the links to its new messages. A repository
    already in the public list from an earlier message is marked "known" and stays in the alert: a new message
    can be a new claim on it (the four floration messages were four claims)."""
    ids={mid for mid,_ in pending}
    known={r for row in public['submissions'] if row['message_id'] not in ids for r in row['repo_urls']}
    repos={}
    for mid,record in pending:
        for repo in sorted({repo_url(u) for u in record['urls']}):repos.setdefault(repo,[]).append(mid)
    owns={}
    for mid,record in own:
        for url in record['own_urls']:owns.setdefault(url,[]).append(mid)
    def links(mids):
        # The webhook path sends at most 4 parts of 1700 characters (poll.lead_notify); keep each paragraph short.
        more=f' and {len(mids)-MAX_LINKS} more' if len(mids)>MAX_LINKS else ''
        return ' '.join(message_link(api,m) for m in mids[:MAX_LINKS])+more
    def count(mids):return '1 new message' if len(mids)==1 else f'{len(mids)} new messages'
    stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
    total=len(ids|{mid for mid,_ in own})
    lines=[f'{stamp}: Discord #submit-a-result: {total} new message{"" if total==1 else "s"} with GitHub links.']
    if repos:lines.append('Possible new bound race or problem pivot; README signals need review.')
    for repo,mids in repos.items():
        kind='Known repo, already flagged' if repo in known else 'New repo'
        lines.append(f'{kind}: {repo} (Discord submission). {count(mids)}: {links(mids)}')
    for url,mids in owns.items():
        lines.append(f'Link to our own repository; read it and answer: {url} (Discord submission). {count(mids)}: {links(mids)}')
    return '\n\n'.join(lines)

def flush(api,notify,root,state,public):
    """Send the one alert for every pending record, and then react to each alerted message. The records and
    the cursor are saved before this step, so a failed delivery or reaction is retried on the next run."""
    rows=sorted(state['messages'].items(),key=lambda x:int(x[0]))
    pending=[(mid,r) for mid,r in rows if r.get('urls') and not r.get('alerted')]
    own=[(mid,r) for mid,r in rows if r.get('own_urls') and not r.get('own_alerted')]
    if pending or own:
        ids=','.join(sorted({mid for mid,_ in pending+own},key=int))
        notify(alert_text(api,public,pending,own),'discord-intake-'+hashlib.sha256(ids.encode()).hexdigest()[:16])
        for _,record in pending:record['alerted']=True
        for _,record in own:record['own_alerted']=True
        save(root/PRIVATE,state)
    for mid,record in rows:
        # Records from before 2026-11-23 have no 'reacted' key; their reaction was done before the cursor moved.
        # Every record is alerted at this point: a failed notify() above raises before this loop.
        if record.get('reacted',True) is False:
            api.react(mid) # PUT @me is idempotent if a prior attempt was interrupted.
            record['reacted']=True;save(root/PRIVATE,state)

def run(api,notify,root=None,dry_run=False):
    # Resolve ROOT at call time; a default bound at definition time ignores a
    # patched ROOT and made a test read the live cursor (2026-10-14 cycle stop).
    root=root or ROOT
    state=load(root/PRIVATE,{'last_seen':'0','messages':{},'content_alerted':False})
    public=load(root/PUBLIC,{'submissions':[]})
    api.check_channel()
    cursor=state['last_seen'];count=0;hits=0;status='ok'
    for _ in range(20):
        batch=api.messages(cursor)
        if not batch:break
        # An empty ordinary message may be intent-redacted. Fail closed for the
        # complete page; do not acknowledge or move past any hidden content.
        if any(not excluded_message(m) and m.get('type',0) in (0,19) and not m.get('content') and
               not m.get('attachments') and not m.get('embeds') for m in batch):
            if not dry_run and not state['content_alerted']:
                notify('Discord submission watch: content unavailable; enable Message Content intent. Cursor unchanged.', 'discord-content-unavailable')
                state['content_alerted']=True;save(root/PRIVATE,state)
            status='content unavailable';break
        for message in sorted(batch,key=lambda m:int(m['id'])):
            mid=message['id']
            if not re.fullmatch(r'[0-9]+',mid) or int(mid)<=int(cursor):raise ValueError('Invalid message order')
            found=[] if excluded_message(message) else github_urls(message.get('content',''),include_own=True);count+=1
            # Links to our own organization are not new races: they alert the lead (Lead, 2026-10-21: no silent
            # pass for a PR link such as bigospeedrun/verifier/pull/27) but stay out of the public repo list.
            urls=[u for u in found if not own_url(u)];own=[u for u in found if own_url(u)]
            if (urls or own) and not dry_run:
                record=state['messages'].setdefault(mid,dict(author_id=message['author']['id'],
                    username=message['author']['username'],urls=urls,alerted=False,reacted=False))
                if own:record['own_urls']=own;record.setdefault('own_alerted',False)
                if urls and not any(r['message_id']==mid for r in public['submissions']):
                    # Persist sanitized evidence before any acknowledgement.
                    public['submissions'].append(dict(message_id=mid,repo_urls=sorted({repo_url(u) for u in urls})))
                    save(root/PUBLIC,public)
            if urls or own:hits+=1
            cursor=mid
            if not dry_run:
                # The record and the cursor are saved together; flush() alerts for the record later in this run.
                state['last_seen']=cursor;save(root/PRIVATE,state)
        if len(batch)<100:break
    else:status='partial: page budget reached'
    if not dry_run:flush(api,notify,root,state,public)
    return {'status':status,'messages':count,'hits':hits}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    config=load(ROOT/'.git/watch-office.json',{})
    def notify(text,identity):
        from poll import lead_notify
        lead_notify(text,identity,'discord-intake')
    try:print(json.dumps(run(Discord(config),notify,dry_run=args.dry_run)))
    except Exception as error:
        # Exceptions can contain response/request data. Never print their text.
        print('Discord watch failed: '+type(error).__name__)
        raise SystemExit(1)

if __name__=='__main__':main()
