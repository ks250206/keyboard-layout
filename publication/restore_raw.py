#!/usr/bin/env python3
"""Restore frozen printable-character counts from existing v3 counts and audited deltas.

Publication-only transfer reconstruction. It neither downloads source bodies nor
changes the corpus. The complete uncompressed result must match its original SHA256.
"""
from pathlib import Path
from collections import Counter
import gzip, hashlib, json, sys
ROOT=Path(sys.argv[1]).resolve()
ALPH='\t\n'+''.join(map(chr,range(32,127)))
DOMAINS=('生活文','業務文','技術文')
def counts(texts):
    u=Counter();g=Counter();first=Counter();last=Counter();n=0
    for txt in texts:
        s=''.join(c for c in txt.replace('\r\n','\n') if c in ALPH)
        if s:
            u.update(s);g.update(zip(s,s[1:]));first[s[0]]+=1;last[s[-1]]+=1;n+=len(s)
    return {'n':n,'u':sorted(u.items()),'g':[[a,b,n] for (a,b),n in sorted(g.items())],'first':sorted(first.items()),'last':sorted(last.items())}
def merge(seq):
    u=Counter();g=Counter();f=Counter();l=Counter();n=0
    for d in seq:
        n+=d['n'];u.update(dict(d['u']));g.update({(a,b):v for a,b,v in d['g']});f.update(dict(d['first']));l.update(dict(d['last']))
    return {'n':n,'u':sorted(u.items()),'g':[[a,b,v] for (a,b),v in sorted(g.items())],'first':sorted(f.items()),'last':sorted(l.items())}
old=json.loads((ROOT/'data/jp_en_corpora.json').read_text())
pack=json.loads((ROOT/'data/synthetic_three_domains.json').read_text());unique={}
for doc in pack['documents']:
    chunks=doc['romaji'].split('.')
    if chunks[-1]=='':chunks=chunks[:-1]
    assert len(chunks)==len(doc['source_sentence_ids'])
    for sid,s in zip(doc['source_sentence_ids'],chunks):
        k=(doc['domain'],doc['topic'],sid)
        if k in unique:assert unique[k]==s+'.'
        unique[k]=s+'.'
data={};meta=[]
for dom in DOMAINS:
    for split,ids in [('train',range(8)),('valid',range(8,10)),('test',range(10,12))]:
        ss=[s for (d,t,i),s in unique.items() if d==dom and i in ids]
        data[dom+'/'+split]=counts(ss)
        meta.append({'group':dom+'/'+split,'documents':len(ss),'chars':sum(map(len,ss)),'sha256':hashlib.sha256('\0'.join(sorted(ss)).encode()).hexdigest()})
en=old['EN_original'];data['EN/train']=counts([en[t] for t in ('Everyday','Research','Business','History')]);data['EN/test']=counts([en[t] for t in ('Software','Literature')])
data['JP/original']=counts(list(old['JP_romaji'].values()))
mod=json.loads((ROOT/'data/modern_jp_corpora.json').read_text());data['JP/loanword']=counts([d['romaji'] for d in mod['documents']])
v3=json.loads((ROOT/'data/v3_ngrams.json').read_text())
deltas={};corrections=json.loads((ROOT/'publication/corrections.json').read_text())
for path in sorted((ROOT/'publication/delta').glob('*.json')):
    payload=json.loads(path.read_text())
    for group, fields in payload.items():
        for field, entries in fields.items():
            values=dict(entries)
            for idx,before,after in corrections.get(path.name,{}).get(group,{}).get(field,[]):
                if values.get(idx)!=before:raise ValueError(f'Transfer correction precondition failed: {path.name}/{group}/{field}/{idx}')
                if after is None:values.pop(idx,None)
                else:values[idx]=after
            fields[field]=values
    deltas.update(payload)
for f in v3['source']['code_files']:
    k=f"CODE/{f['language']}/{f['split']}";base=v3['counts'][k];d={'n':base['n']}
    for newkey,oldkey,width in [('u','unigrams',1),('g','bigrams',2),('first','first',1),('last','last',1)]:
        rows={tuple(r[:-1]):r[-1] for r in base[oldkey]}
        for idx,delta in deltas[k][newkey].items():
            key=(ALPH[idx],) if width==1 else (ALPH[idx%97],ALPH[idx//97])
            rows[key]=rows.get(key,0)+delta
            if rows[key]<0:raise ValueError((k,newkey,key,rows[key]))
        d[newkey]=[[*key,count] for key,count in sorted(rows.items()) if count]
    assert sum(count for _,count in d['u'])==d['n'];data[k]=d
for split in ('train','test'):
    data['CODE/'+split]=merge([d for k,d in data.items() if k.startswith('CODE/') and k.count('/')==2 and k.endswith('/'+split)])
for split in ('train','valid','test'):data['JP/'+split]=merge([data[d+'/'+split] for d in DOMAINS])
out={'version':4,'alphabet':ALPH,'warning':'Synthetic JP, sentence-disjoint split. Legacy diagnostic corpora were previously inspected; not fresh blind tests. No OSS source text.','jp_sentence_groups':meta,'code_sources':v3['source']['code_files'],'groups':data}
raw=json.dumps(out,ensure_ascii=False,separators=(',',':')).encode()
expected='6a84de927b9644798e226b05b14d1cd71e301b270d572d34e6fc545ffe340eca'
if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Restored ngram hash mismatch')
compressed=bytearray(gzip.compress(raw,mtime=0));compressed[9]=255
(ROOT/'data/v4').mkdir(parents=True,exist_ok=True)
(ROOT/'data/v4/raw_ngrams.json.gz').write_bytes(compressed)
print('Restored frozen raw ngrams:',len(raw),'bytes',hashlib.sha256(raw).hexdigest())
