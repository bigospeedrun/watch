#!/usr/bin/env python3
"""Data-only importer. Never imports or runs upstream code."""
import json, re, hashlib
from pathlib import Path
from fractions import Fraction
from datetime import datetime, timezone
ROOT=Path(__file__).parent
CHECK='2026-10-08'
OBS=json.loads((ROOT/'sources/intake.json').read_text())['assembled_at']
def write(path,data):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def rat(s): return str(Fraction(s))
def evidence(name,url,description):
 p='sources/'+name+'.json';write(p,dict(url=url,checked_at=CHECK,description=description));return {'path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()}
def record(id,score,title,authors,url,artifact,commit=None,tier='claimed',theorem=None,kind='improvement',date=None):
 r=dict(id=id,kind=kind,score=rat(score),tier=tier,submitted_at=date or OBS,upstream_status='not-applicable',upstream_status_at=OBS,site_observed_at=OBS,source={'kind':'repo-artifact' if commit else 'paper','url':url},spec_version='1',title=title,authors=[{'name':n,'url':u} for n,u in authors],predecessors=[],submission_url=url,artifact=artifact,evidence={'paper_url':url,'theorem':theorem,'certificate_path':None},dependencies=[])
 if commit:r['source_commit']=commit
 return r
END='https://github.com/anthropics/formal-math/blob/e1a4e6508154ea59f030480661590a9fe3018011/3sum-apsp/EndStatement.lean'
ANTH='e1a4e6508154ea59f030480661590a9fe3018011'
MODELS={
'3sum':('word-ram','Deterministic decision on n integers, three distinct positions. For every fixed k, input magnitude at most n^k. One fixed program for each k; correctness for every word width W >= b(floor(log2 n)+1). Signed fixed-width addition, subtraction, multiplication, indirect load/store and branch are unit-cost steps.',END,'time-exponent','alpha','Worst-case O(n^alpha).','lower-is-better','2'),
'apsp':('word-ram','Deterministic directed APSP with polynomially bounded integer weights and no negative cycles. Same fixed-width word RAM and quantifiers as EndStatement. Input edge-presence and weight matrices; output reachability flags and distances for every ordered pair.',END,'time-exponent','alpha','Worst-case O(n^alpha).','lower-is-better','3'),
'subset-sum':('randomized-word-ram','Positive integers a_1,...,a_n and nonnegative target t, n>=2; repeats and empty subset allowed. Let b be maximum input/target bit length. Word RAM has w=ceil(4(n+b+log2(n+2))) bits. Reads/writes, indirect addressing, comparison, arithmetic including multiply/divide/remainder, bitwise operations and shifts cost one word operation; overflow uses charged multiple operations. Independent uniform w-bit random word costs one operation; one-way randomness with retained words charged to memory. One finite program for all n,b, no advice or external tables; all preprocessing and input access charged. Halts on every run, correct with probability at least 2/3 for every fixed input. For every fixed c and b<=n^c, every random outcome costs O(2^(0.49n)); program does not depend on c.','https://github.com/openai/math/tree/fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb/preprints/Subset-Sum-in-Time-2-power-0-49n-October-4-2026','exponential-time-exponent','alpha','Worst-case over random outcomes O(2^(alpha n)), for each fixed polynomial input-bit bound b<=n^c; per-input success probability at least 2/3.','lower-is-better','1/2'),
'integer-multiplication':('multitape-tm','Multiply two n-bit integers on a fixed finite-alphabet Turing machine with a fixed number of one-dimensional tapes. Community witnesses remain conditional on the OpenAI #109 framework and their stated transfer interfaces.','https://github.com/CrocSwap/integer-mult-bounds','log-saving','kappa','Worst-case O(n (log n)^(1-kappa)).','higher-is-better','0'),
'exact-dft':('uniform-exact-arithmetic','Fixed deterministic programs for every positive n. Exact canonical DFT and full convolution over complex vectors. Root of unity supplied; unrestricted coefficients and exact complex arithmetic. Polynomially bounded integer values and indices. Cost includes root-order selection and scalar preparation. Excludes bit complexity and the separate subsequential circuit result.','https://github.com/openai/math/blob/fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb/lean/docs/130.md','log-saving','kappa','Arithmetic work O(n (log n)^(1-kappa)) for every positive length.','higher-is-better','0'),
'directed-sssp':('comparison-addition-sparse','Uniform deterministic exact directed SSSP with nonnegative real weights in the source RAM/comparison-addition model. Improved branch requires m <= n F(n), F(n)=floor(floor(log2 n)^(3/4)). Score applies only on that density profile. Bellman-Ford fallback outside it; no general-density improvement claimed.','https://github.com/spicylemonade/c-hd-proof/blob/98c53accb47a505482a1781597ae14bf67e81cec/README.md','log-time-exponent','alpha','Worst-case O(n (log n)^alpha) on m <= n floor(floor(log2 n)^(3/4)).','lower-is-better','1')}
BASES={
'3sum':('Gajentaan and Overmars (1995), classical quadratic 3SUM','https://www.sciencedirect.com/science/article/pii/0925772195000222'),
'apsp':('Robert W. Floyd (1962), Algorithm 97: Shortest path','https://doi.org/10.1145/367766.368168'),
'subset-sum':('Ellis Horowitz and Sartaj Sahni (1974), Computing Partitions with Applications to the Knapsack Problem','https://doi.org/10.1145/321812.321823'),
'integer-multiplication':('David Harvey and Joris van der Hoeven (2019 preprint; 2021 journal), Integer multiplication in time O(n log n)','https://annals.math.princeton.edu/2021/193-2/p04'),
'exact-dft':('Cooley and Tukey (1965), FFT; Bluestein (1970), all-length reduction','https://doi.org/10.1090/S0025-5718-1965-0178586-1'),
'directed-sssp':('Fredman and Tarjan (1987), Fibonacci heaps and their uses in improved network optimization algorithms','https://doi.org/10.1145/28869.28874')}
problems={}
for slug,(model,scope,url,sid,sym,definition,direction,base) in MODELS.items():
 title,burl=BASES[slug];a=evidence(slug+'-baseline',burl,title)
 r=record('classical-baseline',base,title,[(title,burl)],burl,a,kind='baseline')
 problems[slug]=dict(schema_version=1,problem_id=slug+'/'+model,model={'id':model,'version':'1','description':scope,'definition_url':url},score={'id':sid,'version':'1','symbol':sym,'definition':definition,'direction':direction,'encoding':'rational-string','minimum':'0','maximum':base if direction=='lower-is-better' else '1'},checked_at=CHECK,sources=[{'url':url,'checked_at':CHECK}],records=[r],record_metadata={r['id']:{'checked_at':CHECK,'eligible_for_record':False,'proof_status':'Classical paper baseline; no site proof check.','date_precision':'Publication year in title; submitted_at is observation time, not an invented publication timestamp.'}})
for slug,value,name in [('3sum','2499/1250','endStatement_theorem_22_3SUM'),('apsp','149971/50000','endStatement_theorem_22_APSP')]:
 a=evidence(slug+'-anthropic',END,'EndStatement target; upstream README states the library proves this target. No site rerun.')
 r=record('anthropic-2026',value,'Anthropic formalization; Alman and Vassilevska Williams result', [('Josh Alman and Virginia Vassilevska Williams', 'https://arxiv.org/abs/2610.06783'),('Anthropic','https://github.com/anthropics/formal-math')],END,a,ANTH,'verified',name)
 r['evidence']['paper_url']='https://arxiv.org/abs/2610.06783';problems[slug]['records'].append(r);problems[slug]['record_metadata'][r['id']]={'checked_at':CHECK,'eligible_for_record':True,'proof_status':'proved upstream, not yet rerun by bigOspeedrun','site_badge':False,'source_url':END}
for slug,p in problems.items():write(slug+'.json',p)
entries=[]
for repo,slugs,mode in [('CrocSwap/integer-mult-bounds',['integer-multiplication'],'independent-read-only'),('Swapnil-jain/integer-mult-kappa',['integer-multiplication'],'related-read-only'),('anthropics/formal-math',['3sum','apsp'],'research-artifact'),('openai/math',['subset-sum','integer-multiplication','exact-dft'],'research-artifact'),('spicylemonade/c-hd-proof',['directed-sssp'],'research-artifact')]:
 meta=json.load(open(ROOT/('sources/'+repo.replace('/','__')+'__repo.json')))
 entries.append(dict(repo_id=meta['id'],repo=repo,owner=repo.split('/')[0],url=meta['html_url'],problem_ids=[problems[s]['problem_id'] for s in slugs],tracking_branch=meta['default_branch'],listing_mode=mode,opted_in=False,manifest_source={'kind':'registry','path':'registry.json','revision':'schema-v1-2026-10-08','editor':'BOS Worker 3'},admitted_at=CHECK,license_status='not-established' if repo.startswith('spicy') else 'Apache-2.0 at inspected snapshot',verification_profile=None,comparison_keys={s:problems[s]['problem_id']+'/v1/'+('conditional-unreviewed' if s=='integer-multiplication' else 'scope-v1') for s in slugs},checked_at=CHECK,source_url=meta['html_url']))
entries.append(dict(repo_id=None,repo='bigospeedrun/3sum',owner='bigospeedrun',url='https://github.com/bigospeedrun/3sum',problem_ids=['3sum/word-ram'],tracking_branch=None,listing_mode='planned',opted_in=False,manifest_source=None,admitted_at=None,license_status='planned',verification_profile=None,comparison_keys={'3sum':'3sum/word-ram/v1/scope-v1'},checked_at=CHECK,source_url=None))
write('registry.json',dict(schema_version=1,checked_at=CHECK,repositories=entries,problems=[{'slug':s,'problem_id':p['problem_id'],'data_file':s+'.json','status':'independent-race' if s=='integer-multiplication' else 'planned-race' if s=='3sum' else 'status-only','race_repo':'CrocSwap/integer-mult-bounds' if s=='integer-multiplication' else None} for s,p in problems.items()]))
# Imported data is a claim until the site's approved checker runs.
# Anthropic's two upstream-only verified labels are explicitly requested for launch.
def add(slug,r,**meta):
 p=problems[slug];p['records'].append(r);p['record_metadata'][r['id']]={'checked_at':CHECK,'source_url':r['source']['url'],'site_badge':False,'eligible_for_record':False,'proof_status':'Source claim; not independently rerun by bigOspeedrun',**meta}
def imported(slug,id,value,title,repo,commit,path,theorem=None,kind='improvement'):
 url=f'https://github.com/{repo}/blob/{commit}/{path}'
 a=evidence(id,url,title)
 return record(id,value,title,[(repo.split('/')[0],'https://github.com/'+repo.split('/')[0])],url,a,commit,theorem=theorem,kind=kind)
for slug,value,title,repo,commit,path,theorem in [
 ('subset-sum','49/100','OpenAI Subset Sum in Time O(2^(0.49n))','openai/math','fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb','preprints/Subset-Sum-in-Time-2-power-0-49n-October-4-2026/README.md',None),
 ('exact-dft','1/10000000000000','OpenAI uniform exact DFT power saving','openai/math','fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb','lean/docs/130.md',None),
 ('directed-sssp','11/12','C-HD uniform deterministic sparse-density SSSP','spicylemonade/c-hd-proof','98c53accb47a505482a1781597ae14bf67e81cec','README.md','Frontier.CHD.Final.chd_exact_within')]:
 r=imported(slug,slug+'-2026',value,title,repo,commit,path,theorem)
 add(slug,r,eligible_for_record=True,comparison_status='source scope only')

ps=sorted(json.load(open(ROOT/'sources/crocswap-pulls.json')),key=lambda p:p['number'])
manual={1:Fraction('1.7523184e-18'),2:Fraction(17,2**63),4:Fraction(591,10**12),10:Fraction(6149999,50000000000000),15:Fraction(1076678,10**12),20:Fraction(5834475279233921242758637328164947,5*10**39),41:Fraction('4.034168124e-5'),62:Fraction(4986133,10**11),83:Fraction(5164326938841,10**17)}
non_numeric={11:'No new bound; inherited PR #9 witness.',26:'Formal checks only; no new bound.',45:'Formal checks and integration; no new bound.',64:'Current PR is a verification inventory; it quotes several other PR values. No unique new headline.',73:'Withdrawn arithmetic note on PR #71; no separate construction.'}
def title_score(p):
 if p['number'] in manual:return manual[p['number']]
 t=p['title']; m=re.search(r'(\d+(?:\.\d+)?e-\d+)',t)
 if m:return Fraction(m[1])
 m=re.search(r'(\d+)/10\^(\d+)',t)
 if m:return Fraction(int(m[1]),10**int(m[2]))
 raise ValueError((p['number'],t))
submissions=[]
for p in ps:
 n=p['number'];status='merged' if p['merged_at'] else 'open' if p['state']=='open' else 'closed-unmerged'
 item=dict(pr_number=n,author=p['user']['login'],author_url=p['user']['html_url'],title=p['title'],url=p['html_url'],submitted_at=p['created_at'],updated_at=p['updated_at'],source_commit=p['head']['sha'],upstream_status=status,upstream_status_at=p['merged_at'] or p['closed_at'] or p['created_at'],checked_at=CHECK,claimed_score=None,record_ids=[],note=non_numeric.get(n))
 if n not in non_numeric:
  value=title_score(p);item['claimed_score']=str(value);id=f'crocswap-pr-{n}'
  # The raw PR is the claim artifact. README is separately pinned and hashed.
  ap=f'sources/pr-{n}.json';write(ap,{k:p[k] for k in ['number','html_url','title','body','created_at','updated_at','closed_at','merged_at','state']})
  a={'path':ap,'sha256':hashlib.sha256((ROOT/ap).read_bytes()).hexdigest()}
  r=record(id,str(value),p['title'],[(p['user']['login'],p['user']['html_url'])],p['html_url'],a,p['head']['sha'],date=p['created_at'])
  r.update(upstream_status=status,upstream_status_at=item['upstream_status_at'])
  # References credit dependencies; they do not assert proof or incorporation.
  refs=sorted(set(int(x) for x in re.findall(r'(?<!\w)#(\d+)\b',p['body'] or '') if 0<int(x)<n))
  r['predecessors']=[f'https://github.com/CrocSwap/integer-mult-bounds/pull/{x}' for x in refs]
  r['dependencies']=[{'id':'openai-109-transfer','statement':'The OpenAI #109 fixed-tape multiplication reduction and the specific all-size compiler, routing, precision, resampling and exact-recovery interfaces cited by this submission hold. The PR body retains its precise per-construction obligations.','source_url':p['html_url'],'status':'unverified'}]
  readme=ROOT/f'sources/pr-{n}-README.md'
  add('integer-multiplication',r,pr_number=n,repo='CrocSwap/integer-mult-bounds',merged=bool(p['merged_at']),merged_at=p['merged_at'],closed_at=p['closed_at'],updated_at=p['updated_at'],eligible_for_record=bool(p['merged_at']),comparison_key='crocswap/openai-109/per-pr-dependencies-unreviewed',comparison_status='Cross-construction dependency compatibility unchecked; numerical ordering is not a global record claim.',score_source='PR body' if n in manual and n not in [2,41,62] else 'PR title',upstream_readme={'path':str(readme.relative_to(ROOT)),'sha256':hashlib.sha256(readme.read_bytes()).hexdigest()},date_precision='PR creation timestamp; score is latest observed claim, not necessarily original score.')
  item['record_ids'].append(id)
  if n==62:
   r2=json.loads(json.dumps(r));r2['id']+='-stacked';r2['score']=str(Fraction(5101691,10**11));r2['title']+=' [stacked witness with PR #57]';add('integer-multiplication',r2,pr_number=n,repo='CrocSwap/integer-mult-bounds',eligible_for_record=True,comparison_key='crocswap/openai-109/per-pr-dependencies-unreviewed',comparison_status='Separate stacked construction; compatibility unchecked.');item['record_ids'].append(r2['id'])
 submissions.append(item)
write('submissions.json',{'schema_version':1,'checked_at':CHECK,'repo':'CrocSwap/integer-mult-bounds','source_url':'https://api.github.com/repos/CrocSwap/integer-mult-bounds/pulls','items':submissions})
# Earlier scalar checkpoints from the README history, before PR #1.
hist=[('frozen-154',Fraction(1,2**154)),('balanced-153',Fraction(1,2**153)),('same-network-129',Fraction(1,2**129)),('h46-111',Fraction(1,2**111)),('h46-109',Fraction(1,2**109)),('h46-108',Fraction(1,2**108)),('h46-rational',Fraction('5.8e-33')),('frozen-nonadjacent-107',Fraction(1,2**107)),('h46-nonadjacent-78',Fraction(1,2**78)),('h46-nonadjacent-76',Fraction(1,2**76)),('h46-shared-side-75',Fraction(1,2**75)),('h46-incidence-67',Fraction(1,2**67)),('h46-dag-63',Fraction(1,2**63)),('h46-shared-point',Fraction(13,2**66)),('h50-paired-59',Fraction(1,2**59)),('compact-control-34',Fraction(83,10**12)),('complex-compression-31',Fraction(1,2**31)),('ternary-30',Fraction(1,2**30))]
for name,value in hist:
 r=imported('integer-multiplication','crocswap-'+name,str(value),'CrocSwap historical '+name,'CrocSwap/integer-mult-bounds','d55bcd62ceb8f322bcf311a5a66e94c3ac7724f0','README.md')
 r['dependencies']=[{'id':'openai-109','statement':'The OpenAI #109 multiplication framework and this patch\'s retained analytic and fixed-tape transfer obligations hold.','source_url':r['source']['url'],'status':'unverified'}]
 add('integer-multiplication',r,repo='CrocSwap/integer-mult-bounds',eligible_for_record=False,date_precision='Checkpoint publication time unchecked; submitted_at is observation time.',comparison_key='crocswap/historical-conditional')
# Independent related listing. Keep its assumptions out of CrocSwap's winner.
repo='Swapnil-jain/integer-mult-kappa';sha=json.load(open(ROOT/'sources/Swapnil-jain__integer-mult-kappa__head.json'))['sha']
for name,v in [('round-1',Fraction(7499,10**12)),('round-3',Fraction(13086957581,3125*10**12)),('round-4',Fraction(59861145819,5*10**15)),('round-5',Fraction(309575208081,2*10**16)),('round-6',Fraction(3666565558019,10**17)),('round-7',Fraction(1599247689723,25*10**15))]:
 r=imported('integer-multiplication','swapnil-'+name,str(v),'Swapnil Jain '+name,repo,sha,'README.md')
 r['dependencies']=[{'id':'swapnil-transfer','statement':'The inherited OpenAI fixed-tape reduction, all-size transfer and source-specific interfaces hold; round seven also assumes stage two is the complement time-reversal of stage one.','source_url':r['source']['url'],'status':'unverified'}]
 add('integer-multiplication',r,repo=repo,comparison_key='swapnil/independent-assumptions-unreviewed',comparison_status='Related listing only; no reviewed compatibility with CrocSwap.',date_precision='Round publication time unchecked; submitted_at is observation time.')
write('chart-cross-check.json',{'checked_at':CHECK,'source_url':'https://x.com/RohanArun/status/2108207365199663189','tweet_access':'unchecked: web fetch failed','image_path':'../bigospeedrun/integer-multiplication-bounds.webp','image_sha256':json.loads((ROOT/'chart-cross-check.json').read_text())['image_sha256'],'image_inspected':True,'chart_pr_range':[1,44],'excluded_prs':[11,26],'numeric_count':42,'first_score':str(manual[1]),'last_score':str(title_score(ps[43])),'detailed_points':[{ 'pr_number':p['number'],'score':str(title_score(p)),'submitted_at':p['created_at']} for p in ps if 36<=p['number']<=44],'result':'42 numeric submissions reproduced from PRs 1 through 44. Nine detailed chart values and EDT minutes agree with GitHub UTC creation times. Chart is an earlier snapshot, not a priority proof.'})
for slug,p in problems.items():
 p['record_metadata']['classical-baseline']['eligible_for_record']=True
 write(slug+'.json',p)
# Original paper, before the community checkpoint history.
url='https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/preprints/Integer-multiplication-below-n-log-n-September-23-2026/build/sections/00-introduction.tex'
r=record('openai-original-109',str(Fraction(1,2**182)),'OpenAI original fixed-tape multiplication bound', [('OpenAI','https://github.com/openai/math')],url,{'path':'sources/mult-00-introduction.tex','sha256':hashlib.sha256((ROOT/'sources/mult-00-introduction.tex').read_bytes()).hexdigest()},'adc7f1241b42e322a6451854ab7e4b4c146bf78a')
add('integer-multiplication',r,eligible_for_record=False,comparison_key='openai/original-109',date_precision='Manuscript dated September 23, 2026; submitted_at is observation time.')
p=problems['integer-multiplication'];p['records']=[p['records'][0],r]+[x for x in p['records'] if x['id'].startswith('crocswap-') and not x['id'].startswith('crocswap-pr-')]+[x for x in p['records'] if x['id'].startswith('crocswap-pr-')]+[x for x in p['records'] if x['id'].startswith('swapnil-')]
# The scope comes from the manuscript, not a guess based on its short README.
p=problems['subset-sum'];scope_url='https://github.com/openai/math/blob/fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb/preprints/Subset-Sum-in-Time-2-power-0-49n-October-4-2026/build/sections/introduction.tex';p['model']['definition_url']=scope_url;p['sources'].append({'url':scope_url,'checked_at':CHECK});p['records'][1]['source']['url']=scope_url;p['records'][1]['evidence']['paper_url']=scope_url;p['records'][1]['artifact']={'path':'sources/subset-introduction.tex','sha256':hashlib.sha256((ROOT/'sources/subset-introduction.tex').read_bytes()).hexdigest()}
# Actual source access, not just DOI resolution.
classic_access={
 '3sum':('https://people.csail.mit.edu/virgi/6.s078/papers/gajovermars.pdf','opened paper mirror; publisher denied access'),
 'apsp':('https://algol60.org/acm/097.pdf','opened paper scan; DOI full text unchecked'),
 'subset-sum':('https://www.cise.ufl.edu/~sahni/papers/computingPartitions.pdf','author-hosted full text timed out; classic bound also stated in opened OpenAI introduction'),
 'integer-multiplication':('https://annals.math.princeton.edu/2021/193-2/p04','opened publisher abstract, including multitape model'),
 'exact-dft':('https://web.stanford.edu/class/cme324/classics/cooley-tukey.pdf','opened classic paper scan; Bluestein full text unchecked'),
 'directed-sssp':('https://web.eecs.umich.edu/~pettie/matching/Fredman-Tarjan-Fibonacci-Heaps.pdf','paper mirror timed out; original full text unchecked')}
for slug,(url,status) in classic_access.items():
 problems[slug]['sources'].append({'url':url,'checked_at':CHECK});problems[slug]['record_metadata']['classical-baseline']['source_access']=status
problems['exact-dft']['sources'].append({'url':'https://doi.org/10.1109/TAU.1970.1162132','checked_at':CHECK,'status':'Full text unchecked: browser challenge. All-length baseline uses Bluestein reduction with FFT; Cooley-Tukey alone is not the all-length source.'})
for slug,p in problems.items():write(slug+'.json',p)
# Verify independent round history against README commits rather than rounded prose.
history=json.loads((ROOT/'sources/swapnil-readme-history.json').read_text())
round_commits={1:history[-1],2:next(x for x in history if x['message'].startswith('Update README and notes for the 7499')),3:next(x for x in history if x['message'].startswith('Round three:')),4:next(x for x in history if x['message'].startswith('Round four:')),5:next(x for x in history if x['message'].startswith('Round five:')),6:next(x for x in history if x['message'].startswith('Round six:')),7:next(x for x in history if x['message'].startswith('Round seven:'))}
p=problems['integer-multiplication']
for r in p['records']:
 if r['id']=='swapnil-round-1':
  r['id']='swapnil-round-2';r['title']='Swapnil Jain round-2';p['record_metadata'][r['id']]=p['record_metadata'].pop('swapnil-round-1')
 if r['id'].startswith('crocswap-'):
  p['record_metadata'][r['id']]['eligible_for_record']=False
  p['record_metadata'][r['id']]['upstream_selected']=(r['id']=='crocswap-pr-61')
  p['record_metadata'][r['id']]['record_eligibility_note']='No cross-construction dependency compatibility review. Upstream status and numerical best remain visible.'
first=round_commits[1]
r=imported('integer-multiplication','swapnil-round-1',str(Fraction(249,5*10**10)),'Swapnil Jain round-1','Swapnil-jain/integer-mult-kappa',first['sha'],'README.md');add('integer-multiplication',r,repo='Swapnil-jain/integer-mult-kappa',comparison_key='swapnil/independent-assumptions-unreviewed',comparison_status='Related assumptions require separate review.')
for r in p['records']:
 if r['id'].startswith('swapnil-round-'):
  n=int(r['id'].split('-')[-1]);event=round_commits[n];r['source_commit']=event['sha'];r['source']['url']=f"https://github.com/Swapnil-jain/integer-mult-kappa/blob/{event['sha']}/README.md";r['submitted_at']=event['date'];p['record_metadata'][r['id']]['date_precision']='README commit committer timestamp, not scientific priority.'
p['records']=[r for r in p['records'] if not r['id'].startswith('swapnil-')]+sorted([r for r in p['records'] if r['id'].startswith('swapnil-')],key=lambda r:r['id'])
# Pin the source artifact for Anthropic's statement; the source does not itself prove it.
for file in ['EndStatement.lean','README.md','LICENSE','NOTICE']:
 assert (ROOT/('sources/anthropic-'+file)).is_file(), 'Missing vendored Anthropic source'
for slug in ['3sum','apsp']:
 r=problems[slug]['records'][1];r['artifact']={'path':'sources/anthropic-EndStatement.lean','sha256':hashlib.sha256((ROOT/'sources/anthropic-EndStatement.lean').read_bytes()).hexdigest()};problems[slug]['sources'].append({'url':END.replace('EndStatement.lean','README.md'),'checked_at':CHECK})
for slug,p in problems.items():write(slug+'.json',p)
for r in problems['integer-multiplication']['records']:
 if r['id'].startswith('swapnil-round-'):
  path='sources/'+r['id']+'-README.md';r['artifact']={'path':path,'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest()};r['submission_url']=r['source']['url'];r['evidence']['paper_url']=r['source']['url'];problems['integer-multiplication']['record_metadata'][r['id']]['source_url']=r['source']['url']
write('integer-multiplication.json',problems['integer-multiplication'])
# Read-only registry manifests. Research-artifact listings are not race manifests.
reg=json.loads((ROOT/'registry.json').read_text())
for listing in reg['repositories']:
 listing['manifest_source']=None
 if listing['repo'] not in ['CrocSwap/integer-mult-bounds','Swapnil-jain/integer-mult-kappa']:continue
 repo=listing['repo'];p=problems['integer-multiplication'];manifest={'schema_version':1,'problem_id':p['problem_id'],'model':p['model'],'score':p['score'],'tiers':['claimed'],'verification':None,'records':{'path':'README.md','format':'adapter-v1','adapter':'crocswap-pr-readme-v1' if repo.startswith('CrocSwap/') else 'swapnil-readme-v1'},'maintainers':[{'github':repo.split('/')[0],'role':'owner'}],'agents':None,'submission_url':f'https://github.com/{repo}/pulls' if repo.startswith('CrocSwap/') else f'https://github.com/{repo}','rules_url':f'https://github.com/{repo}/blob/'+json.loads((ROOT/('sources/'+repo.replace('/','__')+'__head.json')).read_text())['sha']+('/CONTRIBUTING.md' if repo.startswith('CrocSwap/') else '/README.md')}
 path='manifests/'+repo.replace('/','--')+'.json';write(path,manifest);listing['manifest_source']={'kind':'registry','path':path,'revision':'sha256:'+hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),'editor':'BOS Worker 3'}
 listing['comparison_keys']={'integer-multiplication':('crocswap' if repo.startswith('CrocSwap/') else 'swapnil')+'/independent-assumptions-unreviewed'}
write('registry.json',reg)
# Lead review, 2026-10-08: source dates, citation credit, and one CrocSwap race track.
years={'3sum':1995,'apsp':1962,'subset-sum':1974,'integer-multiplication':2021,'exact-dft':1970,'directed-sssp':1987}
for slug,p in problems.items():
 r=p['records'][0];r['submitted_at']=None;m=p['record_metadata'][r['id']]
 m.update(publication_year=years[slug],publication_date_precision='year',publication_source_url=r['source']['url'],date_precision='Publication year only; exact submission time unknown. site_observed_at is separate.')
 for r in p['records']:
  m=p['record_metadata'][r['id']];m['upstream_tier']=r['tier'];m['site_tier']='claimed';m.setdefault('comparison_key',p['problem_id']+'/v1');m.setdefault('publication_date_precision','date-time' if r['id'].startswith('crocswap-pr-') else 'unknown')
  if r['id'].startswith('crocswap-'):
   m['comparison_key']='crocswap/integer-multiplication-v1'
   m['comparison_status']='Same CrocSwap race: numerical within-repo comparison authorized 2026-10-08. Each record retains its stated assumptions; no full proof or cross-repo compatibility claim.'
   m['eligible_for_record']=r['upstream_status']=='merged' or not r['id'].startswith('crocswap-pr-')
   m['record_eligibility_note']='Eligible for the CrocSwap claimed-source race when merged or a published README checkpoint. Open and closed-unmerged PRs cannot hold the record.'
   m['race_repo']='CrocSwap/integer-mult-bounds'
   if r['id'].startswith('crocswap-pr-'):m['publication_date_precision']='date-time';m['publication_date']=r['submitted_at'];m['publication_source_url']=r['submission_url']
 r=p['records'][0]
 if slug=='3sum':
  r['title']='Folklore quadratic 3SUM algorithm; documented by Gajentaan and Overmars (1995)'
  r['authors']=[{'name':'Folklore; cited account by Anka Gajentaan and Mark H. Overmars','url':'https://people.csail.mit.edu/virgi/6.s078/papers/gajovermars.pdf'}]
  m=p['record_metadata'][r['id']];m['attribution_note']='Gajentaan and Overmars introduced the 3SUM-hardness framework and described the existing quadratic algorithm. This citation does not attribute the algorithm invention to them. 1995 is the cited account year; the folklore origin date is unknown.'
  m['publication_source_url']=r['authors'][0]['url'];m['publication_date_role']='cited-account-not-invention'
  r['artifact']=evidence('3sum-baseline',r['authors'][0]['url'],r['title']+'; see pages 168–169, section 3.')
 if slug=='exact-dft':
  p['record_metadata'][r['id']]['publication_source_url']='https://doi.org/10.1109/TAU.1970.1162132';p['record_metadata'][r['id']]['publication_date_role']='Bluestein all-length reduction (1970); Cooley–Tukey FFT account is 1965.'
 write(slug+'.json',p)
reg=json.loads((ROOT/'registry.json').read_text())
for listing in reg['repositories']:
 listing.update(submission_url=None,agents_url=None,rules_url=None)
 if listing['manifest_source']:
  manifest=json.loads((ROOT/listing['manifest_source']['path']).read_text());listing['submission_url']=manifest['submission_url'];listing['rules_url']=manifest['rules_url']
 if listing['repo']=='CrocSwap/integer-mult-bounds':listing['comparison_keys']={'integer-multiplication':'crocswap/integer-multiplication-v1'}
write('registry.json',reg)
# Lead decision: upstream verified tier and independent rerun state are separate.
arxiv=json.loads((ROOT/'sources/arxiv-2610.06783-v1.json').read_text())
reruns=json.loads((ROOT/'sources/anthropic-rerun-status.json').read_text())
for slug in ['3sum','apsp']:
 p=problems[slug];r=next(r for r in p['records'] if r['id']=='anthropic-2026');r['tier']='verified';r['rerun_status']=reruns[slug];r['submitted_at']=arxiv['submitted_at'];r['evidence']['paper_url']=arxiv['url'];m=p['record_metadata'][r['id']]
 m.update(upstream_tier='verified',site_tier='verified',publication_year=2026,publication_date=arxiv['submitted_at'],publication_date_precision='date-time',publication_source_url=arxiv['url'],publication_date_role='arXiv v1 paper submission, not formalization publication',date_precision='Exact arXiv v1 submission timestamp in UTC; observation time separate.')
 m['proof_status']={'pending':'proved upstream, not yet rerun by bigOspeedrun','passed':'proved upstream; independent rerun passed; see rerun_status receipt','failed':'proved upstream; independent rerun failed; see rerun_status receipt'}[r['rerun_status']['state']]
 p['sources'].append({'url':arxiv['url'],'checked_at':CHECK});write(slug+'.json',p)
for r in problems['integer-multiplication']['records']:
 if r['id'].startswith('crocswap-pr-'):
  m=problems['integer-multiplication']['record_metadata'][r['id']];m['race_series']='pr-submissions';m['race_event_at']=r['submitted_at'];m['race_event_kind']='PR creation; latest observed score'
write('integer-multiplication.json',problems['integer-multiplication'])
# Preserve the separate local scored-gate reproduction without a new record claim.
local_source=ROOT/'sources/3sum-scored-baseline/record.json'
if local_source.exists():
 r=json.loads(local_source.read_text());source_id=r['id'];r['id']='bigospeedrun-local-baseline-19992';r['kind']='reproduction';r['artifact']['path']='sources/3sum-scored-baseline/Submission.lean';r['rerun_status']['receipt_path']='sources/3sum-scored-baseline-receipt.json'
 receipt=json.loads((ROOT/r['rerun_status']['receipt_path']).read_text());r['site_observed_at']=receipt['observed_at']
 add('3sum',r,source_record_id=source_id,source_record_path='sources/3sum-scored-baseline/record.json',source_url_public=False,source_url_status='Intended publication URL; local-only repo, not pushed.',repo='bigospeedrun/3sum',reproduction_of='anthropic-2026',upstream_tier='verified',site_tier='verified',comparison_key=problems['3sum']['problem_id']+'/v1',publication_date=r['submitted_at'],publication_date_precision='date-time',publication_date_role='Local wrapper creation, not new mathematical result',date_precision='Exact local wrapper timestamps; paper date remains on the original record.',proof_status='Local scored Comparator gate passed with nanoda and Lean kernels; reused upstream proof artifacts; no public badge.',eligible_for_record=False)
 write('3sum.json',problems['3sum'])
