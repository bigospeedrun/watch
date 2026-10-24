#!/usr/bin/env python3
"""Watch platypii/integer-mult-bounds-lean for three Lean milestones (Nil ask, 2026-10-15).

Each watch cycle reads the head commit; when it changed, it downloads the source
tarball (one GitHub API GET), reads README.md and every .lean file in memory
(nothing is extracted or run) and sends BOS Lead Dev one short alert, with the
commit, when:
  1. the native multitape target IntegerMultBounds.Machine.EndToEnd (saving
     83/10^12) looks proved: the README stops calling it open, its Status section
     changes and names the target, or a Lean declaration has type EndToEnd
     (the alert says whether that file contains sorry);
  2. the proved kappa in the README changes (2^-37 when this watch started), including
     values that came and went between two cycles: the watch reads README.md at each
     commit since the last seen head (3213/2^44 lived 19:40-21:11Z on 2026-10-17,
     between the 19:04Z and 22:04Z cycles, and was missed);
  3. a Lean proof of the FinTM2-to-multitape simulation appears: a declaration
     from FinTM2 or MathlibTM2.Statement to Machine or EndToEnd, or a file named
     for that simulation.
The scan covers the whole tree (3525 .lean files, 9 MB, on 2026-10-15), so large
diffs cannot hide a change; each finding is sent once.
State (last commit, kappa, README markers, sent alerts) is in the local
.git/lean-target-watch.json. stdout holds counts only.
"""
import argparse
import hashlib
import io
import json
import re
import subprocess
import tarfile
from pathlib import Path
from github_read import api, content
MAX_WALK=100  # newest commits read between two cycles (one contents GET each). 30 was too low: 32 commits came between two cycles on 2026-10-24.

ROOT=Path(__file__).resolve().parent
STATE='.git/lean-target-watch.json'
REPO='platypii/integer-mult-bounds-lean'
BASE_KAPPA='2^-37'  # the lead's 2026-10-15 note; the first run reports any later change
DECL=r'(?:theorem|lemma|def|abbrev|instance|noncomputable\s+def)\s+[\w.\'«»]+'
# EndToEnd must be the declaration's result type: followed by :=, where or line end.
END_TO_END=re.compile(DECL+r'[^=]{0,300}?:\s*(?:IntegerMultBounds\.)?(?:Machine\.)?EndToEnd[ \t]*(?::=|where\b|$)',re.M)
SIMULATION=[re.compile(p) for p in (
    DECL+r'[^\n]{0,200}(?:FinTM2|MathlibTM2\.Statement|\bStatement\b)[^\n]{0,200}→[^\n]{0,120}(?:Machine\b|EndToEnd|[Mm]ultitape)',
    r'(?:theorem|lemma|def)\s+[\w.\']*(?:[Ff]inTM2[Tt]o(?:Machine|Multitape|Native)|[Tt]o[Mm]ultitape|[Ee]nd[Tt]o[Ee]nd_of_(?:statement|finTM2|mathlib))[\w.\']*',
    DECL+r'[^=\n]{0,200}\bFinTM2\b[^=\n]{0,200}\)\s*:\s*[^=\n]{0,80}\bMachine\.')]
SIM_PATH=re.compile(r'(?:FinTM2To|ToMultitape|MultitapeSim|SimulateFinTM2|FinTM2Sim)',re.I)

def kappa(readme):
    match=re.search(r'(?:kappa|κ)\s*=\s*`?\s*([0-9][0-9^/{}.\-]*)',readme)
    return match.group(1).rstrip('.,') if match else None

def status_section(readme):
    match=re.search(r'^## Status\s*$(.*?)(?=^## |\Z)',readme,re.M|re.S)
    return match.group(1).strip() if match else ''

def target_open(readme):
    # The README states the 83/10^12 saving as open (or a proposition to be proved).
    return any(re.search(r'83/10\^12|83/10\^\{12\}',s) and re.search(r'\bopen\b|to be proved|not a theorem',s,re.I)
               for s in re.split(r'(?<=\.)\s+',readme))

def readme_signals(old,new):
    out=[]
    if new['kappa']!=old.get('kappa'):
        out.append(('kappa:'+str(new['kappa']),f"README kappa changed from {old.get('kappa')} to {new['kappa']}"))
    if old.get('target_open',True) and not new['target_open']:
        out.append(('target-open-gone','README no longer calls the 83/10^12 EndToEnd target open'))
    if old.get('status_hash') and new['status_hash']!=old['status_hash'] and re.search(r'EndToEnd|83/10|multitape|native',new['status'],re.I):
        first=next((l for l in new['status'].splitlines() if l.strip()),'')[:200]
        out.append(('status:'+new['status_hash'],'README Status section changed and names the target: "'+first+'"'))
    return out

def tree_signals(files):
    """Scan (path, text) pairs of .lean files for the target and simulation."""
    out=[]
    for name,text in files:
        if SIM_PATH.search(name):
            out.append(('sim-file:'+name,f'file named for the FinTM2-to-multitape simulation: {name}'))
        code=re.sub(r'/-.*?-/','',text,flags=re.S)
        code=re.sub(r'--[^\n]*','',code)
        for m in END_TO_END.finditer(code):
            decl=' '.join(m.group(0).split())[:160]
            sorry='file contains sorry' if re.search(r'\bsorry\b',code) else 'no sorry in the file'
            out.append(('endtoend:'+name+':'+decl,f'Lean declaration of type EndToEnd in {name} ({sorry}): {decl}'))
        for pattern in SIMULATION:
            for m in pattern.finditer(code):
                decl=' '.join(m.group(0).split())[:160]
                out.append(('sim:'+name+':'+decl,f'possible FinTM2-to-multitape simulation in {name}: {decl}'))
    return out

def tarball(sha):
    """Download the source tarball (API GET) and return README text and .lean files."""
    out=subprocess.run(['gh','api','--method','GET',f'repos/{REPO}/tarball/{sha}'],capture_output=True,timeout=300)
    if out.returncode:raise RuntimeError('GitHub tarball GET failed')
    readme='';files=[]
    with tarfile.open(fileobj=io.BytesIO(out.stdout),mode='r:gz') as tf:
        for m in tf:
            # Members are read in memory only; paths are names, never written.
            if not m.isfile():continue
            name=m.name.split('/',1)[1] if '/' in m.name else m.name
            if name=='README.md':readme=tf.extractfile(m).read().decode('utf-8','replace')
            elif name.endswith('.lean'):files.append((name,tf.extractfile(m).read().decode('utf-8','replace')))
    return readme,files

def snapshot(readme):
    status=status_section(readme)
    return dict(kappa=kappa(readme),target_open=target_open(readme),status=status,
                status_hash=hashlib.sha256(status.encode()).hexdigest()[:16])

def walk_kappas(get,readme_at,old_head,head):
    """([(sha, kappa)], skipped) for the commits after old_head up to head, oldest first:
    the README kappa at each of the MAX_WALK newest (head excluded: the tarball covers
    it); skipped counts older commits not read. A commit whose README cannot be read gives
    kappa None; a failed compare (for example after a force-push) gives no walk."""
    try:
        commits=[c['sha'] for c in get(f'repos/{REPO}/compare/{old_head}...{head}').get('commits',[])]
    except Exception:
        return [],0
    walk=commits[:-1]
    out=[]
    for sha in walk[-MAX_WALK:]:
        try:value=kappa(readme_at(sha))
        except Exception:value=None
        out.append((sha,value))
    return out,max(0,len(walk)-MAX_WALK)

def run(get,fetch,notify,root=None,dry_run=False,readme_at=None):
    root=root or ROOT;path=root/STATE
    state=json.loads(path.read_text()) if path.exists() else {}
    head=get(f'repos/{REPO}/commits/HEAD')['sha']
    if head==state.get('head'):return {'status':'ok','changed':False,'alerts':0}
    readme,files=fetch(head)
    if not readme or not files:raise ValueError('README or Lean files missing from the tarball')
    new=snapshot(readme)
    old=state.get('readme') or {'kappa':BASE_KAPPA,'target_open':True}
    signals=[]
    # Values between the last seen head and this one, each with the commit that first had it.
    if state.get('head') and readme_at:
        previous=old.get('kappa')
        walked,skipped=walk_kappas(get,readme_at,state['head'],head)
        if skipped:
            signals.append(('skipped:'+head,f'{skipped} earlier commits since the last cycle were not read for README kappa values'))
        for sha,value in walked:
            if value and value!=previous:
                signals.append(('kappa:'+value,f'README kappa changed from {previous} to {value} at {sha[:10]} (between two watch cycles)'))
                previous=value
        old=dict(old,kappa=previous)
    signals+=readme_signals(old,new)+tree_signals(files)
    sent=set(state.get('sent',[]))
    fresh=list(dict((k,t) for k,t in signals if k not in sent).items())
    if fresh and not dry_run:
        url=f'https://github.com/{REPO}/commit/{head}'
        notify(f'{REPO} at {head[:10]} ({url}): '+'; '.join(t for _,t in fresh)+'.',f'lean-target-{head[:12]}')
        sent.update(k for k,_ in fresh)
    if not dry_run:
        state.update(head=head,readme={k:v for k,v in new.items() if k!='status'},sent=sorted(sent)[-500:])
        tmp=path.with_name(path.name+'.tmp');tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(path)
    return {'status':'ok','changed':True,'alerts':len(fresh),'lean_files':len(files)}

def main():
    parser=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--dry-run',action='store_true',help='read GitHub; send and write nothing')
    args=parser.parse_args()
    def notify(text,identity):
        from poll import lead_notify
        lead_notify(text,identity,'lean-target')
    readme_at=lambda sha:content(REPO,'README.md',sha).decode('utf-8','replace')
    try:print(json.dumps(run(api,tarball,notify,dry_run=args.dry_run,readme_at=readme_at)))
    except Exception as error:
        print('Lean target watch failed: '+type(error).__name__)
        raise SystemExit(1)

if __name__=='__main__':main()
