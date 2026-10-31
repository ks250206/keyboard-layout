#!/usr/bin/env python3
"""Publish links and a descriptive corpus-count correction; never alter scores."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
README=ROOT/'README.md'
text=README.read_text(encoding='utf-8')
marker='<!-- NOVA-PAPER:START -->'
block='''<!-- NOVA-PAPER:START -->
## 採用配列と論文

**タイピングゲームGALACTYPEの採用配列はNOVA F5-Pair（内部ID：F5-Balance-mixed）です。** 採用方針の記録であり、ゲーム実装済み・実測効果検証済みという意味ではありません。

| 論文 | DOCX | PDF |
|:--|:--|:--|
| 日本語 | [編集用](papers/nova_f5_pair/nova_f5_pair_ja.docx) | [閲覧用](papers/nova_f5_pair/nova_f5_pair_ja.pdf) |
| English | [Editable](papers/nova_f5_pair/nova_f5_pair_en.docx) | [Read](papers/nova_f5_pair/nova_f5_pair_en.pdf) |

[論文の概要・原稿・再生成手順](papers/nova_f5_pair/README.md)。本文と付録に研究経緯、運動モデル、Shift・記号ペア制約、探索、限界、全30配列×14評価群のKLA-main値をまとめています。

**件数の監査訂正：** 設計上の144元文のうち保存文書に存在するのは142文でした。最終統計は学習94文・検証24文・テスト24文です。従来の96/24/24は名目上の説明値であり、文字数・コーパス・配列・性能値は変更していません。
<!-- NOVA-PAPER:END -->
'''
if marker not in text:
    first,rest=text.split('\n',1)
    README.write_text(first+'\n\n'+block+'\n'+rest.lstrip('\n'),encoding='utf-8')
report=ROOT/'docs/f5/report.md'
s=report.read_text(encoding='utf-8')
flag='<!-- CORPUS-COUNT-AUDIT -->'
if flag not in s:
    first,rest=s.split('\n',1)
    note=flag+'\n> 2026-10-31 論文化時の監査訂正：元文設計144文のうち保存文書に存在するのは142文で、実使用の分割は学習94文・検証24文・テスト24文です。下記の従来記述にある144文／学習96文は名目値です。文字数と全数値結果は変更していません。詳細は[論文](../../papers/nova_f5_pair/README.md)を参照してください。\n'
    report.write_text(first+'\n\n'+note+'\n'+rest.lstrip('\n'),encoding='utf-8')
