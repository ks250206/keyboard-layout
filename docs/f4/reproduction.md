# F4 再現手順

Python 3.11以降。保存統計による検算は依存導入後ネット不要です。

```bash
python -m pip install -r requirements-v4.txt
python tools/check_f4.py
python tools/check_readme.py
python -m unittest discover -s tests -p "test_optimize_v[45].py" -v
```

検算は一時コピーを使い凍結CSVを上書きしません。再探索は別途実行してください。

```bash
python src/optimize_v4.py --search --rounds 64 --iterations 100000
python src/optimize_v4.py --enumerate-number-row
python src/optimize_v4.py --report
python src/report_v4.py
python tools/build_navigation.py
```

再探索は保存結果を更新します。元の結果を残す場合は作業ブランチを分けてください。通常CIは探索を実行せず検算のみです。