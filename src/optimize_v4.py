#!/usr/bin/env python3
"""NOVA F4: JIS-like full printable layer, fixed digits, explicit Shift chords.

Stochastic simulated annealing is NOT exhaustive enumeration or a proof of
human typing optimality. All milliseconds are uncalibrated hypotheses.
Requires Python >=3.11, numpy and numba; tested on Python 3.13.5. Corpus artifacts contain counts only.
"""
from __future__ import annotations
import argparse, csv, gzip, hashlib, json, math, string, time
from collections import Counter
from pathlib import Path
from functools import lru_cache
import numpy as np
from numba import njit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results/v4'
SEARCH = OUT/'search'
ALPH = '\t\n' + ''.join(map(chr,range(32,127)))
CI = {c:i for i,c in enumerate(ALPH)}
N = len(ALPH)
VOWELS = np.array([CI[c] for c in 'aeiou'],np.int32)
LETTERS = set(string.ascii_lowercase)
PUNCT = set(string.punctuation)
# Physical approximate stagger retained from v2, number row offset -0.5.
# No claim these are calibrated coordinates of the user's keyboard.
ROW_LENGTHS = (13,12,12,11)
BASE_JIS = ('1234567890-^¥','qwertyuiop@[','asdfghjkl;:]','zxcvbnm,./\\')
SHIFT_JIS = ('!"#$%&\'()\0=~|','QWERTYUIOP`{','ASDFGHJKL+*}','ZXCVBNM<>?_')
assert [len(s) for s in BASE_JIS] == list(ROW_LENGTHS)
assert [len(s) for s in SHIFT_JIS] == list(ROW_LENGTHS)
PAT = [0,1,2,3,3,4,4,5,6,7]
FNAME = ['L-pinky','L-ring','L-middle','L-index','R-index','R-middle','R-ring','R-pinky','thumb']
ROW_MS = np.array([[18,0,0],[0,0,18],[0,0,12],[0,0,0],[0,0,0],[0,0,9],[0,0,9],[7,0,0],[0,0,0]],float)
CAP = np.array([.12,.16,.20,.28,.28,.20,.16,.12],float)
CO=[]; FI=[]; ROW=[]; KEY=[]
for r,(chars,off,y) in enumerate(zip(BASE_JIS,[-.5,0,.22,.47],[2,1,0,-1])):
    for col,ch in enumerate(chars):
        CO.append((col+off,y)); FI.append(PAT[col] if col<10 else 7)
        ROW.append(r-1); KEY.append(('number','upper','home','lower')[r]+f'_{col+1}')
# 48 Space, 49 Enter, 50 Tab; 51 LShift, 52 RShift.
for name,xy,f,r in [('Space',(5,-2.3),8,-2),('Enter',(12.3,0),7,-2),('Tab',(-1.2,1),0,-2),('LShift',(-1,-1),0,-2),('RShift',(11.8,-1),7,-2)]:
    KEY.append(name); CO.append(xy); FI.append(f); ROW.append(r)
CO=np.array(CO,float); FI=np.array(FI,np.int32); ROW=np.array(ROW,np.int32)
HAND=np.where(FI==8,2,np.where(FI<4,0,1)).astype(np.int32)
HOME=np.array([[.22,0],[1.22,0],[2.22,0],[3.22,0],[6.22,0],[7.22,0],[8.22,0],[9.22,0],[5,-2.3]])
HD=np.linalg.norm(CO-HOME[FI],axis=1)
IN=(CO[:,0]-HOME[FI,0])*np.where(FI<4,1,-1)
ZONE=np.where(FI==8,0,np.where(IN>.4,1,np.where(IN<-.4,-1,0)))
MUTABLE=np.array([i for i in range(48) if i not in list(range(10))+[12]],np.int32)
ALPHA_IDS=np.array([CI[c] for c in string.ascii_lowercase],np.int32)
ISLOWER=np.array([c in LETTERS for c in ALPH],np.bool_)
ISPUNCT=np.array([c in PUNCT for c in ALPH],np.bool_)
PROFILES={'JP':(.30,.30,.25,.08,.07), 'Balance':(.18,.18,.19,.23,.22), 'Code':(.11,.11,.13,.20,.45)}
DOMAINS=('生活文','業務文','技術文')


def counts(texts):
    u=Counter(); g=Counter(); first=Counter(); last=Counter(); total=0
    for txt in texts:
        s=''.join(c for c in txt.replace('\r\n','\n') if c in CI)
        if not s: continue
        u.update(s); g.update(zip(s,s[1:])); first[s[0]]+=1; last[s[-1]]+=1; total+=len(s)
    return {'n':total, 'u':sorted(u.items()), 'g':[[a,b,n] for (a,b),n in sorted(g.items())], 'first':sorted(first.items()),'last':sorted(last.items())}


def merge_counts(seq):
    u=Counter();g=Counter();f=Counter();l=Counter();n=0
    for d in seq:
        n+=d['n'];u.update(dict(d['u']));g.update({(a,b):v for a,b,v in d['g']});f.update(dict(d['first']));l.update(dict(d['last']))
    return {'n':n,'u':sorted(u.items()),'g':[[a,b,v] for (a,b),v in sorted(g.items())], 'first':sorted(f.items()),'last':sorted(l.items())}


def prepare():
    """Deduplicate synthetic JP sentences; preserve raw case/punctuation for OSS."""
    old=json.loads((ROOT/'data/jp_en_corpora.json').read_text())
    pack=json.loads((ROOT/'data/synthetic_three_domains.json').read_text())
    unique={}
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
    # Explicitly assert no sentence leakage across train/valid/test.
    sets=[{s for (d,t,i),s in unique.items() if i in ids} for ids in (range(8),range(8,10),range(10,12))]
    assert not (sets[0]&sets[1] or sets[0]&sets[2] or sets[1]&sets[2])
    en=old['EN_original']
    data['EN/train']=counts([en[t] for t in ('Everyday','Research','Business','History')])
    data['EN/test']=counts([en[t] for t in ('Software','Literature')])
    data['JP/original']=counts(list(old['JP_romaji'].values()))
    mod=json.loads((ROOT/'data/modern_jp_corpora.json').read_text())
    data['JP/loanword']=counts([d['romaji'] for d in mod['documents']])
    v3=json.loads((ROOT/'data/v3_ngrams.json').read_text())
    sources=[]
    for f in v3['source']['code_files']:
        p=Path(f['origin_path_example']);raw=p.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==f['source_sha256'],str(p)
        win=f['sample_window'];s=raw.decode(errors='replace')[win['start']:win['start']+win['length']]
        s=''.join(c for c in s.replace('\r\n','\n') if c in CI)
        assert hashlib.sha256(s.encode()).hexdigest()==f['sample_sha256'],str(p)
        k=f"CODE/{f['language']}/{f['split']}";data[k]=counts([s]);sources.append(f)
    for split in ('train','test'):
        # Training uses equal weight per language, not bytes. Both pooling modes archived.
        data['CODE/'+split]=merge_counts([v for k,v in data.items() if k.startswith('CODE/') and k.count('/')==2 and k.endswith('/'+split)])
    for split in ('train','valid','test'):
        data['JP/'+split]=merge_counts([data[d+'/'+split] for d in DOMAINS])
    out={'version':4,'alphabet':ALPH,'warning':'Synthetic JP, sentence-disjoint split. Legacy diagnostic corpora were previously inspected; not fresh blind tests. No OSS source text.', 'jp_sentence_groups':meta,'code_sources':sources,'groups':data}
    (ROOT/'data/v4/raw_ngrams.json.gz').write_bytes(gzip.compress(json.dumps(out,ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
    return out


def read_data():
    return json.loads(gzip.decompress((ROOT/'data/v4/raw_ngrams.json.gz').read_bytes()))


def arrays(c):
    u=np.zeros(N);g=np.zeros((N,N));f=np.zeros(N);l=np.zeros(N)
    for ch,v in c['u']:u[CI[ch]]=v
    for a,b,v in c['g']:g[CI[a],CI[b]]=v
    for ch,v in c['first']:f[CI[ch]]=v
    for ch,v in c['last']:l[CI[ch]]=v
    assert int(u.sum())==c['n']
    return u,g,f,l


def keycost(row_scale=1.,splay_scale=1.):
    p=np.zeros(len(CO))
    for k in range(len(p)):
        r=ROW[k];f=FI[k]
        p[k]=(ROW_MS[f,r] if 0<=r<3 else 12 if r==-1 else 0)*row_scale
        if ZONE[k]==1:p[k]+=(7 if f in (3,4) else 5)*splay_scale
        if ZONE[k]==-1:p[k]+=(10 if f in (0,7) else 6)*splay_scale
    return p


@lru_cache(maxsize=16)
def matrices(row_scale=1.,splay_scale=1.,shift_scale=1.):
    """Costs in ms. State 2*key+layer; Shift uses opposite-hand pinky.
    8ms chord coordination/shifted character; 30ms engage per run;
    19ms*pitch reach and 9ms*pitch return for modifier; held modifier reused.
    Boundary pinky/modifier conflict +12ms, uncalibrated.
    """
    actions=51*2; akey=np.arange(actions)//2; layers=np.arange(actions)%2
    fs=FI[akey];hs=HAND[akey]
    sh=np.where(layers==0,-1,np.where(hs==0,1,0)).astype(np.int32)
    per=118+keycost(row_scale,splay_scale)[akey]+8*shift_scale*layers
    first=19*HD[akey];last=9*HD[akey];tm=np.zeros((actions,actions))
    for a in range(actions):
        if sh[a]>=0:
            first[a]+=(30+19*HD[51+sh[a]])*shift_scale
            last[a]+=9*HD[51+sh[a]]*shift_scale
        for b in range(actions):
            x,y=akey[a],akey[b];d=math.dist(CO[x],CO[y])
            if FI[x]==FI[y]:
                val=23 if x==y else 36+56*math.log2(1+d)+6*d
                if x!=y:
                    if {ROW[x],ROW[y]}=={0,2}:val+=7*row_scale
                    if ZONE[y]==1:val+=4*splay_scale
                    elif ZONE[y]==-1:val+=6*splay_scale
            else:
                val=19*HD[y]+9*HD[x]+(8 if HAND[x]==HAND[y] and HAND[x]!=2 else 0)
            sa,sb=sh[a],sh[b]
            if sa!=sb:
                if sa>=0:val+=9*HD[51+sa]*shift_scale
                if sb>=0:val+=(30+19*HD[51+sb])*shift_scale
            if sa>=0 and FI[y]==(0 if sa==0 else 7):val+=12*shift_scale
            if sb>=0 and FI[x]==(0 if sb==0 else 7):val+=12*shift_scale
            tm[a,b]=val
    return per,tm,first,last


def jis():
    b=np.array([CI.get(c,-1) for c in ''.join(BASE_JIS)],np.int32)
    s=np.array([CI.get(c,-1) for c in ''.join(SHIFT_JIS)],np.int32)
    return b,s


def mapped(b,s):
    p=np.full(N,-1,np.int32)
    for k in range(48):
        if b[k]>=0:
            assert p[b[k]]<0
            p[b[k]]=2*k
        if s[k]>=0:
            assert p[s[k]]<0
            p[s[k]]=2*k+1
    p[CI[' ']]=96;p[CI['\n']]=98;p[CI['\t']]=100
    assert np.all(p>=0)
    return p


def validate(b,s,vowels_left=False,hyphen=0):
    p=mapped(b,s)
    for i,c in enumerate('1234567890'):assert b[i]==CI[c]
    assert b[12]==-1
    for c in LETTERS:
        k=p[CI[c]]//2;assert k>=13 and p[CI[c]]%2==0 and s[k]==CI[c.upper()]
    assert p[CI['-']]%2==0
    if vowels_left:assert all(HAND[p[i]//2]==0 for i in VOWELS)
    if hyphen:assert HAND[p[CI['-']]//2]==(0 if hyphen<0 else 1)
    return p


def from_rows(rows):
    """JIS-adapted reference: preserve central 30 and fill remaining symbol faces.
    Not a claim of official native JIS Dvorak/Colemak etc. Digits always JIS-fixed.
    """
    b,s=jis();core=list(range(13,23))+list(range(25,35))+list(range(37,47))
    for k in core:b[k]=-1;s[k]=-1
    flat=''.join(rows)
    # Remove central characters from former peripheral positions to avoid duplicate keys.
    for k in MUTABLE:
        if k not in core and b[k]>=0 and ALPH[b[k]] in flat:b[k]=-1;s[k]=-1
    for k,c in zip(core,flat):b[k]=CI[c];s[k]=CI[c.upper()] if c in LETTERS else -1
    # Each reference has same 11 unshifted punctuation where possible.
    used={ALPH[x] for x in b if x>=0}
    missing=[c for c in '-^@[;:],./\\' if c not in used]
    empty=[k for k in MUTABLE if b[k]<0]
    # Dvorak places apostrophe in core: displaces one original JIS punctuation to shift.
    for k,c in zip(empty,missing):b[k]=CI[c]
    assert all(b[k]>=0 for k in MUTABLE)
    # Keep original JIS shifted symbol when its face is free and symbol not unshifted.
    used=set(x for x in b if x>=0)
    for k in range(48):
        if b[k]>=0 and ISLOWER[b[k]]:s[k]=CI[ALPH[b[k]].upper()]
        elif s[k]>=0 and (s[k] in used or not ISPUNCT[s[k]]):s[k]=-1
    seen=set()
    for k in range(48):
        if s[k]>=0:
            if s[k] in seen:s[k]=-1
            else:seen.add(s[k])
    unassigned=[CI[c] for c in string.punctuation if CI[c] not in used and CI[c] not in seen]
    free=[k for k in range(48) if s[k]<0 and not (b[k]>=0 and ISLOWER[b[k]])]
    for k,c in zip(free,unassigned):s[k]=c
    # Preserve ordinary JIS base/Shift punctuation pairs on relocated keys.
    # Dvorak's apostrophe-based core is separately labelled a JIS adaptation.
    if "'" not in flat:
        pairs=dict(zip('-^@[;:],./\\', '=~`{+*}<>?_'))
        s=np.full(48,-1,np.int32)
        for k,c in enumerate(b):
            if k==12:s[k]=CI['|']
            elif c>=0:
                ch=ALPH[c]
                if ch in LETTERS:s[k]=CI[ch.upper()]
                elif ch.isdigit():s[k]=CI.get(SHIFT_JIS[0][k],-1)
                else:s[k]=CI[pairs[ch]]
    validate(b,s)
    return b,s


def objective_arrays(bundle,profile):
    groups=bundle['groups'];weights=PROFILES[profile]
    u=np.zeros(N);g=np.zeros((N,N));f=np.zeros(N);l=np.zeros(N)
    labels=[d+'/train' for d in DOMAINS]+['EN/train','CODE/train']
    for label,w in zip(labels,weights):
        if label=='CODE/train':
            languages=[k for k in groups if k.startswith('CODE/') and k.count('/')==2 and k.endswith('/train')]
            sub=[(groups[k],w/len(languages)) for k in languages]
        else:sub=[(groups[label],w)]
        for c,q in sub:
            aa=arrays(c);n=c['n']
            u+=q*aa[0]/n;g+=q*aa[1]/n;f+=q*aa[2]/n;l+=q*aa[3]/n
    per,tm,first,last=matrices()
    A=u[:,None]*per+f[:,None]*first+l[:,None]*last
    # Same soft constraints as v3, separate from reported motor time.
    home=(ROW[np.arange(102)//2]==1)
    A+=3*u[:,None]*(1-home)
    k=np.arange(102)//2
    sf=(FI[k,None]==FI[k[None,:]])&(k[:,None]!=k[None,:])
    C=tm+12*sf
    return A,C,u,g


@njit(cache=True)
def reg(fl):
    v=0.
    for i in range(8):
        excess=max(0.,fl[i]-CAP[i]);v+=160*excess*excess
    left=fl[0]+fl[1]+fl[2]+fl[3]
    return v+10*(left-.5)**2


@njit(cache=True)
def evaluate_fast(p,A,C,u,g):
    val=0.;fl=np.zeros(8)
    for i in range(N):
        val+=A[i,p[i]]
        f=FI[p[i]//2]
        if f<8:fl[f]+=u[i]
        for j in range(N):val+=g[i,j]*C[p[i],p[j]]
    return val+reg(fl),fl


@njit(cache=True)
def delta(p,ids,news,m,A,C,u,g,fl):
    v=0.;fnew=fl.copy()
    for k in range(m):
        i=ids[k];old=p[i];new=news[k]
        v+=A[i,new]-A[i,old]
        fo,fn=FI[old//2],FI[new//2]
        if fo<8:fnew[fo]-=u[i]
        if fn<8:fnew[fn]+=u[i]
        for j in range(N):
            changed=False
            for h in range(m):
                if ids[h]==j:changed=True;break
            if not changed:
                v+=g[i,j]*(C[new,p[j]]-C[old,p[j]])
                v+=g[j,i]*(C[p[j],new]-C[p[j],old])
    for k in range(m):
        for h in range(m):v+=g[ids[k],ids[h]]*(C[news[k],news[h]]-C[p[ids[k]],p[ids[h]]])
    return v+reg(fnew)-reg(fl),fnew


@njit(cache=True)
def propose(b,s,p,kind,x,y,hyphen,vl,stage=2):
    ids=np.empty(4,np.int32);news=np.empty(4,np.int32);m=0
    if kind==0:  # swap base+shift bundles, keeping uppercase with lowercase
        if x<10 or y<10 or x==12 or y==12 or x==y:return ids,news,0
        if (x<13 and ISLOWER[b[y]]) or (y<13 and ISLOWER[b[x]]):return ids,news,0
        if stage==3 and (ISLOWER[b[x]] or ISLOWER[b[y]]):return ids,news,0
        for z,act in ((b[x],2*y),(s[x],2*y+1),(b[y],2*x),(s[y],2*x+1)):
            if z>=0:ids[m]=z;news[m]=act;m+=1
    elif kind==1: # independent Shift face permutation
        if x==y:return ids,news,0
        if (b[x]>=0 and ISLOWER[b[x]]) or (b[y]>=0 and ISLOWER[b[y]]):return ids,news,0
        if s[x]<0 and s[y]<0:return ids,news,0
        for z,act in ((s[x],2*y+1),(s[y],2*x+1)):
            if z>=0:ids[m]=z;news[m]=act;m+=1
    else: # exchange a non-minus base punctuation with a Shift punctuation
        if x<10 or x==12 or b[x]<0 or not ISPUNCT[b[x]] or b[x]==CI_MINUS:return ids,news,0
        if s[y]<0 or not ISPUNCT[s[y]]:return ids,news,0
        ids[0]=b[x];news[0]=2*y+1;ids[1]=s[y];news[1]=2*x;m=2
    for k in range(m):
        i=ids[k];a=news[k]
        if vl:
            for v in VOWELS:
                if i==v and HAND[a//2]!=0:return ids,news,0
        if i==CI_MINUS:
            if a%2:return ids,news,0
            if hyphen!=0 and HAND[a//2]!=(0 if hyphen<0 else 1):return ids,news,0
    return ids,news,m

CI_MINUS=CI['-']

@njit(cache=True)
def apply_move(b,s,p,kind,x,y,ids,news,m):
    if kind==0:b[x],b[y]=b[y],b[x];s[x],s[y]=s[y],s[x]
    elif kind==1:s[x],s[y]=s[y],s[x]
    else:b[x],s[y]=s[y],b[x]
    for k in range(m):p[ids[k]]=news[k]


@njit(cache=True)
def anneal(b0,s0,p0,A,C,u,g,seed,iterations,hyphen,vl,randomize=True,stage=2):
    np.random.seed(seed)
    b=b0.copy();s=s0.copy();p=p0.copy()
    # Independent random starting states, not perturbations of a shared best.
    if randomize:
        for _ in range(600):
            kind=0 if stage==0 else (1 if stage==1 else np.random.randint(3))
            x=MUTABLE[np.random.randint(len(MUTABLE))] if kind!=1 else np.random.randint(48)
            y=MUTABLE[np.random.randint(len(MUTABLE))] if kind==0 else np.random.randint(48)
            if stage==1 and kind==0:continue
            ids,news,m=propose(b,s,p,kind,x,y,hyphen,vl,stage)
            if m:apply_move(b,s,p,kind,x,y,ids,news,m)
    val,fl=evaluate_fast(p,A,C,u,g)
    best=val;bb=b.copy();bs=s.copy();bp=p.copy()
    checkpoints=np.zeros(11);checkpoints[0]=best
    valid=0;accepted=0
    for it in range(iterations):
        r=np.random.random()
        kind=0 if stage==0 or (stage in (2,3) and r<.64) else (1 if stage==1 or r<.88 else 2)
        x=MUTABLE[np.random.randint(len(MUTABLE))] if kind!=1 else np.random.randint(48)
        y=MUTABLE[np.random.randint(len(MUTABLE))] if kind==0 else np.random.randint(48)
        ids,news,m=propose(b,s,p,kind,x,y,hyphen,vl,stage)
        if m:
            valid+=1
            dv,fn=delta(p,ids,news,m,A,C,u,g,fl)
            temp=1.8*(.001/1.8)**(it/max(1,iterations-1))
            if dv<=0 or np.random.random()<math.exp(-min(745.,dv/temp)):
                apply_move(b,s,p,kind,x,y,ids,news,m);val+=dv;fl=fn;accepted+=1
                if val<best:best=val;bb=b.copy();bs=s.copy();bp=p.copy()
        if (it+1)%(iterations//10)==0:checkpoints[(it+1)//(iterations//10)]=best
    # Complete one-move neighborhood descent, counts reported separately.
    b=bb.copy();s=bs.copy();p=bp.copy();val,fl=evaluate_fast(p,A,C,u,g)
    polished=0
    for sweep in range(12):
        gain=0.;winner=(-1,-1,-1)
        for kind in range(3):
            if stage==0 and kind!=0:continue
            if stage==1 and kind!=1:continue
            for x in range(48):
                for y in range(48):
                    if kind!=2 and y<=x:continue
                    ids,news,m=propose(b,s,p,kind,x,y,hyphen,vl,stage)
                    if not m:continue
                    polished+=1;dv,fn=delta(p,ids,news,m,A,C,u,g,fl)
                    if dv<gain-1e-10:gain=dv;winner=(kind,x,y)
        if winner[0]<0:break
        kind,x,y=winner;ids,news,m=propose(b,s,p,kind,x,y,hyphen,vl,stage)
        dv,fl=delta(p,ids,news,m,A,C,u,g,fl);apply_move(b,s,p,kind,x,y,ids,news,m);val+=dv
    exact,_=evaluate_fast(p,A,C,u,g)
    assert abs(exact-val)<1e-6
    return b,s,exact,valid,accepted,polished,checkpoints


def metrics(b,s,c,row_scale=1.,splay_scale=1.,shift_scale=1.):
    p=validate(b,s);u,g,f,l=arrays(c);n=c['n']
    if n<=0:raise ValueError('No supported input characters')
    per,tm,first,last=matrices(row_scale,splay_scale,shift_scale)
    t=float(u@per[p]+f@first[p]+l@last[p]+np.sum(g*tm[p[:,None],p[None,:]]))
    keys=p//2;finger=FI[keys];hand=HAND[keys]
    sf=(finger[:,None]==finger[None,:])&(keys[:,None]!=keys[None,:])
    sh=(hand[:,None]==hand[None,:])&(hand[:,None]!=2)&(keys[:,None]!=keys[None,:])
    alt=(hand[:,None]!=hand[None,:])&(hand[:,None]!=2)&(hand[None,:]!=2)
    d=np.linalg.norm(CO[keys,None,:]-CO[keys[None,:],:],axis=2)
    travel=float(np.sum(g*np.where(finger[:,None]==finger[None,:],d,HD[keys,None]+HD[keys[None,:]]))+(f+l)@HD[keys])
    fl=np.bincount(finger,weights=u,minlength=9)
    fw=np.array([.5,1,4,2,2,4,1,.5,.5]);cm=travel*1.905/n
    sfb=float(np.sum(g*sf));sameh=float(np.sum(g*sh));pairs=g.sum()
    kla=33*max(0,(4-cm)/4)+33*np.dot(np.minimum(fl*100/n,20),fw)/260+17*max(0,(10-sfb*100/n)/10)+17*max(0,(50-sameh*100/n)/50)
    # Modifier entries are binary events; modifier travel excluded from KLA-main.
    side=np.where(p%2==0,-1,np.where(hand==0,1,0))
    entries=float(np.sum(g*((side[None,:]>=0)&(side[:,None]!=side[None,:])))+np.sum(f*(side>=0)))
    return {'ms_per_char':t/n,'seconds':t/1000,'chars':n,'KLA_main_approx':kla,'main_distance_m':travel*.01905,'SFB_pct':100*sfb/pairs if pairs else 0.,'alternation_pct':100*np.sum(g*alt)/pairs if pairs else 0.,'shifted_char_pct':100*np.sum(u*(p%2))/n,'shift_entries_per_100':100*entries/n,'number_row_pct':100*np.sum(u*(ROW[keys]==-1))/n,'left_main_pct':100*np.sum(u*(hand==0))/n,'max_finger_pct':100*max(fl[:8])/n}


def serialize(b,s):
    off=0;out=[]
    for length in ROW_LENGTHS:
        out.append({'base':[ALPH[x] if x>=0 else ('¥' if k==12 else '') for k,x in enumerate(b) if off<=k<off+length], 'shift':[ALPH[x] if x>=0 else '' for x in s[off:off+length]]});off+=length
    return out


def csv_write(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)


def references():
    old=json.loads((ROOT/'layouts/layouts.json').read_text())
    f3=json.loads((ROOT/'data/v3_candidates.json').read_text())['optimized']
    old.update({k:v['rows'] for k,v in f3.items()})
    return {k:jis() if k=='QWERTY' else from_rows(v) for k,v in old.items()}


def force_hyphen(b,s,side):
    b=b.copy();s=s.copy();p=mapped(b,s);at=p[CI['-']]//2
    if HAND[at]==side:return b,s
    # swap with a low-frequency consonant; the full search subsequently optimizes.
    candidates=[k for k in MUTABLE if HAND[k]==side and k>=13 and ALPH[b[k]] not in 'aeiou']
    k=candidates[-1];b[at],b[k]=b[k],b[at];s[at],s[k]=s[k],s[at]
    return b,s


def run_search(bundle,rounds,iterations,which):
    SEARCH.mkdir(parents=True,exist_ok=True);refs=references();jobs=[]
    # Conditions isolate hyphen side with all five vowels fixed to the left hand.
    for profile in ('JP','Balance'):
        for cond,hp in [('free',0),('left',-1),('right',1)]:jobs.append((profile,cond,hp,2))
    jobs.extend([('Code','right',1,2),('Code','free',0,2),('Balance','symbols_only',0,3)])
    jobs.append(('Balance','shift_only',0,1))
    if which:jobs=[j for j in jobs if j[0]+'_'+j[1] in which.split(',')]
    allruns=[];winners={}
    for idx,(profile,cond,hp,stage) in enumerate(jobs):
        A,C,u,g=objective_arrays(bundle,profile)
        seedname='Nova-F3-'+('JP' if profile=='JP' else 'Code' if profile=='Code' else 'Balance')
        saved=json.loads((ROOT/'data/v4/search_seeds.json').read_text())[seedname]
        b,s=np.array(saved['base'],np.int32),np.array(saved['shift'],np.int32)
        if stage in (1,3):b,s=refs[seedname]
        if hp:b,s=force_hyphen(b,s,0 if hp<0 else 1)
        validate(b,s,True,hp);best=(1e9,None,None)
        for run in range(rounds):
            seed=20261031+{'JP':0,'Balance':100000,'Code':200000}[profile]+{'free':0,'left':10000,'right':20000,'shift_only':30000,'symbols_only':40000}[cond]+run*137
            t=time.time();bb,ss,score,valid,accepted,polish,ck=anneal(b,s,mapped(b,s),A,C,u,g,seed,iterations,hp,True,run>0,stage)
            validate(bb,ss,True,hp)
            if stage==1:assert np.array_equal(bb,b), "Shift-only changed a base key"
            if stage==3:
                pm0,pm1=mapped(b,s),mapped(bb,ss)
                assert all(pm0[i]==pm1[i] for i in ALPHA_IDS), "Symbols-only changed a letter"
            row={'job':profile+'_'+cond,'restart':run,'seed':seed,'objective_ms':float(score),'proposals':iterations,'valid':int(valid),'accepted':int(accepted),'polish_evaluations':int(polish),'wall_seconds':round(time.time()-t,3),'hyphen_key':KEY[mapped(bb,ss)[CI['-']]//2]}
            row.update({f'best_{i*10}pct':float(v) for i,v in enumerate(ck)})
            allruns.append(row)
            if score<best[0]:best=(score,bb.copy(),ss.copy())
            print(profile,cond,run,round(score,6),'best',round(best[0],6),'valid',valid,flush=True)
        name='F4-'+profile+'-'+cond
        winners[name]={'base':best[1].tolist(),'shift':best[2].tolist(),'objective_ms':float(best[0]),'rows':serialize(best[1],best[2]),'vowels_left':True,'hyphen_constraint':hp,'profile':profile,'iterations':iterations,'restarts':rounds}
        (SEARCH/(profile+'_'+cond+'_winner.json')).write_text(json.dumps(winners[name],ensure_ascii=False,indent=2))
        csv_write(SEARCH/(profile+'_'+cond+'_runs.csv'),[r for r in allruns if r['job']==profile+'_'+cond])
    return winners


def report(bundle):
    if not list(SEARCH.glob('*_winner.json')):
        raise FileNotFoundError(f'No frozen search winners in {SEARCH}; restore them before reporting.')
    refs=references();alllayouts=dict(refs);winners={}
    for path in sorted(SEARCH.glob('*_winner.json')):
        d=json.loads(path.read_text());name=('QWERTY-ShiftDigitsExact' if path.stem=='QWERTY_numberrow_exact_winner' else 'F4-'+path.stem.replace('_winner','').replace('_','-'));winners[name]=d
        alllayouts[name]=(np.array(d['base'],np.int32),np.array(d['shift'],np.int32))
    score_rows=[]
    for group,c in bundle['groups'].items():
        q=metrics(*refs['QWERTY'],c)
        for name,(b,s) in alllayouts.items():
            m=metrics(b,s,c);m.update(group=group,layout=name,gain_vs_qwerty_pct=100*(q['seconds']/m['seconds']-1))
            score_rows.append(m)
    csv_write(OUT/'scores.csv',score_rows)
    (ROOT/'data/v4/candidates.json').write_text(json.dumps({'version':4,'hypothetical':True,'winners':winners},ensure_ascii=False,indent=2))
    # Atomic hyphen swaps of F3-JP; all letter/symbol displacement is counted.
    b0,s0=refs['Nova-F3-JP'];p0=mapped(b0,s0);at=p0[CI['-']]//2;swap=[]
    for group in ['JP/train','JP/test','JP/loanword','EN/test','CODE/test']:
        c=bundle['groups'][group];m0=metrics(b0,s0,c)
        for dst in MUTABLE:
            b=b0.copy();s=s0.copy()
            if dst<13:continue
            # Keep vowels to left while changing hyphen's partner.
            if HAND[dst]==1 and ALPH[b[dst]] in 'aeiou':continue
            b[at],b[dst]=b[dst],b[at];s[at],s[dst]=s[dst],s[at]
            m=metrics(b,s,c)
            swap.append({'group':group,'hyphen_key':KEY[dst],'side':('left' if HAND[dst]==0 else 'right'),'swapped':ALPH[b0[dst]],'gain_vs_F3JP_pct':100*(m0['seconds']/m['seconds']-1),'KLA_main_approx':m['KLA_main_approx'],'alternation_pct':m['alternation_pct'],'SFB_pct':m['SFB_pct']})
    csv_write(OUT/'hyphen_swaps.csv',swap)
    # Direct predecessor/successor frequencies, on raw romaji.
    context=[]
    for group,c in bundle['groups'].items():
        if not (group.startswith('JP/') or group.split('/')[0] in DOMAINS):continue
        for a,b,v in c['g']:
            if a=='-' or b=='-':context.append({'group':group,'bigram':a+b,'count':v,'direction':'before' if b=='-' else 'after'})
    csv_write(OUT/'hyphen_context.csv',context)
    return score_rows


@njit(cache=True)
def enumerate_number_row(b0,s0,p0,A,C,u,g,nslots=10):
    """Heap's algorithm: all 10! permutations of Shift+1..0, others fixed."""
    b=b0.copy();s=s0.copy();p=p0.copy();val,fl=evaluate_fast(p,A,C,u,g)
    best=val;best_s=s.copy();c=np.zeros(nslots,np.int64);i=0;visited=1
    while i<nslots:
        if c[i]<i:
            x=0 if i%2==0 else c[i];y=i
            ids,news,m=propose(b,s,p,1,x,y,0,False,1)
            assert m>0
            dv,fl=delta(p,ids,news,m,A,C,u,g,fl)
            apply_move(b,s,p,1,x,y,ids,news,m);val+=dv;visited+=1
            if val<best-1e-9:best=val;best_s=s.copy()
            c[i]+=1;i=0
        else:c[i]=0;i+=1
    return best_s,best,visited


def run_exact_number_row(bundle):
    SEARCH.mkdir(parents=True,exist_ok=True)
    b,s=jis();A,C,u,g=objective_arrays(bundle,'Balance')
    t=time.time();ss,best,visited=enumerate_number_row(b,s,mapped(b,s),A,C,u,g)
    p=validate(b,ss);exact,_=evaluate_fast(p,A,C,u,g)
    assert visited==math.factorial(10)
    assert abs(exact-best)<1e-5
    result={'base':b.tolist(),'shift':ss.tolist(),'objective_ms':float(exact),'rows':serialize(b,ss),'vowels_left':False,'hyphen_constraint':0,'profile':'Balance','search':'exhaustive Shift+1..0 only; all other keys fixed at QWERTY-JIS','enumerated_unique_permutations':int(visited),'wall_seconds':time.time()-t}
    (SEARCH/'QWERTY_numberrow_exact_winner.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print('EXACT',visited,'objective',exact,'shift digits',''.join(ALPH[x] if x>=0 else '·' for x in ss[:10]),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare',action='store_true');p.add_argument('--search',action='store_true');p.add_argument('--report',action='store_true')
    p.add_argument('--enumerate-number-row',action='store_true')
    p.add_argument('--rounds',type=int,default=48);p.add_argument('--iterations',type=int,default=100000);p.add_argument('--jobs')
    args=p.parse_args()
    if args.rounds<1 or args.iterations<10 or args.iterations%10:p.error('rounds must be positive; iterations must be a positive multiple of 10')
    bundle=prepare() if args.prepare else read_data()
    if args.search:run_search(bundle,args.rounds,args.iterations,args.jobs)
    if args.enumerate_number_row:run_exact_number_row(bundle)
    if args.report:report(bundle)

if __name__=='__main__':main()
