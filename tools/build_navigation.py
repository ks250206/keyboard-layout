#!/usr/bin/env python3
"""Build the current README and archive previous landing pages without deletion."""
from pathlib import Path
import csv, html
from build_kla_tables import render
ROOT=Path(__file__).resolve().parents[1]
DESC={'Pair':'日英・コード兼用。9ペアを左右隣接または同一キーに配置','Code':'コード比率を高くしたペア制約案','Shift':'全9ペアを同一キーの通常面／Shift面に統一','Grid':'括弧を2×2ブロック、残り5ペアを同一キーに配置'}
NAMES={'QWERTY':'QWERTY','大西（JIS近似）':'大西','F4-Balance':'F4-Balance-left','F4-Code':'F4-Code-free','F5-Pair':'F5-Balance-mixed','F5-Code':'F5-Code-mixed','F5-Shift':'F5-Balance-shift','F5-Grid':'F5-Balance-grid'}
def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')
def main():
    history=ROOT/'docs/history';history.mkdir(parents=True,exist_ok=True)
    for source,target in [(ROOT/'README.md',history/'README-before-f4-f5.md'),(ROOT/'docs/index.html',history/'index-v1.html')]:
        if source.exists() and not target.exists():target.write_bytes(source.read_bytes())
    with (ROOT/'results/v5/scores.csv').open(encoding='utf-8') as f:rows=list(csv.DictReader(f))
    lookup={(r['layout'],r['group']):r for r in rows}
    speed=['| 配列 | 日本語test | 長音符多め | 英語test | コードtest |','|:--|--:|--:|--:|--:|']
    for label,name in NAMES.items():
        speed.append('| '+label+' | '+' | '.join(f"{float(lookup[name,g]['gain_vs_qwerty_pct']):+.2f}%" for g in ('JP/test','JP/loanword','EN/test','CODE/test'))+' |')
    all_kla,csv_text=render()
    md='''# NOVA — 日本語・英語・コードのキーボード配列研究

**最新：F5 / 記号ペア制約 / 2026-10-31 / 研究用プロトタイプ**

数字1〜0を固定し、指×段×内外側とShift操作を考慮して探索した配列です。関連記号は左右隣接または同一キーの通常面／Shift面に揃えます。**速度は未校正の運動モデルによる推定で、実測WPM・学習しやすさは未検証です。**

[最新F5レポート](docs/f5/report.md) · [ブラウザ入口](docs/index.html) · [再現手順](docs/f5/reproduction.md) · [F4自由配置](docs/f4/report.md) · [実験履歴](docs/history/README.md)

## まず見る4案

| 候補 | 狙い | 通常面・Shift面 |
|:--|:--|:--|
'''
    for name,desc in DESC.items():md+=f'| **F5-{name}** | {desc} | [キー図](diagrams/f5/{name.lower()}.svg) |\n'
    md+='''
![F5-Pair：通常面とShift面](diagrams/f5/pair.svg)

上側がShift面、下側が通常面です。[4案一覧](diagrams/f5/overview.svg)・[全キーJSON](layouts/f5/full_layers.json)。QMK/VIAへ直接書き込める設定ではありません。

対象は `()` `[]` `{}` `<>` `;:` 単引用符／二重引用符、カンマ／ピリオド、ハイフン／アンダースコア、スラッシュ／バックスラッシュの9組です。括弧の開閉順序も固定します。Gridでは通常面`[ ]`とShift面`{ }`、通常面`( )`とShift面`< >`を2キーずつのブロックにします。

## 同じF4モデルでの推定速度

'''+ '\n'.join(speed)+'''

`+10%`はモデル上の速度1.10倍です。F5-Pairのコード追加所要時間は自由配置F4-Balanceから約0.15%増える一方、9ペアの位置規則をすべて満たします。記憶時間の改善を実測したわけではありません。KLA点とは別指標です。

## KLA：今回の一式

'''+all_kla+'''

## 再現と検算

```bash
python -m pip install -r requirements-v4.txt
python tools/check_f4.py
python tools/check_f5.py
python tools/check_readme.py
python -m unittest discover -s tests -p 'test_optimize_v[45].py' -v
```

F4の768ケース、F5の736ケースを凍結統計から再計算します。検算は一時コピーを使い保存CSVを上書きしません。**通常CIは探索を実行せず検算だけ**です。再探索は[別手順](docs/f5/reproduction.md)。F4は6,400万提案、F5は3,840万提案の焼きなまし法で、全配置の網羅や大域最適性の証明ではありません。

## 資料の整理

| 内容 | 入口 |
|:--|:--|
| 最新・過去の報告 | [docs](docs/README.md) |
| 全キー定義 | [layouts](layouts/README.md) |
| キーボード図 | [diagrams](diagrams/README.md) |
| コーパス・凍結統計 | [data](data/README.md) |
| スコア・探索ログ・係数感度 | [results](results/README.md) |
| 計算コード | [src](src/README.md) |

F4/F5を版別ディレクトリに分離し、旧成果は削除せず履歴に残しました。OSSの本文は同梱せず、出典と文字・連続文字の集計を保存しています。公開用の再探索ログには実行環境に依存する新しい所要時間が記録されますが、配列定義と数値結果は元の凍結成果物と照合しています。IME・補完・誤打鍵・疲労・学習時間・実機マッピングは別途検証が必要です。[LICENSE](LICENSE)
'''
    write(ROOT/'README.md',md);write(ROOT/'results/kla_all.csv',csv_text)
    write(history/'README.md','# 実験履歴\n\n[整理前README](README-before-f4-f5.md) · [旧ブラウザ比較](index-v1.html)\n\n[F3](../nova-f3-v3.md) · [指別モデル](../finger-row-v2.md) · [現代文試験](../modern-japanese-and-row-model.md) · [F4](../f4/report.md) · [F5](../f5/report.md)\n\n旧表はモデル・コーパスが異なる場合があります。直接比較には最新の共通条件表を使ってください。\n')
    contents={
      'docs':'[F5](f5/report.md) · [F4](f4/report.md) · [履歴](history/README.md) · [ブラウザ](index.html)',
      'layouts':'[F5全キー](f5/full_layers.json) · [F4全キー](f4/full_layers.json) · [旧30キー](layouts.json)',
      'diagrams':'[F5一覧](f5/overview.svg) · [F4一覧](f4/overview.svg) · [F3一覧](nova-f3-overview.svg)',
      'data':'[F5候補](v5/candidates.json) · [F4候補](v4/candidates.json) · [凍結生文字統計](v4/raw_ngrams.json.gz) · [元合成文](synthetic_three_domains.json)',
      'results':'[全30配列KLA](kla_all.csv) · [F5全指標](v5/scores.csv) · [F4全指標](v4/scores.csv) · [F5係数感度](v5/sensitivity.csv) · [F5探索ログ](v5/search/)',
      'src':'[F5最適化](optimize_v5.py) · [F4最適化](optimize_v4.py) · [F5表示](report_v5.py) · [F4表示](report_v4.py) · [再現手順](../docs/f5/reproduction.md)'}
    for folder,links in contents.items():write(ROOT/folder/'README.md',f'# {folder}\n\n'+links+'\n\n版ごとに保存し、旧ファイルは履歴として保持しています。\n')
    cards=''.join(f'<article><h2>F5-{name}</h2><p>{html.escape(desc)}</p><img alt="F5-{name}" src="../diagrams/f5/{name.lower()}.svg"></article>' for name,desc in DESC.items())
    page='''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NOVA F5</title><style>body{font:16px/1.8 system-ui,sans-serif;max-width:1150px;margin:40px auto;padding:0 24px;color:#22364d;background:#fafbfd}.grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}article{padding:16px;background:white;border:1px solid #d3dce7}img{width:100%}nav{margin:25px 0}a{color:#275780}@media(max-width:800px){.grid{grid-template-columns:1fr}}</style></head><body><h1>NOVA — 速さと、覚えやすい記号配置。</h1><p>最新F5：数字固定・関連記号のペア制約。未校正モデルによる研究用候補です。</p><nav><a href="f5/report.html">F5詳細</a> · <a href="f4/report.html">F4比較</a> · <a href="../README.md">全KLA値</a> · <a href="history/README.md">履歴</a></nav><main class="grid">'''+cards+'</main></body></html>'
    write(ROOT/'docs/index.html',page)
    print('Generated README, complete KLA CSV, version indexes and archived landing pages.')
if __name__=='__main__':main()
