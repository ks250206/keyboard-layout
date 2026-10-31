#!/usr/bin/env python3
"""Deterministic, standard-library-only keyboard layout motor-time simulation.

Usage:
  python src/benchmark.py --check
  python src/benchmark.py --category JP
  python src/benchmark.py --text "my sample text 123"

NOT a measured human speed predictor. The KLA-style score is an approximation,
not a direct result of the patorjk.com analyzer.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import string

ROOT = Path(__file__).resolve().parents[1]
PITCH_M = 0.01905
BASE = 0.118
REACH = 0.019
RETURN = 0.009
SAME_HAND = 0.008
SAME_SETUP = 0.036
SAME_LOG = 0.056
SAME_LINEAR = 0.006
REPEAT = 0.023
SHIFT_COST = 0.038
FINGER_PATTERN = (0,1,2,3,3,4,4,5,6,7)
FINGER_SCORE = (.5,1,4,2,2,4,1,.5,.5)
HOME_COORDS = ((.22,0),(1.22,0),(2.22,0),(3.22,0),(6.22,0),(7.22,0),(8.22,0),(9.22,0),(5,-2.3))

POSITIONS = []
FINGERS = []
for row in range(3):
    for col in range(10):
        POSITIONS.append((col + (0, .22, .47)[row], 1-row))
        FINGERS.append(FINGER_PATTERN[col])
PERIPHERAL = [
    ('-',10,2,7), ('=',11,2,7), ('`',-1,2,0), ('[',10,1,7), (']',11,1,7),
    ('\\',12,1,7), ("'",10,0,7), ('/',10,-1,7), (' ',5,-2.3,8),
    ('\n',11,0,7), ('\t',-1,1,0),
]
for char in '1234567890':
    j = (int(char)-1)%10
    finger = 0 if j==0 else 1 if j==1 else 2 if j==2 else 3 if j in (3,4) else 4 if j in (5,6) else 5 if j==7 else 6 if j==8 else 7
    PERIPHERAL.append((char,j,2,finger))
EXTRA = {}
for char,x,y,finger in PERIPHERAL:
    EXTRA[char] = len(POSITIONS)
    POSITIONS.append((x,y));FINGERS.append(finger)
HD = [math.hypot(p[0]-HOME_COORDS[FINGERS[i]][0], p[1]-HOME_COORDS[FINGERS[i]][1]) for i,p in enumerate(POSITIONS)]
HAND = [2 if i==8 else 0 if i<=3 else 1 for i in FINGERS]
SHIFT = dict(zip('!@#$%^&*()','1234567890'))
SHIFT.update({'_':'-', '+':'=', '~':'`', '{':'[', '}':']', '|':'\\', ':':';', '"':"'", '<':',', '>':'.', '?':'/'})


def read_layouts():
    return json.loads((ROOT/'layouts/layouts.json').read_text(encoding='utf-8'))


def make_map(name, layouts):
    rows = layouts[name]
    assert len(rows)==3 and all(len(row)==10 for row in rows), name
    mapping = {c:i for i,c in enumerate(''.join(rows))}
    assert len(mapping)==30 and set(string.ascii_lowercase) <= set(mapping), name
    for char,i in EXTRA.items():
        mapping.setdefault(char,i)
    # Physical key mapping for standard US Dvorak punctuation around the 30-key core.
    if name == 'Dvorak':
        mapping.update({'[':EXTRA['-'],']':EXTRA['='],'-':EXTRA["'"], '/':EXTRA['['],'=':EXTRA[']']})
    return mapping


def chars_map(name, layouts, alphabet):
    mapping = make_map(name,layouts)
    positions=[];shifted=[]
    for char in alphabet:
        if char in string.ascii_uppercase:
            key = char.lower(); need_shift = True
        elif char in SHIFT:
            key = SHIFT[char];need_shift=True
        else:
            key=char;need_shift=False
        positions.append(mapping[key]);shifted.append(int(need_shift))
    return positions,shifted


def document_counts(text: str, alphabet: str):
    char_idx = {c:i for i,c in enumerate(alphabet)}
    filtered=[char_idx[c] for c in text.replace('\r\n','\n') if c in char_idx]
    u={};g={};first={};last={}
    for i in filtered:u[i]=u.get(i,0)+1
    for i,j in zip(filtered,filtered[1:]):g[(i,j)]=g.get((i,j),0)+1
    if filtered:
        first[filtered[0]]=1;last[filtered[-1]]=1
    return {'n':len(filtered), 'unigrams':[[k,v] for k,v in u.items()],
            'bigrams':[[i,j,n] for (i,j),n in g.items()],
            'first':[[k,v] for k,v in first.items()], 'last':[[k,v] for k,v in last.items()]}


def metrics(name, layouts, counts, alphabet, same_finger_scale=1.):
    pos,shifted=chars_map(name,layouts,alphabet)
    n=counts['n']
    if not n:raise ValueError('No supported keystrokes')
    unigrams=counts['unigrams'];bigrams=counts['bigrams']
    first=counts['first'];last=counts['last']
    type_time=BASE*n
    shifted_n=sum(c*shifted[i] for i,c in unigrams)
    type_time+=SHIFT_COST*shifted_n
    type_time+=REACH*sum(c*HD[pos[i]] for i,c in first)
    type_time+=RETURN*sum(c*HD[pos[i]] for i,c in last)
    travel=sum(c*HD[pos[i]] for pairs in (first,last) for i,c in pairs)
    same_finger_different = 0
    same_hand_different = 0
    alternate = 0
    for ai,bi,count in bigrams:
        a=pos[ai];b=pos[bi]
        distance=math.hypot(POSITIONS[a][0]-POSITIONS[b][0],POSITIONS[a][1]-POSITIONS[b][1])
        if FINGERS[a] == FINGERS[b]:
            if a==b:
                time=REPEAT
            else:
                time=(SAME_SETUP+SAME_LOG*math.log2(1+distance)+SAME_LINEAR*distance)*same_finger_scale
                same_finger_different+=count
            travel+=distance*count
        else:
            same_hand=HAND[a]==HAND[b] and HAND[a]!=2
            time=REACH*HD[b]+RETURN*HD[a]+(SAME_HAND if same_hand else 0)
            travel+=(HD[a]+HD[b])*count
        type_time+=time*count
        if a!=b and HAND[a]==HAND[b] and HAND[a]!=2: same_hand_different+=count
        if HAND[a]!=HAND[b] and HAND[a]!=2 and HAND[b]!=2: alternate+=count
    finger_counts=[0]*9
    home_count=0
    for idx,count in unigrams:
        finger_counts[FINGERS[pos[idx]]]+=count
        if 10<=pos[idx]<20:home_count+=count
    cm=travel*PITCH_M*100/n
    finger_score=sum(min(f*100/n,20)*w for f,w in zip(finger_counts,FINGER_SCORE))/260
    kla=33*max(0,(4-cm)/4)+33*finger_score+17*max(0,(10-100*same_finger_different/n)/10)+17*max(0,(50-100*same_hand_different/n)/50)
    npairs=sum(count for _,_,count in bigrams)
    return {
        'layout':name,'keystrokes':n, 'estimated_seconds':type_time,
        'home_pct':100*home_count/n, 'distance_m':travel*PITCH_M,
        'same_finger_pct':100*same_finger_different/npairs if npairs else 0.,
        'same_hand_pct':100*same_hand_different/npairs if npairs else 0.,
        'alternating_pct':100*alternate/npairs if npairs else 0.,
        'shift_pct':100*shifted_n/n, 'KLA_approx':kla,
        'ideal_home_seconds':BASE*n+SHIFT_COST*shifted_n,
    }


def summary_rows(counts,layout_names=None):
    layouts=read_layouts()
    names=layout_names or list(layouts)
    alphabet=counts['alphabet']
    for cat,docs in counts['categories'].items():
        aggregate=docs['aggregate']
        baseline=metrics('QWERTY',layouts,aggregate,alphabet)['estimated_seconds']
        for name in names:
            row=metrics(name,layouts,aggregate,alphabet)
            row['category']=cat
            row['gain_vs_qwerty_pct']=100*(baseline/row['estimated_seconds']-1)
            yield row


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--category', choices=['JP','EN','CODE'], help='Only this category')
    ap.add_argument('--text',help='Simulate a literal ASCII/romanized Japanese string')
    ap.add_argument('--check',action='store_true',help='Check recomputed results against published CSV')
    args=ap.parse_args()
    archive=json.loads((ROOT/'data/aggregates.json').read_text(encoding='utf-8'))
    if args.text is not None:
        cs=document_counts(args.text,archive['alphabet']); layouts=read_layouts();q=metrics('QWERTY',layouts,cs,archive['alphabet'])
        for name in layouts:
            r=metrics(name,layouts,cs,archive['alphabet'])
            print(f'{name:14} {r["estimated_seconds"]:.4f}s  {(q["estimated_seconds"]/r["estimated_seconds"]-1)*100:+6.2f}%')
        return
    rows=list(summary_rows(archive))
    if args.check:
        with (ROOT/'data/local_summary.csv').open(encoding='utf-8-sig',newline='') as f:published={(r['task'],r['layout']):r for r in csv.DictReader(f)}
        for row in rows:
            pub=published[(row['category'],row['layout'])]
            for computed,csvkey in [('estimated_seconds','estimated_seconds'),('home_pct','home_pct'),('distance_m','distance_m'),('same_finger_pct','same_finger_pct'),('KLA_approx','KLA_approx'),('gain_vs_qwerty_pct','gain_vs_qwerty_pct')]:
                err=abs(row[computed]-float(pub[csvkey]))
                if err>0.015:raise AssertionError(f'{row["category"]} {row["layout"]} {csvkey} {row[computed]} vs {pub[csvkey]}')
        print(f'PASS: {len(rows)} layout/category predictions match data/local_summary.csv')
    else:
        for r in rows:
            if args.category and r['category']!=args.category:continue
            print(f'{r["category"]:4} {r["layout"]:14} gain={r["gain_vs_qwerty_pct"]:+6.2f}%  KLA={r["KLA_approx"]:6.2f}  travel={r["distance_m"]:.2f}m')

if __name__=='__main__':main()
