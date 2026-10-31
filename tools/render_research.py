#!/usr/bin/env python3
"""Render versioned reports and exact key legends from frozen F4/F5 artifacts."""
from __future__ import annotations
import csv, hashlib, html, json, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import optimize_v4 as v
SELECTED={4:{'F4-JP':'F4-JP-free','F4-Balance':'F4-Balance-left','F4-Code':'F4-Code-free','F4-Balance-R':'F4-Balance-right'},5:{'F5-Pair':'F5-Balance-mixed','F5-Code':'F5-Code-mixed','F5-Shift':'F5-Balance-shift','F5-Grid':'F5-Balance-grid'}}
EXTRA_NAMES={'F5-JP-mixed':'F5-JP','F5-Code-grid':'F5-Grid-Code'}
PAIRS=('()','[]','{}','<>',';:', '\'"', ',.', '-_', '/\\')
COLORS=('#e0ebff','#dff2e7','#e8e0fa','#fff0ce','#f8e2e7','#e2f1f7','#f0e8db','#e5f4d4','#eceaf6')
GROUPS=('JP/test','JP/loanword','EN/test','CODE/test')
HEADINGS=('日本語test','長音符多め','英語test','コードtest')
LANGUAGES=('Python','JavaScript','TypeScript','Go','C','C++','Java')
NOTE='KLA-mainはPatorjkの公開式を参考にした主文字キーの近似値です。公式サイトで直接採点した値ではなく、Shift小指の運動は別の時間モデルに含めています。実測WPM・学習時間・開発生産性の予測ではありません。'
def read_csv(path):
    with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')
def table(headers,rows):
    esc=lambda x:str(x).replace('|','\\|').replace('\n',' ')
    return '| '+' | '.join(map(esc,headers))+' |\n|'+ '|'.join([':--']+['--:']*(len(headers)-1))+'|\n'+''.join('| '+' | '.join(map(esc,row))+' |\n' for row in rows)
def html_table(headers,rows):
    row=lambda cells,tag:'<tr>'+''.join(f'<{tag}>{html.escape(str(x))}</{tag}>' for x in cells)+'</tr>'
    return '<div class="scroll"><table><thead>'+row(headers,'th')+'</thead><tbody>'+''.join(row(c,'td') for c in rows)+'</tbody></table></div>'
def diagram(label,b,s):
    out=['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="460" viewBox="0 0 1100 460" role="img">',f'<title>{html.escape(label)} base and Shift keymap</title>', '<rect width="1100" height="460" fill="#fafbfd"/>',f'<text x="30" y="39" font-family="Arial,sans-serif" font-size="27" font-weight="700">{html.escape(label)}</text>', '<text x="30" y="65" font-family="Arial,sans-serif" font-size="14">Upper legend: Shift  |  Lower legend: base  |  digits 1-0 fixed  |  dot: no output</text>']
    offset=0
    for row,length in enumerate(v.ROW_LENGTHS):
        for col in range(length):
            k=offset+col;x=30+75*col+[0,37.5,54,72.75][row];y=85+76*row
            base=v.ALPH[b[k]] if b[k]>=0 else '¥';shift=v.ALPH[s[k]] if s[k]>=0 else '·'
            fill='#ffffff'
            for chars,color in zip(PAIRS,COLORS):
                if base in chars or shift in chars:fill=color;break
            if base in 'aeiou':fill='#d9f0f3'
            stroke=3 if base=='-' else 1.3
            out.extend([f'<rect x="{x}" y="{y}" width="68" height="66" rx="7" fill="{fill}" stroke="#42546b" stroke-width="{stroke}"/>',f'<text x="{x+9}" y="{y+22}" font-family="monospace" font-size="19" fill="#53667d">{html.escape(shift)}</text>',f'<text x="{x+34}" y="{y+53}" text-anchor="middle" font-family="monospace" font-size="25" font-weight="bold" fill="#182b42">{html.escape(base)}</text>'])
        offset+=length
    out.append('<text x="30" y="417" font-family="Arial,sans-serif" font-size="14">Related symbols share colors. Vowels are cyan. This is a research mapping, not tested firmware.</text>')
    out.append('<text x="30" y="439" font-family="Arial,sans-serif" font-size="12">Approximate JIS geometry / fixed digit row / uncalibrated motor-time coefficients</text></svg>')
    return '\n'.join(out)
def main(version):
    version=int(version)
    if version not in (4,5):raise ValueError('version must be 4 or 5')
    folder=ROOT/f'results/v{version}';docs=ROOT/f'docs/f{version}'
    winners=json.loads((ROOT/f'data/v{version}/candidates.json').read_text())['winners']
    rows=read_csv(folder/'scores.csv');lookup={(r['layout'],r['group']):r for r in rows}
    names=list(dict.fromkeys(r['layout'] for r in rows));labels={n:l for l,n in SELECTED[version].items()};labels.update(EXTRA_NAMES)
    refs=v.references();maps={n:(np.array(d['base'],np.int32),np.array(d['shift'],np.int32)) for n,d in winners.items()}
    if version==5:
        for n,d in json.loads((ROOT/'data/v4/candidates.json').read_text())['winners'].items():maps.setdefault(n,(np.array(d['base'],np.int32),np.array(d['shift'],np.int32)))
    maps={**refs,**maps};export={'schema_version':1,'version':version,'status':'research mappings, not tested QMK/VIA firmware','digits_fixed':True,'uppercase_follows_lowercase':True,'layouts':{}}
    figures={}
    for name,entry in winners.items():
        b,s=maps[name];label=labels.get(name,name);slug=label.lower().removeprefix(f'f{version}-')
        svg=diagram(label,b,s);figures[name]=svg
        write(ROOT/f'diagrams/f{version}/{slug}.svg',svg)
        export['layouts'][label]=[{'physical_key':v.KEY[k],'base':v.ALPH[b[k]] if b[k]>=0 else '¥','shift':v.ALPH[s[k]] if s[k]>=0 else None,'finger':v.FNAME[v.FI[k]],'coordinate_pitch':v.CO[k].tolist()} for k in range(48)]
    write(ROOT/f'layouts/f{version}/full_layers.json',json.dumps(export,ensure_ascii=False,indent=2)+'\n')
    overview=['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="1840" viewBox="0 0 1100 1840">']
    for i,name in enumerate(SELECTED[version].values()):
        svg=figures[name];overview.append(f'<g transform="translate(0,{460*i})">'+svg[svg.index('>')+1:svg.rindex('</svg>')]+'</g>')
    overview.append('</svg>');overview='\n'.join(overview);write(ROOT/f'diagrams/f{version}/overview.svg',overview)
    def numeric(field,groups=GROUPS,percentage=False):
        return [[labels.get(n,n)]+[f"{float(lookup[n,g][field]):+.2f}%" if percentage else f"{float(lookup[n,g][field]):.2f}" for g in groups] for n in names]
    bundle=v.read_data();sensitivity=[]
    for rs,ls,ss in [(0,0,.5),(.5,.5,.5),(1,1,0),(1,1,1),(1,1,2),(2,2,2)]:
        for group in GROUPS:
            c=bundle['groups'][group];q=v.metrics(*refs['QWERTY'],c,rs,ls,ss)
            for name in names:
                m=v.metrics(*maps[name],c,rs,ls,ss)
                sensitivity.append({'layout':name,'group':group,'row_scale':rs,'splay_scale':ls,'shift_scale':ss,'gain_vs_qwerty_pct':100*(q['seconds']/m['seconds']-1),'seconds':m['seconds']})
    v.csv_write(folder/'sensitivity.csv',sensitivity)
    v.csv_write(folder/'summary.csv',[r for r in rows if r['group'] in GROUPS])
    runs=[]
    for path in sorted((folder/'search').glob('*_runs.csv')):runs+=read_csv(path)
    valid_col='valid' if version==4 else 'valid_evaluations'
    totals={key:sum(int(r[key]) for r in runs) for key in ('proposals',valid_col,'polish_evaluations')}
    runstats=[]
    for job in sorted(set(r['job'] for r in runs)):
        scores=[float(r['objective_ms']) for r in runs if r['job']==job]
        runstats.append({'job':job,'restarts':len(scores),'best':min(scores),'median':float(np.median(scores)),'worst':max(scores)})
    v.csv_write(folder/'restart_summary.csv',runstats)
    provenance={'source_base_commit':'748bdb47a3239c4d0a0c66214a639377ee17078c','data_sha256':hashlib.sha256((ROOT/'data/v4/raw_ngrams.json.gz').read_bytes()).hexdigest(),'cases':len(rows),'layouts':len(names),'search_totals':totals,'runtime_note':'Logs were reproduced with frozen seeds during publication; elapsed wall time is environment-dependent. Numerical snapshots were independently compared.'}
    write(folder/'publication_provenance.json',json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
    intro=('数字を固定した通常面・Shift面の自由配置。長音符の左右制約、Shift記号だけ、記号面だけの対照実験と限定全列挙を含みます。' if version==4 else '記号の9ペアを同段・同面の左右隣接、または同一キーの通常面→Shift面に揃える制約を導入しました。記憶の改善を仮の時間短縮として加算していません。')
    method=f"確率的焼きなましの提案{totals['proposals']:,}回、制約を満たして採点{totals[valid_col]:,}回、局所改善{totals['polish_evaluations']:,}回。重複状態を含み、全配列の網羅・大域最適性の証明ではありません。候補は訓練目的関数で選び、各検証表は固定配置を再評価しています。"
    corpus='日本語は合成144文をトピック別に文単位分離（train 96文5,104文字、validation 24文1,331文字、test 24文1,301文字）。英語train 2,412文字／test 1,208文字。OSSはPython・JavaScript・TypeScript・Go・C・C++・Javaの別ファイル（train 80,357文字／test 76,876文字）。長音符多め6課題2,733文字など、既に結果を見た診断用データを含むため、新たな盲検評価ではありません。'
    model='基準118ms、ホームからの距離19ms/キー間隔、戻り9ms/キー間隔、同手異指8ms。同指異鍵は36+56*log2(1+d)+6*d ms。指×段×内外側と数字段の費用、反対側小指によるShift開始・継続・切替・競合を加えます。係数は実測校正前の仮定値です。探索用の負担正則化項は、報告する運動時間の値には含めません。'
    heading=['配列',*HEADINGS]
    sections=[('推定速度増加率・対QWERTY',heading,numeric('gain_vs_qwerty_pct',percentage=True)),('KLA-main近似・全候補',heading,numeric('KLA_main_approx')),('日本語の分野別KLA-main',['配列','生活文','業務文','技術文'],numeric('KLA_main_approx',[d+'/test' for d in v.DOMAINS])),('OSS言語別KLA-main',['配列',*LANGUAGES],numeric('KLA_main_approx',[f'CODE/{lang}/test' for lang in LANGUAGES]))]
    md=f'# NOVA F{version}：配列図・速度・KLA近似\n\n2026-10-31 / 研究用プロトタイプ\n\n{intro}\n\n**{NOTE}**\n\n[最新README](../../README.md) · [再現手順](reproduction.md) · [全指標CSV](../../results/v{version}/scores.csv)\n\n![通常面とShift面の4案](../../diagrams/f{version}/overview.svg)\n\n'
    body=f'<h1>NOVA F{version}</h1><p>{html.escape(intro)}</p><p class="note">{html.escape(NOTE)}</p><nav><a href="../../README.md">README</a> · <a href="reproduction.md">再現手順</a> · <a href="../../results/v{version}/scores.csv">全指標CSV</a></nav>'+overview
    for title,headers,values in sections:
        md+='## '+title+'\n\n'+table(headers,values)+'\n';body+='<h2>'+html.escape(title)+'</h2>'+html_table(headers,values)
    details=[('探索',method),('コーパスと検証の範囲',corpus),('モデル',model),('解釈の注意','KLA集計は言語別点数の単純平均ではなく、合算した文字・連続文字統計から算出。F4/F5は同じJIS近似への適応版として既存配列を評価しています。誤打鍵・疲労・IME・補完・ショートカット・学習時間は未計測です。')]
    if version==4:details.append(('長音符と全列挙','母音→長音符→子音は、母音が左・子音が右の場合、長音符をどちらに置いても交互遷移が1回となり得ます。長音符の左右だけでなく前後の指競合を評価します。QWERTY-JISのShift+1〜0だけは10!=3,628,800通りを全列挙。他の条件は確率探索です。'))
    else:details.append(('記号の規則','対象は () [] {} <> ;: 単引用符/二重引用符 ,. -_ /バックスラッシュ の9組。Pair/Code/JPは隣接または同一キー、Shiftは全組同一キー、Gridは通常[]・Shift{}と通常()・Shift<>の2×2ブロック、その他5組を同一キーにします。'))
    for title,text in details:md+='## '+title+'\n\n'+text+'\n\n';body+='<h2>'+html.escape(title)+'</h2><p>'+html.escape(text)+'</p>'
    md+='[係数感度](../../results/v'+str(version)+'/sensitivity.csv) · [探索ログ](../../results/v'+str(version)+'/search/) · [全キーJSON](../../layouts/f'+str(version)+'/full_layers.json)\n'
    write(docs/'report.md',md)
    css='body{font:16px/1.8 system-ui,sans-serif;max-width:1180px;margin:40px auto;padding:0 24px;color:#203249;background:#fafbfd}h1{font-size:2.5rem}h2{margin-top:45px}svg{width:100%;height:auto}.scroll{overflow:auto}table{border-collapse:collapse;white-space:nowrap;font-size:14px}th,td{padding:8px 13px;border-bottom:1px solid #cdd5df;text-align:right}th:first-child,td:first-child{text-align:left}.note{padding:18px;background:#e6eef6}a{color:#275780}'
    write(docs/'report.html','<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NOVA F'+str(version)+'</title><style>'+css+'</style></head><body>'+body+'</body></html>')
    commands=f'python -m pip install -r requirements-v4.txt\npython tools/check_f{version}.py\npython tools/check_readme.py\npython -m unittest discover -s tests -p "test_optimize_v[45].py" -v'
    reproduce=f'# F{version} 再現手順\n\nPython 3.11以降。保存統計による検算は依存導入後ネット不要です。\n\n```bash\n{commands}\n```\n\n検算は一時コピーを使い凍結CSVを上書きしません。再探索は別途実行してください。\n\n```bash\npython src/optimize_v{version}.py --search --rounds 64 --iterations 100000\n'
    reproduce+=('python src/optimize_v4.py --enumerate-number-row\npython src/optimize_v4.py --report\n' if version==4 else 'python src/optimize_v5.py --evaluate\n')
    reproduce+=f'python src/report_v{version}.py\npython tools/build_navigation.py\n```\n\n再探索は保存結果を更新します。元の結果を残す場合は作業ブランチを分けてください。通常CIは探索を実行せず検算のみです。'
    write(docs/'reproduction.md',reproduce)
    print(f'Rendered F{version}: {len(winners)} layouts, {len(rows)} score cases, figures and reports.')
if __name__=='__main__':main(sys.argv[1])
