#!/usr/bin/env python3
"""Build the bilingual NOVA F5-Pair manuscript from frozen research artifacts.

Run from repository root: python papers/nova_f5_pair/build.py --pdf
No optimization is performed. Input hashes are checked before publication.
Requires python-docx, cairosvg, matplotlib; PDF export requires LibreOffice.
"""
from __future__ import annotations
import argparse, csv, gzip, hashlib, json, os, re, shutil, subprocess, tempfile
from pathlib import Path
from collections import Counter
from docx import Document
from docx.shared import Mm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
import cairosvg
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SNAPSHOT = 'ec596b262328ce66629c4f56874dffb364395e7d'
DATE = '2026-10-31'
AUTHOR = 'ks250206'
F5 = 'F5-Balance-mixed'
GROUPS = ['JP/test','JP/loanword','EN/test','CODE/test']
ALIASES = {'F4-Balance-left':'F4-Balance','F4-Balance-right':'F4-Balance-R','F4-Code-free':'F4-Code','F4-JP-free':'F4-JP', 'F5-Balance-mixed':'F5-Pair','F5-Code-mixed':'F5-Code','F5-Balance-shift':'F5-Shift','F5-Balance-grid':'F5-Grid','F5-Code-grid':'F5-Grid-Code','F5-JP-mixed':'F5-JP'}
SELECTION = ['QWERTY','Dvorak','Colemak','Workman','大西','Nova-F3-Balance','F4-Balance-left','F4-Code-free','F5-Balance-mixed','F5-Code-mixed','F5-Balance-shift','F5-Balance-grid','F5-JP-mixed']
REFERENCES = [
 '[1] ks250206. NOVA keyboard-layout research repository. Snapshot ec596b262328ce66629c4f56874dffb364395e7d (31 October 2026). https://github.com/ks250206/keyboard-layout/tree/ec596b262328ce66629c4f56874dffb364395e7d',
 '[2] Patorjk. Keyboard Layout Analyzer; analyzer.js, scoreLayouts implementation. https://patorjk.com/keyboard-layout-analyzer/ ; https://github.com/patorjk/keyboard-layout-analyzer/blob/master/js/analyzer.js (accessed 31 October 2026).',
 '[3] MacKenzie IS. Motor behaviour models for human-computer interaction. In: Carroll JM, editor. HCI Models, Theories, and Frameworks: Toward a Multidisciplinary Science. Morgan Kaufmann; 2003. pp. 27–54. https://www.yorku.ca/mack/mackenzie_chapter.html',
 '[4] Onishi T. ローマ字入力に最適なキー配列を考える（比較編） [Comparing keyboard layouts for Japanese romanized input]. 11 November 2022. https://note.com/illlilllililill/n/nc099239c5565 ; official layout: https://o24.works/layout/ (accessed 31 October 2026).',
 '[5] Coleman S. Colemak: Design. https://colemak.com/Design (accessed 31 October 2026).',
 '[6] Bucao OJ. The Workman Keyboard Layout Philosophy. 6 September 2010. https://workmanlayout.org/ (accessed 31 October 2026).',
 '[7] Zhai S, Hunter M, Smith BA. Performance optimization of virtual keyboards. Human–Computer Interaction. 2002;17(2–3):229–269. doi:10.1080/07370024.2002.9667315.',
 '[8] Kirkpatrick S, Gelatt CD Jr, Vecchi MP. Optimization by simulated annealing. Science. 1983;220(4598):671–680. doi:10.1126/science.220.4598.671.',
 '[9] QMK contributors. Japanese keycode definitions, quantum/keymap_extras/keymap_japanese.h. https://github.com/qmk/qmk_firmware/blob/master/quantum/keymap_extras/keymap_japanese.h (accessed 31 October 2026).',
]

def csv_rows(rel):
    with (ROOT/rel).open(encoding='utf-8-sig', newline='') as f:return list(csv.DictReader(f))

def checked_inputs():
    manifest=json.loads((HERE/'source/input_manifest.json').read_text(encoding='utf-8'))
    for rel, expected in manifest['sha256'].items():
        actual=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
        if actual != expected:raise ValueError(f'Frozen source mismatch: {rel}: {actual} != {expected}')
    bundle=json.loads(gzip.decompress((ROOT/'data/v4/raw_ngrams.json.gz').read_bytes()))
    counts={}
    for split in ('train','valid','test'):
        counts[split]=sum(sum(v for c,v in bundle['groups'][d+'/'+split]['first']) for d in ('生活文','業務文','技術文'))
    assert counts == {'train':94,'valid':24,'test':24},counts
    assert sum(counts.values())==142
    lookup={}
    for rel in ('results/v4/scores.csv','results/v5/scores.csv'):
        for row in csv_rows(rel):
            key=(row['layout'],row['group'])
            if key in lookup:
                for field in ('KLA_main_approx','seconds','gain_vs_qwerty_pct'):
                    assert abs(float(row[field])-float(lookup[key][field]))<1e-8,(key,field)
            lookup[key]=row
    return bundle,lookup

def display_name(name,lang):
    name=ALIASES.get(name,name)
    if name=='大西' and lang=='en':return 'Onishi'
    return name.replace('Nova-F3-','F3-')

def make_tables(lang,bundle,lookup):
    ja=lang=='ja';tables={}
    def put(key,caption,headers,rows,note='',widths=None):tables[key]={'caption':caption,'headers':headers,'rows':rows,'note':note,'widths':widths}
    put('history','表1．研究段階と追加した設計要素' if ja else 'Table 1. Development stages and their roles.',
        ['段階','内容','解釈上の注意'] if ja else ['Stage','Design change','Interpretation'],
        ([['初期NOVA','自作日本語6課題、英語・コード比較','小規模入力、距離中心'],['現代文診断','長音符の多い自作6課題','代表標本ではない'],['指×段／F3','左右の指、段、内外側コスト','主観に基づく未校正係数'],['F4','数字固定、通常／Shift面、長音符左右','記号自由配置と切り分け'],['F5','9記号ペアを位置関係で制約','学習時間の効果は未測定'],['本報告','F5-Pairを採用、入力件数を監査','配置と既存の数値は変更しない']] if ja else
         [['Initial NOVA','Six authored Japanese tasks; bilingual/code tests','Small inputs; distance-oriented'],['Modern diagnostics','Six loanword-rich Japanese tasks','Not a representative population sample'],['Finger–row / F3','Side-specific row and lateral costs','Uncalibrated subjective priors'],['F4','Fixed digits, base/Shift symbols, hyphen-side tests','Free symbols and ablations'],['F5','Hard constraints on nine symbol pairs','Learning benefit not measured'],['This report','Select F5-Pair; audit corpus counts','No candidate or score modification']]),widths=[25,70,71])
    cor=[]
    labels={'生活文':('生活文','Everyday JP'),'業務文':('業務文','Business JP'),'技術文':('技術文','Technical JP')}
    for d in labels:
        vals=[]
        for sp in ('train','valid','test'):
            g=bundle['groups'][d+'/'+sp];n=sum(v for c,v in g['first']);vals.append(f"{n} / {g['n']:,}")
        cor.append([labels[d][0 if ja else 1]]+vals)
    cor += [(['日本語計','94 / 5,104','24 / 1,331','24 / 1,301'] if ja else ['Japanese total','94 / 5,104','24 / 1,331','24 / 1,301']),(['英語','4 / 2,412','—','2 / 1,208'] if ja else ['English','4 / 2,412','—','2 / 1,208']),(['コード7言語','7 / 80,357','—','7 / 76,876'] if ja else ['Code, 7 languages','7 / 80,357','—','7 / 76,876']),(['長音符診断','—','—','6 / 2,733'] if ja else ['Loanword diagnostic','—','—','6 / 2,733'])]
    put('corpus','表2．凍結統計に含まれる実使用文書数と入力文字数' if ja else 'Table 2. Actual document counts / input-character counts in the frozen statistics.',
        ['分野','学習','検証','テスト／診断'] if ja else ['Domain','Training','Validation','Test / diagnostic'],cor,
        '日本語の単位は文、英語は文章、コードはファイル。長音符診断は既出の課題。' if ja else 'Units are sentences for synthetic Japanese, passages for English, and files for code. The loanword set is a previously inspected diagnostic.',[42,41,41,42])
    put('costs','表3．主な時間係数（すべて未校正）' if ja else 'Table 3. Principal timing parameters (all uncalibrated).',
        ['項目','値／式'] if ja else ['Term','Value / rule'],
        ([['基準入力','118 ms/文字'],['異指到達・復帰','19h_next + 9h_previous ms'],['同手・異指','さらに8 ms'],['同一キー反復','さらに23 ms'],['同指・異鍵','36 + 56 log₂(1+d) + 6d ms'],['数字段','1文字当たり12 ms'],['Shift協調／開始','8 ms/Shift文字；開始30 ms＋到達'],['小指と修飾キーの競合','該当する境界ごとに12 ms']] if ja else
         [['Base interval','118 ms per input character'],['Different-finger reach / return','19h_next + 9h_previous ms'],['Same hand, different fingers','Additional 8 ms'],['Repeated physical key','Additional 23 ms'],['Same finger, different keys','36 + 56 log₂(1+d) + 6d ms'],['Number-row action','12 ms per character'],['Shift coordination / engagement','8 ms per shifted character; 30 ms + reach per start'],['Pinky / modifier conflict','12 ms per applicable boundary condition']]),widths=[61,105])
    put('weights','表4．目的別の学習重み' if ja else 'Table 4. Training weights by optimization profile.',
        ['用途','生活文','業務文','技術文','英語','コード'] if ja else ['Profile','Everyday JP','Business JP','Technical JP','English','Code'],
        [['JP',.30,.30,.25,.08,.07],['Balance',.18,.18,.19,.23,.22],['Code',.11,.11,.13,.20,.45]],widths=[30,27,27,28,27,27])
    pairs=[x for x in csv_rows('results/v5/pair_relations.csv') if x['layout']==F5]
    assert len(pairs)==9 and all(x['constraint_pass']=='True' for x in pairs)
    def where(k,layer):
        row,col=k.split('_'); names={'number':('数字','Number'),'upper':('上段','Upper'),'home':('中段','Home'),'lower':('下段','Lower')}; lay=('通常' if layer=='base' else 'Shift') if ja else ('base' if layer=='base' else 'Shift');return f"{names[row][0 if ja else 1]} {col} / {lay}"
    pair_rows=[[p['pair'],where(p['first_key'],p['first_layer']),where(p['second_key'],p['second_layer']),('隣接' if p['relation']=='adjacent' else '同一キー') if ja else p['relation']] for p in pairs]
    put('pairs','表5．F5-Pairの9組の記号関係' if ja else 'Table 5. All nine punctuation relations in F5-Pair.', ['ペア','第1記号','第2記号','関係'] if ja else ['Pair','First symbol','Second symbol','Relation'],pair_rows,
        '列番号は各物理段の左端を1とする。' if ja else 'Column numbers start at 1 on each physical row.',[19,56,56,35])
    head=['配列','日本語test','長音符診断','英語test','コードtest'] if ja else ['Layout','JP test','Loanword JP','EN test','Code test']
    speed=[];kla=[]
    for name in SELECTION:
        speed.append([display_name(name,lang)]+[f"{float(lookup[name,g]['gain_vs_qwerty_pct']):+.2f}%" for g in GROUPS])
        kla.append([display_name(name,lang)]+[f"{float(lookup[name,g]['KLA_main_approx']):.2f}" for g in GROUPS])
    put('speed','表6．最終モデルの推定速度増加率（QWERTY比）' if ja else 'Table 6. Final-model speed gain relative to QWERTY.',head,speed,
        '各列で同じ文章・モデルを適用。実測WPMではない。' if ja else 'The same input and model apply within each column. These are not measured WPM gains.',[46,30,30,30,30])
    put('kla_selected','表7．主な比較配列のKLA-main近似' if ja else 'Table 7. KLA-main approximation for principal comparisons.',head,kla,
        'Shift小指動作はKLA-mainに含めない。' if ja else 'Modifier-pinky motion is excluded from KLA-main.',[46,30,30,30,30])
    code=[]
    for lg in ['Python','JavaScript','TypeScript','Go','C','C++','Java']:
        g='CODE/'+lg+'/test';x=lookup[F5,g];code.append([lg,f"{int(x['chars']):,}",f"{float(lookup['QWERTY',g]['KLA_main_approx']):.2f}",f"{float(x['KLA_main_approx']):.2f}",f"{float(x['gain_vs_qwerty_pct']):+.2f}%"])
    put('code_languages','表8．F5-Pairの言語別コード評価' if ja else 'Table 8. Per-language code results for F5-Pair.',
        ['言語','文字数','QWERTY KLA','F5-Pair KLA','速度増加'] if ja else ['Language','Characters','QWERTY KLA','F5-Pair KLA','Speed gain'],code,widths=[35,30,34,34,33])
    allrows=csv_rows('results/kla_all.csv');assert len(allrows)==30
    for key,cols,cap,headers in [
        ('kla_all',GROUPS,'表A1．全30配列の集約KLA-main近似' if ja else 'Table A1. Aggregate KLA-main scores for all 30 layouts.',head),
        ('kla_jp_domains',['生活文/test','業務文/test','技術文/test'],'表B1．日本語3分野のKLA-main近似' if ja else 'Table B1. KLA-main scores in three Japanese domains.',['配列','生活文','業務文','技術文'] if ja else ['Layout','Everyday JP','Business JP','Technical JP']),
        ('kla_code_all',['CODE/'+lg+'/test' for lg in ['Python','JavaScript','TypeScript','Go','C','C++','Java']],'表B2．コード7言語のKLA-main近似' if ja else 'Table B2. KLA-main scores for seven code languages.',['配列','Python','JS','TS','Go','C','C++','Java'] if ja else ['Layout','Python','JS','TS','Go','C','C++','Java'])]:
        rr=[[display_name(x['layout'],lang)]+[f"{float(x[c]):.2f}" for c in cols] for x in allrows]
        widths=[54]+[(166-54)/len(cols)]*len(cols)
        put(key,cap,headers,rr,widths=widths)
    layers=json.loads((ROOT/'layouts/f5/full_layers.json').read_text())['layouts']['F5-Pair'];mp=[]
    row_names={'number':('数字段','Number'),'upper':('上段','Upper'),'home':('中段','Home'),'lower':('下段','Lower')}
    for row,labels in row_names.items():
        part=[x for x in layers if x['physical_key'].startswith(row+'_')]
        for layer in ('base','shift'):
            mp.append([labels[0 if ja else 1],('通常' if layer=='base' else 'Shift') if ja else layer,' '.join(x[layer] or '∅' for x in part)])
    put('mapping','表C1．通常面・Shift面の完全な行定義' if ja else 'Table C1. Complete row definitions for base and Shift layers.',
        ['物理段','面','左から右への出力'] if ja else ['Physical row','Layer','Outputs from left to right'],mp,'∅：出力なし。¥：固定表示、ASCII評価対象外。' if ja else '∅: no output. ¥: fixed legend outside the evaluated ASCII alphabet.',[27,20,119])
    return tables


def make_figures(out):
    out.mkdir(parents=True,exist_ok=True)
    cairosvg.svg2png(url=str(ROOT/'diagrams/f5/pair.svg'),write_to=str(out/'layout.png'),output_width=2200)
    datasets=[]
    specs=[('results/v4/search/Balance_left_runs.csv','F4-Balance'),('results/v5/search/Balance_mixed_runs.csv','F5-Pair'),('results/v5/search/Balance_shift_runs.csv','F5-Shift'),('results/v5/search/Balance_grid_runs.csv','F5-Grid')]
    for path,label in specs:
        rows=csv_rows(path);col='objective_ms';assert len(rows)==64
        datasets.append([float(r[col]) for r in rows])
    fig,ax=plt.subplots(figsize=(7.0,3.0))
    ax.boxplot(datasets,tick_labels=[s[1] for s in specs],showmeans=True,meanline=True,widths=.5)
    ax.set_ylabel('Training objective\n(ms-equivalent / character)')
    ax.set_xlabel('64 fixed-seed starts per condition')
    ax.grid(axis='y',alpha=.22);fig.tight_layout()
    fig.savefig(out/'restarts.png',dpi=220,bbox_inches='tight');plt.close(fig)
    return {'layout':out/'layout.png','restarts':out/'restarts.png'}


def rfont(run,name='Liberation Serif',size=None,bold=None):
    run.font.name=name
    if size:run.font.size=Pt(size)
    if bold is not None:run.bold=bold
    rp=run._element.get_or_add_rPr();rf=rp.rFonts
    if rf is None:rf=OxmlElement('w:rFonts');rp.insert(0,rf)
    rf.set(qn('w:ascii'),name);rf.set(qn('w:hAnsi'),name);rf.set(qn('w:eastAsia'),'Noto Serif CJK JP')
    return run


def setup(lang):
    doc=Document();sec=doc.sections[0]
    sec.page_width=Mm(210);sec.page_height=Mm(297)
    sec.top_margin=Mm(20);sec.bottom_margin=Mm(19);sec.left_margin=Mm(22);sec.right_margin=Mm(22)
    sec.header_distance=Mm(9);sec.footer_distance=Mm(9)
    for name in ['Normal','Body Text','Caption']:
        st=doc.styles[name];st.font.name='Liberation Serif';st.font.size=Pt(10.2 if lang=='en' else 10)
        st.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Noto Serif CJK JP')
        st.paragraph_format.space_after=Pt(5.3)
        st.paragraph_format.line_spacing=1.12 if lang=='en' else 1.23
    for name,size in [('Title',19),('Heading 1',13),('Heading 2',11.2),('Heading 3',10.5)]:
        st=doc.styles[name];st.font.name='Liberation Sans';st.font.size=Pt(size);st.font.bold=True
        st.font.color.rgb=RGBColor.from_string('173949')
        st.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Noto Sans CJK JP')
        st.paragraph_format.space_before=Pt(12 if name!='Title' else 0);st.paragraph_format.space_after=Pt(5)
        st.paragraph_format.keep_with_next=True
    doc.styles['Title'].paragraph_format.line_spacing=1.1
    cap=doc.styles['Caption'];cap.font.size=Pt(9);cap.paragraph_format.line_spacing=1.08
    # Widow/orphan protection and character wrapping at long URLs/hashes.
    for name in ['Normal','Body Text','Caption']:
        pp=doc.styles[name].element.get_or_add_pPr()
        for tag in ['widowControl','overflowPunct']:
            el=OxmlElement('w:'+tag);el.set(qn('w:val'),'1');pp.append(el)
    hdr=sec.header.paragraphs[0];hdr.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    rfont(hdr.add_run('NOVA F5-PAIR  |  COMPUTATIONAL DESIGN STUDY'),name='Liberation Sans',size=8)
    f=sec.footer.paragraphs[0];f.alignment=WD_ALIGN_PARAGRAPH.CENTER
    rfont(f.add_run('Research manuscript · 2026-10-31  |  '),name='Liberation Sans',size=8)
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');f._p.append(field)
    doc.core_properties.author=AUTHOR;doc.core_properties.last_modified_by=AUTHOR;doc.core_properties.subject='Reproducible keyboard layout optimization; Japanese and English manuscript'
    doc.core_properties.keywords='NOVA F5-Pair; keyboard layout; simulated annealing; synthetic corpus'
    doc.core_properties.comments='Generated from frozen research artifacts. No measured human-performance claim.'
    return doc


def paragraph(doc,text,style=None,align=None):
    p=doc.add_paragraph(style=style)
    if align is not None:p.alignment=align
    # Avoid overlong URLs/hashes extending beyond margins, while preserving text.
    rfont(p.add_run(text))
    return p


def add_table(doc,t,key,lang):
    cp=paragraph(doc,t['caption'],'Caption');cp.paragraph_format.keep_with_next=True
    table=doc.add_table(rows=1, cols=len(t['headers']));table.alignment=WD_TABLE_ALIGNMENT.CENTER;table.autofit=False
    widths=t['widths'] or [166/len(t['headers'])]*len(t['headers'])
    for c,w in zip(table.columns,widths):c.width=Mm(w)
    allrows=[t['headers']]+t['rows']
    compact=key.startswith('kla_') and key not in ('kla_selected',)
    font=8.3 if key=='kla_code_all' else 8.6 if compact else 9.2
    for i,rowdata in enumerate(allrows):
        row=table.rows[0] if i==0 else table.add_row()
        # Rows never split; header repeats across a page break.
        trpr=row._tr.get_or_add_trPr();ns=OxmlElement('w:cantSplit');trpr.append(ns)
        if i==0:
            rep=OxmlElement('w:tblHeader');trpr.append(rep)
        for j,(cell,value,w) in enumerate(zip(row.cells,rowdata,widths)):
            cell.width=Mm(w);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcpr=cell._tc.get_or_add_tcPr();m=OxmlElement('w:tcMar')
            for side,n in [('top',45 if compact else 60),('bottom',45 if compact else 60),('left',70),('right',70)]:
                e=OxmlElement('w:'+side);e.set(qn('w:w'),str(n));e.set(qn('w:type'),'dxa');m.append(e)
            tcpr.append(m)
            if i==0 or ('F5-Pair' in str(rowdata[0])):
                sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'EAF0F3' if i==0 else 'F3F6F7');tcpr.append(sh)
            p=cell.paragraphs[0];p.paragraph_format.space_after=Pt(0);p.paragraph_format.line_spacing=1.05
            if len(allrows)<20:p.paragraph_format.keep_with_next=(i<len(allrows)-1)
            p.alignment=WD_ALIGN_PARAGRAPH.LEFT if j==0 or key in ('history','costs','pairs','mapping') else WD_ALIGN_PARAGRAPH.CENTER
            rr=p.add_run(str(value));rfont(rr,'Liberation Mono' if key=='mapping' and j==2 else 'Liberation Serif',size=font,bold=(i==0 or 'F5-Pair' in str(rowdata[0])))
    borders=OxmlElement('w:tblBorders')
    for side in ['top','bottom','insideH']:
        el=OxmlElement('w:'+side);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'CCD6DC');borders.append(el)
    table._tbl.tblPr.append(borders)
    if t.get('note'):
        p=paragraph(doc,t['note'],'Caption');p.paragraph_format.space_before=Pt(3)
    doc.add_paragraph().paragraph_format.space_after=Pt(0)


def markdown_table(t):
    def esc(x):return str(x).replace('|','\\|')
    return t['caption']+'\n\n| '+' | '.join(map(esc,t['headers']))+' |\n| '+' | '.join(['---']*len(t['headers']))+' |\n'+'\n'.join('| '+' | '.join(map(esc,r))+' |' for r in t['rows'])+'\n\n'+t.get('note','')


def build(lang,bundle,lookup,figs,out):
    doc=setup(lang);ja=lang=='ja';tabs=make_tables(lang,bundle,lookup)
    src=(HERE/'source'/f'{lang}.md').read_text(encoding='utf-8')
    # Final consistent numbering after adding the parameter table.
    src=src.replace('[[PAGEBREAK]]','\n\n[[PAGEBREAK]]\n\n')
    chunks=re.split(r'\n\s*\n',src.strip());expanded=[]
    for block in chunks:
        b=block.strip()
        if not b:continue
        if b=='[[PAGEBREAK]]':doc.add_page_break();expanded.append('');continue
        if b.startswith('# '):
            p=doc.add_paragraph(b[2:],style='Title');doc.core_properties.title=b[2:];expanded.append(b);continue
        if b.startswith('## '):
            if b[3:] in ('References','参考文献'):doc.add_page_break()
            doc.add_heading(b[3:],1);expanded.append(b);continue
        if b.startswith('### '):doc.add_heading(b[4:],2);expanded.append(b);continue
        match=re.fullmatch(r'\{\{table:([^}]+)\}\}',b)
        if match:
            key=match.group(1);add_table(doc,tabs[key],key,lang);expanded.append(markdown_table(tabs[key]));continue
        match=re.fullmatch(r'\{\{figure:([^}]+)\}\}',b)
        if match:
            key=match.group(1)
            captions={'layout':('図1．採用するF5-Pairの通常面・Shift面。上の小文字列がShift、下が通常面。数字位置と英字の大小対応を保持する。図は実装定義であり、ファームウェアではない。','Figure 1. Adopted F5-Pair base and Shift layers. Upper legends show Shift; lower legends show base. Digit positions and uppercase correspondence are retained. This is a mapping specification, not firmware.'),
                      'restarts':('図2．Balance目的関数における64再始動の結果。箱は四分位範囲、中央線は中央値、破線は平均。ひげは1.5 IQR以内、外側を外れ値として示す。人間の性能の信頼区間ではない。','Figure 2. Results of 64 starts under the Balance training objective. Boxes show interquartile ranges, solid lines medians, dashed lines means, and whiskers extend to observations within 1.5 IQR; outlying starts are shown separately. These are not confidence intervals for human performance.')}
            p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.keep_with_next=True
            run=p.add_run();shape=run.add_picture(str(figs[key]),width=Mm(166))
            shape._inline.docPr.set('descr',captions[key][0 if ja else 1])
            paragraph(doc,captions[key][0 if ja else 1],'Caption')
            expanded.append(f'![{key}](assets/{key}.png)\n\n'+captions[key][0 if ja else 1]);continue
        match=re.fullmatch(r'\{\{equation:([^}]+)\}\}',b)
        if match:
            key=match.group(1);eq={'time':'T = Σᵢ uᵢ C[p(i)] + Σᵢⱼ gᵢⱼ M[p(i),p(j)] + Σᵢ fᵢ B[p(i)] + Σᵢ lᵢ E[p(i)]     (1)', 'kla':'KLA-main = 33D + 33U + 17F + 17H                                                    (2)'}[key]
            p=paragraph(doc,eq,align=WD_ALIGN_PARAGRAPH.CENTER)
            for run in p.runs:rfont(run,'DejaVu Serif',size=9)
            expanded.append(eq);continue
        if b=='{{references}}':
            for ref in REFERENCES:
                p=paragraph(doc,ref);p.paragraph_format.space_after=Pt(5);p.paragraph_format.line_spacing=1.05
                p.paragraph_format.left_indent=Mm(5);p.paragraph_format.first_line_indent=Mm(-5);p.paragraph_format.keep_together=True
                for run in p.runs:rfont(run,size=8.7)
            expanded.append('\n\n'.join(REFERENCES));continue
        if b=='{{code:reproduce}}':
            code='git checkout '+SNAPSHOT+'\npython -m pip install -r requirements-v4.txt\npython tools/check_f4.py\npython tools/check_f5.py\npython -m unittest discover -s tests -p "test_optimize_v[45].py" -v'
            p=paragraph(doc,code)
            for run in p.runs:rfont(run,'Liberation Mono',size=8.5)
            p.paragraph_format.line_spacing=1.1
            expanded.append('```bash\n'+code+'\n```');continue
        p=paragraph(doc,b)
        if b==AUTHOR:
            p.paragraph_format.space_after=Pt(2)
            for r in p.runs:rfont(r,size=11,bold=True)
        if b.startswith('NOVA keyboard-layout project'):
            for r in p.runs:rfont(r,'Liberation Sans',size=8.5)
        if b.startswith(('Keywords:','キーワード')):
            for r in p.runs:rfont(r,size=9)
        expanded.append(b)
    dest=out/f'nova_f5_pair_{lang}.docx';doc.save(dest)
    (out/f'nova_f5_pair_{lang}.md').write_text('\n\n'.join(expanded)+'\n',encoding='utf-8')
    return dest


def export_pdf(docx,out):
    exe=shutil.which('libreoffice') or shutil.which('soffice')
    if not exe:raise RuntimeError('LibreOffice is required for --pdf')
    with tempfile.TemporaryDirectory(prefix='nova-lo-') as tmp:
        profile=Path(tmp)/'profile';env={**os.environ,'HOME':tmp}
        cmd=[exe,'-env:UserInstallation='+profile.as_uri(),'--headless','--convert-to','pdf','--outdir',str(out),str(docx)]
        p=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=120)
        pdf=out/(docx.stem+'.pdf')
        if p.returncode or not pdf.is_file():raise RuntimeError(p.stdout+'\n'+p.stderr)
    return pdf


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--pdf',action='store_true');ap.add_argument('--out',type=Path,default=HERE)
    args=ap.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    bundle,lookup=checked_inputs();figs=make_figures(out/'assets')
    files=[]
    for lang in ('ja','en'):
        f=build(lang,bundle,lookup,figs,out);files.append(f)
        if args.pdf:files.append(export_pdf(f,out))
    audit={'author':AUTHOR,'source_commit':SNAPSHOT,'adopted_layout_id':F5,'display_name':'F5-Pair','decision':'Selected for GALACTYPE; integration is not asserted', 'actual_japanese_sentences':{'train':94,'validation':24,'test':24,'total':142}, 'kla_layouts':30,'kla_evaluation_groups':14,'score_cases_reproduced':1504,'outputs':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
    (out/'build_manifest.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(audit,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
