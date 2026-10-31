# NOVA F5-Pair — bilingual research manuscript

**Version 1.0 · 2026-10-31 · ks250206**

NOVA F5-PairをGALACTYPEの採用配列に選定した研究経緯、モデル、探索、比較結果、限界を論文形式で整理した日本語版・英語版です。採用方針の記録であり、ゲームへの実装完了や、人間の入力速度・学習効果の実証を意味しません。

| Language | Editable manuscript | PDF | Plain text with tables |
|:--|:--|:--|:--|
| 日本語 | [DOCX](nova_f5_pair_ja.docx) | [PDF](nova_f5_pair_ja.pdf) | [Markdown](nova_f5_pair_ja.md) |
| English | [DOCX](nova_f5_pair_en.docx) | [PDF](nova_f5_pair_en.pdf) | [Markdown](nova_f5_pair_en.md) |

本文は要旨、緒言、データの由来、計算方法、結果、考察、限界、再現性、申告事項、参考文献で構成。付録には全30配列×14評価群の420個のKLA-main値と、採用配列の通常／Shift面の完全定義を収録しています。表は凍結したCSVから自動生成し、根拠ファイルのSHA-256を照合します。

## Audit correction

The corpus was designed from 144 source sentences, but the stored composite documents actually contain 142 distinct sentences. The final frozen split contains **94 training / 24 validation / 24 test sentences**, not the nominal 96/24/24 previously described. Character counts (5,104 / 1,331 / 1,301), corpus bytes, layouts, and numerical scores are unchanged. This correction is described in both manuscripts.

## Scope

This is a research manuscript, not a peer-reviewed publication. Motor-time coefficients are uncalibrated; KLA-main is a Patorjk-inspired approximation, not a direct official-site result. Human speed, memorability, fatigue, errors, IME behavior, and developer productivity have not been measured. Author affiliation, funding, and conflict-of-interest declarations remain to be completed before journal submission.

Source snapshot: [`ec596b262328ce66629c4f56874dffb364395e7d`](https://github.com/ks250206/keyboard-layout/tree/ec596b262328ce66629c4f56874dffb364395e7d).

## Rebuild

From repository root, with LibreOffice and Noto CJK, Liberation, and DejaVu fonts installed:

```bash
python -m pip install -r papers/nova_f5_pair/requirements.txt
python papers/nova_f5_pair/build.py --pdf
python papers/nova_f5_pair/verify.py
```

The build does not run simulated annealing or alter benchmark data. PDF pagination can vary slightly across LibreOffice/font versions. `build_manifest.json` records the source snapshot and output hashes. Manuscript source is in `source/`; `assets/` contains the two figures. No font files are redistributed.
