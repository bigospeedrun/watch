#!/usr/bin/env python3
"""Data-only Discord intake. Message bodies never leave process memory."""
import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT=Path(__file__).resolve().parent
PUBLIC='discord-submissions.json'
PRIVATE='discord-submissions.local.json'

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def github_urls(content):
    urls=set()
    for token in re.findall(r'https?://[^\s<>"\x00-\x20]+',content):
        token=token.rstrip('.,;:!?)]}')
        try:
            u=urlsplit(token)
            if u.scheme!='https' or u.netloc!='github.com' or u.username or u.password:continue
            parts=u.path.strip('/').split('/')
            if len(parts)<2 or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})',parts[0]):continue
            if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',parts[1]) or parts[1] in ('.','..'):continue
            if parts[0].lower()=='bigospeedrun':continue
            tail=parts[2:]
            if tail:
                if tail[0]=='pull':
                    if len(tail)!=2 or not re.fullmatch(r'[1-9][0-9]*',tail[1]):continue
                elif tail[0]=='commit':
                    if len(tail)!=2 or not re.fullmatch(r'[0-9a-fA-F]{7,40}',tail[1]):continue
                elif tail[0] in ('tree','blob'):
                    if len(tail)<2 or (tail[0]=='blob' and len(tail)<3):continue
                    if any(not re.fullmatch(r'[A-Za-z0-9_.-]+',p) or p in ('.','..') for p in tail[1:]):continue
                else:continue
            urls.add('https://github.com/'+'/'.join(parts))
        except ValueError:continue
    return sorted(urls)

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
        with build_opener(NoRedirect).open(request,timeout=20) as response:
            raw=response.read(4_000_001)
            if len(raw)>4_000_000:raise ValueError('Discord response too large')
            return json.loads(raw) if raw else None
    def check_channel(self):
        channel=self.request('channels/'+self.channel)
        if channel.get('guild_id')!=self.guild or channel.get('type')!=0:raise ValueError('Unexpected channel')
    def messages(self,after):
        return self.request('channels/'+self.channel+'/messages?limit=100&after='+after)
    def react(self,message):
        self.request('channels/'+self.channel+'/messages/'+message+'/reactions/'+quote('👀',safe='')+'/@me','PUT')

def run(api,notify,root=None,dry_run=False):
    # Resolve ROOT at call time; a default bound at definition time ignores a
    # patched ROOT and made a test read the live cursor (2026-10-14 cycle stop).
    root=root or ROOT
    state=load(root/PRIVATE,{'last_seen':'0','messages':{},'content_alerted':False})
    public=load(root/PUBLIC,{'submissions':[]})
    api.check_channel()
    cursor=state['last_seen'];count=0;hits=0
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
            return {'status':'content unavailable','messages':count,'hits':hits}
        for message in sorted(batch,key=lambda m:int(m['id'])):
            mid=message['id']
            if not re.fullmatch(r'[0-9]+',mid) or int(mid)<=int(cursor):raise ValueError('Invalid message order')
            urls=[] if excluded_message(message) else github_urls(message.get('content',''));count+=1
            if urls:
                hits+=1
                if not dry_run:
                    repos=sorted({repo_url(u) for u in urls})
                    record=state['messages'].setdefault(mid,dict(author_id=message['author']['id'],
                        username=message['author']['username'],urls=urls,alerted=False))
                    # Persist sanitized evidence before any acknowledgement.
                    if not any(r['message_id']==mid for r in public['submissions']):
                        public['submissions'].append(dict(message_id=mid,repo_urls=repos))
                    save(root/PUBLIC,public);save(root/PRIVATE,state)
                    if not record['alerted']:
                        stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
                        notify(stamp+': Possible new bound race or problem pivot; README signals need review: '+
                               '; '.join(u+' (Discord submission)' for u in repos),'discord-submission-'+mid)
                        record['alerted']=True;save(root/PRIVATE,state)
                    api.react(mid) # PUT @me is idempotent if a prior attempt was interrupted.
            cursor=mid
            if not dry_run:
                state['last_seen']=cursor;save(root/PRIVATE,state)
        if len(batch)<100:break
    else:return {'status':'partial: page budget reached','messages':count,'hits':hits}
    return {'status':'ok','messages':count,'hits':hits}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    config=load(ROOT/'.git/watch-office.json',{})
    def notify(text,identity):
        from poll import office,LEAD
        result=office(f'/api/agents/{LEAD}/messages',{'text':text,'clientMessageId':identity})
        if not result.get('messageId'):raise RuntimeError('Alert delivery unconfirmed')
    try:print(json.dumps(run(Discord(config),notify,dry_run=args.dry_run)))
    except Exception as error:
        # Exceptions can contain response/request data. Never print their text.
        print('Discord watch failed: '+type(error).__name__)
        raise SystemExit(1)

if __name__=='__main__':main()
