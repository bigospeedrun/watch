#!/usr/bin/env python3
"""Read the private #chat-log channel and find chatbot answers that show doc gaps.

The site chat handler posts two webhook messages per exchange, with the same
random 6-hex tag (entries from before site d5229ee have no tag):
  [bigospeedrun.com] Visitor 3fa9c1:\n<question>\nIP: ..\nBrowser: ..\nPage: <path>
  [bigospeedrun.com] Bot 3fa9c1:\n<reply>
This script pairs them, drops IP, browser and other personal data, and writes
the ignored file chat-gaps.local.json. It never writes to Discord. Chat text
stays out of stdout and out of tracked files (this repository is public).
"""
import argparse
import json
import os
import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT=Path(__file__).resolve().parent
OUTPUT='chat-gaps.local.json'
STATE='chat-gaps-state.local.json'
CHANNEL='1559408355347533865'
GUILD='1558627054826692751'
TOKEN_FILE=Path.home()/'nil/bigospeedrun-notes/secrets/discord-bot-token'
HEADER=re.compile(r'\[bigospeedrun\.com\] (Visitor|Bot)(?: ([0-9a-f]{6}))?:\n')
MAX_CHARS=500
SAMPLE=5
PAGES=20
# The handler logs a reply only after the full answer streams, and it stops a
# request after 45 s. A reply pairs only with a question at most this old, and
# a question without a reply stays unread for this long.
GRACE=timedelta(minutes=5)
GAP_PHRASES=('not in the site facts','the site facts do not','the site facts don\'t','i have nothing on',
    'i don\'t have','i do not have','not a tracked problem','the site has nothing','the site does not track',
    'the site doesn\'t track','i don\'t know','i do not know','no information')

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

class Discord:
    """Read-only client: GET requests only."""
    def __init__(self,token_file=TOKEN_FILE):self.token=Path(token_file).read_text().strip()
    def request(self,path):
        request=Request('https://discord.com/api/v10/'+path,
            headers={'Authorization':'Bot '+self.token,'User-Agent':'BigOSpeedrunChatGaps/1.0'})
        with build_opener(NoRedirect).open(request,timeout=20) as response:
            raw=response.read(4_000_001)
            if len(raw)>4_000_000:raise ValueError('Discord response too large')
            return json.loads(raw)
    def check_channel(self):
        channel=self.request('channels/'+CHANNEL)
        if channel.get('guild_id')!=GUILD or channel.get('type')!=0:raise ValueError('Unexpected channel')
    def messages(self,after):return self.request('channels/'+CHANNEL+'/messages?limit=100&after='+after)

SCRUB=[
    (re.compile(r'<@[!&]?\d+>'),'[mention]'),
    (re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+'),'[email]'),
    (re.compile(r'(https?://[^\s?#<>]+)[?#][^\s<>]*?(?=[.,;:!?)\]]*(?:\s|$))'),r'\1'),
    (re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),'[ip]'),
    (re.compile(r'\b(?:[0-9A-Fa-f]{1,4}:){3,7}[0-9A-Fa-f]{1,4}\b|\b[0-9A-Fa-f]{1,4}(?::[0-9A-Fa-f]{1,4})*::(?:[0-9A-Fa-f]{1,4}(?::[0-9A-Fa-f]{1,4})*)?\b'),'[ip]'),
    (re.compile(r'\+\d[\d ().-]{7,}\d|\(?\b\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b'),'[phone]'),
]

def clean(text):
    """Remove personal data patterns, then cut to MAX_CHARS."""
    for pattern,replacement in SCRUB:text=pattern.sub(replacement,text)
    text=text.strip()
    return text if len(text)<=MAX_CHARS else text[:MAX_CHARS-1]+'…'

def parse(message):
    """Return (kind, tag, text, page) for a chat-log message, or None for other messages."""
    header=HEADER.match(message.get('content') or '')
    if not header:return None
    kind,tag=header.group(1).lower(),header.group(2)
    body=message['content'][header.end():]
    if kind=='visitor':
        # The handler appends these lines after the question. Cut at the last
        # IP line, so a cut-off tail never leaks into the question. A question
        # that itself holds '\nIP: ' loses its end; that is the safe side.
        cut=body.rfind('\nIP: ')
        tail=re.search(r'\nPage: (/[A-Za-z0-9/_-]*)$',body[cut:]) if cut>=0 else None
        return kind,tag,body[:cut] if cut>=0 else body,tail.group(1) if tail else None
    return kind,tag,body,None

def gap_reasons(answer):
    text=answer.lower().replace('’',"'")
    return [p for p in GAP_PHRASES if p in text]

def stamp(message):
    return datetime.fromisoformat(message['timestamp'].replace('Z','+00:00')).astimezone(timezone.utc)

def load(path,default):return json.loads(path.read_text()) if path.exists() else default

def save(path,value):
    temp=path.with_name(path.name+'.tmp')
    with temp.open('w') as f:
        os.chmod(temp,0o600)
        json.dump(value,f,indent=2,ensure_ascii=False);f.write('\n')
    os.replace(temp,path)

def run(api,root=ROOT,dry_run=False,now=None,rng=None,sample=SAMPLE):
    now=now or datetime.now(timezone.utc);rng=rng or random.Random()
    state=load(root/STATE,{'last_seen':'0','consumed':[]})
    consumed=set(state['consumed'])
    api.check_channel()
    rows=[];after=state['last_seen'];status='ok'
    for _ in range(PAGES):
        batch=api.messages(after)
        if not batch:break
        # An empty webhook message means Message Content is not visible. Fail
        # closed: write nothing and keep the cursor.
        if any(m.get('webhook_id') and not m.get('content') and not m.get('embeds') for m in batch):
            return {'status':'content unavailable','messages':0,'pairs':0,'flagged':0}
        batch=sorted(batch,key=lambda m:int(m['id']))
        if any(not re.fullmatch(r'[0-9]+',m['id']) or int(m['id'])<=int(after) for m in batch):
            raise ValueError('Invalid message order')
        rows+=batch;after=batch[-1]['id']
        if len(batch)<100:break
    else:status='partial: page budget reached'
    pairs=[];pending=[];stats=dict(messages=len(rows),ambiguous=0,unanswered=0,orphan_replies=0)
    for message in rows:
        if message['id'] in consumed:continue
        parsed=parse(message)
        if not parsed:continue
        kind,tag,text,page=parsed
        if kind=='visitor':pending.append((message,tag,text,page));continue
        while pending and stamp(message)-stamp(pending[0][0])>GRACE:
            stats['unanswered']+=1;consumed.add(pending.pop(0)[0]['id'])
        # Pair with the oldest open question that has the same tag. Old
        # untagged entries pair oldest-first; mark the pair when two untagged
        # exchanges overlapped.
        match=[i for i,p in enumerate(pending) if p[1]==tag]
        if not match:stats['orphan_replies']+=1;consumed.add(message['id']);continue
        ambiguous=tag is None and len(match)>1
        if ambiguous:stats['ambiguous']+=1
        question,_,qtext,page=pending.pop(match[0])
        consumed.update((question['id'],message['id']))
        pairs.append(dict(time=stamp(question).strftime('%Y-%m-%dT%H:%MZ'),page=page or 'unknown',
            question=clean(qtext),answer=clean(text),ambiguous_pairing=ambiguous or None))
    held=[]
    for question,*_ in pending:
        if now-stamp(question)<GRACE:held.append(question)
        else:stats['unanswered']+=1;consumed.add(question['id'])
    # Reread from the oldest held question next time; skip what was used.
    cursor=str(int(held[0]['id'])-1) if held else after
    consumed={i for i in consumed if int(i)>int(cursor)}
    flagged=[];rest=[]
    for pair in pairs:
        if pair['ambiguous_pairing'] is None:del pair['ambiguous_pairing']
        reasons=gap_reasons(pair['answer'])
        (flagged if reasons else rest).append(dict(pair,matched=reasons) if reasons else pair)
    report=dict(generated=now.strftime('%Y-%m-%dT%H:%MZ'),status=status,
        counts=dict(stats,pairs=len(pairs),flagged=len(flagged),held=len(held),sampled=min(sample,len(rest))),
        flagged=flagged,sample=sorted(rng.sample(rest,min(sample,len(rest))),key=lambda p:p['time']))
    if not dry_run:
        # Save the report before the cursor, so a crash rereads, not loses.
        save(root/OUTPUT,report)
        save(root/STATE,{'last_seen':cursor,'consumed':sorted(consumed,key=int)})
    return dict(status=status,**report['counts'])

def main():
    parser=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--dry-run',action='store_true',help='read Discord, write no file')
    parser.add_argument('--sample',type=int,default=SAMPLE,help='unflagged pairs to include')
    args=parser.parse_args()
    try:print(json.dumps(run(Discord(),dry_run=args.dry_run,sample=args.sample)))
    except Exception as error:
        # Exception text can hold response or request data. Never print it.
        print('Chat gaps failed: '+type(error).__name__)
        raise SystemExit(1)

if __name__=='__main__':main()
