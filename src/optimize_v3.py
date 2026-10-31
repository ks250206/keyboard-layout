#!/usr/bin/env python3
"""Optimize 30-key layout against v2 finger×row×lateral motor-time model.

This experiment holds old nine layouts fixed. Train on synthetic Japanese,
4 English prose passages, and seven public OSS source excerpts installed in
local runtimes. Validation is strictly excluded from the objective: older
Japanese corpora, two English documents, and different OSS source files.

Requires numpy and numba for search; deterministic seeds. Re-running with
--check prints reevaluated metrics without search. The published code inputs
are derived unigram/bigram statistics, not third-party source bodies.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, random, string
from collections import Counter
from pathlib import Path
import numpy as np
from numba import njit
import benchmark as legacy
import benchmark_finger_rows as v2

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
RESULT=ROOT/'results'
ALPHABET='\t\n'+''.join(chr(i) for i in range(32,127))
SYMBOLS='abcdefghijklmnopqrstuvwxyz-.,;' # Core uses exactly these 30 characters.
assert len(SYMBOLS)==30
CAT_NAMES=('生活文','業務文','技術文','EN','CODE')
# Real public OSS samples in machine environments, same sources as first experiments.
# Only aggregate ngrams are stored in the repository (source licenses retained upstream).
CODE_FILES={
    'Python':('/opt/pyvenv/lib/python3.13/site-packages/requests/sessions.py','/usr/lib/python3.13/asyncio/base_events.py'),
    'JavaScript':('/opt/novnc/core/rfb.js','/opt/novnc/app/ui.js'),
    'TypeScript':('/opt/nvm/versions/node/v22.16.0/lib/node_modules/mathjax-full/ts/adaptors/liteAdaptor.ts', '/opt/nvm/versions/node/v22.16.0/lib/node_modules/mathjax-full/ts/adaptors/lite/Parser.ts'),
    'Go':('/usr/local/go/src/net/http/server.go', '/usr/local/go/src/encoding/json/decode.go'),
    'C':('/opt/pyvenv/lib/python3.13/site-packages/Bio/Align/_pairwisealigner.c', '/opt/pyvenv/lib/python3.13/site-packages/Bio/Align/_codonaligner.c'),
    'C++':('/opt/nvm/versions/node/v22.16.0/lib/node_modules/sharp/src/pipeline.cc','/opt/nvm/versions/node/v22.16.0/lib/node_modules/sharp/src/operations.cc'),
    'Java':('/usr/lib/libreoffice/share/Scripts/java/Highlight/HighlightText.java', '/usr/lib/libreoffice/share/Scripts/java/MemoryUsage/MemoryUsage.java'),
}
CODE_SAMPLING={'start':1100,'length':12000}
SEED=20261031
LOAD_CAP=np.array([.12,.16,.20,.28,.28,.20,.16,.12,.30], dtype=np.float64)


def read_rows():
    return json.loads((ROOT/'layouts/layouts.json').read_text(encoding='utf-8'))


def counts_strs(texts):
    # The comma / punctuation serialization matches legacy's document_counts.
    u=Counter();g=Counter();fst=Counter();lst=Counter();count=0;shifts=0
    for s in texts:
        original=''.join(c for c in s.replace('\r\n','\n') if c in ALPHABET)
        if not original:continue
        shifts+=sum(('A'<=c<='Z') or (c in legacy.SHIFT) for c in original)
        physical=[c.lower() if ('A'<=c<='Z') else legacy.SHIFT.get(c,c) for c in original]
        count+=len(physical)
        u.update(physical);g.update(zip(physical,physical[1:]));fst[physical[0]]+=1;lst[physical[-1]]+=1
    return dict(n=count,shift=shifts,unigrams=u,bigrams=g,first=fst,last=lst)


def to_json_count(c):
    return {'n':c['n'],'shift':c['shift'], 'unigrams':sorted(c['unigrams'].items()),
            'bigrams':sorted([[a,b,v] for (a,b),v in c['bigrams'].items()]),
            'first':sorted(c['first'].items()), 'last':sorted(c['last'].items())}


def from_json_count(d):
    return {'n':int(d['n']), 'shift':int(d['shift']), 'unigrams':Counter(dict(d['unigrams'])),
            'bigrams':Counter({(a,b):int(v) for a,b,v in d['bigrams']}),
            'first':Counter(dict(d['first'])), 'last':Counter(dict(d['last']))}


def sum_counts(*arr):
    out={'n':sum(d['n'] for d in arr),'shift':sum(d['shift'] for d in arr)}
    for k in ('unigrams','bigrams','first','last'):
        out[k]=sum((d[k] for d in arr),Counter())
    return out


def prepare_data():
    package=json.loads((DATA/'synthetic_three_domains.json').read_text(encoding='utf-8'))
    jp_old=json.loads((DATA/'jp_en_corpora.json').read_text(encoding='utf-8'))
    jp_mod=json.loads((DATA/'modern_jp_corpora.json').read_text(encoding='utf-8'))
    def docs_where(dom,split):return [d['romaji'] for d in package['documents'] if d['domain']==dom and (d['split']==split or split=='all')]
    counts={};source=[]
    # NB: synthesized documents recycle base sentences. The 'holdout' doc
    # set is not independent at sentence level; prior Japanese tests ARE.
    for dom in package['domains']:
        for split in ('development','holdout','all'):
            counts[f'{dom}/{split}']=counts_strs(docs_where(dom,split))
    counts['JP_original6']=counts_strs(list(jp_old['JP_romaji'].values()))
    counts['JP_loanword6']=counts_strs([d['romaji'] for d in jp_mod['documents']])
    english=jp_old['EN_original']
    counts['EN/train']=counts_strs([english[t] for t in ('Everyday','Research','Business','History')])
    counts['EN/test']=counts_strs([english[t] for t in ('Software','Literature')])
    counts['EN/all']=counts_strs(list(english.values()))
    code_by_split={'train':[], 'test':[]}
    for lang,(train,test) in CODE_FILES.items():
        for split,path in [('train',train),('test',test)]:
            p=Path(path)
            if not p.is_file():
                raise FileNotFoundError(f'Cannot reproduce local OSS input: {path}. Use checked-in ngrams with --check, or generate from this exact path.')
            raw=p.read_bytes()
            contents=raw.decode('utf-8',errors='replace')
            original=contents[CODE_SAMPLING['start']:CODE_SAMPLING['start']+CODE_SAMPLING['length']]
            filtered=''.join(c for c in original.replace('\r\n','\n') if c in ALPHABET)
            if len(filtered)<500:raise AssertionError((lang,split,len(filtered)))
            counts[f'CODE/{lang}/{split}']=counts_strs([filtered]);code_by_split[split].append(filtered)
            source.append({'language':lang,'split':split,'repo_description':p.parts[-1],
                           'origin_path_example':path,'sample_window':CODE_SAMPLING,
                           'source_sha256':hashlib.sha256(raw).hexdigest(),
                           'sample_sha256':hashlib.sha256(filtered.encode('utf-8')).hexdigest(),
                           'keys':len(filtered)})
    for split in ('train','test'):
        counts[f'CODE/{split}']=counts_strs(code_by_split[split])
    counts['CODE/all']=sum_counts(counts['CODE/train'],counts['CODE/test'])
    out={'version':3,'source':{'jp_synthetic':str('data/synthetic_three_domains.json'),
                              'jp_prior6':'data/jp_en_corpora.json','loanword_prior6':'data/modern_jp_corpora.json',
                              'code_files':source,'warning':'Synthetic JP holdout overlaps train at sentence-source level.'},
         'counts':{k:to_json_count(v) for k,v in sorted(counts.items())}}
    (DATA/'v3_ngrams.json').write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    return out


def stored_data():return json.loads((DATA/'v3_ngrams.json').read_text(encoding='utf-8'))


def collect(bundle):return {k:from_json_count(v) for k,v in bundle['counts'].items()}


def coord_arrays():
    p=len(v2.POSITIONS);cost=np.array([v2.key_penalty(i) for i in range(p)],dtype=np.float64)/1000
    tt=np.zeros((p,p),dtype=np.float64)
    for a in range(p):
        for b in range(p):
            d=math.dist(v2.POSITIONS[a],v2.POSITIONS[b])
            if v2.FINGERS[a]==v2.FINGERS[b]:
                t=legacy.REPEAT if a==b else legacy.SAME_SETUP+legacy.SAME_LOG*math.log2(1+d)+legacy.SAME_LINEAR*d
            else:
                sh=v2.FINGERS[a]<=3 and v2.FINGERS[b]<=3 or 4<=v2.FINGERS[a]<=7 and 4<=v2.FINGERS[b]<=7
                t=legacy.REACH*legacy.HD[b]+legacy.RETURN*legacy.HD[a]+(legacy.SAME_HAND if sh else 0.)
            tt[a,b]=t+v2.delta_transition(a,b)/1000
    return cost,tt,np.array(legacy.HD,dtype=np.float64),np.array(v2.FINGERS,dtype=np.int64),np.array(v2.POSITIONS,dtype=np.float64)


def canon_items(groups):
    return sorted(set(ch for data in groups.values() for ch in data['unigrams'])|set(SYMBOLS)|set(v2.EXTRA))


def ngram_arrays(data,canon):
    inds={c:i for i,c in enumerate(canon)}
    u=np.zeros(len(canon),dtype=np.float64);first=np.zeros_like(u);last=np.zeros_like(u)
    bigrams=np.zeros((len(canon),len(canon)),dtype=np.float64)
    for c,n in data['unigrams'].items():u[inds[c]]=n
    for c,n in data['first'].items():first[inds[c]]=n
    for c,n in data['last'].items():last[inds[c]]=n
    for (a,b),n in data['bigrams'].items():bigrams[inds[a],inds[b]]=n
    i,j=np.nonzero(bigrams)
    return {'n':data['n'],'shift':data['shift'],'u':u,'first':first,'last':last,
            'bi':i.astype(np.int32),'bj':j.astype(np.int32),'bv':bigrams[i,j],
            'g':bigrams}


@njit(cache=True)
def fast_score(assign,core_ids,canonical_fallback,per_pen,transition,homedist,whichfinger,groups,weights,level=1.0):
    # Maps physical key slot for each canonical alphabet char.
    p=canonical_fallback.copy()
    for key in range(30):p[core_ids[assign[key]]]=key
    t_total=0.
    finger_load=np.zeros(8,dtype=np.float64)
    home_usage=0.;left_usage=0.;samefinger=0.
    for ix in range(len(groups)):
        u,first,last,bi,bj,bv,n,shift=groups[ix]
        w=weights[ix]
        cost=.118*n+.038*shift
        sf=0.
        for i in range(len(u)):
            key=p[i];count=u[i]
            cost+=count*per_pen[key]
            cost+=first[i]*.019*homedist[key]+last[i]*.009*homedist[key]
            f=whichfinger[key]
            if f<8:finger_load[f]+=w*count/n
            if 10<=key<20:home_usage+=w*count/n
            if f<4:left_usage+=w*count/n
        for k in range(len(bv)):
            a=p[bi[k]];b=p[bj[k]];v=bv[k]
            cost+=v*transition[a,b]
            if whichfinger[a]==whichfinger[b] and a!=b:sf+=v
        t_total+=w*cost/n
        samefinger+=w*sf/n
    # Ergonomic soft constraints, originally not part of motor-time estimator.
    regularizer=0.
    for k in range(8):
        overflow=finger_load[k]-LOAD_CAP[k]
        if overflow>0:regularizer+=.16*overflow*overflow
    regularizer+=.010*(left_usage-.5)**2+.003*(1-home_usage)+.012*samefinger
    return t_total+level*regularizer


def serializable_groups(groups):
    return tuple((d['u'],d['first'],d['last'],d['bi'],d['bj'],d['bv'],float(d['n']),float(d['shift'])) for d in groups)


def map_rows(rows):
    return [c for row in rows for c in row]


def from_existing(rows,core=SYMBOLS):
    flat=''.join(rows)
    if set(flat)!=set(core):raise ValueError(f'Symbol mismatch: {flat} vs {core}')
    return np.array([core.index(c) for c in flat],dtype=np.int32)


def optimize(data, rounds=16, iterations=22000, jobs=None):
    rows=read_rows();source=collect(data)
    target_names=('生活文/development','業務文/development','技術文/development','EN/train','CODE/train')
    canon=canon_items(source);cidx={x:i for i,x in enumerate(canon)}
    fallback=np.array([v2.EXTRA.get(k,-1) for k in canon],dtype=np.int32)
    # All alphabetic characters are remapped into 30 core positions. For the
    # numba evaluator, the fallback for these characters is initialized to 0.
    fallback[fallback<0]=0
    core_ids=np.array([cidx[c] for c in SYMBOLS],dtype=np.int32)
    arrays={k:ngram_arrays(v,canon) for k,v in source.items()}
    group=serializable_groups([arrays[x] for x in target_names])
    per,tm,hd,fi,_=coord_arrays()
    # Favoring native Japanese is intentionally built into the profiles.
    jobs=jobs or {
       'Nova-F3-JP':(.30,.30,.25,.08,.07),
       'Nova-F3-Balance':(.18,.18,.19,.23,.22),
       'Nova-F3-Code':(.11,.11,.13,.20,.45),
       'Nova-F3-Ctrl':(.16,.18,.21,.20,.25),
    }
    init={
       'Nova-F3-JP':rows['Nova-JP'],
       'Nova-F3-Balance':rows['Nova-Hybrid'],
       'Nova-F3-Code':rows['Nova-Dev'],
       'Nova-F3-Ctrl':rows['Nova-Ctrl'],
    }
    globalbest={}
    for label,wts in jobs.items():
        weights=np.asarray(wts,dtype=float)
        assert abs(sum(weights)-1)<1e-10
        lock={20,21,22,23} if label.endswith('Ctrl') else set()
        candidates=[(i,j) for i in range(30) for j in range(i+1,30) if i not in lock and j not in lock]
        starts=[init[label],rows['大西'],rows['Nova-JP'],rows['Nova-Hybrid'],rows['Nova-Ctrl']]
        starts=[start for start in starts if set(''.join(start))==set(SYMBOLS) and all(''.join(start)[k]=='zxcv'[k-20] for k in lock)]
        best=(float('inf'),None)
        history=[]
        for rnd in range(rounds):
            rng=random.Random(SEED+rnd*1907+list(jobs).index(label)*78263)
            if rnd%3==0 and rnd//3<len(starts):cur=from_existing(starts[rnd//3]).copy()
            elif best[1] is not None:cur=best[1].copy()
            else:cur=from_existing(init[label]).copy()
            if rnd>0:
                for _ in range(7+rnd%15):
                    a,b=rng.choice(candidates);cur[a],cur[b]=cur[b],cur[a]
            val=fast_score(cur,core_ids,fallback,per,tm,hd,fi,group,weights)
            for k in range(iterations):
                a,b=rng.choice(candidates)
                cur[a],cur[b]=cur[b],cur[a]
                new=fast_score(cur,core_ids,fallback,per,tm,hd,fi,group,weights)
                # anneal with restarts, cooled from 1.1ms/key to 0.001ms/key
                temp=.0011*((1-k/iterations)**1.6)+.000001
                if new<=val or rng.random()<math.exp(max(-100,(val-new)/temp)):
                    val=new
                else:cur[a],cur[b]=cur[b],cur[a]
                if val < best[0]-1e-13:best=(val,cur.copy())
            history.append([rnd,round(best[0]*1000,5)])
            if rnd%4==0:print(label,'restart',rnd,'best objective',best[0]*1000,'ms/key',flush=True)
        layout=''.join(SYMBOLS[i] for i in best[1])
        assert len(layout)==30 and len(set(layout))==30
        if lock:assert layout[20:24]=='zxcv'
        globalbest[label]={'rows':[layout[:10],layout[10:20],layout[20:]],'weights':dict(zip(target_names,wts)),'objective_ms_key':best[0]*1000,'history':history,'locked':sorted(lock)}
    archive={'version':3,'run_seed':SEED,'train_names':target_names,'model':'2026-10-31 v2 finger-row and splay costs','optimized':globalbest}
    (DATA/'v3_candidates.json').write_text(json.dumps(archive,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Results:',[(k,v['rows'],v['objective_ms_key']) for k,v in globalbest.items()]);return archive


def evaluate_one(rows,cs,row_scale=1.0,lateral_scale=1.0):
    alphabet=ALPHABET
    # Evaluate via original same equations. Need no extra symbol/blank issues.
    name='candidate'
    layouts={name:rows}
    i={k:p for p,k in enumerate(alphabet)}
    def emit_counts(unigrams):return [[i[k],int(v)] for k,v in unigrams.items()]
    # v2.evaluate expects original character statistics; evaluate with
    # canonical normalized key chars. Shift penalties are constant per corpus.
    transformed={'n':cs['n'],
                'unigrams':emit_counts(cs['unigrams']),
                'bigrams':[[i[a],i[b],int(v)] for (a,b),v in cs['bigrams'].items()],
                'first':emit_counts(cs['first']), 'last':emit_counts(cs['last'])}
    # Since SHIFT was collapsed before storage, add constant shift penalty
    # (KLA unaffected since key positions are unchanged by shift in model).
    output=v2.evaluate(name,layouts,transformed,alphabet,row_scale,lateral_scale)
    shift=cs['shift']*.038
    output['v2_s']+=shift
    output['legacy_s']+=shift
    output['v2_s_per_1000']=output['v2_s']*1000/cs['n']
    return output


def make_reports(data,candidates):
    original=read_rows(); selected={name:item['rows'] for name,item in candidates['optimized'].items()}
    allrows=dict(original,**selected)
    cs=collect(data)
    interesting=['生活文/development','生活文/holdout','生活文/all',
                 '業務文/development','業務文/holdout','業務文/all',
                 '技術文/development','技術文/holdout','技術文/all',
                 'JP_original6','JP_loanword6','EN/train','EN/test','EN/all',
                 'CODE/train','CODE/test','CODE/all']
    summary=[]
    for cat in interesting:
        q=evaluate_one(original['QWERTY'],cs[cat])
        for name,rows in allrows.items():
            r=evaluate_one(rows,cs[cat]);summary.append(dict(dataset=cat,layout=name,n=cs[cat]['n'],
                 speed_gain_pct=round(100*(q['v2_s']/r['v2_s']-1),4),
                 est_ms_per_key=round(r['v2_s']*1000/cs[cat]['n'],4),
                 legacy_ms_per_key=round(r['legacy_s']*1000/cs[cat]['n'],4),
                 KLA_approx=round(r['KLA_approx_unchanged'],4),
                 home_pct=round(r['home_pct'],4),
                 same_finger_pct=round(r['same_finger_pct'],4),
                 row_extra_ms_key=round(r['row_extra_s']*1000/cs[cat]['n'],4),
                 lateral_extra_ms_key=round(r['lateral_extra_s']*1000/cs[cat]['n'],4),
                 transition_extra_ms_key=round(r['transition_extra_s']*1000/cs[cat]['n'],4)))
    for lang in CODE_FILES:
        for stage in ('train','test'):
            cat=f'CODE/{lang}/{stage}'
            q=evaluate_one(original['QWERTY'],cs[cat])
            for name,rows in allrows.items():
                r=evaluate_one(rows,cs[cat]);summary.append(dict(dataset=cat,layout=name,n=cs[cat]['n'],
                    speed_gain_pct=round(100*(q['v2_s']/r['v2_s']-1),4),
                    est_ms_per_key=round(r['v2_s']*1000/cs[cat]['n'],4),
                    legacy_ms_per_key=round(r['legacy_s']*1000/cs[cat]['n'],4),
                    KLA_approx=round(r['KLA_approx_unchanged'],4),
                    home_pct=round(r['home_pct'],4),
                    same_finger_pct=round(r['same_finger_pct'],4),
                    row_extra_ms_key=round(r['row_extra_s']*1000/cs[cat]['n'],4),
                    lateral_extra_ms_key=round(r['lateral_extra_s']*1000/cs[cat]['n'],4),
                    transition_extra_ms_key=round(r['transition_extra_s']*1000/cs[cat]['n'],4)))
    RESULT.mkdir(exist_ok=True)
    with (RESULT/'v3_scores.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
    # Finger-by-row / splay penalty scaling; the legacy distance model stays
    # unchanged, and the same QWERTY baseline is re-evaluated for each scale.
    sensitivity=[]
    regimes=[(0.,0.),(.5,.5),(1.,0.),(0.,1.),(1.,1.),(1.5,1.5),(2.,2.),(3.,3.)]
    for cat in ['生活文/holdout','業務文/holdout','技術文/holdout','JP_original6','JP_loanword6','EN/test','CODE/test']:
        for rs,ls in regimes:
            q=evaluate_one(original['QWERTY'],cs[cat],rs,ls)
            for name,layout in allrows.items():
                r=evaluate_one(layout,cs[cat],rs,ls)
                sensitivity.append(dict(dataset=cat,layout=name,row_factor=rs,splay_factor=ls,
                    speed_gain_pct=round(100*(q['v2_s']/r['v2_s']-1),4),
                    ms_per_key=round(1000*r['v2_s']/cs[cat]['n'],4)))
    with (RESULT/'v3_sensitivity.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(sensitivity[0]));writer.writeheader();writer.writerows(sensitivity)
    # Weighted use cases use per-key typing time to prevent longer texts from
    # having an arbitrary effect on each profile.
    profiles={
        'JP_heavy': {'生活文/holdout':.27,'業務文/holdout':.27,'技術文/holdout':.26,'EN/test':.10,'CODE/test':.10},
        'Bilingual': {'生活文/holdout':.15,'業務文/holdout':.15,'技術文/holdout':.20,'EN/test':.25,'CODE/test':.25},
        'Developer': {'生活文/holdout':.10,'業務文/holdout':.10,'技術文/holdout':.15,'EN/test':.20,'CODE/test':.45},
        'JP_loanword_heavy':{'JP_loanword6':.60,'生活文/holdout':.10,'業務文/holdout':.10,'技術文/holdout':.10,'EN/test':.05,'CODE/test':.05},
    }
    lookups={(r['dataset'],r['layout']):r for r in summary}
    mixture=[]
    for pname,weights in profiles.items():
        rates={name:sum(w*lookups[(cat,name)]['est_ms_per_key'] for cat,w in weights.items()) for name in allrows}
        for name,per_key in rates.items():
            mixture.append(dict(profile=pname,layout=name,ms_per_key=round(per_key,4),
                 speed_gain_pct=round(100*(rates['QWERTY']/per_key-1),4),
                 rank=1+sum(x<per_key-1e-10 for x in rates.values())))
    with (RESULT/'v3_mixtures.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(mixture[0]));writer.writeheader();writer.writerows(mixture)
    print('PROFILE RANKINGS:')
    for pname in profiles:
        first=sorted((r for r in mixture if r['profile']==pname),key=lambda a:a['ms_per_key'])[:6]
        print(pname,[(r['layout'],r['speed_gain_pct']) for r in first])
    for cat in ['JP_original6','JP_loanword6','EN/test','CODE/test']:
        r=sorted((x for x in summary if x['dataset']==cat),key=lambda x:x['est_ms_per_key'])
        print('TEST',cat,'TOP:',[(x['layout'],x['speed_gain_pct'],x['KLA_approx']) for x in r[:7]])
    return summary


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--build-data',action='store_true');ap.add_argument('--optimize',action='store_true')
    ap.add_argument('--check',action='store_true');ap.add_argument('--rounds',type=int,default=16);ap.add_argument('--iters',type=int,default=22000)
    args=ap.parse_args()
    if args.build_data:bundle=prepare_data()
    else:bundle=stored_data()
    if args.optimize:candidates=optimize(bundle,rounds=args.rounds,iterations=args.iters)
    else:candidates=json.loads((DATA/'v3_candidates.json').read_text(encoding='utf-8'))
    rows=make_reports(bundle,candidates)
    if args.check:
        for r in rows:
            assert math.isfinite(r['est_ms_per_key']) and math.isfinite(r['KLA_approx'])
        print('PASS:',len(rows),'row-level evaluations',flush=True)

if __name__=='__main__':main()
