#!/usr/bin/env python3
"""Read offered X profiles through office browser text actions. Never interact."""
import hashlib, json, re, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from github_read import api, content
from poll import office, SELF, LEAD
from refresh import git_state_dir
ROOT=Path(__file__).resolve().parent
TERMS=re.compile(r'\bbounds?\b|\bkappa\b|κ|\bexponent\b|github\.com/',re.I)
MATH=re.compile(r'\bbounds?\b|\bkappa\b|κ|\bexponent\b|power saving|\b3sum\b|\bDFT\b|matrix.multiplication|Walsh.Hadamard',re.I)
WALL=re.compile(r'log in to x|sign in to x|sign in to twitter|verify (?:that )?you are human|captcha|unusual activity|authenticate your account',re.I)

def save(path,data):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n');temp.chmod(0o600);temp.replace(path)

def browser(action,**params):
    assert action in ('tabs','goto','text'), 'Disallowed browser action'
    return office(f'/api/agents/{SELF}/browser',{'action':action,**params})

def profile_text(target,account,selector=None):
    result=browser('text',target=target,**({'selector':selector} if selector else {}))
    parsed=urllib.parse.urlsplit(result.get('url',''))
    if parsed.hostname not in ('x.com','www.x.com','twitter.com','www.twitter.com') or parsed.path.strip('/').lower()!=account.lower():
        raise ValueError('Profile navigation changed during text read')
    return result.get('text','')

def visible_links(text):
    links=[]
    for match in re.finditer(r'(?:https?://)?(?:www\.)?(?:github\.com|arxiv\.org)/[^\s<>]+|https?://[^\s<>]+\.pdf(?:\?[^\s<>]*)?',text,re.I):
        raw=match[0].rstrip('.,);]')
        if '…' in raw or '...' in raw:continue
        if not raw.startswith(('http://','https://')):raw='https://'+raw
        p=urllib.parse.urlsplit(raw)
        if p.username or p.password:continue
        url=urllib.parse.urlunsplit(('https',p.netloc,p.path,'',''))
        if url not in links:links.append(url)
    return links

def post_time(text,now):
    # Keep the displayed time. A relative display has a range, not an exact time.
    found=re.search(r'(?m)^\s*(\d{1,3})([smhd])\s*$',text)
    if found:
        n=int(found[1]);unit={'s':1,'m':60,'h':3600,'d':86400}[found[2]]
        return found[0].strip(),now-timedelta(seconds=(n+1)*unit),now-timedelta(seconds=n*unit)
    found=re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}(?:, \d{4})?',text)
    if found:
        raw=found[0];year=now.year if ',' not in raw else int(raw[-4:])
        date=datetime.strptime(raw.split(',')[0]+' '+str(year),'%b %d %Y').replace(tzinfo=timezone.utc)
        if date>now+timedelta(days=1):date=date.replace(year=year-1)
        return raw,date,date+timedelta(days=1)
    return None,None,None

def check_source(url,known_sources):
    """Check allowlisted public source data; never evaluate downloaded content."""
    parsed=urllib.parse.urlsplit(url);host=parsed.hostname;parts=parsed.path.strip('/').split('/')
    if host in ('github.com','www.github.com') and len(parts)>=2 and all(re.fullmatch(r'[\w.-]+',p) for p in parts[:2]):
        repo='/'.join(parts[:2]);key='github:'+repo.lower()
        if len(parts)>=4 and parts[2]=='pull' and parts[3].isdigit():
            pr=api(f'repos/{repo}/pulls/{parts[3]}');text=pr['title']+'\n'+(pr.get('body') or '');revision=pr['updated_at'];key+=':pr:'+parts[3]
            observed=json.loads((ROOT/'submissions.json').read_text())['items'] if repo.lower()=='crocswap/integer-mult-bounds' else []
            previous=next((p['updated_at'] for p in observed if p['pr_number']==int(parts[3])),known_sources.get(key))
            return dict(url=pr['html_url'],key=key,revision=revision,actionable=bool(MATH.search(text)) and revision!=previous,kind='new or changed PR source',title=pr['title'])
        meta=api(f'repos/{repo}');head=api(f'repos/{repo}/commits/{meta["default_branch"]}');raw=content(repo,'README.md',head['sha']);text=raw.decode('utf-8',errors='replace');revision=hashlib.sha256(raw).hexdigest()
        local=ROOT/('sources/'+repo.replace('/','__')+'__README.md')
        previous=hashlib.sha256(local.read_bytes()).hexdigest() if local.exists() else known_sources.get(key)
        for item in json.loads((ROOT/'registry.json').read_text())['problems']:
            problem=json.loads((ROOT/item['data_file']).read_text())
            if any(r.get('source_commit')==head['sha'] and r.get('source',{}).get('url','').startswith('https://github.com/'+repo+'/') for r in problem['records']):previous=revision
        return dict(url=meta['html_url'],key=key,revision=revision,head=head['sha'],actionable=bool(MATH.search((meta.get('description') or '')+'\n'+text)) and revision!=previous,kind='new or changed research source; compare pinned README',title=meta.get('description') or repo)
    if host in ('arxiv.org','www.arxiv.org'):
        identifier=parsed.path.removeprefix('/abs/').removeprefix('/pdf/').removesuffix('.pdf')
        if not re.fullmatch(r'(?:\d{4}\.\d{4,5}|[a-z-]+/\d{7})(?:v\d+)?',identifier):return dict(url=url,actionable=False,reason='Unrecognized arXiv identifier')
        endpoint='https://export.arxiv.org/api/query?'+urllib.parse.urlencode({'id_list':identifier})
        with urllib.request.urlopen(endpoint,timeout=30) as response:raw=response.read(200000)
        import xml.etree.ElementTree as ET
        entry=ET.fromstring(raw).find('{http://www.w3.org/2005/Atom}entry')
        if entry is None:return dict(url=url,actionable=False,reason='No arXiv entry')
        def value(name):return entry.findtext('{http://www.w3.org/2005/Atom}'+name,'')
        title=value('title');abstract=value('summary');revision=value('updated');key='arxiv:'+identifier
        return dict(url='https://arxiv.org/abs/'+identifier,key=key,revision=revision,title=title,actionable=bool(MATH.search(title+' '+abstract)) and revision!=known_sources.get(key),kind='paper source located; full statement review needed')
    return dict(url=url,actionable=False,reason='PDF source needs agent review; no automatic fetch from unapproved hosts')

def run():
    now=datetime.now(timezone.utc);stamp=now.isoformat(timespec='seconds').replace('+00:00','Z');state_dir=git_state_dir()
    state_path=state_dir/'x-watch-state.json';report_path=state_dir/'x-watch-report.json';journal=state_dir/'x-watch-restore.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else {'accounts':{},'sources':{},'wall_notified':False}
    config=json.loads((ROOT/'x-watchlist.local.json').read_text());report=dict(checked_at=stamp,status='starting',posts=[],actionable_leads=[],coverage=['Only rendered posts and visible complete URLs can be read. Hidden link targets, exact hidden timestamps, and unloaded posts are unavailable to text-only reads. Relative dates are saved as ranges.'])
    target=None;original=None;navigation_started=False
    pending=list(state.get('pending_leads',[]))
    source_updates={}
    try:
        offered=browser('tabs');tabs=offered.get('tabs',[])
        if not tabs:
            report['status']='skipped-no-offered-tab';return report
        # Resume a saved restoration before any new navigation after a crash.
        if journal.exists():
            saved=json.loads(journal.read_text())
            if any(t['target']==saved['target'] for t in tabs):
                browser('goto',target=saved['target'],url=saved['url']);journal.unlink()
            else:
                report['status']='skipped-unrestored-tab-unavailable';return report
        chosen=next((t for t in tabs if t.get('scope')!='all'),tabs[0]);target=chosen['target']
        initial=browser('text',target=target);original=initial['url']
        parsed=urllib.parse.urlsplit(original)
        if parsed.scheme not in ('http','https') or parsed.username or parsed.password:
            report['status']='skipped-original-url-not-restorable';return report
        save(journal,{'target':target,'url':original})
        for account in config['accounts']:
            assert re.fullmatch(r'[A-Za-z0-9_]{1,15}',account)
            navigation_started=True;browser('goto',target=target,url='https://x.com/'+account)
            page=browser('text',target=target);body=page.get('text','')
            if WALL.search(body) or '/i/flow/login' in page.get('url',''):
                report['status']='stopped-login-or-captcha'
                if not state['wall_notified']:
                    office(f'/api/agents/{LEAD}/messages',{'text':stamp+': X watch stopped at a login wall or CAPTCHA. No login was attempted; GitHub watches continue.'});state['wall_notified']=True
                break
            if urllib.parse.urlsplit(page.get('url','')).hostname not in ('x.com','www.x.com','twitter.com','www.twitter.com') or urllib.parse.urlsplit(page.get('url','')).path.strip('/').lower()!=account.lower():
                report['status']='stopped-unexpected-profile-navigation';break
            prior=state['accounts'].get(account,{});since=datetime.fromisoformat(prior['checked_at'].replace('Z','+00:00')) if prior.get('checked_at') else now-timedelta(hours=config['first_run_hours']);seen=set(prior.get('seen',[]));posts_read=0;profile_complete=True
            for index in range(config['max_posts_per_profile']):
                try:
                    article=profile_text(target,account,f'article >> nth={index}')
                except TimeoutError:
                    profile_complete=False
                    report['coverage'].append(account+': article read timed out; remaining profile text was not read.')
                    break
                except urllib.error.HTTPError as error:
                    if error.code in (400,409,422):break
                    raise
                try:body_text=profile_text(target,account,f'article >> nth={index} >> [data-testid="tweetText"]')
                except (urllib.error.HTTPError,TimeoutError):body_text='';profile_complete=False
                if not body_text:continue
                posts_read+=1;key=hashlib.sha256((account+'\n'+body_text).encode()).hexdigest()
                display,earliest,latest=post_time(article,now)
                if key in seen:continue
                seen.add(key)
                if latest and latest<=since:continue
                links=list(dict.fromkeys(visible_links(body_text)+visible_links(article)));post=dict(account=account,observed_at=stamp,time_text=display,published_at=None,time_range=[earliest.isoformat(),latest.isoformat()] if earliest else None,newness='newer-than-last-check' if earliest and earliest>since else 'first-seen; exact newness unavailable',text=body_text,links=links,source_checks=[])
                if TERMS.search(body_text):
                    for url in links:
                        try:
                            check=check_source(url,state['sources']);post['source_checks'].append(check)
                            if check.get('actionable'):report['actionable_leads'].append(check);pending.append(check)
                            if check.get('key'):source_updates[check['key']]=check['revision']
                        except Exception:post['source_checks'].append(dict(url=url,actionable=False,reason='Source check failed; pending agent review'))
                report['posts'].append(post)
            if posts_read:state['accounts'][account]={'checked_at':stamp if profile_complete else prior.get('checked_at'),'seen':sorted(seen)[-2000:]}
            else:report['coverage'].append(account+': no readable posts; last successful check time was preserved.')
            report.setdefault('profiles',{})[account]={'posts_read':posts_read}
        else:
            report['status']='completed'
            if any(p['posts_read'] for p in report.get('profiles',{}).values()):state['wall_notified']=False
        # Alert only sources checked outside X. Mathematical import remains the normal refresh path.
        if pending:
            links=list(dict.fromkeys(x['url'] for x in pending))
            office(f'/api/agents/{LEAD}/messages',{'text':stamp+': X watch found source-backed leads for review: '+'; '.join(links[:8])+'. Source checks are in local .git/x-watch-report.json. No score was imported from X; board imports require BOS Lead Dev review in the public repo.'})
            pending=[]
        state['sources'].update(source_updates)
        return report
    except Exception as error:
        report['status']='browser-or-source-error';report['error_type']=type(error).__name__;return report
    finally:
        if navigation_started and original:
            try:
                browser('goto',target=target,url=original);report['tab_restored']=True;journal.unlink(missing_ok=True)
            except Exception:
                report['tab_restored']=False;report['status']='restoration-pending';report['coverage'].append('Saved restoration will be retried when the same tab is offered.')
        elif journal.exists() and original:journal.unlink(missing_ok=True)
        state['pending_leads']=list({(p['key'],p['revision']):p for p in pending}.values())
        save(state_path,state);save(report_path,report)
        print(f"X watch {stamp}: {report['status']}; {len(report['posts'])} first-seen posts; {len(report['actionable_leads'])} source-backed leads.")
if __name__=='__main__':run()
