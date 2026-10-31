#!/usr/bin/env python3
"""Frozen-layout sensitivity test; authored loanword-rich Japanese, not a population sample.

Run in ks250206/keyboard-layout: python src/benchmark_modern_jp.py
No layout optimization. KLA_approx is NOT output of the official KLA website.
Row surcharges are deliberately hypothetical, not empirically fitted milliseconds.
"""
from __future__ import annotations
import csv
import json
from collections import Counter
from pathlib import Path
import benchmark as b

ROOT = Path(__file__).resolve().parents[1]
ALPHABET = '\t\n' + ''.join(chr(i) for i in range(32, 127))

def aggregate(texts):
    result = {'n': 0}
    counters = {key: Counter() for key in ('unigrams', 'bigrams', 'first', 'last')}
    for text in texts:
        if any(c not in ALPHABET for c in text):
            raise ValueError('Non-ASCII romaji input must be reviewed, never silently discarded')
        one = b.document_counts(text, ALPHABET)
        result['n'] += one['n']
        for key in counters:
            for *indices, count in one[key]:
                counters[key][tuple(indices)] += count
    for key, counter in counters.items():
        result[key] = [list(indices) + [count] for indices, count in sorted(counter.items())]
    return result

def mix(left, right, weight):
    result = {'n': 100000}
    for key in ('unigrams', 'bigrams', 'first', 'last'):
        values = Counter()
        for counts, scale in ((left, 1-weight), (right, weight)):
            for *indices, count in counts[key]:
                values[tuple(indices)] += count * scale * result['n'] / counts['n']
        result[key] = [list(indices) + [count] for indices, count in sorted(values.items())]
    return result

def write_csv(path, rows):
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def evaluate(layouts, counts, label):
    baseline = b.metrics('QWERTY', layouts, counts, ALPHABET)['estimated_seconds']
    for name in layouts:
        result = b.metrics(name, layouts, counts, ALPHABET)
        pos, _ = b.chars_map(name, layouts, ALPHABET)
        result['corpus'] = label
        result['long_marks'] = sum(n for i, n in counts['unigrams'] if ALPHABET[i] == '-')
        result['long_pct'] = 100 * result['long_marks'] / counts['n']
        result['gain_vs_qwerty_pct'] = 100 * (baseline / result['estimated_seconds'] - 1)
        result['upper_pct'] = 100 * sum(n for i, n in counts['unigrams'] if 0 <= pos[i] < 10) / counts['n']
        result['lower_pct'] = 100 * sum(n for i, n in counts['unigrams'] if 20 <= pos[i] < 30) / counts['n']
        yield result

def main():
    layouts = b.read_layouts()
    old = json.loads((ROOT/'data/jp_en_corpora.json').read_text(encoding='utf-8'))['JP_romaji']
    package = json.loads((ROOT/'data/modern_jp_corpora.json').read_text(encoding='utf-8'))
    docs = package['documents']
    for d in docs:
        assert len(d['romaji']) == d['keystrokes'], d['name']
        assert d['romaji'].count('-') == d['text_ja'].count('ー') == d['reading_hiragana'].count('ー') == d['long_marks'], d['name']
    groups = {'original6': aggregate(old.values()), 'modern6': aggregate(d['romaji'] for d in docs)}
    assert (groups['original6']['n'], groups['modern6']['n']) == (2749, 2733)
    rows = [r for label, counts in groups.items() for r in evaluate(layouts, counts, label)]
    with (ROOT/'data/local_summary.csv').open(encoding='utf-8-sig', newline='') as f:
        published = {r['layout']: r for r in csv.DictReader(f) if r['task'] == 'JP'}
    for row in rows:
        if row['corpus'] != 'original6':
            continue
        for key in ('estimated_seconds', 'KLA_approx', 'distance_m', 'gain_vs_qwerty_pct'):
            assert abs(row[key]-float(published[row['layout']][key])) < 0.015, (row['layout'], key)
    out = ROOT/'results/modern_jp'
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out/'summary.csv', rows)
    details = [r for d in docs for r in evaluate(layouts, aggregate([d['romaji']]), d['name'])]
    write_csv(out/'by_document.csv', details)
    mixtures = []
    for w in (0, .25, .5, .75, 1):
        for row in evaluate(layouts, mix(groups['original6'], groups['modern6'], w), 'mixture'):
            row['modern_weight_per_keystroke'] = w
            mixtures.append(row)
    write_csv(out/'mixture_sensitivity.csv', mixtures)
    row_sensitivity = []
    for label, counts in groups.items():
        base_rows = list(evaluate(layouts, counts, label))
        for upper_ms, lower_ms in ((0, 0), (5, 10), (10, 20), (0, 20), (10, 0)):
            times = {r['layout']: r['estimated_seconds'] + counts['n']*(upper_ms*r['upper_pct']+lower_ms*r['lower_pct'])/100000 for r in base_rows}
            for name, time in times.items():
                row_sensitivity.append({'corpus':label, 'upper_ms':upper_ms, 'lower_ms':lower_ms, 'layout':name, 'estimated_seconds':time, 'gain_vs_qwerty_pct':100*(times['QWERTY']/time-1), 'rank':1+sum(t<time for t in times.values())})
    write_csv(out/'row_sensitivity.csv', row_sensitivity)
    for row in rows:
        print(f'{row["corpus"]:10} {row["layout"]:12} KLA={row["KLA_approx"]:6.2f} gain={row["gain_vs_qwerty_pct"]:+6.2f}% long={row["long_pct"]:.3f}%')
    print('PASS: frozen input lengths, preserved long marks, and original baseline; CSV:', out)

if __name__ == '__main__':
    main()
