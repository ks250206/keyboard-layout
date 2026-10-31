#!/usr/bin/env python3
"""Deterministic lossless SVG keyboard diagrams for NOVA F3 proposals."""
from pathlib import Path
from html import escape
import json, math, sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import benchmark_finger_rows as v2
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'diagrams';OUT.mkdir(parents=True,exist_ok=True)
PITCH=86;W=77;H=72
BG='#0B1726';KEY='#263C50';KEY_HOME='#334D62';KEY_VOWEL='#217F96';KEY_PUNCT='#8E673A';TEXT='#E8F3FF';MUTED='#94ABBF';ACCENT='#72E8DA'
FINGER_SHORT=['L5','L4','L3','L2','R2','R3','R4','R5']
NAMES={'Nova-F3-JP':'NOVA F3-JP','Nova-F3-Balance':'NOVA F3-Balance','Nova-F3-Code':'NOVA F3-Code','Nova-F3-Ctrl':'NOVA F3-Ctrl'}
SUBTITLE={
 'Nova-F3-JP':'ROMAJI FIRST  ·  INWARD STRETCH / FINGER-ROW OPTIMIZED',
 'Nova-F3-Balance':'JAPANESE + ENGLISH + CODE  ·  BALANCED OBJECTIVE',
 'Nova-F3-Code':'OSS CODE + ENGLISH  ·  DEVELOPMENT WEIGHTED',
 'Nova-F3-Ctrl':'SHORTCUT FRIENDLY  ·  Z / X / C / V PHYSICAL POSITIONS PRESERVED',
}

def keyboard(rows, xoff=32,yoff=110,scale=1):
    parts=[]
    parts.append('<g font-family="DejaVu Sans, Arial, sans-serif">')
    for r,row in enumerate(rows):
        label=['UPPER','HOME','LOWER'][r]
        parts.append(f'<text x="{xoff-15}" y="{yoff+r*83+40}" font-size="11" text-anchor="end" fill="{MUTED}">{label}</text>')
        for c,ch in enumerate(row):
            x=xoff+c*PITCH+[0,18,36][r];y=yoff+r*83
            penalty=v2.key_penalty(r*10+c)
            is_home=r==1
            is_vowel=ch in 'aeiou'
            fill=KEY_VOWEL if is_vowel else KEY_PUNCT if ch in '-.,;' else KEY_HOME if is_home else KEY
            border=('#EFA969' if penalty>=12 else '#B3DEB4' if penalty>=7 else '#7491A3')
            parts.append(f'<rect x="{x}" y="{y}" rx="9" width="{W}" height="{H}" fill="{fill}" stroke="{border}" stroke-width="{2.5 if penalty>=12 else 1.3}"/>')
            parts.append(f'<text x="{x+W/2}" y="{y+37}" text-anchor="middle" font-family="DejaVu Sans Mono, monospace" fill="{TEXT}" font-size="25" font-weight="700">{escape(ch.upper())}</text>')
            f=v2.FINGERS[r*10+c]
            parts.append(f'<text x="{x+10}" y="{y+62}" text-anchor="start" fill="#BAD1E1" font-size="10">{FINGER_SHORT[f]}</text>')
            if penalty>0:
                parts.append(f'<text x="{x+W-6}" y="{y+62}" text-anchor="end" fill="#FFE1A1" font-size="10">+{penalty:g}</text>')
    parts.append('</g>')
    return ''.join(parts)


def svg_single(name,rows):
    title=NAMES[name]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="488" viewBox="0 0 1100 488" role="img" aria-label="{title} 30-key layout">
<rect width="1100" height="488" fill="{BG}"/>
<text x="38" y="57" font-family="DejaVu Sans, Arial, sans-serif" font-size="32" font-weight="700" fill="{TEXT}">{title}</text>
<text x="39" y="85" font-family="DejaVu Sans, Arial, sans-serif" font-size="12" letter-spacing="1.4" fill="{MUTED}">{SUBTITLE[name]}</text>
{keyboard(rows,xoff=125,yoff=118)}
<g font-family="DejaVu Sans, Arial, sans-serif" font-size="13" fill="{MUTED}">
<rect x="40" y="412" width="17" height="17" rx="4" fill="{KEY_VOWEL}"/><text x="66" y="425">vowels</text>
<rect x="210" y="412" width="17" height="17" rx="4" fill="{KEY_PUNCT}"/><text x="236" y="425">punctuation</text>
<rect x="405" y="412" width="17" height="17" rx="4" fill="{KEY_HOME}"/><text x="431" y="425">home row</text>
<rect x="570" y="412" width="17" height="17" rx="4" fill="{KEY}" stroke="#EFA969" stroke-width="2.5"/><text x="596" y="425">high posture surcharge</text>
<text x="40" y="458">+ms labels represent uncalibrated key posture penalties (not total typing time). 3×10 US-like staggered core only.</text>
</g></svg>'''


def overview(groups):
    height=1515
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1150" height="{height}" viewBox="0 0 1150 {height}" role="img" aria-label="NOVA F3 four layouts side by side">',f'<rect width="1150" height="{height}" fill="{BG}"/>',f'<text x="39" y="58" font-family="DejaVu Sans, Arial, sans-serif" font-weight="700" font-size="32" fill="{TEXT}">NOVA F3  ·  FOUR OPTIMIZED LAYOUTS</text>',f'<text x="40" y="85" font-family="DejaVu Sans, Arial, sans-serif" font-size="14" fill="{MUTED}">Finger × row × lateral splay · seed 20261031 · 30 core keys</text>']
    for index,(name,rows) in enumerate(groups.items()):
        y=109+index*345
        out.append(f'<rect x="25" y="{y}" width="1095" height="329" rx="17" fill="#122539" stroke="#29455D" stroke-width="1.2"/>')
        out.append(f'<text x="57" y="{y+39}" font-family="DejaVu Sans, Arial, sans-serif" font-weight="700" font-size="23" fill="{TEXT}">{NAMES[name]}</text>')
        out.append(f'<text x="57" y="{y+60}" font-family="DejaVu Sans, Arial, sans-serif" font-size="12" fill="{MUTED}">{SUBTITLE[name]}</text>')
        out.append(keyboard(rows,xoff=155,yoff=y+70))
    out.append('</svg>')
    return ''.join(out)


def main():
    content=json.loads((ROOT/'data/v3_candidates.json').read_text())
    l={name:item['rows'] for name,item in content['optimized'].items()}
    for name,rows in l.items():
        p=OUT/(name.lower()+'.svg');p.write_text(svg_single(name,rows),encoding='utf-8');print('Wrote',p,p.stat().st_size)
    o=OUT/'nova-f3-overview.svg';o.write_text(overview(l),encoding='utf-8');print('Wrote',o,o.stat().st_size)
if __name__=='__main__':main()
