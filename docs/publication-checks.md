# F4/F5 公開時の検証記録

2026-10-31。元の成果物を整理し、READMEへ全30配列・14評価群・420個のKLA-main近似値を追加した。

## 検証

GitHub上の[公開前検証](https://github.com/ks250206/keyboard-layout/actions/runs/41195506348)で、元の乱数シードによるF4/F5探索、限定Shift数字列の全列挙、結果照合、図・報告書・README生成、回帰テストを実行した。

- 生文字統計の展開後SHA256: `6a84de927b9644798e226b05b14d1cd71e301b270d572d34e6fc545ffe340eca`
- 保存gzipのSHA256: `311a34d5d6c1bc83bc56f83288617877beedee224edc1d06de4c676fc91d7b14`
- F4: 768ケース。F5: 736ケース。合計1,504ケースを元の成果物と照合した。
- 全候補の通常面・Shift面の配置を照合した。
- 22件のF4/F5回帰テストに成功した。
- READMEの420個のKLA値は結果CSVから自動生成し、CSVとの一致を検査した。

乱数シードを固定して再実行したため、探索ログの実行時間は公開環境のものに更新されている。配列定義とスコアの数値は元の凍結成果物と一致する。数値ダイジェストは、配列名・評価群順に整列し、CSV数値を小数5桁に正規化したもののSHA256。配列配置ダイジェストは通常面・Shift面をそのまま照合している。

```bash
python tools/check_publication_snapshot.py
python tools/check_f4.py
python tools/check_f5.py
python tools/check_readme.py
```

通常CIでは重い探索を繰り返さず、保存統計からの再計算とテストだけを実行する。実測WPMやPatorjkサイトでの直接採点を実施したという意味ではない。
