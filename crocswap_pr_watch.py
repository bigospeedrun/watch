"""Read recent CrocSwap PR claims for problems outside integer multiplication.

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

def source_claims(text):
    """Keep a claim near its problem name, not an unrelated inherited number."""
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
        labels=names or section or [name for group in recent for name in group]
        lines=claim_lines(line)
        if not lines and re.search(r'\d',line) and re.search(r'\bkappa\b|κ|\bO\s*\(',line):lines=[line.strip()[:1000]]
        for claim in lines:
            for label in labels:
                found.setdefault(label,[]).append(claim)
    return found

def collect(since,previous):
    states=json.loads(json.dumps(previous.get('crocswap_pr_states',{})))
    rows=[];errors=[];truncated=[];checked=[]
    deadline=time.monotonic()+MAX_SECONDS
    requests=0
    def request(path,params):
        nonlocal requests
        if requests>=MAX_REQUESTS or time.monotonic()>=deadline:
            raise RuntimeError('CrocSwap PR inspection budget exhausted; unfinished PRs will be retried')
        requests+=1
        return api(path,params,deadline=deadline)
    for page in range(1,11):
        try:
            batch=request(f'repos/{REPO}/pulls',dict(state='all',sort='updated',direction='desc',per_page=100,page=page))
        except (RuntimeError,ValueError) as error:
            errors.append(str(error));break
        for pr in batch:
            if pr['updated_at']<since:continue
            number=str(pr['number']);old=states.get(number,{})
            head=pr['head']['sha']
            body=(pr.get('title') or '')+'\n'+(pr.get('body') or '')
            revision=hashlib.sha256((head+'\n'+body).encode()).hexdigest()
            if old.get('revision')==revision:continue
            documents=[('PR body',body)];complete=True;finished=False
            next_page=old.get('next_file_page',1) if old.get('pending_revision')==revision else 1
            try:
                for file_page in range(next_page,min(next_page+3,31)):
                    files=request(f'repos/{REPO}/pulls/{number}/files',dict(per_page=100,page=file_page))
                    for file in files:
                        if file.get('status')=='removed' or not re.search(r'\.(?:md|tex|lean)$',file['filename'],re.I):continue
                        # Copied dependency trees are not the PR author's new claims.
                        if DEPENDENCY_DIRS.intersection(file['filename'].split('/')[:-1]):continue
                        if 'patch' not in file:
                            errors.append(f'{REPO} PR #{number}: missing diff patch '+file['filename'])
                            complete=False;continue
                        documents.append((file['filename'],'\n'.join(line[1:] for line in file['patch'].splitlines() if line.startswith('+') and not line.startswith('+++'))))
                    next_page=file_page+1
                    if len(files)<100:
                        finished=True;break
                else:
                    truncated.append(dict(query=f'{REPO} PR #{number} files',total_count=f'continued through page {next_page-1}; at most 300 files per cycle'))
                    complete=False
                    # GitHub only exposes the first 3000 changed files.
                    if next_page>30:finished=True
            except (RuntimeError,ValueError) as error:
                errors.append(str(error));complete=False
            claims={};paths={}
            for path,document in documents:
                for label,lines in source_claims(document).items():
                    claims.setdefault(label,[]).extend(lines)
                    paths.setdefault(label,[]).append(path)
            seen=list(old.get('seen_claims',[]))
            for label,lines in claims.items():
                lines=list(dict.fromkeys(lines));key=claim_key(label,lines)
                if not key or key in seen:continue
                family=label.removeprefix('family:') if label.startswith('family:') else None
                problem=f"Family {family}: {FAMILIES[family]['title']}" if family else label
                rows.append(dict(repo=REPO,url=pr['html_url'],pr_number=pr['number'],author=pr['user']['login'],created_at=pr['created_at'],pushed_at=pr['updated_at'],stars=0,rank=25,description=pr['title'],problem_guess=problem,readme_commit=head,source_claim_evidence=lines[:8],source_claim_files=paths[label],claim_signature=key,cross_problem_pr=True,other_family=family,stated_bound_changed=True,likely_tracked_source=True,likely_new_race=False,likely_pivot=True,on_board=True,evidence=['recent-crocswap-pr'],coverage_complete=complete))
                seen.append(key)
            # Resume file pagination; do not spend each cycle on the first 300 files.
            states[number]=dict(revision=revision if finished else None,pending_revision=revision,next_file_page=next_page,head=head,seen_claims=seen,updated_at=pr['updated_at'])
            checked.append(pr['number'])
            if requests>=MAX_REQUESTS or time.monotonic()>=deadline:
                truncated.append(dict(query=REPO+' PR inspection budget',total_count=f'at most {MAX_REQUESTS} GETs / {MAX_SECONDS} seconds; more PRs may remain'))
                return dict(candidates=rows,states=states,errors=errors,truncated=truncated,checked=checked,requests=requests)
        if len(batch)<100 or (batch and batch[-1]['updated_at']<since):break
    else:truncated.append(dict(query=REPO+' recent PRs',total_count='at least 1000 PRs'))
    return dict(candidates=rows,states=states,errors=errors,truncated=truncated,checked=checked,requests=requests)
