"""Data-only discovery of Other bounds claims and OpenAI math fork improvements."""
import hashlib,json,re,time
from fractions import Fraction
from pathlib import Path
from urllib.parse import quote
from github_read import api,content
from watch_budget import WatchBudget, BudgetExhausted
CONFIG=json.loads(Path(__file__).with_name('other-bounds-watchlist.json').read_text())['families']
FAMILIES={r['family']:r for r in CONFIG}
MAX_REQUESTS=360
MAX_SECONDS=360
DISCOVERY_REQUESTS=20
DISCOVERY_SECONDS=60
FORK_PAGES_PER_CYCLE=5

def normalize(text):return re.sub(r'[^a-z0-9]+',' ',text.lower()).strip()

def family_configs():
    # A family can list several repos; match and search each family once, with
    # the union of its entries' aliases (entries need not repeat each alias).
    merged={}
    for r in CONFIG:
        m=merged.setdefault(r['family'],dict(r,aliases=[]))
        m['aliases']+=[a for a in r['aliases'] if a not in m['aliases']]
    return list(merged.values())

def search_phrases():
    # Search every distinct alias, not only the first: a repo can use only a
    # later phrase (shea256 says "binary matrix removal", 2026-10-14).
    pairs=[]
    for cfg in family_configs():
        seen=set()
        for alias in cfg['aliases']:
            if normalize(alias) not in seen:seen.add(normalize(alias));pairs.append((cfg,alias))
    return pairs

def family_matches(text):
    normalized=normalize(text)
    return [r['family'] for r in family_configs() if any(normalize(a) in normalized for a in r['aliases']) or re.search(r'\bfamily\s*#?\s*0*'+str(int(r['family']))+r'\b',text,re.I)]

def other_problem(text):return bool(family_matches(text))

def openai_fork(meta):
    return bool(meta.get('fork') and any(meta.get(k,{}).get('full_name','').lower()=='openai/math' for k in ('parent','source')))

def untouched_fork(meta):
    return bool((meta.get('_openai_fork') or openai_fork(meta))
                and meta.get('created_at') and meta.get('pushed_at')
                and meta['pushed_at'] <= meta['created_at'])

def claim_lines(text,improvement=False):
    result=[]
    for line in text.splitlines():
        line=line.strip()
        if not re.search(r'\d',line) or re.search(r'https?://|\b(?:commit|copyright|checked_at|sha256)\b',line,re.I):continue
        if re.search(r'\b(?:no|not|without)\s+(?:new\s+)?(?:improv\w*|better|sharper)',line,re.I):continue
        if not re.search(r'bound|exponent|saving|constant|threshold|gap|coefficient|moves|μ|θ|gamma|theorem|[≤≥<>]=?|\\(?:le|ge)\b',line,re.I):continue
        if improvement and not re.search(r'improv|sharper|stronger|better|reduc|increas|new\s+(?:bound|saving|exponent|constant)|from.+to',line,re.I):continue
        result.append(line[:1000])
    return result

def scoped_claims(text,family,improvement=False):
    if len(family_matches(text))<=1:return claim_lines(text,improvement)
    lines=text.splitlines();selected=[];section=[];start=0
    for i,line in enumerate(lines):
        if re.match(r'^#{1,6}\s',line):section=family_matches(line);start=i
        nearby=family_matches('\n'.join(lines[max(start,i-3):i+1]))
        if family in section or family in nearby:selected.extend(claim_lines(line,improvement))
    return selected

def claim_key(family,lines):
    # Ignore prose-only edits. Retain exact numerical tokens and comparisons.
    values=sorted(set(tuple(re.findall(r'\d+(?:\.\d+)?|[≤≥<>/=+^−-]',line)) for line in lines))
    return hashlib.sha256(json.dumps([family,values],sort_keys=True).encode()).hexdigest() if values else None

SITE='bigospeedrun/site'
SITE_BOUNDS='src/lib/other-bounds.json'

def stated_values(pattern,text):
    """Every value the pattern's num group states, with digit grouping removed
    ('mu(G) < 2 294', MarcosCarreira 2026-10-21)."""
    values=[]
    for match in re.finditer(pattern,text,re.M):
        try:values.append(Fraction(re.sub(r'[\s,\u2009\u202f]','',match['num'])))
        except (ValueError,ZeroDivisionError):continue
    return values

def site_leader(budget,slug):
    """(direction, leader value) of an Other bounds row on site main: the best claim value."""
    families=json.loads(budget.read(SITE,SITE_BOUNDS,'main'))['families']
    row=next(f for f in families if f['slug']==slug)
    values=[Fraction(c['value']) for c in row['claims']]
    return row['direction'],(min(values) if row['direction']=='lower' else max(values))

def bound_key(family,value):
    # The claim key of a configured stated bound: only its value counts.
    return claim_key(family,[f'stated bound {Fraction(value)}'])

def candidate(meta,head,family,lines,old,kind,key=None):
    key=key or claim_key(family,lines)
    if not key or key in old.get('seen_claims',[]):return None,key
    label=FAMILIES[family]['title'] if family in FAMILIES else 'OpenAI family '+family
    row=dict(repo=meta['full_name'],url=meta['html_url'],stars=meta.get('stargazers_count',0),created_at=meta.get('created_at'),pushed_at=meta.get('pushed_at'),description=meta.get('description'),problem_guess=f'Family {family}: {label}',rank=20,evidence=[kind],readme_commit=head,source_claim_evidence=lines[:6],claim_signature=key,other_family=family if family in FAMILIES else None,openai_fork_improvement=kind=='openai-math-fork',stated_bound_changed=True,likely_tracked_source=True,likely_new_race=False,likely_pivot=False,on_board=False)
    return row,key

def readme(budget,repo,ref):
    """README.md text at ref, or '' when the tree at ref has no README.md.

    A repo without README.md (karirogg's fork, 2026-10-15) failed this read every
    cycle and stalled. Both the head read and the first-run baseline read use this;
    the baseline read was missed at first (64a3b09), so the repo stayed stalled.
    A failure while README.md exists is transient and raises."""
    try:return budget.read(repo,'README.md',ref).decode('utf-8',errors='replace')
    except BudgetExhausted:raise
    except RuntimeError:
        tree=budget.get(f'repos/{repo}/git/trees/{ref}')
        if any(e.get('path')=='README.md' for e in tree.get('tree',[])):raise
        return ''

def compact_meta(meta):
    keys=('full_name','html_url','default_branch','created_at','pushed_at','description','stargazers_count','fork','_openai_fork')
    result={key:meta[key] for key in keys if key in meta}
    if openai_fork(meta):result['_openai_fork']=True
    return result


def collect(since,previous,people_hits=(),search=True):
    state=json.loads(json.dumps(previous.get('other_bound_states',{})))
    checkpoint=json.loads(json.dumps(previous.get('other_bounds_checkpoint',{})))
    pending={meta['full_name']:meta for meta in checkpoint.get('pending',[])}
    starting_pending=len(pending)
    starting_forks=sum(bool(meta.get('_openai_fork')) for meta in pending.values())
    skipped_untouched=set()
    unchanged_forks=[]
    changed_forks=[]
    for name,meta in list(pending.items()):
        if untouched_fork(meta):
            skipped_untouched.add(name)
            del pending[name]
    errors=[];truncated=[];queries=[];rows=[];checked=[]
    budget=WatchBudget(MAX_REQUESTS,MAX_SECONDS,api,content)
    cycle=checkpoint.get('cycle',0)+1
    search_cursor=checkpoint.get('search_cursor',0)
    fork_page=checkpoint.get('fork_page',1)
    fork_since=checkpoint.get('fork_since') or since
    discovery_started=time.monotonic()
    discovery_requests=budget.requests
    def add(meta,force=False):
        name=meta['full_name']
        if untouched_fork(meta):
            skipped_untouched.add(name)
            pending.pop(name,None)
            return
        if not force and name not in pending and meta.get('pushed_at') and meta.get('pushed_at')==state.get(name,{}).get('meta',{}).get('pushed_at'):return
        pending[name]={**pending.get(name,{}),**compact_meta(meta)}
    def discovery_ready():
        return budget.requests-discovery_requests<DISCOVERY_REQUESTS and time.monotonic()-discovery_started<DISCOVERY_SECONDS
    # Store metadata with pending work. No GET is needed just to requeue a source.
    known=list(dict.fromkeys(cfg['repo'] for cfg in CONFIG))
    unfinished_known=[name for name in pending if name in known]
    for name in known:add(state.get(name,{}).get('meta',{'full_name':name}),force=True)
    for hit in people_hits:
        if other_problem(hit['repo']+' '+(hit.get('title') or '')) or hit.get('openai_math_fork'):
            add(dict(full_name=hit['repo'],_openai_fork=bool(hit.get('openai_math_fork'))))
    for name,old in state.items():
        if old.get('openai_fork'):
            add({**old.get('meta',{'full_name':name}),'_openai_fork':True},force=True)
    if search:
        # Always check the newest page first. Continue older pages at the saved
        # position, using the original cutoff until that sweep finishes.
        pages=[1]+list(range(max(2,fork_page),max(2,fork_page)+FORK_PAGES_PER_CYCLE-1))
        for page in pages:
            if not discovery_ready():break
            try:
                forks=budget.get('repos/openai/math/forks',{'sort':'newest','per_page':100,'page':page})
                for fork in forks:
                    if (fork.get('created_at') or '')>=fork_since:add({**fork,'_openai_fork':True})
                if len(forks)<100 or (forks and (forks[-1].get('created_at') or '')<fork_since):
                    fork_page=1;fork_since=since;break
                fork_page=max(fork_page,page+1)
            except BudgetExhausted as error:errors.append(str(error));break
            except (RuntimeError,ValueError) as error:errors.append(str(error));break
        # Round-robin family searches retain their position if discovery is cut short.
        searches=search_phrases()
        for _ in range(len(searches)):
            if not discovery_ready():break
            cfg,alias=searches[search_cursor%len(searches)]
            q='"'+' '.join(alias.split())+'"'+f' in:name,description,readme pushed:>={since} fork:false'
            queries.append(q)
            try:
                result=budget.get('search/repositories',{'q':q,'sort':'updated','order':'desc','per_page':100})
                if result.get('incomplete_results') or result['total_count']>100:truncated.append(dict(query=q,total_count=result['total_count']))
                for meta in result['items']:add(meta)
                search_cursor=(search_cursor+1)%len(searches)
                budget.pause(2.1)
            except BudgetExhausted as error:errors.append(str(error));break
            except (RuntimeError,ValueError) as error:
                errors.append(str(error)+'; query='+q)
                break
    # Reviewed sources first, then alternate fork and other-source work. New
    # forks precede known forks and run newest first. Rechecks rotate by cycle.
    fork_names=[name for name,meta in pending.items() if meta.get('_openai_fork') and name not in known]
    fresh=[name for name in fork_names if name not in state or pending[name].get('pushed_at')!=state[name].get('meta',{}).get('pushed_at')]
    fresh.sort(key=lambda name:(pending[name].get('created_at') or '',name),reverse=True)
    rechecks=sorted((name for name in fork_names if name not in fresh),key=lambda name:(state.get(name,{}).get('checked_cycle',0),name))
    forks=fresh+rechecks
    sources=[name for name in pending if name not in known and name not in fork_names]
    work=unfinished_known+[name for name in known if name not in unfinished_known]
    for i in range(max(len(forks),len(sources))):
        if i<len(forks):work.append(forks[i])
        if i<len(sources):work.append(sources[i])
    upstream_head=None
    leaders={}
    for repo in work:
        meta=pending[repo];old=state.get(repo,{})
        seen=list(old.get('seen_claims',[]))
        try:
            budget.check()
            if 'default_branch' not in meta:
                loaded=compact_meta(budget.get('repos/'+repo))
                if meta.get('_openai_fork'):loaded['_openai_fork']=True
                meta=loaded
                pending[repo]=meta
            is_fork=meta.get('_openai_fork') or openai_fork(meta)
            if untouched_fork(meta):
                skipped_untouched.add(repo)
                del pending[repo]
                continue
            head=budget.get(f'repos/{repo}/commits/{meta["default_branch"]}')['sha']
            if old.get('head')==head:
                state[repo]={**old,'meta':meta,'checked_cycle':cycle}
                del pending[repo];checked.append(repo);continue
            if is_fork:
                # Compare fork additions to upstream. Never scan inherited preprints
                # as if their original bounds were this fork's new discoveries.
                if upstream_head is None:upstream_head=budget.get('repos/openai/math/commits/main')['sha']
                diff=budget.get('repos/openai/math/compare/'+upstream_head+'...'+quote(repo.split('/')[0]+':'+head,safe=':'))
                if not diff.get('files'):
                    # Synced or behind upstream: there is no changed source to inspect.
                    unchanged_forks.append(repo)
                    state[repo]=dict(head=head,seen_claims=seen,openai_fork=True,meta=meta,checked_cycle=cycle)
                    del pending[repo];checked.append(repo);continue
                changed_forks.append(repo)
                additions=[]
                for f in diff.get('files',[]):
                    if f.get('status')=='removed' or not re.search(r'\.(?:md|tex|lean)$',f['filename']):continue
                    if 'patch' not in f:errors.append(repo+': missing diff patch '+f['filename']);continue
                    added='\n'.join(line[1:] for line in f['patch'].splitlines() if line.startswith('+') and not line.startswith('+++'))
                    families=family_matches(f['filename']+'\n'+added)
                    families+=re.findall(r'\bfamily\s*#?\s*(\d{1,3})\b',added,re.I)
                    families+=[m.zfill(3) for m in re.findall(r'(?:^|/)(\d{3})(?:[-_/]|$)',f['filename'])]
                    if not families and ('preprints/' in f['filename'] or re.search(r'OpenAI|family|challenge',added,re.I)) and claim_lines(added,True):families=['unmapped']
                    for family in sorted(set(x.zfill(3) for x in families)):
                        additions.append((family,scoped_claims(added,family,True),None))
                if len(diff.get('files',[]))>=300:truncated.append(dict(query=repo+' upstream diff',total_count='at least 300 files'))
            else:
                text=readme(budget,repo,head)
                # A watched repo always counts for its configured family, even when
                # its README does not use a family alias.
                families=list(dict.fromkeys(family_matches(repo+' '+(meta.get('description') or '')+'\n'+text)+
                    [cfg['family'] for cfg in CONFIG if cfg['repo']==repo]))
                additions=[(family,scoped_claims(text,family),None) for family in families]
                # A configured bound_pattern makes the stated bound the only claim of the repo.
                # slitsey's Catalan README and notes changed companion constants (L(2,chi_-3),
                # G +/- 5pi^2/48) twice on 2026-10-20 while G stayed b^(-740): no alert.
                bound_cfg=next((c for c in CONFIG if c['repo']==repo and c.get('bound_pattern')),None)
                bound=re.search(bound_cfg['bound_pattern'],text,re.M) if bound_cfg else None
                if bound_cfg and not bound:
                    errors.append(f'{repo}: configured bound not found in README.md at {head[:7]}; all README claims checked')
                leader=None
                values=stated_values(bound_cfg['bound_pattern'],text) if bound else []
                if bound and not values:  # No readable value: all README claims, as without a pattern.
                    bound=None;errors.append(f'{repo}: configured bound has no readable value in README.md at {head[:7]}; all README claims checked')
                if bound and bound_cfg.get('beats_leader'):
                    # Flag only a stated value that beats the row's current leader, not an author's
                    # own improvement that stays behind it (Carreira mu(G) < 2294 vs 740, 2026-10-21).
                    try:
                        if bound_cfg['beats_leader'] not in leaders:leaders[bound_cfg['beats_leader']]=site_leader(budget,bound_cfg['beats_leader'])
                        leader=leaders[bound_cfg['beats_leader']]
                    except BudgetExhausted:raise
                    except (RuntimeError,ValueError,KeyError,TypeError,StopIteration,ZeroDivisionError) as error:
                        errors.append(f'{repo}: cannot read the {bound_cfg["beats_leader"]} leader from {SITE} ({type(error).__name__}); stated bound checked without it')
                if bound and leader:
                    direction,best_known=leader
                    best=(min if direction=='lower' else max)(values)
                    additions=[]
                    if (best<best_known if direction=='lower' else best>best_known):
                        family=bound_cfg['family']
                        match=next(m for m in re.finditer(bound_cfg['bound_pattern'],text,re.M) if stated_values(bound_cfg['bound_pattern'],m[0])==[best])
                        line=text[text.rfind('\n',0,match.start())+1:].split('\n',1)[0].strip()[:1000]
                        additions=[(family,[line],bound_key(family,best))]
                elif bound:
                    family=bound_cfg['family']
                    if bound_cfg.get('reviewed_bound') and bound_key(family,bound_cfg['reviewed_bound']) not in seen:
                        seen.append(bound_key(family,bound_cfg['reviewed_bound']))
                    line=text[text.rfind('\n',0,bound.start())+1:].split('\n',1)[0].strip()[:1000]
                    additions=[(family,[line],bound_key(family,stated_values(bound_cfg['bound_pattern'],bound[0])[0]))]
                base=None if bound else old.get('head') or next((cfg['baseline_commit'] for cfg in CONFIG if cfg['repo']==repo),None)
                if base and base!=head:
                    try:diff=budget.get(f'repos/{repo}/compare/{base}...{head}')
                    except BudgetExhausted:raise
                    except RuntimeError:
                        # A rewritten history has no common ancestor with the stored
                        # head, so this compare fails every cycle. Before 2026-10-16 the
                        # repo then stalled: slitsey's Catalan records (Oct 12-13) were
                        # never read. Keep the README claims at head and move on.
                        errors.append(f'{repo}: compare from {base[:7]} failed (history may be rewritten); README read at {head[:7]}')
                        diff={'files':[]}
                    for f in diff.get('files',[]):
                        if f['filename']=='README.md' or f.get('status')=='removed' or not re.search(r'\.(?:md|tex)$',f['filename']):continue
                        if 'patch' not in f:errors.append(repo+': missing diff patch '+f['filename']);continue
                        added='\n'.join(line[1:] for line in f['patch'].splitlines() if line.startswith('+') and not line.startswith('+++'))
                        targets=family_matches(f['filename']+'\n'+added) or families
                        for family in targets:additions.append((family,scoped_claims(added,family,True),None))
                    if len(diff.get('files',[]))>=300:truncated.append(dict(query=repo+' claim diff',total_count='at least 300 files'))
                # On first run, suppress the reviewed starting claim at its pin.
                if not old:
                    for cfg in CONFIG:
                        if cfg['repo']!=repo:continue
                        baseline=readme(budget,repo,cfg['baseline_commit'])
                        key=claim_key(cfg['family'],scoped_claims(baseline,cfg['family']))
                        if key:seen.append(key)
            for family,lines,key in additions:
                row,key=candidate(meta,head,family,lines,{'seen_claims':seen},'openai-math-fork' if is_fork else 'other-bounds',key)
                if key and key not in seen:seen.append(key)
                if row:rows.append(row)
            state[repo]=dict(head=head,seen_claims=seen,openai_fork=bool(is_fork),meta=meta,checked_cycle=cycle)
            del pending[repo];checked.append(repo)
        except BudgetExhausted as error:
            errors.append(str(error));break
        except (RuntimeError,ValueError,KeyError) as error:
            errors.append(repo+': '+str(error))
            # Move a failed source behind other pending sources for the next pass.
            pending[repo]=pending.pop(repo)
    checkpoint=dict(version=1,cycle=cycle,search_cursor=search_cursor,fork_page=fork_page,fork_since=fork_since,pending=list(pending.values()))
    if pending or fork_page>1:
        truncated.append(dict(query='Other bounds deferred work',total_count=f'{len(pending)} repositories pending; next older fork page {fork_page}'))
    usage=dict(requests=budget.requests,elapsed_seconds=round(time.monotonic()-budget.started,3),request_limit=MAX_REQUESTS,seconds_limit=MAX_SECONDS,repositories_checked=len(checked),pending_repositories=len(pending))
    usage.update(starting_pending_repositories=starting_pending,starting_pending_forks=starting_forks,
                 pending_forks=sum(bool(meta.get('_openai_fork')) for meta in pending.values()),
                 untouched_forks_skipped=len(skipped_untouched),forks_without_changed_files=len(unchanged_forks),
                 forks_with_changed_files=len(changed_forks))
    return dict(candidates=rows,states=state,checkpoint=checkpoint,usage=usage,checked=checked,errors=errors,truncated=truncated,queries=queries)
