#!/usr/bin/env python3
"""Generate NOVA F3 report and README snippet from CSV/JSON (deterministic)."""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs';OUT.mkdir(exist_ok=True)
ORDER=['QWERTY','Dvorak','Colemak','Workman','大西','Nova-JP','Nova-Hybrid','Nova-Dev','Nova-Ctrl','Nova-F3-JP','Nova-F3-Balance','Nova-F3-Code','Nova-F3-Ctrl']
NEW=ORDER[-4:]
with (ROOT/'results/v3_scores.csv').open() as f:S=list(csv.DictReader(f))
with (ROOT/'results/v3_sensitivity.csv').open() as f:X=list(csv.DictReader(f))
with (ROOT/'results/v3_mixtures.csv').open() as f:M=list(csv.DictReader(f))
layouts=json.loads((ROOT/'data/v3_candidates.json').read_text())['optimized']
lookup={(r['dataset'],r['layout']):r for r in S}

def tab(cols,metric='speed_gain_pct',names=ORDER):
    z=['| 配列 | '+' | '.join(cols)+' |','|:--|'+'|'.join(['--:']*len(cols))+'|']
    for name in names:
        values=[]
        for c in cols:
            v=float(lookup[(c,name)][metric]);values.append(f'{v:+.2f}%' if metric=='speed_gain_pct' else f'{v:.2f}')
        z.append(f'| {"**"+name+"**" if name in NEW else name} | '+' | '.join(values)+' |')
    return '\n'.join(z)

keys=['| 候補 | 上段 | 中段 | 下段 | 最適化の用途 |','|:--|:--|:--|:--|:--|']
caption={'Nova-F3-JP':'日本語優先','Nova-F3-Balance':'日英・コード兼用','Nova-F3-Code':'開発優先','Nova-F3-Ctrl':'Z/X/C/Vを維持'}
for name,entry in layouts.items():
    keys.append('| **'+name+'** | '+' | '.join('`'+r.upper()+'`' for r in entry['rows'])+' | '+caption[name]+' |')
keys='\n'.join(keys)
held_cols=['JP_original6','JP_loanword6','EN/test','CODE/test']
held=tab(held_cols)
kla=tab(['JP_loanword6','EN/test','CODE/test'],'KLA_approx')
code=['| 未使用OSS・言語 | 大西 | Nova-Hybrid | F3-Balance | F3-Code | F3-Ctrl |','|:--|--:|--:|--:|--:|--:|']
for lang in ['Python','JavaScript','TypeScript','Go','C','C++','Java']:
    cat=f'CODE/{lang}/test';vals=[float(lookup[(cat,n)]['speed_gain_pct']) for n in ['大西','Nova-Hybrid','Nova-F3-Balance','Nova-F3-Code','Nova-F3-Ctrl']]
    code.append('| '+lang+' | '+' | '.join(f'{v:+.2f}%' for v in vals)+' |')
code='\n'.join(code)
profile=['| 配列 | 日本語中心 | 日英兼用 | 開発中心 | カタカナ多め |','|:--|--:|--:|--:|--:|']
for name in ORDER:
    vals=[float(next(r['speed_gain_pct'] for r in M if r['layout']==name and r['profile']==p)) for p in ['JP_heavy','Bilingual','Developer','JP_loanword_heavy']]
    profile.append('| '+name+' | '+' | '.join(f'{v:+.2f}%' for v in vals)+' |')
profile='\n'.join(profile)
sens=['| 段・横ペナルティ倍率 | F3-JP：カタカナ多め | F3-Code：英語 | F3-Code：コード |','|:--|--:|--:|--:|']
for factor in [0,.5,1,1.5,2,3]:
    vals=[]
    for cat,name in [('JP_loanword6','Nova-F3-JP'),('EN/test','Nova-F3-Code'),('CODE/test','Nova-F3-Code')]:
        vals.append(float(next(r['speed_gain_pct'] for r in X if r['dataset']==cat and r['layout']==name and float(r['row_factor'])==factor and float(r['splay_factor'])==factor)))
    sens.append(f'| ×{factor:g} | '+' | '.join(f'{v:+.2f}%' for v in vals)+' |')
sens='\n'.join(sens)

report=f'''# NOVA F3：指×段×内外側コストを考慮した新キーボード4配列

> 2026-10-31。**研究用のモデル推定であり、実測WPMや疲労の測定ではありません。** KLA型近似スコアはPatorjk公式サイトで直接採点したものではなく、既存の公開式を参考に再実装した値です。局所的な焼きなまし法による最適化であり大域最適性は保証しません。

![4つのキー配置](../diagrams/nova-f3-overview.svg)

## 1. 4つの候補と用途

{keys}

各案は中央の3段×10キーに26英字と4記号（`- . , ;`）を配置します。周辺の数字、`/`, `[]`, `=`, Shift等は従来の単純なUS型座標を仮定し、JISキーボード実機には未対応です。**QMK/VIA/OSへ直ちに適用できるキーマップではありません。** F3-Ctrlは、`ZXCV`の4物理キーだけをQWERTYと同じ下段左端に固定しています。

最適化重み（すべて打鍵数で正規化）：日本語優先 `[生活30, 業務30, 技術25, 英語8, コード7]%`；日英兼用 `[18,18,19,23,22]%`；開発優先 `[11,11,13,20,45]%`；ショートカット `[16,18,21,20,25]%`。数値は利用実態を実測した重みではなく、用途別に設定した設計条件です。

## 2. 運動モデル（前回のv2から変更なし）

基準118 ms/打鍵と前後キーの移動時間（異なる指の距離項、同指での直接移動）は維持。そのうえで、仮定したキー姿勢コストを加算します。

| 指 | 上段追加 | 下段追加 |
|:--|--:|--:|
| 左小指 | +18 ms | 0 |
| 左薬指 | 0 | +18 ms |
| 左中指 | 0 | +12 ms |
| 右中指 | 0 | +9 ms |
| 右薬指 | 0 | +9 ms |
| 右小指 | +7 ms | 0 |

さらに人差し指の内側+7 ms、小指の外側+10 ms、その他の指の内側+5 ms・外側+6 ms、同指で上段↔下段+7 ms、同指の内向き遷移+4 ms・外向き遷移+6 ms、数字列+12 msを仮定。内外判定はホームから0.40キー間隔をしきい値としています。**すべて実測ではなく、主観的な打ちにくさの仮説値**です。旧KLA型スコアにこれらの追加コストは反映していません。

最適化目的関数は、v2推定時間に加えて、負荷集中、左右の偏り、ホーム段使用率、同指異鍵連打への小さな正則化を加えています。実装：[モデル](../src/benchmark_finger_rows.py)、[最適化](../src/optimize_v3.py)。

## 3. 探索データと独立性

- **学習日本語**：従来作成した生活・業務・技術の合成文章で、各ドメインのdevelopmentグループ。144文を48文書に再構成したもので、**holdout側の合成文書にも元の同じ文が出現**します。よって合成文書のholdoutは完全な独立検証ではありません。
- **学習英語**：6つの自作英文から日常・研究・ビジネス・歴史の4課題。検証は別の2課題Software/Literature（1,208打鍵）。
- **学習OSS**：Python, JavaScript, TypeScript, Go, C, C++, Javaの各2ソース断片のうち先頭を学習に使用。検証は各言語で**別のソースファイル**を使用（計76,876打鍵）。同一プロジェクトの別ファイルも含まれるので、別プロジェクトへの汎化を保証しません。
- **別原稿での日本語検証**：元の6課題（2,749打鍵）およびカタカナ語を意図的に増やした6課題（2,733打鍵）を学習から除外。いずれも人工的な自作文で、現代日本語のランダムサンプリングではありません。
- **ローマ字規則**：従来に合わせ`si/ti/tu/hu/zi`、長音符`ー`は`-`。IME変換や誤打鍵は未考慮。

コードの元ファイルは著作権のため再配布せず、**文字・連続文字の統計とSHA-256**だけを[学習／検証nグラム](../data/v3_ngrams.json)に保存してあります。訓練と検証に使った集計値は、ネット接続なしでも再採点できます。ただし別のOSSファイルを探索して検証したわけではありません。

## 4. 既存9配列と新4配列の比較

QWERTYに対する**推定入力速度増加率**（`100×(T_QWERTY/T_layout−1)`）。**1〜2%ポイントの差を実測上の有意差とはみなしません。**

### 未使用の日本語原稿、英文、OSSコード

{held}

### 日本語合成文書の別分割（元文の重複あり）

{tab(['生活文/holdout','業務文/holdout','技術文/holdout'])}

### 同じ未使用データでのKLA型近似スコア（0〜100点）

{kla}

KLA型スコアと時間モデルは別の指標です。カタカナ多めの別原稿では、**大西のKLA型73.22点がF3-JPの72.84点より高い**一方、未校正の速度モデルではF3-JPが優位になります。

### OSSコードの言語別・別ファイル評価

{code}

## 5. モデル係数への感度

指×段、内外側の追加ペナルティを**両方同じ倍率**で0〜3倍に変え、配列は固定したまま再採点しています。旧距離項は固定。

{sens}

倍数が0なら**旧モデルと同じ**です。旧日本語6課題では、この条件でF3-JPの+17.09%は旧Nova-JPの+17.25%を下回ります。つまり新案の優劣には本人の指の苦手さの仮定が効いています。

## 6. 日本語・英語・コードの利用割合を変える

一つの用途だけが長文で重くならないよう、各カテゴリの**1打鍵あたりの時間**を重み付けしています（混合比率は想定値）。

{profile}

日本語中心は生活27/業務27/技術26/英語10/コード10%、日英兼用は生活15/業務15/技術20/英語25/コード25%、開発中心は生活10/業務10/技術15/英語20/コード45%、カタカナ多めは別原稿60/生活10/業務10/技術10/英語5/コード5%です。

## 7. 再現手順

```bash
python -m pip install -r requirements-optimizer.txt
python src/optimize_v3.py --check               # 保存した統計から13配列を再採点
python src/render_v3_keyboards.py               # 配列SVG図5枚を再生成
python src/render_v3_report.py                  # このレポートとREADME節を更新
python -m unittest discover -s tests -p 'test_optimize_v3.py' -v
python src/optimize_v3.py --optimize --rounds 28 --iters 15000  # 再探索（決定的seed）
```

OSS原本からの統計再構築には、`src/optimize_v3.py --build-data`を使用しますが、元OSSの指定パス・バージョンがローカルに存在する環境に限定されます。`data/v3_ngrams.json`に全統計・出典のSHA-256・抽出範囲を含めています。元ファイルのテキスト自体はコミットしていません。

**未解決事項**：JIS/USの記号・Shift配置、IME変換操作、ショートカットやコーディング補完、長時間疲労、誤打鍵率、ブラインドタッチの習熟コスト、個人の実測IKIによる係数フィット。現段階で確定配列とはしません。
'''

snippet=f'''## NOVA F3：指×段×内外側コストによる新配列4案

旧モデルで作った配列に加え、左右の指ごとの段移動と内外側の動きに仮の追加コストを置き、**4案を再最適化**しました。係数は個人の打鍵感覚を数値化したもので、実測WPMではありません。

![NOVA F3 layout overview](diagrams/nova-f3-overview.svg)

{keys}

### 未使用の日本語・英文・OSSによる検証（QWERTY比の推定速度増加率）

{held}

### KLA型近似スコア（同じ検証データ、公式サイト直接実行ではない）

{kla}

**データ上の制約**：合成日本語文書の訓練／holdout間には元文の重複があります。上表は探索に不使用の別の自作日本語6＋6課題、英文2課題、OSSの別ファイル7言語での評価です。詳細な配列図、係数、学習と検証の分割、言語別OSS評価、感度分析、再現コードは[研究レポート](docs/nova-f3-v3.md)に記載。

'''
(OUT/'nova-f3-v3.md').write_text(report,encoding='utf-8')
(OUT/'nova-f3-readme-section.md').write_text(snippet,encoding='utf-8')
print('Generated report',len(report),'README section',len(snippet))
