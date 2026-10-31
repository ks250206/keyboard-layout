#!/usr/bin/env python3
"""Uncalibrated finger×row×lateral-splay model for synthetic Japanese corpora.

The old KLA-style approximation and time model are unchanged and imported from
src/benchmark.py. This adds explicit per-key posture penalties and selected
same-finger transitions. Source corpora are original authored and synthetic.

  python src/generate_corpus.py
  python src/benchmark_finger_rows.py --check
"""
from __future__ import annotations
import argparse,csv,json,math,random
from collections import Counter,defaultdict
from pathlib import Path
import benchmark as legacy

ROOT=Path(__file__).resolve().parents[1]
PITCH_MM=19.05
# Number columns remain legacy US-like simplified peripheral positions, NOT JIS calibrated.
FINGER_PATTERN=[0,1,2,3,3,4,4,5,6,7]
FINGER_NAMES=['L-pinky','L-ring','L-middle','L-index','R-index','R-middle','R-ring','R-pinky','Thumb']
POSITIONS=[];FINGERS=[]
for row in range(3):
    for col in range(10):
        POSITIONS.append((col+[0,.22,.47][row],1-row));FINGERS.append(FINGER_PATTERN[col])
PERIPHERAL=[('-',10,2,7),('=',11,2,7),('`',-1,2,0),('[',10,1,7),(']',11,1,7),('\\',12,1,7),("'",10,0,7),('/',10,-1,7),(' ',5,-2.3,8),('\n',11,0,7),('\t',-1,1,0)]
for char in '1234567890':
    j=(int(char)-1)%10
    f=0 if j==0 else 1 if j==1 else 2 if j==2 else 3 if j in (3,4) else 4 if j in (5,6) else 5 if j==7 else 6 if j==8 else 7
    PERIPHERAL.append((char,j,2,f))
EXTRA={}
for ch,x,y,f in PERIPHERAL:
    EXTRA[ch]=len(POSITIONS);POSITIONS.append((x,y));FINGERS.append(f)
HOMEX=(.22,1.22,2.22,3.22,6.22,7.22,8.22,9.22,5.)
# Hypotheses, milliseconds on every strike, not measured. Top/middle/bottom.
FINGER_ROW_MS={
    'L-pinky':(18,0,0), 'L-ring':(0,0,18), 'L-middle':(0,0,12),
    'L-index':(0,0,0), 'R-index':(0,0,0), 'R-middle':(0,0,9),
    'R-ring':(0,0,9), 'R-pinky':(7,0,0), 'Thumb':(0,0,0)
}
# Home-row center column of the finger. Stagger offset within +/-0.40 pitches
# is neutral; left is inward +x, right is inward -x.
SPLAY_THRESHOLD=.40
INWARD_MS={'L-index':7,'R-index':7} # other fingers are 5ms
OUTWARD_MS={'L-pinky':10,'R-pinky':10} # other fingers are 6ms
NUMBER_ROW_MS=12
HURDLE_MS=7  # same finger upper<->lower (no home row stop)
INWARD_TRANSITION_MS=4  # same finger going into displaced inward key
OUTWARD_TRANSITION_MS=6 # same finger going to displaced outward key


def layout_keymap(name, layouts):
    out={c:i for i,c in enumerate(''.join(layouts[name]))}
    for c,i in EXTRA.items():out.setdefault(c,i)
    if name=='Dvorak':out.update({'[':EXTRA['-'],']':EXTRA['='],'-':EXTRA["'"],'/':EXTRA['['],'=':EXTRA[']']})
    return out


def key_lookup(name, layouts, alphabet):
    mapping=layout_keymap(name,layouts)
    shift=legacy.SHIFT if hasattr(legacy,'SHIFT') else dict(zip('!@#$%^&*()','1234567890'))
    if not hasattr(legacy,'SHIFT'):
        shift.update({'_':'-', '+':'=', '~':'`', '{':'[', '}':']', '|':'\\', ':':';', '"':"'", '<':',', '>':'.', '?':'/'})
    indexes=[]
    for c in alphabet:
        physical=c.lower() if 'A'<=c<='Z' else shift.get(c,c)
        indexes.append(mapping[physical])
    return indexes


def zone(idx):
    f=FINGERS[idx]
    if f==8:return 'neutral'
    delta=POSITIONS[idx][0]-HOMEX[f]
    signed=delta if f<=3 else -delta
    return 'inward' if signed>SPLAY_THRESHOLD else 'outward' if signed<-SPLAY_THRESHOLD else 'neutral'


def row(idx):
    if idx<30:return idx//10 # 0=upper,1=home,2=lower
    y=POSITIONS[idx][1]
    return -1 if y>1 else 1 if y==0 else -2 # -1=number row, -2=special


def key_penalty(idx, ms_scale=1., lateral_scale=1.):
    f=FINGERS[idx];r=row(idx)
    x=(FINGER_ROW_MS[FINGER_NAMES[f]][r] if r in (0,1,2) else NUMBER_ROW_MS if r==-1 else 0)*ms_scale
    z=zone(idx)
    if z=='inward':x+=(INWARD_MS.get(FINGER_NAMES[f],5))*lateral_scale
    if z=='outward':x+=(OUTWARD_MS.get(FINGER_NAMES[f],6))*lateral_scale
    return x


def delta_transition(prev,cur,ms_scale=1.,lateral_scale=1.):
    if prev==cur or FINGERS[prev]!=FINGERS[cur]:return 0.
    r1,r2=row(prev),row(cur)
    # Same-finger direct movement across the full two-row span; direction matters
    # only through the destination posture and splay direction.
    p=(HURDLE_MS if {r1,r2}=={0,2} else 0)*ms_scale
    v=zone(cur)
    if v=='inward':p+=INWARD_TRANSITION_MS*lateral_scale
    if v=='outward':p+=OUTWARD_TRANSITION_MS*lateral_scale
    return p


def aggregate(docs, alphabet):
    result={'n':0}
    counters={k:Counter() for k in ('unigrams','bigrams','first','last')}
    for doc in docs:
        rom=doc['romaji']
        if any(c not in alphabet for c in rom):raise AssertionError(f"unsupported romaji {doc['id']}")
        counts=legacy.document_counts(rom,alphabet)
        result['n']+=counts['n']
        for k,ctr in counters.items():
            for *indices,value in counts[k]:ctr[tuple(indices)]+=value
    for k,v in counters.items():result[k]=[list(idx)+[c] for idx,c in sorted(v.items())]
    return result


def evaluate(name,layouts,cs,alphabet,strength=1.,lateral_strength=1.):
    base=legacy.metrics(name,layouts,cs,alphabet)
    indexes=key_lookup(name,layouts,alphabet)
    u=cs['unigrams'];g=cs['bigrams'];n=cs['n']
    rowcost=sum(count*key_penalty(indexes[i],strength,0) for i,count in u)/1000
    lateralcost=sum(count*key_penalty(indexes[i],0,lateral_strength) for i,count in u)/1000
    transitioncost=sum(count*delta_transition(indexes[i],indexes[j],strength,lateral_strength) for i,j,count in g)/1000
    cost=rowcost+lateralcost+transitioncost
    return {'layout':name,'keystrokes':n,'legacy_s':base['estimated_seconds'], 'v2_s':base['estimated_seconds']+cost,
            'row_extra_s':rowcost,'lateral_extra_s':lateralcost,'transition_extra_s':transitioncost,
            'KLA_approx_unchanged':base['KLA_approx'],'distance_m':base['distance_m'],
            'same_finger_pct':base['same_finger_pct'], 'home_pct':base['home_pct']}


def score_group(docs,layouts,alphabet,domain,split,scenario='proposed',strength=1,lateral_strength=1):
    counts=aggregate(docs,alphabet)
    results=[evaluate(name,layouts,counts,alphabet,strength,lateral_strength) for name in layouts]
    lookup={x['layout']:x for x in results}
    for r in results:
        q=lookup['QWERTY']
        r.update(domain=domain,split=split,scenario=scenario,
                 legacy_gain_pct=100*(q['legacy_s']/r['legacy_s']-1),
                 v2_gain_pct=100*(q['v2_s']/r['v2_s']-1),
                 gain_delta_pp=100*(q['v2_s']/r['v2_s']-q['legacy_s']/r['legacy_s']),
                 v2_s_per_1000=r['v2_s']/r['keystrokes']*1000)
    return results


def write(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check',action='store_true',help='Validate sources and original baseline model')
    args=p.parse_args()
    package=json.loads((ROOT/'data/synthetic_three_domains.json').read_text(encoding='utf-8'))
    docs=package['documents']
    assert len(docs)==48 and all(d['text'].count('ー')==d['reading_hiragana'].count('ー')==d['romaji'].count('-')==d['long_marks'] for d in docs)
    assert all(d['split'] in ('development','holdout') for d in docs)
    assert len({d['id'] for d in docs})==len(docs)
    alphabet='\t\n'+''.join(chr(i) for i in range(32,127))
    layouts=legacy.read_layouts()
    expected={'QWERTY':38.40,'大西':76.12,'Nova-JP':76.59,'Nova-Hybrid':71.91}
    if args.check:
        old=json.loads((ROOT/'data/jp_en_corpora.json').read_text(encoding='utf-8'))['JP_romaji']
        d=[dict(id=k,romaji=v)for k,v in old.items()]
        baseline=aggregate(d,alphabet)
        assert baseline['n']==2749
        for k,v in expected.items():
            actual=legacy.metrics(k,layouts,baseline,alphabet)['KLA_approx']
            assert abs(actual-v)<.015,(k,actual,v)
        print('PASS: original fixed-corpus KLA values agree with published 2026-10-31 values')
    assert len(layouts)==9
    groups={(dom,split):[d for d in docs if d['domain']==dom and (d['split']==split if split!='all' else True)]
            for dom in package['domains'] for split in ('development','holdout','all')}
    summary=[];detail=[];sens=[]
    for (domain,split),seq in groups.items():
        summary.extend(score_group(seq,layouts,alphabet,domain,split))
    for d in docs:detail.extend(score_group([d],layouts,alphabet,d['topic'],d['id']))
    # Vary perceived finger asymmetry and splay independently: test ranking robustness.
    for strength,lateral in ((0,0),(.5,.5),(1,0),(0,1),(1,1),(1.5,1.5),(2,2)):
        scenario=f'row_x{strength:g}_splay_x{lateral:g}'
        for (domain,split),seq in groups.items():
            if split!='all':continue
            sens.extend(score_group(seq,layouts,alphabet,domain,split,scenario,strength,lateral))
    out=ROOT/'results/finger_rows_v2'
    write(out/'summary.csv',summary);write(out/'by_document.csv',detail);write(out/'sensitivity.csv',sens)
    keyrows=[]
    for i in range(30):
        keyrows.append(dict(position=i,physical_qwerty='qwertyuiopasdfghjkl;zxcvbnm,./'[i],finger=FINGER_NAMES[FINGERS[i]],row=['upper','home','lower'][row(i)],zone=zone(i),
                            row_extra_ms=key_penalty(i,1,0),splay_extra_ms=key_penalty(i,0,1),total_extra_ms=key_penalty(i)))
    write(out/'key_costs.csv',keyrows)
    freq=[]
    for dom in package['domains']:
        s=[d for d in docs if d['domain']==dom];n=sum(d['keystrokes'] for d in s);h=sum(d['long_marks'] for d in s)
        freq.append(dict(domain=dom,documents=len(s),unique_source_sentences=sum(v for name,v in package['unique_source_sentences'].items() if name.startswith(dom+'/')),
                         keystrokes=n,long_marks=h,long_mark_pct=100*h/n,original_ja_chars=sum(len(d['text']) for d in s),heldout_keystrokes=sum(d['keystrokes'] for d in s if d['split']=='holdout')))
    write(out/'corpus_stats.csv',freq)
    # Two pre-existing, independent-of-this-generation reference corpora:
    # a small original 6-task corpus and a deliberately loanword-rich 6-task stress test.
    old_package=json.loads((ROOT/'data/jp_en_corpora.json').read_text(encoding='utf-8'))
    modern_package=json.loads((ROOT/'data/modern_jp_corpora.json').read_text(encoding='utf-8'))
    controls=[]
    for label,entries in (
        ('prior_original6',[dict(id=str(i),romaji=r)for i,r in enumerate(old_package['JP_romaji'].values())]),
        ('prior_loanword_stress6',[dict(id=d['name'],romaji=d['romaji'])for d in modern_package['documents']]),
    ):
        controls.extend(score_group(entries,layouts,alphabet,label,'all'))
    write(out/'prior_controls.csv',controls)
    # Domain equal weights means means of per-key time; avoids a long topic dominating.
    cat={d:{r['layout']:r for r in summary if r['domain']==d and r['split']=='all'} for d in package['domains']}
    mixes=[]
    for scenario,weights in [('equal_1_1_1',[1/3]*3),('daily_60_25_15',[.6,.25,.15]),('work_25_50_25',[.25,.5,.25]),('research_15_25_60',[.15,.25,.6])]:
        r={}
        for name in layouts:
            avg=sum(w*cat[domain][name]['v2_s_per_1000'] for domain,w in zip(package['domains'],weights))
            r[name]=avg
        for name in layouts:
            mixes.append(dict(profile=scenario,layout=name,model_s_per_1000_keys=r[name],gain_vs_qwerty_pct=100*(r['QWERTY']/r[name]-1),rank=1+sum(v<r[name]-1e-8 for v in r.values())))
    write(out/'mixture_profiles.csv',mixes)
    for r in freq:print(f"{r['domain']}: {r['keystrokes']:,} keystrokes; {r['long_marks']:,} long signs ({r['long_mark_pct']:.2f}%)")
    print('Domain  Model     rank  gain_v2 vs QWERTY   gain old  KLA unchanged')
    for dom in package['domains']:
        rows=sorted((r for r in summary if r['domain']==dom and r['split']=='all'),key=lambda x:x['v2_s'])
        for rank,r in enumerate(rows[:5],1):print(f"{dom} {r['layout']:14} {rank} {r['v2_gain_pct']:+7.2f}%  old {r['legacy_gain_pct']:+7.2f}% KLA {r['KLA_approx_unchanged']:.2f}")
    for profile in ['equal_1_1_1','daily_60_25_15','work_25_50_25','research_15_25_60']:
        print(profile, [(r['layout'],round(r['gain_vs_qwerty_pct'],2)) for r in mixes if r['profile']==profile and r['rank']<=3])
    print('PASS: 48 documents, rows, sensitivity and profile CSV output:',out)
if __name__=='__main__':main()
