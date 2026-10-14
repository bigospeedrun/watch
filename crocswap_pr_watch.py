"""Read recent PR claims: CrocSwap PRs for problems outside integer multiplication,
and PRs on the upstream repos of Other bounds families.

The PR list covers all authors and all states. Only added source text is read;
upstream programs are never run. Rows are review leads, not accepted bounds.
"""
import hashlib
import json
import re
import time
from github_read import api
from other_bounds_watch import FAMILIES, family_matches, claim_lines, claim_key
from watch_policy import cross_board_problems

REPO='CrocSwap/integer-mult-bounds'
DEPENDENCY_DIRS={'inputs','vendor','vendored','third_party','node_modules'}
MAX_REQUESTS=80
MAX_SECONDS=120
# Claims often reach these upstreams only as fork PRs (artuskg's 1/19 sat in
# open PR #4 for 3 days, 2026-10-14). Their PRs run first, within this share
# of the PR budget; CrocSwap gets the rest.
# Smaller repo first, so a large PR backlog on the other cannot starve it.
FAMILY_PR_REPOS={'rohanarun/van-der-waerden-refinement':'160','GTimG/QuasiRiemannTracker':'003'}
FAMILY_MAX_REQUESTS=24

def source_claims(text,default=None):
    """Keep a claim near its problem name, not an unrelated inherited number.

    default labels a claim with no problem name nearby (a family's own repo)."""
    found={}
    section=[]
    recent=[]
    for line in text.splitlines():
        # Link destinations and file paths do not state mathematical claims.
        line=re.sub(r'https?://\S+', '', line)
        names=cross_board_problems(line)+['family:'+f for f in family_matches(line)]
        if not names and re.search(r'\binteger[ -]mult',line,re.I):
            section=[];recent=[]
            continue
        if re.match(r'^#{1,6}\s',line):
            section=names
            recent=[]
        recent.append(names)
        recent=recent[-4:]
        labels=names or section or [name for group in recent for name in group] or ([default] if default else [])
        lines=claim_lines(line)
        if not lines and re.search(r'\d',line) and re.search(r'\bkappa\b|κ|\bO\s*\(',line):lines=[line.strip()[:1000]]
        for claim in lines:
            for label in labels:
                found.setdefault(label,[]).append(claim)
    return found

class Budget:
    def __init__(self,max_requests,max_seconds):
        self.deadline=time.monotonic()+max_seconds;self.limit=max_requests;self.requests=0
    def request(self,path,params,name):
        if self.requests>=self.limit or time.monotonic()>=self.deadline:
            raise RuntimeError(f'{name} PR inspection budget exhausted; unfinished PRs will be retried')
        self.requests+=1
        return api(path,params,deadline=self.deadline)
    def spent(self):return self.requests>=self.limit or time.monotonic()>=self.deadline

def scan(repo,since,states,budget,out,family=None):
    """Check one repo's PRs; return False when the budget stopped the scan."""
    name='CrocSwap' if repo==REPO else repo
    done=set()
    def inspect(pr):
        number=str(pr['number']);old=states.get(number,{})
        head=pr['head']['sha']
        body=(pr.get('title') or '')+'\n'+(pr.get('body') or '')
        revision=hashlib.sha256((head+'\n'+body).encode()).hexdigest()
        if old.get('revision')==revision:return
        documents=[('PR body',body)];complete=True;finished=False
        next_page=old.get('next_file_page',1) if old.get('pending_revision')==revision else 1
        try:
            for file_page in range(next_page,min(next_page+3,31)):
                files=budget.request(f'repos/{repo}/pulls/{number}/files',dict(per_page=100,page=file_page),name)
                for file in files:
                    # Family repos state claims in titles, bodies and notes; their Lean
                    # diffs repeat statement constants and only add noise.
                    if file.get('status')=='removed' or not re.search(r'\.(?:md|tex)$' if family else r'\.(?:md|tex|lean)$',file['filename'],re.I):continue
                    # Copied dependency trees are not the PR author's new claims.
                    if DEPENDENCY_DIRS.intersection(file['filename'].split('/')[:-1]):continue
                    if 'patch' not in file:
                        out['errors'].append(f'{repo} PR #{number}: missing diff patch '+file['filename'])
                        complete=False;continue
                    documents.append((file['filename'],'\n'.join(line[1:] for line in file['patch'].splitlines() if line.startswith('+') and not line.startswith('+++'))))
                next_page=file_page+1
                if len(files)<100:
                    finished=True;break
            else:
                out['truncated'].append(dict(query=f'{repo} PR #{number} files',total_count=f'continued through page {next_page-1}; at most 300 files per cycle'))
                complete=False
                # GitHub only exposes the first 3000 changed files.
                if next_page>30:finished=True
        except (RuntimeError,ValueError) as error:
            out['errors'].append(str(error));complete=False
        claims={};paths={}
        for path,document in documents:
            for label,lines in source_claims(document,family and 'family:'+family).items():
                # In a family's own repo, every claim is about that family.
                label='family:'+family if family else label
                claims.setdefault(label,[]).extend(lines)
                paths.setdefault(label,[]).append(path)
        seen=list(old.get('seen_claims',[]))
        for label,lines in claims.items():
            lines=list(dict.fromkeys(lines));key=claim_key(label,lines)
            if not key or key in seen:continue
            fam=label.removeprefix('family:') if label.startswith('family:') else None
            problem=f"Family {fam}: {FAMILIES[fam]['title']}" if fam else label
            out['candidates'].append(dict(repo=repo,url=pr['html_url'],pr_number=pr['number'],author=pr['user']['login'],created_at=pr['created_at'],pushed_at=pr['updated_at'],stars=0,rank=25,description=pr['title'],problem_guess=problem,readme_commit=head,source_claim_evidence=lines[:8],source_claim_files=paths[label],claim_signature=key,cross_problem_pr=True,other_family=fam,stated_bound_changed=True,likely_tracked_source=True,likely_new_race=False,likely_pivot=True,on_board=True,evidence=['recent-family-pr' if family else 'recent-crocswap-pr'],coverage_complete=complete))
            seen.append(key)
        # Resume file pagination; do not spend each cycle on the first 300 files.
        states[number]=dict(revision=revision if finished else None,pending_revision=revision,next_file_page=next_page,head=head,seen_claims=seen,updated_at=pr['updated_at'])
        out['checked'].append(pr['number'] if repo==REPO else f'{repo}#{number}')
    def stop():
        if not budget.spent():return False
        out['truncated'].append(dict(query=repo+' PR inspection budget',total_count=f'at most {budget.limit} GETs / {MAX_SECONDS} seconds; more PRs may remain'))
        return True
    if family:
        # An open PR can hold a claim for days without an update.
        try:batch=budget.request(f'repos/{repo}/pulls',dict(state='open',sort='updated',direction='desc',per_page=100),name)
        except (RuntimeError,ValueError) as error:
            out['errors'].append(str(error));return False
        for pr in batch:
            inspect(pr);done.add(pr['number'])
            if stop():return False
    for page in range(1,11):
        try:
            batch=budget.request(f'repos/{repo}/pulls',dict(state='all',sort='updated',direction='desc',per_page=100,page=page),name)
        except (RuntimeError,ValueError) as error:
            out['errors'].append(str(error));break
        for pr in batch:
            if pr['updated_at']<since or pr['number'] in done:continue
            inspect(pr)
            if stop():return False
        if len(batch)<100 or (batch and batch[-1]['updated_at']<since):break
    else:out['truncated'].append(dict(query=repo+' recent PRs',total_count='at least 1000 PRs'))
    return True

def collect(since,previous):
    """CrocSwap PRs only, with the full PR budget."""
    states=json.loads(json.dumps(previous.get('crocswap_pr_states',{})))
    out=dict(candidates=[],errors=[],truncated=[],checked=[])
    budget=Budget(MAX_REQUESTS,MAX_SECONDS)
    scan(REPO,since,states,budget,out)
    return dict(out,states=states,requests=budget.requests)

def collect_all(since,previous):
    """Family upstream PRs first (at most FAMILY_MAX_REQUESTS), then CrocSwap,
    together within MAX_REQUESTS GETs and MAX_SECONDS."""
    states=json.loads(json.dumps(previous.get('crocswap_pr_states',{})))
    family_states=json.loads(json.dumps(previous.get('family_pr_states',{})))
    out=dict(candidates=[],errors=[],truncated=[],checked=[])
    budget=Budget(FAMILY_MAX_REQUESTS,MAX_SECONDS)
    for repo,family in FAMILY_PR_REPOS.items():
        if not scan(repo,since,family_states.setdefault(repo,{}),budget,out,family):break
    budget.limit=MAX_REQUESTS
    scan(REPO,since,states,budget,out)
    return dict(out,states=states,family_states=family_states,requests=budget.requests)
