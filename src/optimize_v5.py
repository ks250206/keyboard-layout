#!/usr/bin/env python3
"""NOVA F5: constrained simulated annealing for mnemonic punctuation pairs.

Reuses the frozen F4 corpus, geometry, motor-time model and training objective.
Memory is a HARD structural constraint, not an invented millisecond benefit.
A stochastic search is not exhaustive and does not prove a global optimum.
"""
from __future__ import annotations
import argparse, hashlib, json, math, time
from pathlib import Path
import numpy as np
from numba import njit
import optimize_v4 as v

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/v5'
PAIR_STRINGS = ('()', '[]', '{}', '<>', ';:', "'\"", ',.', '-_', '/\\')
PAIRS = np.array([[v.CI[c] for c in x] for x in PAIR_STRINGS], dtype=np.int32)
UPPER = np.array([v.CI[c.upper()] for c in 'abcdefghijklmnopqrstuvwxyz'], np.int32)
LOWER = np.array([v.CI[c] for c in 'abcdefghijklmnopqrstuvwxyz'], np.int32)
DIGITS = np.array([v.CI[c] for c in '1234567890'], np.int32)
SPACE_IDX, ENTER_IDX, TAB_IDX = v.CI[' '], v.CI['\n'], v.CI['\t']
# 0 unconstrained control, 1 either horizontal OR same-key, 2 every pair same-key,
# 3 two 2x2 bracket blocks: ()/<>, []/{}, other five pairs same-key.
MODES = {'free': 0, 'mixed': 1, 'shift': 2, 'grid': 3}
JOBS = [('JP','mixed'), ('Balance','mixed'), ('Code','mixed'),
        ('Balance','shift'), ('Balance','grid'), ('Code','grid')]


def structure(mode: int):
    """Finite legal destination patterns for each semantic group."""
    groups = [list(x) for x in PAIR_STRINGS]
    if mode == 3:
        groups = [list('()<>'), list('[]{}')] + [list(x) for x in PAIR_STRINGS[4:]]
    ids = np.full((len(groups), 4), -1, np.int32)
    lens = np.array([len(x) for x in groups], np.int32)
    pats = []
    for gi, cs in enumerate(groups):
        ids[gi,:len(cs)] = [v.CI[c] for c in cs]
        arr = []
        if len(cs) == 4:
            for k in range(13,47):
                if v.ROW[k] == v.ROW[k+1]:
                    arr.append([2*k,2*(k+1),2*k+1,2*(k+1)+1])
        else:
            for k in v.MUTABLE:
                arr.append([2*k,2*k+1,-1,-1])
            if mode == 1:
                for k in range(47):
                    if v.ROW[k] != v.ROW[k+1]: continue
                    for layer in (0,1):
                        if layer == 0 and (k < 10 or k in (11,12)): continue
                        arr.append([2*k+layer,2*(k+1)+layer,-1,-1])
        pats.append(arr)
    dest = np.full((len(groups),max(map(len,pats)),4),-1,np.int32)
    plen = np.array(list(map(len,pats)),np.int32)
    for i, arr in enumerate(pats):dest[i,:len(arr)] = arr
    return ids,lens,dest,plen


@njit(cache=True)
def valid_mapping(p, mode):
    for i in range(10):
        if p[DIGITS[i]] != 2*i:return False
    for j in range(26):
        a=p[LOWER[j]]
        if a < 26 or a%2 != 0 or p[UPPER[j]] != a+1:return False
    for i in v.VOWELS:
        if v.HAND[p[i]//2] != 0:return False
    if p[v.CI_MINUS]%2:return False
    for i in range(9):
        a=p[PAIRS[i,0]];b=p[PAIRS[i,1]]
        same=(a%2==0 and b==a+1)
        hori=(a%2==b%2 and b//2==a//2+1 and v.ROW[a//2]==v.ROW[b//2])
        if mode==1:
            if not (same or hori):return False
        elif mode==2:
            if not same:return False
        elif mode==3:
            if i<4:
                if not hori:return False
            elif not same:return False
    if mode==3:
        # Ordered base and Shift pairs in two compact blocks.
        if p[PAIRS[0,0]]%2 or p[PAIRS[1,0]]%2:return False
        if p[PAIRS[3,0]]!=p[PAIRS[0,0]]+1:return False
        if p[PAIRS[3,1]]!=p[PAIRS[0,1]]+1:return False
        if p[PAIRS[2,0]]!=p[PAIRS[1,0]]+1:return False
        if p[PAIRS[2,1]]!=p[PAIRS[1,1]]+1:return False
    return True


@njit(cache=True)
def proposal(board,p,kind,x,y,reverse,mode,group_ids,lens,patterns):
    """Permutation of faces; never duplicate/drop an ASCII output.

    Ordinary moves preserve letter bundles by validation. Group moves relocate
    two related symbols or a complete four-symbol bracket block atomically.
    """
    new=board.copy()
    if kind==0:
        if x==y or x<10 or y<10 or x==12 or y==12:return new,p,0,np.empty(8,np.int32),np.empty(8,np.int32)
        new[2*x],new[2*y]=new[2*y],new[2*x]
        new[2*x+1],new[2*y+1]=new[2*y+1],new[2*x+1]
    elif kind==1:
        if x==y:return new,p,0,np.empty(8,np.int32),np.empty(8,np.int32)
        new[2*x+1],new[2*y+1]=new[2*y+1],new[2*x+1]
    elif kind==2:
        if x<10 or x==12:return new,p,0,np.empty(8,np.int32),np.empty(8,np.int32)
        new[2*x],new[2*y+1]=new[2*y+1],new[2*x]
    else:
        m=lens[x]
        old=np.empty(4,np.int32);target=patterns[x,y]
        for i in range(m):old[i]=p[group_ids[x,i]]
        holes=np.empty(4,np.int32);occ=np.empty(4,np.int32);nh=0;no=0
        for i in range(m):
            included=False
            for j in range(m):
                if old[i]==target[j]:included=True
            if not included:holes[nh]=old[i];nh+=1
            included=False
            for j in range(m):
                if target[i]==old[j]:included=True
            if not included:occ[no]=board[target[i]];no+=1
        if nh!=no:raise AssertionError('Invalid relocation permutation')
        for i in range(m):new[old[i]]=-1
        for i in range(m):new[target[i]]=group_ids[x,i]
        # Preserve layer order for displaced full-key bundles in the default
        # orientation. Reverse is useful when two singleton symbols are displaced.
        for i in range(nh):new[holes[i]]=occ[nh-i-1 if reverse else i]
    if new[24]!=-1:return new,p,0,np.empty(8,np.int32),np.empty(8,np.int32)
    ids=np.empty(8,np.int32);news=np.empty(8,np.int32);count=0;npmap=p.copy()
    for slot in range(96):
        if new[slot]!=board[slot] and new[slot]>=0:
            if count>=8:raise AssertionError('Move too large')
            ch=new[slot];ids[count]=ch;news[count]=slot;count+=1;npmap[ch]=slot
    if count==0 or not valid_mapping(npmap,mode):return new,p,0,ids,news
    return new,npmap,count,ids,news


@njit(cache=True)
def search_one(b0,s0,A,C,u,g,seed,iterations,mode,gi,gl,gp,gn,randomize=True):
    np.random.seed(seed)
    board=np.empty(96,np.int32)
    for k in range(48):board[2*k]=b0[k];board[2*k+1]=s0[k]
    p=np.full(v.N,-1,np.int32)
    for k in range(96):
        if board[k]>=0:p[board[k]]=k
    p[SPACE_IDX]=96;p[ENTER_IDX]=98;p[TAB_IDX]=100
    # The shuffled starts are generated independently from the same valid seed;
    # they are not uniform samples of the feasible space.
    warmup_accepted=0
    if randomize:
        for it in range(1200):
            kind=np.random.randint(4)
            if kind==3:x=np.random.randint(len(gi));y=np.random.randint(gn[x])
            else:x=np.random.randint(48);y=np.random.randint(48)
            nb,pp,m,ids,news=proposal(board,p,kind,x,y,np.random.randint(2),mode,gi,gl,gp)
            if m:board=nb;p=pp;warmup_accepted+=1
    val,fl=v.evaluate_fast(p,A,C,u,g)
    best=val;bestboard=board.copy();bestp=p.copy()
    valid=0;accepted=0;ck=np.zeros(11);ck[0]=best
    interval=max(1,iterations//10)
    for it in range(iterations):
        r=np.random.random()
        kind=0 if r<.48 else 1 if r<.62 else 2 if r<.72 else 3
        if kind==3:x=np.random.randint(len(gi));y=np.random.randint(gn[x])
        else:
            x=v.MUTABLE[np.random.randint(len(v.MUTABLE))] if kind!=1 else np.random.randint(48)
            y=v.MUTABLE[np.random.randint(len(v.MUTABLE))] if kind==0 else np.random.randint(48)
        nb,pp,m,ids,news=proposal(board,p,kind,x,y,np.random.randint(2),mode,gi,gl,gp)
        if m:
            valid+=1;dv,fn=v.delta(p,ids,news,m,A,C,u,g,fl)
            temp=1.8*(.001/1.8)**(it/max(1,iterations-1))
            if dv<=0 or np.random.random()<math.exp(-min(745.,dv/temp)):
                board=nb;p=pp;fl=fn;val+=dv;accepted+=1
                if val<best:best=val;bestboard=board.copy();bestp=p.copy()
        if (it+1)%interval==0 and (it+1)//interval<=10:ck[(it+1)//interval]=best
    board=bestboard;p=bestp;val,fl=v.evaluate_fast(p,A,C,u,g)
    polish=0
    # Descent over the implemented moves, not all possible feasible moves.
    for sweep in range(8):
        gain=-1e-10;win=(-1,-1,-1,-1)
        for kind in range(4):
            xmax=len(gi) if kind==3 else 48
            for x in range(xmax):
                ymax=gn[x] if kind==3 else 48
                for y in range(ymax):
                    if kind<2 and y<=x:continue
                    for rev in range(2 if kind==3 else 1):
                        nb,pp,m,ids,news=proposal(board,p,kind,x,y,rev,mode,gi,gl,gp)
                        if m==0:continue
                        polish+=1;dv,fn=v.delta(p,ids,news,m,A,C,u,g,fl)
                        if dv<gain:gain=dv;win=(kind,x,y,rev)
        if win[0]<0:break
        nb,pp,m,ids,news=proposal(board,p,win[0],win[1],win[2],win[3],mode,gi,gl,gp)
        dv,fl=v.delta(p,ids,news,m,A,C,u,g,fl);board=nb;p=pp;val+=dv
    exact,_=v.evaluate_fast(p,A,C,u,g)
    if abs(exact-val)>1e-6:raise AssertionError('Delta score drift')
    return board[::2].copy(),board[1::2].copy(),exact,valid,accepted,polish,warmup_accepted,ck


def make_seed(b0,s0,mode):
    """Preserve F4 letters where possible; repair symbols into valid blocks."""
    b=b0.copy();s=s0.copy()
    # Ensure two two-key symbol blocks for the grid condition. Only right-hand
    # consonants can be displaced; the five left-hand vowels remain untouched.
    reserved=(23,24,35,36) if mode==3 else ()
    for k in reserved:
        if b[k]>=0 and v.ISLOWER[b[k]]:
            available=[j for j in v.MUTABLE if j>=13 and j not in reserved and b[j]>=0 and not v.ISLOWER[b[j]]]
            if not available:raise ValueError('No space for bracket blocks')
            j=min(available,key=lambda q:float(v.HD[q]))
            b[k],b[j]=b[j],b[k];s[k],s[j]=s[j],s[k]
    board=np.full(96,-1,np.int32)
    for i in range(10):board[2*i]=DIGITS[i]
    for k in range(48):
        if b[k]>=0 and v.ISLOWER[b[k]]:board[2*k]=b[k];board[2*k+1]=s[k]
    symbolkeys=[int(k) for k in v.MUTABLE if board[2*k]<0]
    gi,gl,gp,gn=structure(mode)
    if mode==3:
        for group,k in [(0,23),(1,35)]:
            for ch,slot in zip(gi[group], [2*k,2*(k+1),2*k+1,2*(k+1)+1]):board[slot]=ch
        symbolkeys=[k for k in symbolkeys if k not in reserved]
        start=2
    else:start=0
    # Near-home keys first for high-frequency semantic groups; annealing may
    # change both position and mode later. No held-out text is consulted.
    symbolkeys.sort(key=lambda k:(v.HD[k],k))
    for idx in range(start,len(gi)):
        k=symbolkeys.pop(0)
        board[2*k]=gi[idx,0];board[2*k+1]=gi[idx,1]
    used=set(board[board>=0]);singles=[v.CI[c] for c in sorted(v.PUNCT) if v.CI[c] not in used]
    free=[k for k in range(96) if board[k]<0 and k!=24]
    old=v.mapped(b0,s0)
    for ch in singles[:]:
        k=int(old[ch])
        if k in free:board[k]=ch;free.remove(k);singles.remove(ch)
    for ch,k in zip(singles,free):board[k]=ch
    out=(board[::2].copy(),board[1::2].copy())
    p=v.validate(*out,True)
    if not valid_mapping(p,mode):raise AssertionError('Seed repair failed')
    return out


def pair_details(b,s):
    p=v.mapped(b,s);rows=[]
    for text,chars in zip(PAIR_STRINGS,PAIRS):
        a,bp=map(int,p[chars]);k,l=a//2,bp//2
        same=(a%2==0 and bp==a+1)
        horiz=(a%2==bp%2 and l==k+1 and v.ROW[k]==v.ROW[l])
        rows.append(dict(pair=text,first_key=v.KEY[k],second_key=v.KEY[l],
                         first_layer='shift' if a%2 else 'base',
                         second_layer='shift' if bp%2 else 'base',
                         relation='same-key' if same else 'adjacent' if horiz else 'separated',
                         constraint_pass=bool(same or horiz)))
    return rows


def search(rounds=64,iterations=100000,only=None):
    bundle=v.read_data();f4=json.loads((ROOT/'data/v4/candidates.json').read_text())['winners']
    (OUT/'search').mkdir(parents=True,exist_ok=True)
    for jobidx,(profile,method) in enumerate(JOBS):
        label=f'{profile}_{method}'
        if only and label not in only.split(','):continue
        mode=MODES[method];A,C,u,g=v.objective_arrays(bundle,profile)
        original=f4[{'JP':'F4-JP-free','Balance':'F4-Balance-left','Code':'F4-Code-free'}[profile]]
        b0=np.array(original['base'],np.int32);s0=np.array(original['shift'],np.int32)
        b0,s0=make_seed(b0,s0,mode);gi,gl,gp,gn=structure(mode)
        records=[];best=(float('inf'),None,None)
        for run in range(rounds):
            seed=20261101+jobidx*1000003+run*1543
            t=time.perf_counter()
            b,s,obj,nvalid,naccept,npolish,nwarm,ck=search_one(b0,s0,A,C,u,g,seed,iterations,mode,gi,gl,gp,gn,run>0)
            p=v.validate(b,s,True);assert valid_mapping(p,mode)
            records.append(dict(job=label,restart=run,seed=seed,objective_ms=float(obj),proposals=iterations,
                valid_evaluations=int(nvalid),accepted=int(naccept),polish_evaluations=int(npolish),
                warmup_accepted=int(nwarm),elapsed_seconds=time.perf_counter()-t,
                hyphen_key=v.KEY[p[v.CI_MINUS]//2],**{f'best_{i*10}pct':float(x) for i,x in enumerate(ck)}))
            if obj<best[0]:best=(float(obj),b.copy(),s.copy())
            print(label,run,'best',round(best[0],6),'valid',nvalid,flush=True)
        winner=dict(profile=profile,mode=method,objective_ms=best[0],base=best[1].tolist(),shift=best[2].tolist(),
                    rows=v.serialize(best[1],best[2]),pairs=pair_details(best[1],best[2]),restarts=rounds,
                    iterations=iterations,selected_by='minimum training objective only',digits_fixed=True,
                    vowels_left=True,hyphen_unshifted=True)
        (OUT/'search'/f'{label}_winner.json').write_text(json.dumps(winner,ensure_ascii=False,indent=2)+'\n')
        v.csv_write(OUT/'search'/f'{label}_runs.csv',records)


def evaluate():
    bundle=v.read_data();allmaps=v.references()
    f4=json.loads((ROOT/'data/v4/candidates.json').read_text())['winners']
    for n in ['F4-JP-free','F4-Balance-left','F4-Code-free','F4-Balance-right']:
        d=f4[n];allmaps[n]=(np.array(d['base'],np.int32),np.array(d['shift'],np.int32))
    winners={}
    for path in sorted((OUT/'search').glob('*_winner.json')):
        d=json.loads(path.read_text());n='F5-'+path.stem.removesuffix('_winner').replace('_','-')
        b=np.array(d['base'],np.int32);s=np.array(d['shift'],np.int32)
        assert valid_mapping(v.validate(b,s,True),MODES[d['mode']])
        allmaps[n]=(b,s);winners[n]=d
    if not winners:raise ValueError('Run the search first or restore frozen winners.')
    rows=[]
    for name,(b,s) in allmaps.items():
        for group,c in bundle['groups'].items():
            r=v.metrics(b,s,c);q=v.metrics(*allmaps['QWERTY'],c)
            r.update(layout=name,group=group,gain_vs_qwerty_pct=100*(q['seconds']/r['seconds']-1))
            rows.append(r)
    v.csv_write(OUT/'scores.csv',rows)
    pr=[]
    for name,(b,s) in allmaps.items():
        for d in pair_details(b,s):pr.append(dict(layout=name,**d))
    v.csv_write(OUT/'pair_relations.csv',pr)
    (ROOT/'data/v5').mkdir(parents=True,exist_ok=True)
    (ROOT/'data/v5/candidates.json').write_text(json.dumps(dict(version=5,pairs=PAIR_STRINGS,winners=winners),ensure_ascii=False,indent=2)+'\n')
    return allmaps,winners


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--search',action='store_true');ap.add_argument('--evaluate',action='store_true')
    ap.add_argument('--rounds',type=int,default=64);ap.add_argument('--iterations',type=int,default=100000)
    ap.add_argument('--only',help='Comma-separated jobs such as Balance_mixed,Code_grid')
    args=ap.parse_args()
    if args.rounds<1 or args.iterations<10:ap.error('rounds >= 1 and iterations >= 10 are required')
    if args.search:search(args.rounds,args.iterations,args.only)
    if args.evaluate:evaluate()
    if not (args.search or args.evaluate):ap.print_help()

if __name__=='__main__':main()
