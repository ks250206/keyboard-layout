#!/usr/bin/env python3
"""Verify numerical publication provenance, independent of runtime metadata."""
from pathlib import Path
import csv,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode()).hexdigest()
expected=json.loads((ROOT/'data/publication_snapshot.json').read_text())
for version in (4,5):
    with (ROOT/f'results/v{version}/scores.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
    normalized=[{k:(value if k in ('layout','group') else f'{float(value):.5f}') for k,value in row.items()} for row in sorted(rows,key=lambda r:(r['layout'],r['group']))]
    winners=json.loads((ROOT/f'data/v{version}/candidates.json').read_text())['winners']
    maps={k:{field:d[field] for field in ('base','shift')} for k,d in winners.items()}
    actual={'cases':len(rows),'scores_sha256':digest(normalized),'maps_sha256':digest(maps)}
    print('F'+str(version),actual)
    if actual!=expected[str(version)]:raise AssertionError(f'F{version} differs from the frozen publication')
print('PASS: 1504 score cases and all winning keymaps match the original publication snapshot.')
