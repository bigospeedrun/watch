#!/usr/bin/env python3
"""Wrapper schemas; core model, score and record schemas come from design section 4."""
import json
from pathlib import Path
P=Path(__file__).parent
load=lambda n:json.loads((P/n).read_text())
def save(n,d):(P/n).write_text(json.dumps(d,indent=2)+'\n')
def obj(props):return {'type':'object','additionalProperties':False,'required':list(props),'properties':props}
str_={'type':'string'};nullable={'type':['string','null']};date={'type':'string','format':'date'};url={'type':'string','format':'uri','pattern':'^https://'}
manifest=load('schemas/manifest-v1.json');records=load('schemas/records-v1.json')
problem=obj({'schema_version':{'const':1},'problem_id':manifest['properties']['problem_id'],'model':manifest['properties']['model'],'score':manifest['properties']['score'],'checked_at':date,'updated_at':{'type':'string','format':'date-time','pattern':'Z$'},'sources':{'type':'array','minItems':1,'items':{'type':'object','required':['url','checked_at'],'properties':{'url':url,'checked_at':date,'status':str_},'additionalProperties':False}},'records':records,'record_metadata':{'type':'object','additionalProperties':{'type':'object','required':['checked_at','eligible_for_record','proof_status'],'properties':{'checked_at':date,'eligible_for_record':{'type':'boolean'},'proof_status':str_}}}})
problem['$schema']='https://json-schema.org/draft/2020-12/schema';save('schemas/problem-v1.json',problem)
r=load('registry.json');sample=r['repositories'][0];props={k:{} for k in sample};props.update(repo_id={'type':['integer','null']},repo=str_,owner=str_,url=url,problem_ids={'type':'array','items':str_},tracking_branch=nullable,listing_mode={'enum':['independent-read-only','related-read-only','research-artifact','planned']},opted_in={'const':False},admitted_at={'type':['string','null'],'format':'date'},checked_at=date,source_url={'type':['string','null'],'format':'uri'},verification_profile={'type':['string','null']})
registry=obj({'schema_version':{'const':1},'checked_at':date,'updated_at':{'type':'string','format':'date-time','pattern':'Z$'},'repositories':{'type':'array','items':obj(props)},'problems':{'type':'array','minItems':6,'maxItems':6,'items':obj({'slug':str_,'problem_id':str_,'data_file':str_,'status':{'enum':['independent-race','planned-race','status-only']},'race_repo':nullable})}});registry['$schema']=problem['$schema'];save('schemas/registry-v1.json',registry)
# These are adapter evidence formats, not native upstream manifests.
for filename in ['submissions','chart-cross-check']:
 data=load(filename+'.json');schema=obj({k:{} for k in data});schema['$schema']=problem['$schema'];schema['properties']['checked_at']=date
 if filename=='submissions':
  schema['properties']['items']={'type':'array','items':obj({k:{} for k in data['items'][0]})}
 save('schemas/'+filename+'-v1.json',schema)

for key in ['submission_url','rules_url','agents_url']:
 registry['properties']['repositories']['items']['properties'][key]={'type':['string','null'],'format':'uri'}
save('schemas/registry-v1.json',registry)
meta=problem['properties']['record_metadata']['additionalProperties']['properties']
meta.update(publication_year={'type':'integer','minimum':1,'maximum':2026},publication_date_precision={'type':'string'},publication_source_url=url,comparison_key=str_,upstream_tier={'enum':['verified','certified-conditional','claimed']},site_tier={'enum':['verified','certified-conditional','claimed']})
save('schemas/problem-v1.json',problem)
