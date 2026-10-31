#!/usr/bin/env python3
"""SVG visualisation of physical key-specific posture surcharges (editable vector)."""
from __future__ import annotations
from pathlib import Path
from xml.sax.saxutils import escape
import benchmark_finger_rows as v
ROOT=Path(__file__).resolve().parents[1]

def render():
    w,h=1130,480
    chunks=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
    '<rect width="100%" height="100%" fill="#101827"/>',
    '<text x="42" y="43" font-family="sans-serif" font-size="25" fill="#eff6ff" font-weight="700">Finger × row × lateral position: uncalibrated added milliseconds</text>',
    '<text x="42" y="69" font-family="sans-serif" font-size="14" fill="#9caac2">Physical QWERTY key positions · same motor-time baseline retained · colored keys have an additional surcharge</text>']
    names={'L-pinky':'L5','L-ring':'L4','L-middle':'L3','L-index':'L2','R-index':'R2','R-middle':'R3','R-ring':'R4','R-pinky':'R5'}
    rows=['UPPER','HOME','LOWER']
    for row in range(3):
        y=104+row*104
        chunks.append(f'<text x="42" y="{y+38}" font-family="sans-serif" font-weight="bold" font-size="13" fill="#b6c5d8">{rows[row]}</text>')
        for col in range(10):
            idx=row*10+col
            x=122+col*96+([0,16,34][row]);f=v.FINGER_NAMES[v.FINGERS[idx]]
            cost=v.key_penalty(idx);splay=v.zone(idx);ch='qwertyuiopasdfghjkl;zxcvbnm,./'[idx]
            ratio=min(cost/20,1);bg=('#20354d' if cost==0 else f'rgb({int(47+167*ratio)},{int(82+34*(1-ratio))},{int(117-46*ratio)})')
            border='#5e9de6' if splay=='inward' else '#c1d5ed' if cost>0 else '#42627c'
            chunks.append(f'<rect x="{x}" y="{y}" width="86" height="86" rx="11" fill="{bg}" stroke="{border}" stroke-width="2"/>')
            chunks.append(f'<text x="{x+12}" y="{y+31}" font-family="monospace" font-size="22" fill="#ffffff">{escape(ch.upper())}</text>')
            chunks.append(f'<text x="{x+77}" y="{y+31}" text-anchor="end" font-family="sans-serif" font-size="12" fill="#f9e2b1">+{cost:g}ms</text>')
            chunks.append(f'<text x="{x+12}" y="{y+65}" font-family="monospace" font-size="12" fill="#d8e8ff">{names[f]}{(" ↔" if splay=="inward" else "")}</text>')
    chunks.append('<text x="42" y="447" font-family="sans-serif" font-size="15" fill="#c6d3e7">Key-specific penalties are **hypotheses**, not empirical reaction times. Keyboard pitch, JIS punctuation and IME remain simplified.</text>')
    chunks.append('</svg>')
    out=ROOT/'diagrams/finger_row_costs.svg';out.parent.mkdir(exist_ok=True)
    out.write_text('\n'.join(chunks)+'\n',encoding='utf-8');print(out)
if __name__=='__main__':render()
