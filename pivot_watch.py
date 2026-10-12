#!/usr/bin/env python3
"""Search GitHub metadata and README indexes for possible new bound races."""
import json, re, time, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fractions import Fraction
from github_read import api, pages, content
from other_bounds_watch import collect as collect_other_bounds, FAMILIES
from watch_policy import wht_only, hourly_imported, new_research_source, visible_problem
from crocswap_pr_watch import collect as collect_crocswap_prs
ROOT=Path(__file__).resolve().parent
SITE_ROOT=ROOT.parent/'bigospeedrun-site'
CORE=['matrix multiplication','integer multiplication','DFT','FFT','3SUM','threesum','APSP','subset sum','discrete Fourier transform']

def stated_bound(readme, pattern):
    match=re.search(pattern,readme,re.M)
    if not match:raise ValueError('Configured headline bound was not found; no change inferred')
    groups=match.groupdict()
    return str(Fraction(groups['num'])/Fraction(groups.get('den') or 1))

def board_snapshot():
    registry=json.loads((ROOT/'registry.json').read_text())
    board={r['repo'] for r in registry['repositories']}
    # The watch's data snapshot can lag behind approved site listings.
    # Read the site registry without importing or modifying either snapshot.
    site_registry=SITE_ROOT/'data/registry.json'
    if site_registry.exists():
        listed=json.loads(site_registry.read_text())
        board.update(r['repo'] for r in listed['repositories'])
    records={}
    for problem in registry['problems']:
        data=json.loads((ROOT/problem['data_file']).read_text())
        for record in data['records']:
            repo=data['record_metadata'][record['id']].get('repo')
            if repo and record.get('source_commit'):
                if repo not in records or (record['submitted_at'] or '')>(records[repo]['submitted_at'] or ''):
                    records[repo]=record
    return board,records

def alert_candidate(row, known, changed_heads):
    if row.get('cross_problem_pr'):
        return bool(row.get('source_claim_evidence') and row.get('stated_bound_changed') and row.get('claim_signature'))
    if row.get('other_family') in FAMILIES or row.get('openai_fork_improvement'):
        return bool(row.get('source_claim_evidence') and row.get('stated_bound_changed') and row.get('claim_signature'))
    if not visible_problem(row.get('problem_guess','')):return False
    if hourly_imported(row['repo'],row.get('problem_guess','')):return False
    if row.get('wht_only') or wht_only(row.get('problem_guess','')+' '+(row.get('description') or '')):return False
    if row.get('on_board'):return row.get('stated_bound_changed',False)
    return bool((row.get('likely_new_race') or row.get('likely_pivot') or row.get('likely_tracked_source')) and row['repo'] not in known)

def main():
    now=datetime.now(timezone.utc);cutoff=now-timedelta(hours=72)
    since=cutoff.strftime('%Y-%m-%dT%H:%M:%SZ')
    names=[];dynamic=[]  # Only the six problems currently shown on the site.
    queries=[]
    # Search concise metadata separately; broad README hits can hide real projects.
    for term in CORE:
        queries.append(f'"{term}" in:name,description pushed:>={since} fork:false')
    # A push is at least as recent as creation for an active repo. Query both
    # fields explicitly so empty/new repos are included too.
    for term in ['bounds','kappa','exponent','speedrun']+list(dict.fromkeys(CORE+dynamic)):
        for field in ('created','pushed'):
            queries.append(f'"{term}" in:name,description,readme {field}:>={since} fork:false')
    queries.append('"CrocSwap/integer-mult-bounds" in:readme fork:true')
    repos={};errors=[];truncated=[]
    def add(r,reason):
        key=r['full_name']
        if key not in repos:repos[key]={'repo':r,'reasons':[]}
        if reason not in repos[key]['reasons']:repos[key]['reasons'].append(reason)
    people_path=ROOT/'people-watch.json'
    if people_path.exists():
        leads=json.loads(people_path.read_text()).get('ranked_hits',[])
        for repo in dict.fromkeys(h['repo'] for h in leads if h['rank']>=10 and h['kind']!='new-bound-pr'):
            try:add(api(f'repos/{repo}'),'people-watch')
            except RuntimeError as error:errors.append(str(error))
    watch_only='--watch-only' in sys.argv
    recheck='--recheck' in sys.argv or watch_only
    prior=json.loads((ROOT/'pivot-watch.json').read_text()) if recheck else None
    if recheck:
        for row in prior['candidates']+prior['related']:
            r=dict(full_name=row['repo'],html_url=row['url'],stargazers_count=row['stars'],created_at=row['created_at'],pushed_at=row['pushed_at'],description=row['description'],fork='fork' in row['evidence'])
            for reason in row['evidence']:add(r,reason)
        errors=prior['errors'];truncated=prior['truncated_queries']
    previous=json.loads((ROOT/'pivot-watch.json').read_text()) if (ROOT/'pivot-watch.json').exists() else {}
    old_heads={r['repo']:r['head_sha'] for r in previous.get('watched_repositories',[])}
    board,board_records=board_snapshot()
    bound_states=dict(previous.get('board_bound_states',{}));bound_changes={}
    watched=[];watch_heads={};watch_problems={}
    for item in json.loads((ROOT/'pivot-watchlist.json').read_text())['repositories']:
        repo=item['repo'];meta=api(f'repos/{repo}');head=api(f'repos/{repo}/commits/{meta["default_branch"]}')
        add(meta,'watchlist');repos[repo]['repo']=meta;watch_heads[repo]=head;watch_problems[repo]=item['problem']
        watched.append(dict(repo=repo,head_sha=head['sha'],previous_head=old_heads.get(repo),new_commit=old_heads.get(repo)!=head['sha'],problem=item['problem'],status=item['status']))
        if repo in board and (item.get('bound_pattern') or item.get('bound_patterns')):
            try:
                readme=content(repo,'README.md',head['sha']).decode()
                current=[stated_bound(readme,p) for p in item['bound_patterns']] if item.get('bound_patterns') else stated_bound(readme,item['bound_pattern'])
                baseline=bound_states.get(repo,{}).get('bound')
                if baseline is None and repo in board_records:baseline=board_records[repo]['score']
                bound_changes[repo]=baseline is not None and current!=baseline
                bound_states[repo]={'bound':current,'source_commit':head['sha'],'checked_at':now.isoformat()}
            except (RuntimeError,ValueError) as e:errors.append(repo+': '+str(e))
    active_queries=queries if not recheck else [f'"discrete Fourier transform" in:name,description,readme pushed:>={since} fork:false']
    if watch_only:active_queries=[]
    for q in active_queries:
        try:
            data=api('search/repositories',{'q':q,'sort':'updated','order':'desc','per_page':100})
            if data.get('incomplete_results') or data['total_count']>100:truncated.append({'query':q,'total_count':data['total_count']})
            for r in data['items']:add(r,'citation' if q.startswith('"CrocSwap/') else q.split(' in:')[0].strip('"'))
        except RuntimeError as e:errors.append(str(e)+'; query='+q)
        time.sleep(2.1)
    for r in pages('repos/CrocSwap/integer-mult-bounds/forks',{'sort':'newest'}):add(r,'fork')
    related=[];candidates=[]
    for entry in repos.values():
        r=entry['repo'];why=entry['reasons'];text=(r['full_name']+' '+(r.get('description') or '')).lower().replace('-',' ')
        problem=next((p for p in CORE+dynamic if p.lower() in text),None)
        if not problem:problem='unknown; inspect source'
        if r['full_name'] in watch_problems:problem=watch_problems[r['full_name']]
        if not visible_problem(problem):continue
        rank=10*('watchlist' in why)
        rank+=8*('people-watch' in why)
        rank+=4*bool(re.search(r'\b(?:bounds?|kappa|exponents?|speedrun)\b',text))
        rank+=3*(problem!='unknown; inspect source')
        rank+=4*bool(re.search(r'\b(?:race|leaderboard|challenge|record|community)\b',text))
        rank+=2*('citation' in why)
        rank-=5*bool(r.get('fork'))
        row=dict(repo=r['full_name'],url=r['html_url'],stars=r['stargazers_count'],created_at=r['created_at'],pushed_at=r['pushed_at'],problem_guess=problem,description=r.get('description'),rank=rank,evidence=why,likely_new_race=False)
        row['on_board']=r['full_name'] in board
        row['stated_bound_changed']=bound_changes.get(r['full_name'],False)
        if 'fork' in why or 'citation' in why:related.append(row)
        if row['on_board'] and not row['stated_bound_changed']:continue
        if hourly_imported(r['full_name'],problem) or r['full_name']=='openai/math':continue
        recent=any(r.get(k) and r[k]>=since for k in ['created_at','pushed_at'])
        if (recent or 'watchlist' in why) and rank>=5 and problem!='unknown; inspect source' and not r.get('fork'):candidates.append(row)
    candidates.sort(key=lambda x:(x['rank'],x['stars'],x['pushed_at'] or ''),reverse=True)
    # Verify the top candidates against pinned source text, never execute it.
    for row in candidates[:12]:
        try:
            r=repos[row['repo']]['repo']
            if 'default_branch' not in r:r=api(f'repos/{row["repo"]}')
            head=watch_heads.get(row['repo']) or api(f'repos/{row["repo"]}/commits/{r["default_branch"]}')
            readme=content(row['repo'],'README.md',head['sha']).decode('utf-8',errors='replace')
            row['readme_commit']=head['sha']
            if 'van der waerden' in (row.get('description') or '').lower():row['problem_guess']='van der Waerden lower bound'
            row['wht_only']=wht_only(readme)
            if row['wht_only']:
                row['likely_pivot']=False
                row['likely_new_race']=False
                continue
            if wht_only(readme) and re.search(r'^#.*Walsh.Hadamard',readme,re.I|re.M):row['problem_guess']='Walsh-Hadamard transform'
            signals=[]
            for line in readme.splitlines():
                if re.search(r'\bleaderboard\b|\bsubmit(?:ting)?\s+(?:(?:a|an|your|new)\s+)*(?:bounds?|records?)\b|\b(?:bound|exponent|kappa)\b.*\b(?:race|challenge)\b|\b(?:race|challenge)\b.*\b(?:bound|exponent|kappa)\b',line,re.I):
                    signals.append(line[:350])
            math_claim=bool(re.search(r'(?:exponent|power saving|asymptotic|logarithm)',readme,re.I)) and bool(re.search(r'\b(?:bound|theorem|proof)\b',readme,re.I))
            row['likely_tracked_source']=math_claim and new_research_source(row,since) and not row['on_board']
            cited_upstream=any(source.lower() in readme.lower() for source in ('CrocSwap/integer-mult-bounds','Swapnil-jain/integer-mult-kappa','anthropics/formal-math','2610.06783','openai/math'))
            row['likely_pivot']=math_claim and cited_upstream and row['problem_guess'] not in ('integer multiplication','unknown; inspect source')
            row['pivot_evidence']=[line[:350] for line in readme.splitlines() if re.search(r'power saving|improved exponent|CrocSwap/integer-mult-bounds|Swapnil-jain/integer-mult-kappa',line,re.I)][:5] if row['likely_pivot'] else []
            row['race_evidence']=signals[:4]
            row['likely_new_race']=math_claim and bool(signals) and row['problem_guess'] not in ('integer multiplication','unknown; inspect source')
        except (RuntimeError,ValueError) as e:row['readme_error']=str(e)
    candidates.sort(key=lambda x:(x.get('likely_pivot',False),x['likely_new_race'],x['rank'],x['stars']),reverse=True)
    result=dict(checked_at=now.isoformat(),watched_repositories=watched,window_start=since,queries=(prior['queries']+active_queries if recheck else queries),rechecked_retained_candidates=recheck,preprint_names=names,preprint_search_families=dynamic,coverage_note='Only the six problems currently shown on the site. Search indexes can lag. Each query is capped at 100 hits; truncations and failures are listed. Fork and citation lists cover all dates.',errors=errors,truncated_queries=truncated,candidates=candidates[:20],related=sorted(related,key=lambda x:(x['stars'],x['pushed_at'] or ''),reverse=True))
    print('Checking Other bounds and OpenAI forks with saved work and a six-minute budget.',flush=True)
    other=collect_other_bounds(since,previous,leads if people_path.exists() else (),search=not recheck)
    result['candidates'].extend(other['candidates'])
    result['other_bound_states']=other['states']
    result['other_bounds_checkpoint']=other['checkpoint']
    result['other_bounds_usage']=other['usage']
    print('Other bounds pass:',json.dumps(other['usage']),flush=True)
    result['errors'].extend(other['errors']);result['truncated_queries'].extend(other['truncated']);result['queries'].extend(other['queries'])
    result['coverage_note']+=' Other bounds: 13 reviewed families plus added improvement claims in new OpenAI math forks; 360 GET attempts / 360 seconds per cycle. Pending repositories and fork/search positions are checkpointed. Deferred work is incomplete coverage, not an all-clear; diff patches can be truncated.'
    result['board_bound_states']=bound_states
    prs=collect_crocswap_prs(since,previous)
    result['candidates'].extend(prs['candidates'])
    result['crocswap_pr_states']=prs['states']
    result['crocswap_prs_checked']=prs['checked']
    result['errors'].extend(prs['errors']);result['truncated_queries'].extend(prs['truncated'])
    result['coverage_note']+=' Recent CrocSwap PRs: all authors and states, updated within 72 hours; inspect cross-problem claims in PR bodies and added Markdown, TeX and Lean lines. At most 1000 PRs and 300 files per PR; incomplete reads are retried.'
    path=ROOT/'pivot-watch.json';temp=path.with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2)+'\n');temp.replace(path)
    print('Checked',result['checked_at'],'window',since)
    for i,row in enumerate(candidates[:10],1):print(f'{i}. {row["repo"]} | stars {row["stars"]} | created {row["created_at"]} | pushed {row["pushed_at"]} | {row["problem_guess"]} | likely race: {row["likely_new_race"]}; likely pivot: {row.get("likely_pivot",False)}')
    print(f'Related forks/citations: {len(related)}. Failed queries: {len(errors)}. Capped/incomplete queries: {len(truncated)}. Full evidence: pivot-watch.json')
if __name__=='__main__':main()
