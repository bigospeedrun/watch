#!/usr/bin/env python3
"""Read public GitHub events; retain leads without treating them as bound evidence."""
import collections, json, re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from github_read import api
from other_bounds_watch import other_problem, openai_fork
from watch_policy import wht_only, board_fork, HOURLY_REPOS, hourly_imported, visible_problem
ROOT=Path(__file__).resolve().parent
WORDS=re.compile(r'bound|kappa|exponent|speedrun|fourier|(?:^|[- /])dft|(?:^|[- /])fft|3sum|threesum|apsp|subset.sum|shortest.path|matrix.mult|integer.mult|walsh|hadamard',re.I)

def listed_repos():
    """Lowercase repos in the local snapshot plus the live site registry.

    The local registry.json is an old snapshot. The live Relevant repos list is
    the sibling site's data/registry.json; read it, never modify it.
    """
    repos={r['repo'].lower() for r in json.loads((ROOT/'registry.json').read_text())['repositories']}
    site=ROOT.parent/'bigospeedrun-site'/'data'/'registry.json'
    if site.exists():repos.update(r['repo'].lower() for r in json.loads(site.read_text())['repositories'])
    return repos

def classify(event, watched):
    kind=event['type'];payload=event.get('payload',{});repo=event.get('repo',{}).get('name')
    if not repo:return None
    if kind=='CreateEvent' and payload.get('ref_type')=='repository':return 'new-repository',repo
    if kind=='CreateEvent' and payload.get('ref_type')=='branch' and repo.lower() not in watched:return 'branch-outside-watchlist',repo
    if kind=='ForkEvent' and payload.get('forkee',{}).get('full_name'):return 'new-fork',payload['forkee']['full_name']
    if kind=='PushEvent' and repo.lower() not in watched:return 'push-outside-watchlist',repo
    if kind=='PullRequestEvent' and payload.get('action')=='opened' and (repo.lower() in watched or WORDS.search(repo) or other_problem(repo)):
        return 'new-bound-pr',repo
    return None

def main():
    now=datetime.now(timezone.utc);stamp=now.isoformat(timespec='seconds').replace('+00:00','Z');since=(now-timedelta(hours=72)).isoformat(timespec='seconds').replace('+00:00','Z')
    config=json.loads((ROOT/'people-watchlist.json').read_text())
    submissions=json.loads((ROOT/'submissions.json').read_text());counts=collections.Counter(s['author'] for s in submissions['items'])
    users={p['github']:dict(p) for p in config['people']}
    for login,count in counts.most_common(config['active_author_count']):
        users.setdefault(login,dict(github=login,confirmation='CrocSwap PR author login in saved GitHub API submissions',evidence_url='https://github.com/CrocSwap/integer-mult-bounds/pulls'))
        users[login]['crocswap_pr_count']=count
    watched=listed_repos()
    watched.update(r['repo'].lower() for r in json.loads((ROOT/'pivot-watchlist.json').read_text())['repositories'])
    prior=json.loads((ROOT/'people-watch.json').read_text()) if (ROOT/'people-watch.json').exists() else {}
    prior_users=prior.get('users',{});state={};hits=[];errors=[];warnings=[]
    cached_prs={s['pr_number']:s for s in submissions['items']}
    for login,person in users.items():
        previous=prior_users.get(login,{});seen=set(previous.get('seen_ids',[]));events=[]
        try:
            for page in range(1,4):
                batch=api(f'users/{login}/events/public',{'per_page':100,'page':page});events.extend(batch)
                if len(batch)<100 or (batch and batch[-1]['created_at']<since):break
            if len(events)==300 and events[-1]['created_at']>=since:warnings.append(login+': 300-event API cap reached within the 72-hour window; events may be missing.')
            profile=api(f'users/{login}')
        except RuntimeError as error:
            errors.append(login+': '+str(error));state[login]=previous;continue
        missing=sum(not e.get('repo',{}).get('name') for e in events)
        if missing:warnings.append(f'{login}: {missing} public events have no repository name and were skipped.')
        state[login]=dict(**person,profile={'login':profile['login'],'name':profile.get('name'),'twitter_username':profile.get('twitter_username'),'url':profile['html_url']},checked_at=stamp,seen_ids=list(dict.fromkeys([e['id'] for e in events]+previous.get('seen_ids',[])))[:1500],event_count=len(events),oldest_returned_at=events[-1]['created_at'] if events else None)
        # Repository inventory also catches public pushes absent from the event feed.
        inventory=dict(previous.get('repository_inventory',{}))
        try:
            for page in range(1,4):
                batch=api(f'users/{login}/repos',{'type':'owner','sort':'pushed','direction':'desc','per_page':100,'page':page})
                for repository in batch:
                    name=repository['full_name'];pushed=repository.get('pushed_at')
                    if pushed and pushed>=since and pushed!=inventory.get(name) and name.lower() not in watched and (WORDS.search(name+' '+(repository.get('description') or '')) or other_problem(name+' '+(repository.get('description') or '')) or repository.get('fork')):
                        hits.append(dict(event_id='inventory:'+name+':'+pushed,actor=login,kind='repository-inventory-change',repo=name,url=repository['html_url'],created_at=pushed,title=repository.get('description'),head=None,rank=30,relevance='Recent owned bound repository; inspect source'))
                    inventory[name]=pushed
                if len(batch)<100 or (batch and (batch[-1].get('pushed_at') or '')<since):break
            else:warnings.append(login+': owned repository inventory capped at 300.')
        except RuntimeError as error:errors.append(login+': repository inventory: '+str(error))
        state[login]['repository_inventory']=inventory
        # Process a single event ID once; all types enter seen_ids, including non-leads.
        for event in events:
            newly_supported=prior.get('classifier_version')!=2 and event['type']=='CreateEvent' and event.get('payload',{}).get('ref_type')=='branch'
            if (event['id'] in seen and not newly_supported) or event['created_at']<since:continue
            result=classify(event,watched)
            if not result:continue
            kind,repo=result;payload=event.get('payload',{});title=None;body=None;url='https://github.com/'+repo
            if kind=='new-bound-pr':
                number=payload.get('number') or payload['pull_request']['number'];url+=f'/pull/{number}'
                body=payload.get('pull_request',{}).get('body')
                if repo.lower()=='crocswap/integer-mult-bounds' and number in cached_prs:title=cached_prs[number]['title']
                else:
                    try:
                        pr=api(f'repos/{repo}/pulls/{number}');title=pr['title'];body=pr.get('body')
                    except RuntimeError as error:errors.append(str(error)+'; title unavailable')
            rank=10*bool(WORDS.search(repo+' '+(title or '')+' '+(payload.get('description') or '')))+20*(kind in ('new-repository','branch-outside-watchlist'))+2*(kind=='new-bound-pr')
            hits.append(dict(event_id=event['id'],actor=login,kind=kind,repo=repo,url=url,created_at=event['created_at'],title=title,head=payload.get('head') if kind=='push-outside-watchlist' else None,rank=rank,relevance='bound-related lead; inspect source' if rank>=10 else 'unknown; inspect source'))
            if body:hits[-1]['body']=body
    board=listed_repos()
    repo_cache={};filtered=[]
    for hit in hits:
        # Reuse event/body data; the bounded direct PR pass covers missing bodies.
        scope=(hit.get('title') or '')+'\n'+(hit.get('body') or '')
        if hourly_imported(hit['repo'],scope) or wht_only(scope or hit['repo']):continue
        try:
            if hit['repo'] not in repo_cache:repo_cache[hit['repo']]=api('repos/'+hit['repo'])
            if board_fork(repo_cache[hit['repo']],board) and not openai_fork(repo_cache[hit['repo']]):continue
        except RuntimeError as error:
            errors.append(str(error)+'; lead retained for source review')
        scope=hit['repo']+' '+scope+' '+(repo_cache.get(hit['repo'],{}).get('description') or '')
        if visible_problem(scope) or other_problem(scope) or openai_fork(repo_cache.get(hit['repo'],{})):
            hit['openai_math_fork']=openai_fork(repo_cache.get(hit['repo'],{}))
            if other_problem(scope) or hit['openai_math_fork']:hit['rank']=max(20,hit['rank'])
            filtered.append(hit)
    hits=filtered
    hits.sort(key=lambda h:(h['rank'],h['created_at']),reverse=True)
    # Group repeated pushes but retain all event IDs in the full hit list.
    grouped={}
    for hit in hits:
        key=(hit['kind'],hit['url']);row=grouped.setdefault(key,{**hit,'event_count':0,'actors':[]});row['event_count']+=1
        if hit['actor'] not in row['actors']:row['actors'].append(hit['actor'])
    report=dict(checked_at=stamp,first_run=not bool(prior),window_start=since,users=state,hits=hits,ranked_hits=list(grouped.values()),errors=errors,warnings=warnings,coverage='Public events only. GitHub may delay events and returns at most 300 per user; this is not a complete commit feed. First run uses 72 hours; later runs deduplicate event IDs. X handles are identity context supplied by Nil, not an X data feed. Leads never alter mathematical records automatically.')
    report['classifier_version']=2
    path=ROOT/'people-watch.json';temp=path.with_suffix('.tmp');temp.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');temp.replace(path)
    print(f'Checked {stamp}: {len(users)} accounts; {len(hits)} new events, {len(grouped)} grouped leads; {len(errors)} errors; {len(warnings)} coverage warnings.')
    for hit in list(grouped.values())[:12]:print(f"{hit['kind']}: {hit['url']} | {', '.join(hit['actors'])} | {hit['title'] or hit['relevance']}")
if __name__=='__main__':main()
