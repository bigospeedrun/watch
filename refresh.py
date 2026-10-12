#!/usr/bin/env python3
"""Refresh known races through gh GET only; validate a staging copy before publication."""
import copy, fcntl, hashlib, json, os, re, shutil, subprocess, tempfile
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from github_read import api, pages, content
ROOT = Path(__file__).resolve().parent
CROC = 'CrocSwap/integer-mult-bounds'
SWAP = 'Swapnil-jain/integer-mult-kappa'
IMPORTER_VERSION = 2

def dump(root, path, data):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

def load(root, path):
    return json.loads((root / path).read_text())

def artifact(root, path):
    return {'path': path, 'sha256': hashlib.sha256((root / path).read_bytes()).hexdigest()}

def best(problem):
    pool = [r for r in problem['records'] if r['id'].startswith('crocswap-') and problem['record_metadata'][r['id']]['eligible_for_record']]
    r = max(pool, key=lambda r: Fraction(r['score']))
    return {k: r[k] for k in ('id', 'score', 'title', 'submission_url')}

def title_score(title):
    title=title.translate(str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻','0123456789-'))
    title=re.sub(r'\s*[·×]\s*10\s*(?:\^\s*)?(-?\d+)',r'e\1',title)
    # A ceiling, supplier saving or multiple alternatives is not a multiplication claim.
    if re.search(r'no new|no κ|ceiling|effective bit saving|complex-only|not a witness|target,? not built', title, re.I):
        return None
    values = re.findall(r'(?:κ|kappa)\s*(?:=|to)?\s*(\d+(?:\.\d+)?(?:e-\d+)?(?:/10\^\d+)?)', title, re.I)
    if len(values) != 1:
        return None
    v = values[0]
    if '/10^' in v:
        a, b = v.split('/10^'); q = Fraction(a) / 10**int(b)
    else:
        q = Fraction(v)
    return str(q) if 0 < q < 1 else None

def refresh(stage, now):
    day = now[:10]
    problem = load(stage, 'integer-multiplication.json')
    before = copy.deepcopy(problem)
    subs = load(stage, 'submissions.json')
    old = {s['pr_number']: s for s in subs['items']}
    records = {r['id']: r for r in problem['records']}
    template = copy.deepcopy(records['crocswap-pr-61'])
    metadata = problem['record_metadata']
    mt = copy.deepcopy(metadata['crocswap-pr-61'])
    pulls = sorted(pages(f'repos/{CROC}/pulls', {'state': 'all', 'sort': 'created', 'direction': 'asc'}), key=lambda p: p['number'])
    assert len({p['number'] for p in pulls}) == len(pulls)
    assert set(old) <= {p['number'] for p in pulls}, 'PR coverage regressed'
    heads = {}
    repo_meta = {}
    for repo in (CROC, SWAP):
        meta = api(f'repos/{repo}')
        head = api(f'repos/{repo}/commits/{meta["default_branch"]}')
        # File diffs are unused metadata and can contain workstation paths.
        for changed_file in head.get('files', []):
            changed_file.pop('patch', None)
        heads[repo] = head
        repo_meta[repo] = meta
    fingerprint = hashlib.sha256(json.dumps({'importer_version':IMPORTER_VERSION,'heads': {repo: h['sha'] for repo,h in heads.items()}, 'pulls': [{k:p[k] for k in ('number','title','body','updated_at','merged_at','closed_at','state')} | {'head_sha':p['head']['sha']} for p in pulls]}, sort_keys=True).encode()).hexdigest()
    if load(stage, 'sources/intake.json').get('fingerprint') == fingerprint:
        return dict(checked_at=now,new_prs=[],new_merged_records=[],previous_record=best(before),current_record=best(before),new_current_record=False,unparsed_new_prs=[])
    dump(stage, 'sources/crocswap-pulls.json', pulls)
    for repo, head in heads.items():
        meta = repo_meta[repo]
        prefix = 'sources/' + repo.replace('/', '__')
        dump(stage, prefix + '__repo.json', meta)
        dump(stage, prefix + '__head.json', head)
        (stage / (prefix + '__README.md')).write_bytes(content(repo, 'README.md', head['sha']))
    items = []
    new_merged = []
    for p in pulls:
        n = p['number']; prior = old.get(n)
        status = 'merged' if p['merged_at'] else 'open' if p['state'] == 'open' else 'closed-unmerged'
        score = title_score(p['title'])
        if prior and prior['title']==p['title'] and prior['claimed_score'] is not None and not re.search(r'[·×⁻]|not a witness|target,? not built',p['title'],re.I):
            score=prior['claimed_score']
        # Preserve early manually reviewed multi-score submissions.
        if n<=44 and prior and prior['title']==p['title']:score=prior['claimed_score']
        ids = list(prior['record_ids']) if prior and prior['record_ids'] and score else ([f'crocswap-pr-{n}'] if score else [])
        ap = f'sources/pr-{n}.json'
        dump(stage, ap, {k: p[k] for k in ['number','html_url','title','body','created_at','updated_at','closed_at','merged_at','state']})
        item = dict(pr_number=n, author=p['user']['login'], author_url=p['user']['html_url'], title=p['title'], url=p['html_url'], submitted_at=p['created_at'], updated_at=p['updated_at'], source_commit=p['head']['sha'], upstream_status=status, upstream_status_at=p['merged_at'] or p['closed_at'] or p['created_at'], checked_at=day, claimed_score=score, record_ids=ids, note=(prior['note'] if prior and prior['title']==p['title'] else None) if score else 'No unique supported headline score; retained for review.')
        items.append(item)
        if status == 'merged' and ids and (not prior or prior['upstream_status'] != 'merged'):
            new_merged.extend(ids)
        for rid in ids:
            r = records.get(rid, copy.deepcopy(template))
            m = metadata.get(rid, copy.deepcopy(mt))
            new = rid not in records
            r.update(id=rid, score=r['score'] if rid.endswith('-stacked') else score, title=p['title'], submitted_at=p['created_at'], upstream_status=status, upstream_status_at=item['upstream_status_at'], source_commit=p['head']['sha'], source={'kind':'repo-artifact','url':p['html_url']}, submission_url=p['html_url'], artifact=artifact(stage, ap), authors=[{'name':p['user']['login'],'url':p['user']['html_url']}])
            if new:
                r['site_observed_at'] = now
            r['predecessors'] = [f'https://github.com/{CROC}/pull/{x}' for x in sorted({int(x) for x in re.findall(r'(?<!\w)#(\d+)\b', p['body'] or '') if 0<int(x)<n})]
            r['evidence']['paper_url'] = p['html_url']
            for d in r['dependencies']:
                d['source_url'] = p['html_url']
            m.update(checked_at=day, source_url=p['html_url'], pr_number=n, merged=bool(p['merged_at']), merged_at=p['merged_at'], closed_at=p['closed_at'], updated_at=p['updated_at'], eligible_for_record=bool(p['merged_at']), upstream_selected=False, publication_date=p['created_at'], publication_source_url=p['html_url'], race_event_at=p['created_at'])
            if new:
                m.pop('upstream_readme', None)
                m['score_source'] = 'PR title; exact displayed value, source claim only'
            records[rid] = r; metadata[rid] = m
        for rid in prior['record_ids'] if prior else []:
            if rid not in ids:
                records.pop(rid, None); metadata.pop(rid, None)
    # A maintainer can publish a reviewed integration without merging its source PR.
    head = heads[CROC]; sha = head['sha']
    raw = content(CROC, 'certificates/selected-result.json', sha)
    selected = json.loads(raw)
    score = str(Fraction(selected['kappa']))
    ap = f'sources/crocswap-selected-{sha}.json'; (stage / ap).write_bytes(raw)
    cert = selected['certificate']
    cert_raw = content(CROC, cert, sha)
    assert hashlib.sha256(cert_raw).hexdigest() == selected['certificate_sha256'], 'Selected certificate hash mismatch'
    (stage / f'sources/crocswap-certificate-{sha}.json').write_bytes(cert_raw)
    rid = 'crocswap-selected-' + hashlib.sha256((score + ':' + selected['certificate_sha256']).encode()).hexdigest()[:16]
    if rid not in records:
        r = copy.deepcopy(template); url = f'https://github.com/{CROC}/blob/{sha}/certificates/selected-result.json'
        r.update(id=rid, score=score, title='CrocSwap reviewed conditional result: ' + score, submitted_at=head['commit']['committer']['date'], site_observed_at=now, upstream_status='not-applicable', upstream_status_at=head['commit']['committer']['date'], source_commit=sha, source={'kind':'repo-artifact','url':url}, submission_url=url, artifact=artifact(stage,ap), authors=[{'name':'CrocSwap community','url':f'https://github.com/{CROC}'}], predecessors=[f'https://github.com/{CROC}/pull/{n}' for n in selected['source_prs']])
        r['evidence']['paper_url']=url
        r['dependencies']=[{'id':'openai-109-transfer','statement':selected['scope'],'source_url':url,'status':'unverified'}]
        records[rid]=r
        metadata[rid]=dict(checked_at=day,source_url=url,site_badge=False,eligible_for_record=True,proof_status=selected['status']+'; not independently rerun',comparison_key='crocswap/integer-multiplication-v1',race_repo=CROC,repo=CROC,upstream_tier='claimed',site_tier='claimed',publication_date_precision='date-time',date_precision='Snapshot commit time; not scientific priority',source_prs=selected['source_prs'])
    for key,m in metadata.items():
        if key.startswith('crocswap-'): m['upstream_selected'] = key==rid
    # Parse the first displayed exact rational in the related repository's README.
    head=heads[SWAP]; sha=head['sha']; readme=(stage/'sources/Swapnil-jain__integer-mult-kappa__README.md').read_text()
    match=re.search(r'\\kappa\s*=\s*\\frac\{(\d+)\}\{(?:10\^\{(\d+)\}|(\d+))\}',readme)
    if not match: raise ValueError('Swapnil headline format changed; last good bundle retained')
    score=str(Fraction(int(match[1]),10**int(match[2]) if match[2] else int(match[3])))
    rid='swapnil-snapshot-'+hashlib.sha256(score.encode()).hexdigest()[:16]
    if not any(r['id'].startswith('swapnil-') and r['score']==score for r in records.values()):
        r=copy.deepcopy(records['swapnil-round-7']); m=copy.deepcopy(metadata['swapnil-round-7'])
        ap=f'sources/swapnil-{sha}-README.md';(stage/ap).write_text(readme)
        url=f'https://github.com/{SWAP}/blob/{sha}/README.md'
        r.update(id=rid,score=score,title='Swapnil Jain current conditional witness: '+score,source_commit=sha,submitted_at=head['commit']['committer']['date'],site_observed_at=now,upstream_status_at=head['commit']['committer']['date'],source={'kind':'repo-artifact','url':url},submission_url=url,artifact=artifact(stage,ap))
        r['evidence']['paper_url']=url
        r['dependencies']=[{'id':'swapnil-transfer','statement':'Retained OpenAI reduction and source-specific proof interfaces in the pinned README; not independently checked.','source_url':url,'status':'unverified'}]
        m.update(checked_at=day,source_url=url,eligible_for_record=False,date_precision='Snapshot commit timestamp; not scientific priority')
        records[rid]=r;metadata[rid]=m
    problem.update(records=list(records.values()),checked_at=day,updated_at=now)
    subs.update(items=items,checked_at=day)
    dump(stage,'integer-multiplication.json',problem);dump(stage,'submissions.json',subs)
    reg=load(stage,'registry.json');reg['checked_at']=day;reg['updated_at']=now
    for listing in reg['repositories']:
        if listing['repo'] in heads:
            listing['checked_at']=day
            path=listing['manifest_source']['path'];manifest=load(stage,path)
            manifest['rules_url']=f"https://github.com/{listing['repo']}/blob/{heads[listing['repo']]['sha']}/"+('CONTRIBUTING.md' if listing['repo']==CROC else 'README.md')
            dump(stage,path,manifest);listing['rules_url']=manifest['rules_url'];listing['manifest_source']['revision']='sha256:'+artifact(stage,path)['sha256']
    dump(stage,'registry.json',reg)
    dump(stage,'sources/intake.json',dict(checked_at=day,assembled_at=now,pulls_source=f'https://api.github.com/repos/{CROC}/pulls',count=len(pulls),fingerprint=fingerprint))
    return dict(checked_at=now,new_prs=[p['number'] for p in pulls if p['number'] not in old],new_merged_records=new_merged,previous_record=best(before),current_record=best(problem),new_current_record=best(before)!=best(problem),unparsed_new_prs=[s['pr_number'] for s in items if s['pr_number'] not in old and s['claimed_score'] is None])

def git_state_dir():
    return Path(subprocess.check_output(['git','rev-parse','--absolute-git-dir'],cwd=ROOT,text=True).strip())

def main():
    state = git_state_dir()
    with (state/'refresh.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        tracked=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
        dirty=subprocess.check_output(['git','diff','--relative','--name-only','HEAD','--','.'],cwd=ROOT,text=True).splitlines()
        if any(p.endswith('.json') or p.startswith('sources/') for p in dirty):
            raise RuntimeError('Data has uncommitted edits; commit or review them before refresh')
        originals={p:(ROOT/p).read_bytes() for p in tracked if (ROOT/p).is_file()}
        with tempfile.TemporaryDirectory(prefix='.refresh-',dir=state) as temp:
            stage=Path(temp)
            for p,raw in originals.items():
                (stage/p).parent.mkdir(parents=True,exist_ok=True);(stage/p).write_bytes(raw)
            now=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
            summary=refresh(stage,now)
            subprocess.run(['python3',str(stage/'validate.py')],check=True,cwd=stage)
            changed=[]
            for path in sorted(stage.rglob('*')):
                if not path.is_file():continue
                rel=path.relative_to(stage).as_posix();raw=path.read_bytes()
                if originals.get(rel)==raw:continue
                target=ROOT/rel
                if target.exists() and target.read_bytes()!=originals.get(rel):raise RuntimeError('Concurrent edit: '+rel)
                changed.append((rel,raw))
            for rel,raw in changed:
                target=ROOT/rel;target.parent.mkdir(parents=True,exist_ok=True)
                temp_path=target.with_name(target.name+'.refresh-tmp');temp_path.write_bytes(raw);os.replace(temp_path,target)
            summary['changed_files']=[p for p,_ in changed]
            dump(state,'refresh-summary.json',summary)
            print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
