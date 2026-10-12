#!/usr/bin/env python3
"""Validate published data and exact rankings; never execute upstream artifacts."""
import hashlib,json,re,sys
from pathlib import Path
from fractions import Fraction
from jsonschema import Draft202012Validator,FormatChecker
ROOT=Path(__file__).resolve().parent
TIERS=('verified','certified-conditional','claimed')
def load(p):return json.loads((ROOT/p).read_text())
def validate(data,schema):Draft202012Validator(schema,format_checker=FormatChecker()).validate(data)
def safe_path(rel):
 p=ROOT/rel
 assert not p.is_symlink(),rel
 assert p.resolve().is_relative_to(ROOT),rel
 assert p.is_file(),rel
 return p
for p in (ROOT/'schemas').glob('*.json'):Draft202012Validator.check_schema(json.loads(p.read_text()))
registry=load('registry.json');validate(registry,load('schemas/registry-v1.json'))
for listing in registry['repositories']:
 manifest=listing['manifest_source']
 if manifest:
  raw=safe_path(manifest['path']).read_bytes();assert manifest['revision']=='sha256:'+hashlib.sha256(raw).hexdigest()
  validate(json.loads(raw),load('schemas/manifest-v1.json'))
for stem in ['submissions','chart-cross-check']:validate(load(stem+'.json'),load('schemas/'+stem+'-v1.json'))
print('Checked',registry['checked_at'])
print('problem | verified | certified-conditional | claimed (observed maximum/minimum) | records')
for entry in registry['problems']:
 p=load(entry['data_file']);validate(p,load('schemas/problem-v1.json'));assert p['problem_id']==entry['problem_id'];assert p['model']['id']==p['problem_id'].split('/')[1]
 records=p['records'];ids=[r['id'] for r in records];assert len(ids)==len(set(ids));assert set(ids)==set(p['record_metadata']);assert records[0]['kind']=='baseline'
 assert records[0]['submitted_at'] is None
 assert isinstance(p['record_metadata']['classical-baseline']['publication_year'],int)
 for r in records:
  if r.get('score_relation')=='strict-upper-bound':assert p['score']['direction']=='higher-is-better' and r['kind']!='baseline'
  q=Fraction(r['score']);assert str(q)==r['score'];assert Fraction(p['score']['minimum'])<=q<=Fraction(p['score']['maximum'])
  if 'source_commit' in r:assert r['source_commit']!='0'*40
  a=r['artifact'];assert a['sha256']!='0'*64;assert hashlib.sha256(safe_path(a['path']).read_bytes()).hexdigest()==a['sha256'],r['id']
  m=p['record_metadata'][r['id']]
  assert not m.get('site_badge',False),'No site receipt exists'
  if r['upstream_status'] in ['open','closed-unmerged']:assert not m['eligible_for_record']
  if r['tier']=='certified-conditional':safe_path(r['evidence']['certificate_path'])
  if 'rerun_status' in r:
   validate(r['rerun_status'],load('schemas/records-v1.json')['items']['properties']['rerun_status'])
   if r['rerun_status']['state']!='pending':
    checked_receipt=json.loads(safe_path(r['rerun_status']['receipt_path']).read_text())
    if 'artifact_sha256' in checked_receipt:assert hashlib.sha256(safe_path(checked_receipt['artifact_path']).read_bytes()).hexdigest()==checked_receipt['artifact_sha256']
    for kind in ('log','time'):
     if kind+'_sha256' in checked_receipt:assert hashlib.sha256(safe_path(checked_receipt[kind+'_path']).read_bytes()).hexdigest()==checked_receipt[kind+'_sha256']
  if r['id']=='anthropic-2026':
   assert r['tier']==m['site_tier']=='verified'
   assert r['submitted_at']==load('sources/arxiv-2610.06783-v1.json')['submitted_at']
   assert r['rerun_status']==load('sources/anthropic-rerun-status.json')[entry['slug']]
  if r['id'].startswith('crocswap-'):assert m['comparison_key']=='crocswap/integer-multiplication-v1'
  if r['id'].startswith('crocswap-pr-'):
   source=next(x for x in load('submissions.json')['items'] if x['pr_number']==m['pr_number'])
   assert r['submitted_at']==source['submitted_at'] and r['submitted_at'].endswith('Z')
   assert m['publication_date_precision']=='date-time'
 choose=min if p['score']['direction']=='lower-is-better' else max
 vals=[]
 for tier in TIERS:
  pool=[Fraction(r['score']) for r in records if r['tier']==tier];vals.append(str(choose(pool)) if pool else '—')
 print(entry['slug'],'|',' | '.join(vals),'|',len(records))
sub=load('submissions.json')['items'];assert len(sub)==len({s['pr_number'] for s in sub});assert {s['pr_number'] for s in sub}=={p['number'] for p in load('sources/crocswap-pulls.json')}
assert sub[0]['pr_number']==1 and sub[0]['submitted_at']=='2026-10-07T20:58:44Z'
assert any(s['upstream_status']=='merged' for s in sub) and any(s['upstream_status']=='open' for s in sub)
nums=[s for s in sub if s['pr_number']<=44 and s['claimed_score'] is not None];assert len(nums)==42
assert Fraction(nums[0]['claimed_score'])==Fraction('1.7523184e-18');assert Fraction(nums[-1]['claimed_score'])==Fraction('4.100629254e-5')
receipt_path=ROOT/'sources/anthropic-comparator-receipt.json'
if receipt_path.exists():
 receipt=json.loads(receipt_path.read_text())
 for kind in ['log','time']:
  assert hashlib.sha256(safe_path(receipt[kind+'_path']).read_bytes()).hexdigest()==receipt[kind+'_sha256']
 assert receipt['comparator_exit_code']==0 and len(receipt['targets'])==5
print('All schemas, IDs, score ranges, rational encodings, source hashes, PR coverage and chart checks passed.')
print('Observed best numbers are not global record claims. Open PRs and unreviewed comparison tracks cannot hold the record.')

print('Scores marked strict-upper-bound are excluded endpoints, not attained savings.')
