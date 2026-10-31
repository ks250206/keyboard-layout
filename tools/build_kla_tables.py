#!/usr/bin/env python3
"""Render all frozen F4/F5 KLA scores, rejecting divergent shared cases."""
from __future__ import annotations
import csv
import io
import math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MARKER_START = '<!-- KLA-ALL:START -->'
MARKER_END = '<!-- KLA-ALL:END -->'
ALIASES = {
    'F4-JP-free': 'F4-JP', 'F4-Balance-left': 'F4-Balance',
    'F4-Code-free': 'F4-Code', 'F4-Balance-right': 'F4-Balance-R',
    'F5-Balance-mixed': 'F5-Pair', 'F5-Code-mixed': 'F5-Code',
    'F5-Balance-shift': 'F5-Shift', 'F5-Balance-grid': 'F5-Grid',
    'F5-JP-mixed': 'F5-JP', 'F5-Code-grid': 'F5-Grid-Code',
}

def load_scores():
    rows, names = {}, []
    for version in (4, 5):
        path = ROOT / f'results/v{version}/scores.csv'
        with path.open(encoding='utf-8', newline='') as f:
            for row in csv.DictReader(f):
                key = row['layout'], row['group']
                if row['layout'] not in names:
                    names.append(row['layout'])
                if key in rows:
                    for field in ('KLA_main_approx', 'chars', 'ms_per_char', 'gain_vs_qwerty_pct'):
                        if not math.isclose(float(row[field]), float(rows[key][field]), rel_tol=1e-11, abs_tol=1e-8):
                            raise ValueError(f'F4/F5 conflict: {key}, {field}')
                rows[key] = row
    return rows, names

def matrix(rows, names, groups, headings):
    output = ['| 配列 | ' + ' | '.join(headings) + ' |', '|:--|' + '--:|' * len(groups)]
    for name in names:
        label = ALIASES.get(name, name)
        if label != name:
            label += ' `' + name + '`'
        values = [f"{float(rows[name, g]['KLA_main_approx']):.2f}" for g in groups]
        output.append('| ' + label + ' | ' + ' | '.join(values) + ' |')
    return '\n'.join(output)

def csv_text(rows, names, groups):
    out = io.StringIO(newline='')
    writer = csv.writer(out, lineterminator='\n')
    writer.writerow(['layout', 'display_name', *groups])
    for name in names:
        writer.writerow([name, ALIASES.get(name, name), *[rows[name, g]['KLA_main_approx'] for g in groups]])
    return out.getvalue()

def render():
    rows, names = load_scores()
    overall = ['JP/test', 'JP/loanword', 'EN/test', 'CODE/test']
    domains = ['生活文/test', '業務文/test', '技術文/test']
    code = [f'CODE/{lang}/test' for lang in ('Python', 'JavaScript', 'TypeScript', 'Go', 'C', 'C++', 'Java')]
    groups = overall + domains + code
    counts = '、'.join(f"{g}={int(float(rows['QWERTY', g]['chars'])):,}文字" for g in overall)
    content = f'''{MARKER_START}
### 全30配列のKLA-main近似（F4・F5を同一条件で再計算）

F4の24配列とF5の23配列を、共通配列の重複を除いて**30配列**として掲載します。F4の記号だけを変えた対照実験、長音符の左右制約、F5-JP／F5-Grid-Codeも省略していません。表示名と内部IDを併記し、結果CSVとの対応を固定しています。

評価文字数：{counts}。日本語testは文単位で分離した24文、長音符多めは既出の6診断課題、英文は2課題、コードは7言語の別ファイルです。すでに結果を見たデータを含み、新たな盲検評価ではありません。

{matrix(rows, names, overall, ['日本語test', '長音符多め', '英語test', 'コードtest'])}

<details><summary><strong>日本語：生活文・業務文・技術文の内訳（全30配列）</strong></summary>

{matrix(rows, names, domains, ['生活文test', '業務文test', '技術文test'])}

</details>

<details><summary><strong>OSS：7言語別KLA-main近似（全30配列）</strong></summary>

{matrix(rows, names, code, ['Python', 'JavaScript', 'TypeScript', 'Go', 'C', 'C++', 'Java'])}

</details>

コード集計は言語ごとのKLA点の単純平均ではなく、全対象ファイルの文字・連続文字統計から再計算しています。今回のF4/F5には旧実験のRustを合算していません。

**Patorjk公式サイトを直接実行したスコアではありません。** KLA-mainは主文字キーの移動距離33%、指配分33%、異鍵同指17%、同手連打17%の近似です。Shift小指は運動時間モデルに含み、KLA-mainには含めません。指別の仮の時間コストや記憶しやすさもKLA点へ加算していません。速度改善率とは別指標です。旧配列は同じJIS近似に載せ替えた参照版です。

[全30配列・14評価群のKLA値CSV](results/kla_all.csv) · [F4の全指標](results/v4/scores.csv) · [F5の全指標](results/v5/scores.csv)。各表は保存CSVから自動生成し、`python tools/check_readme.py`で一致を検査できます。
{MARKER_END}'''
    return content, csv_text(rows, names, groups)

if __name__ == '__main__':
    text, data = render()
    print(text)
