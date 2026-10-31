#!/usr/bin/env python3
"""Regenerate portable vector keyboard diagrams with exact key labels."""
from __future__ import annotations
import html,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'diagrams'
OUT.mkdir(exist_ok=True)
PALETTES={
 'Nova-JP':('JP-FIRST / ROMAJI','#3ee0be'),
 'Nova-Hybrid':('JP + EN + CODE','#b2a3ff'),
 'Nova-Dev':('PROGRAMMING','#f2bd70'),
 'Nova-Ctrl':('SHORTCUT-AWARE','#ff93ad'),
 'QWERTY':('BASELINE','#8ca6ce'),
 'Dvorak':('BASELINE','#8ca6ce'),
 'Colemak':('BASELINE','#8ca6ce'),
 'Workman':('BASELINE','#8ca6ce'),
 '大西':('JAPANESE ROMAJI','#8ca6ce'),
}
SLUGS={'大西':'onishi'}

def slug(name):return SLUGS.get(name,name.lower())

def text(x,y,s,size,color,weight=500,anchor='start'):
 return f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" text-anchor="{anchor}" font-family="Inter,Arial,Noto Sans,sans-serif" font-size="{size}" font-weight="{weight}">{html.escape(s)}</text>'

def rect(x,y,w,h,r,fill,stroke='none',sw=1):
 return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" />'

def keys_markup(rows,x,y,kw,kh,gap,accent,labels=True,mini=False):
 out=[]
 for ridx,line in enumerate(rows):
  for col,char in enumerate(line):
   # two banks separated by slight mid-gap; physical rows staggered
   xx=x+(ridx*kw*.2)+col*(kw+gap)+(gap*1.25 if col>=5 else 0)
   yy=y+ridx*(kh+gap)
   vowel=char in 'aiueo'; sym=char in ',./;\'-=';
   fill= '#154c4a' if vowel else '#2c334b' if sym else '#1a2946'
   stroke=accent if ridx==1 else ('#49616f' if vowel else '#33465e')
   out.append(rect(xx,yy,kw,kh,max(7,kw*.11),fill,stroke,2.0 if ridx==1 else 1.0))
   if ridx==1:
    out.append(rect(xx+kw*.25,yy+kh-8,kw*.5,2.3,1,accent))
   out.append(text(xx+kw/2,yy+kh*.58,char.upper(),int(kh*.39), '#c9fff0' if vowel else '#f1f4fb',750,'middle'))
   if labels and not mini and ridx==1:
    out.append(text(xx+kw/2,yy+kh*.83,'HOME',9,'#a8bfd3',600,'middle'))
 return '\n'.join(out)

def diagram(name,rows):
 accent=PALETTES[name][1]
 w,h=1320,560
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Keyboard layout {html.escape(name)}">',
 '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#091421"/><stop offset="1" stop-color="#182033"/></linearGradient></defs>',rect(0,0,w,h,28,'url(#bg)'),rect(28,28,1264,500,22,'#111c2e','#314158',1),
 text(65,81,name,42,'#f0f5fe',760),text(65,115,PALETTES[name][0],16,accent,700),
 text(1245,85,'30-KEY CORE / STAGGERED',14,'#98aec9',600,'end'),
 keys_markup(rows,85,152,92,82,16,accent),
 rect(85,491,12,12,5,'#154c4a','#49616f'),text(106,502,'VOWELS / 母音',13,'#c0cedd'),
 rect(325,491,12,12,4,'#1a2946','#33465e'),text(345,502,'CONSONANTS / 子音',13,'#c0cedd'),
 rect(595,491,12,12,4,'#2c334b','#33465e'),text(615,502,'PUNCTUATION',13,'#c0cedd'),
 text(1232,502,'HOME ROW OUTLINED',13,'#c0cedd',600,'end'),
 '</svg>']
 return '\n'.join(svg)

def overview(layouts):
 names=['Nova-JP','Nova-Hybrid','Nova-Dev','Nova-Ctrl']; w,h=1450,880
 s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Four proposed NOVA keyboard layouts">',
 '<defs><linearGradient id="back" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#081521"/><stop offset="1" stop-color="#1a263a"/></linearGradient></defs>',rect(0,0,w,h,28,'url(#back)'),
 text(45,70,'NOVA / FOUR EXPERIMENTAL KEYBOARD LAYOUTS',32,'#f2f6fc',750),text(45,104,'Japanese romaji / English / open-source code    ·    30-key remaps',17,'#adc0d7')]
 for idx,name in enumerate(names):
  cx=45+(idx%2)*695;cy=135+(idx//2)*360;accent=PALETTES[name][1]
  s.extend([rect(cx,cy,661,333,22,'#101d30','#2b4058',1.4),text(cx+24,cy+44,name,29,'#f4f8fc',760),text(cx+620,cy+43,PALETTES[name][0],11,accent,700,'end')])
  s.append(keys_markup(layouts[name],cx+28,cy+79,50,58,7,accent,labels=False,mini=True))
  s.append(text(cx+28,cy+315,'Teal: vowels  /  outlined: home row',13,'#a2b7d0'))
 s.extend([text(50,859,'Conceptual keycaps: surrounding punctuation / modifiers are not finalized',13,'#9eb2c9'),'</svg>'])
 return '\n'.join(s)

def main():
 layouts=json.loads((ROOT/'layouts/layouts.json').read_text(encoding='utf-8'))
 for name,rows in layouts.items():
  path=OUT/f'{slug(name)}.svg';path.write_text(diagram(name,rows),encoding='utf-8')
 (OUT/'overview.svg').write_text(overview(layouts),encoding='utf-8')
 print('SVG diagrams:',len(list(OUT.glob('*.svg'))))
if __name__=='__main__':main()
